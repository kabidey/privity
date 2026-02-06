"""
Day-End Revenue Report Service
Sends revenue summary at 6 PM IST to users and their managers via email and WhatsApp
Follows full hierarchy for consolidated reports
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import uuid
import asyncio

from database import db


async def get_user_hierarchy(user_id: str) -> List[Dict]:
    """
    Get the full hierarchy above a user (all managers up to PE Desk)
    Returns list of managers from immediate manager to top
    """
    hierarchy = []
    current_user_id = user_id
    visited = set()  # Prevent infinite loops
    
    while current_user_id and current_user_id not in visited:
        visited.add(current_user_id)
        user = await db.users.find_one(
            {"id": current_user_id},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "mobile_number": 1, "reports_to": 1, "role": 1}
        )
        
        if not user:
            break
            
        manager_id = user.get("reports_to")
        if manager_id:
            manager = await db.users.find_one(
                {"id": manager_id},
                {"_id": 0, "id": 1, "name": 1, "email": 1, "mobile_number": 1, "reports_to": 1, "role": 1}
            )
            if manager:
                hierarchy.append(manager)
        
        current_user_id = manager_id
    
    return hierarchy


async def get_all_reportees(manager_id: str) -> List[str]:
    """
    Get all users who report to this manager (direct and indirect)
    """
    all_reportees = []
    to_check = [manager_id]
    visited = set()
    
    while to_check:
        current_id = to_check.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        
        # Find direct reports
        direct_reports = await db.users.find(
            {"reports_to": current_id},
            {"_id": 0, "id": 1}
        ).to_list(1000)
        
        for report in direct_reports:
            if report["id"] not in visited:
                all_reportees.append(report["id"])
                to_check.append(report["id"])
    
    return all_reportees


async def calculate_user_revenue(user_id: str, date_str: str) -> Dict:
    """
    Calculate revenue for a user on a specific date
    """
    # Get bookings created by this user on the date
    bookings = await db.bookings.find({
        "created_by": user_id,
        "created_at": {"$regex": f"^{date_str}"},
        "is_voided": {"$ne": True},
        "status": {"$ne": "cancelled"}
    }, {"_id": 0}).to_list(1000)
    
    total_bookings = len(bookings)
    total_quantity = sum(b.get("quantity", 0) for b in bookings)
    total_value = sum(b.get("quantity", 0) * b.get("buying_price", 0) for b in bookings)
    total_revenue = sum(b.get("employee_revenue", 0) for b in bookings)
    
    # Get payments collected on the date
    payments = await db.payment_logs.find({
        "recorded_by": user_id,
        "created_at": {"$regex": f"^{date_str}"}
    }, {"_id": 0}).to_list(1000)
    
    total_collections = sum(p.get("amount", 0) for p in payments)
    
    # Get pending collections
    pending_bookings = await db.bookings.find({
        "created_by": user_id,
        "payment_status": {"$in": ["pending", "partial"]},
        "is_voided": {"$ne": True}
    }, {"_id": 0, "total_amount": 1, "paid_amount": 1}).to_list(1000)
    
    pending_amount = sum((b.get("total_amount", 0) - b.get("paid_amount", 0)) for b in pending_bookings)
    
    return {
        "bookings_count": total_bookings,
        "quantity": total_quantity,
        "booking_value": total_value,
        "revenue_earned": total_revenue,
        "collections": total_collections,
        "pending_collections": pending_amount
    }


async def generate_revenue_report(user_id: str, date_str: str, include_team: bool = False) -> Dict:
    """
    Generate revenue report for a user
    If include_team=True, includes all reportees' revenue (for managers)
    """
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1, "email": 1, "mobile_number": 1, "role": 1})
    if not user:
        return None
    
    # Calculate user's own revenue
    own_revenue = await calculate_user_revenue(user_id, date_str)
    
    team_revenue = {
        "bookings_count": 0,
        "quantity": 0,
        "booking_value": 0,
        "revenue_earned": 0,
        "collections": 0,
        "pending_collections": 0
    }
    
    team_members = []
    
    if include_team:
        # Get all reportees
        reportee_ids = await get_all_reportees(user_id)
        
        for reportee_id in reportee_ids:
            reportee = await db.users.find_one({"id": reportee_id}, {"_id": 0, "name": 1})
            reportee_revenue = await calculate_user_revenue(reportee_id, date_str)
            
            # Aggregate team totals
            for key in team_revenue:
                team_revenue[key] += reportee_revenue.get(key, 0)
            
            if reportee_revenue["bookings_count"] > 0 or reportee_revenue["collections"] > 0:
                team_members.append({
                    "name": reportee.get("name") if reportee else "Unknown",
                    **reportee_revenue
                })
    
    return {
        "user": user,
        "date": date_str,
        "own": own_revenue,
        "team": team_revenue if include_team else None,
        "team_members": team_members if include_team else [],
        "total": {
            "bookings_count": own_revenue["bookings_count"] + team_revenue["bookings_count"],
            "quantity": own_revenue["quantity"] + team_revenue["quantity"],
            "booking_value": own_revenue["booking_value"] + team_revenue["booking_value"],
            "revenue_earned": own_revenue["revenue_earned"] + team_revenue["revenue_earned"],
            "collections": own_revenue["collections"] + team_revenue["collections"],
            "pending_collections": own_revenue["pending_collections"] + team_revenue["pending_collections"]
        }
    }


def build_revenue_email(report: Dict, is_manager: bool = False) -> str:
    """Build email content for revenue report"""
    user = report["user"]
    date = report["date"]
    own = report["own"]
    total = report["total"]
    
    email_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #10B981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
        .metric {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #10B981; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #10B981; }}
        .team-section {{ margin-top: 20px; padding-top: 20px; border-top: 2px solid #e5e7eb; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f3f4f6; font-weight: 600; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Daily Revenue Report</h1>
            <p>{date}</p>
        </div>
        <div class="content">
            <p>Hello {user['name']},</p>
            <p>Here's your revenue summary for today:</p>
            
            <h3>Your Performance</h3>
            <div class="metric">
                <div class="metric-label">Bookings Created</div>
                <div class="metric-value">{own['bookings_count']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Booking Value</div>
                <div class="metric-value">₹{own['booking_value']:,.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Revenue Earned</div>
                <div class="metric-value">₹{own['revenue_earned']:,.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Collections Today</div>
                <div class="metric-value">₹{own['collections']:,.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Pending Collections</div>
                <div class="metric-value" style="color: #f59e0b;">₹{own['pending_collections']:,.2f}</div>
            </div>
"""
    
    if is_manager and report.get("team"):
        team = report["team"]
        team_members = report.get("team_members", [])
        
        email_content += f"""
            <div class="team-section">
                <h3>Team Performance (Consolidated)</h3>
                <div class="metric">
                    <div class="metric-label">Team Bookings</div>
                    <div class="metric-value">{team['bookings_count']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Team Booking Value</div>
                    <div class="metric-value">₹{team['booking_value']:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Team Revenue</div>
                    <div class="metric-value">₹{team['revenue_earned']:,.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Team Collections</div>
                    <div class="metric-value">₹{team['collections']:,.2f}</div>
                </div>
                
                <h4>Total (You + Team)</h4>
                <div class="metric" style="border-left-color: #3b82f6;">
                    <div class="metric-label">Combined Revenue</div>
                    <div class="metric-value" style="color: #3b82f6;">₹{total['revenue_earned']:,.2f}</div>
                </div>
"""
        
        if team_members:
            email_content += """
                <h4>Team Member Details</h4>
                <table>
                    <tr>
                        <th>Name</th>
                        <th>Bookings</th>
                        <th>Revenue</th>
                        <th>Collections</th>
                    </tr>
"""
            for member in team_members:
                email_content += f"""
                    <tr>
                        <td>{member['name']}</td>
                        <td>{member['bookings_count']}</td>
                        <td>₹{member['revenue_earned']:,.2f}</td>
                        <td>₹{member['collections']:,.2f}</td>
                    </tr>
"""
            email_content += "</table>"
        
        email_content += "</div>"
    
    email_content += """
            <p style="margin-top: 20px;">Keep up the great work!</p>
        </div>
        <div class="footer">
            <p>This is an automated report from SMIFS Private Equity</p>
            <p>Report generated at 6:00 PM IST</p>
        </div>
    </div>
</body>
</html>
"""
    
    return email_content


def build_revenue_whatsapp(report: Dict, is_manager: bool = False) -> str:
    """Build WhatsApp message for revenue report"""
    user = report["user"]
    date = report["date"]
    own = report["own"]
    total = report["total"]
    
    message = f"""📊 *Daily Revenue Report*
Date: {date}

Hello {user['name']}!

*Your Performance Today:*
📈 Bookings: {own['bookings_count']}
💰 Booking Value: ₹{own['booking_value']:,.0f}
✨ Revenue Earned: ₹{own['revenue_earned']:,.0f}
💵 Collections: ₹{own['collections']:,.0f}
⏳ Pending: ₹{own['pending_collections']:,.0f}
"""
    
    if is_manager and report.get("team"):
        team = report["team"]
        message += f"""
*Team Performance:*
📈 Team Bookings: {team['bookings_count']}
💰 Team Value: ₹{team['booking_value']:,.0f}
✨ Team Revenue: ₹{team['revenue_earned']:,.0f}

*Combined Total:*
💎 Total Revenue: ₹{total['revenue_earned']:,.0f}
💵 Total Collections: ₹{total['collections']:,.0f}
"""
    
    message += "\n- SMIFS Private Equity"
    
    return message


async def send_day_end_reports():
    """
    Main function to send day-end reports to all users
    Called by scheduler at 6 PM IST
    """
    from services.email_service import send_email
    from services.activity_alerts import log_whatsapp_message, get_whatsapp_config
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Get all active users
    users = await db.users.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "mobile_number": 1, "role": 1, "reports_to": 1}
    ).to_list(10000)
    
    # Check WhatsApp config
    wa_config = await get_whatsapp_config()
    wa_enabled = wa_config and wa_config.get("status") == "connected" and wa_config.get("enabled")
    
    sent_count = 0
    
    for user in users:
        try:
            # Determine if user is a manager (has reportees)
            reportees = await db.users.count_documents({"reports_to": user["id"]})
            is_manager = reportees > 0
            
            # Generate report
            report = await generate_revenue_report(user["id"], today, include_team=is_manager)
            if not report:
                continue
            
            # Skip if no activity
            if report["total"]["bookings_count"] == 0 and report["total"]["collections"] == 0:
                continue
            
            # Send email with CC to PE Desk
            try:
                email_content = build_revenue_email(report, is_manager)
                await send_email(
                    to_email=user["email"],
                    subject=f"Daily Revenue Report - {today}",
                    body=email_content,
                    cc_email="pe@smifs.com"
                )
            except Exception as e:
                print(f"Failed to send email to {user['email']}: {e}")
            
            # Send WhatsApp if enabled and user has mobile
            if wa_enabled and user.get("mobile_number"):
                try:
                    wa_message = build_revenue_whatsapp(report, is_manager)
                    await log_whatsapp_message(
                        phone_number=user["mobile_number"],
                        message=wa_message,
                        template_id="daily_revenue_report",
                        recipient_type="user",
                        recipient_id=user["id"]
                    )
                except Exception as e:
                    print(f"Failed to send WhatsApp to {user['name']}: {e}")
            
            sent_count += 1
            
        except Exception as e:
            print(f"Error processing report for {user.get('name', 'Unknown')}: {e}")
    
    # Log the job completion
    await db.scheduled_jobs.insert_one({
        "id": str(uuid.uuid4()),
        "job_type": "day_end_revenue_report",
        "date": today,
        "users_processed": len(users),
        "reports_sent": sent_count,
        "completed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"processed": len(users), "sent": sent_count}


async def trigger_manual_report(user_id: str, date_str: str = None):
    """
    Manually trigger a revenue report for a specific user
    """
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return None
    
    reportees = await db.users.count_documents({"reports_to": user_id})
    is_manager = reportees > 0
    
    return await generate_revenue_report(user_id, date_str, include_team=is_manager)
