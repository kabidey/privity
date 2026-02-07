"""
Fixed Income - Coupon Due Date Notification Service

Sends automated email reminders for upcoming coupon payments:
- 7 days before
- 1 day before
- On the payment date

Also handles:
- Maturity notifications
- Reinvestment reminders
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from database import db
from services.email_service import send_email
from .calculations import generate_cash_flow_schedule
from .models import CouponFrequency

logger = logging.getLogger(__name__)


class CouponNotificationService:
    """Service for managing coupon due date notifications"""
    
    REMINDER_DAYS = [7, 1, 0]  # Days before payment to send reminders
    
    async def get_upcoming_payments(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get all upcoming coupon/principal payments within specified days.
        """
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        # Get all holdings
        holdings = await db.fi_holdings.find({}, {"_id": 0}).to_list(length=10000)
        
        if not holdings:
            return []
        
        # Get instruments
        isins = list(set(h.get("isin") for h in holdings))
        instruments = await db.fi_instruments.find(
            {"isin": {"$in": isins}},
            {"_id": 0}
        ).to_list(length=1000)
        
        instrument_map = {i["isin"]: i for i in instruments}
        
        upcoming_payments = []
        
        for holding in holdings:
            isin = holding.get("isin")
            inst = instrument_map.get(isin)
            if not inst:
                continue
            
            client_id = holding.get("client_id")
            quantity = holding.get("quantity", 0)
            
            # Parse dates
            try:
                issue_dt = date.fromisoformat(inst["issue_date"]) if isinstance(inst["issue_date"], str) else inst["issue_date"]
                maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst["maturity_date"]
            except:
                continue
            
            face_value = Decimal(str(inst.get("face_value", 100)))
            coupon_rate = Decimal(str(inst.get("coupon_rate", 0)))
            freq = CouponFrequency(inst.get("coupon_frequency", "annual"))
            
            # Generate cash flows
            cash_flows = generate_cash_flow_schedule(
                face_value=face_value,
                coupon_rate=coupon_rate,
                settlement_date=today,
                issue_date=issue_dt,
                maturity_date=maturity_dt,
                frequency=freq,
                quantity=quantity
            )
            
            # Filter to upcoming payments
            for cf in cash_flows:
                if today <= cf.date <= end_date:
                    upcoming_payments.append({
                        "client_id": client_id,
                        "isin": isin,
                        "issuer_name": inst.get("issuer_name", "Unknown"),
                        "payment_date": cf.date,
                        "payment_type": cf.type,
                        "amount": cf.amount,
                        "description": cf.description,
                        "quantity": quantity,
                        "days_until": (cf.date - today).days
                    })
        
        # Sort by date
        upcoming_payments.sort(key=lambda x: x["payment_date"])
        
        return upcoming_payments
    
    async def send_coupon_reminders(self, days_before: int = 7) -> Dict[str, Any]:
        """
        Send email reminders for upcoming coupon payments.
        
        Args:
            days_before: Only send for payments exactly this many days away
        
        Returns:
            Summary of sent notifications
        """
        target_date = date.today() + timedelta(days=days_before)
        
        # Get upcoming payments for target date
        payments = await self.get_upcoming_payments(days_ahead=days_before + 1)
        
        # Filter to exact date
        target_payments = [p for p in payments if p["payment_date"] == target_date]
        
        if not target_payments:
            logger.info(f"No coupon payments due in {days_before} days")
            return {"sent": 0, "target_date": target_date.isoformat()}
        
        # Group by client
        client_payments = {}
        for payment in target_payments:
            client_id = payment["client_id"]
            if client_id not in client_payments:
                client_payments[client_id] = []
            client_payments[client_id].append(payment)
        
        sent_count = 0
        errors = []
        
        for client_id, payments in client_payments.items():
            try:
                # Get client
                client = await db.clients.find_one({"id": client_id}, {"_id": 0})
                if not client or not client.get("email"):
                    continue
                
                # Calculate total
                total_amount = sum(p["amount"] for p in payments)
                
                # Build email
                if days_before == 0:
                    subject = f"Coupon Payment Today - ₹{total_amount:,.2f}"
                    intro = "The following coupon payments are scheduled for today:"
                elif days_before == 1:
                    subject = f"Coupon Payment Tomorrow - ₹{total_amount:,.2f}"
                    intro = "The following coupon payments are scheduled for tomorrow:"
                else:
                    subject = f"Upcoming Coupon Payment in {days_before} Days - ₹{total_amount:,.2f}"
                    intro = f"The following coupon payments are scheduled for {target_date.strftime('%d %b %Y')}:"
                
                # Payment details
                payment_rows = ""
                for p in payments:
                    payment_rows += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{p['issuer_name']}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{p['isin']}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{p['payment_type']}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹{p['amount']:,.2f}</td>
                    </tr>
                    """
                
                body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #064E3B;">Fixed Income Payment Reminder</h2>
                    <p>Dear {client.get('name', 'Client')},</p>
                    <p>{intro}</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <thead>
                            <tr style="background-color: #064E3B; color: white;">
                                <th style="padding: 10px; text-align: left;">Issuer</th>
                                <th style="padding: 10px; text-align: left;">ISIN</th>
                                <th style="padding: 10px; text-align: left;">Type</th>
                                <th style="padding: 10px; text-align: right;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {payment_rows}
                        </tbody>
                        <tfoot>
                            <tr style="background-color: #f3f4f6; font-weight: bold;">
                                <td colspan="3" style="padding: 10px; border: 1px solid #e5e7eb;">Total</td>
                                <td style="padding: 10px; border: 1px solid #e5e7eb; text-align: right;">₹{total_amount:,.2f}</td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    <p style="color: #666; font-size: 14px;">
                        The payment will be credited to your registered bank account on the payment date,
                        subject to the issuer's payment schedule.
                    </p>
                    
                    <p>Best regards,<br>Fixed Income Desk</p>
                </div>
                """
                
                await send_email(
                    to_email=client.get("email"),
                    subject=subject,
                    body=body,
                    template_key="fi_coupon_reminder",
                    related_entity_type="fi_coupon_notification",
                    related_entity_id=f"{client_id}_{target_date.isoformat()}"
                )
                
                sent_count += 1
                logger.info(f"Sent coupon reminder to {client.get('email')} for {len(payments)} payments")
                
            except Exception as e:
                logger.error(f"Failed to send coupon reminder to client {client_id}: {e}")
                errors.append(str(e))
        
        return {
            "sent": sent_count,
            "target_date": target_date.isoformat(),
            "total_clients": len(client_payments),
            "errors": errors[:5] if errors else []
        }
    
    async def send_maturity_notifications(self, days_before: int = 30) -> Dict[str, Any]:
        """
        Send notifications for bonds approaching maturity.
        Helps clients plan reinvestment.
        """
        target_date = date.today() + timedelta(days=days_before)
        
        # Get holdings with instruments
        holdings = await db.fi_holdings.find({}, {"_id": 0}).to_list(length=10000)
        
        if not holdings:
            return {"sent": 0}
        
        isins = list(set(h.get("isin") for h in holdings))
        instruments = await db.fi_instruments.find(
            {"isin": {"$in": isins}},
            {"_id": 0}
        ).to_list(length=1000)
        
        instrument_map = {i["isin"]: i for i in instruments}
        
        # Find holdings maturing around target date
        maturing_holdings = []
        for h in holdings:
            inst = instrument_map.get(h.get("isin"))
            if not inst:
                continue
            
            try:
                maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst["maturity_date"]
            except:
                continue
            
            # Check if maturity is within 3 days of target
            if abs((maturity_dt - target_date).days) <= 3:
                face_value = Decimal(str(inst.get("face_value", 100)))
                quantity = h.get("quantity", 0)
                
                maturing_holdings.append({
                    "client_id": h.get("client_id"),
                    "isin": h.get("isin"),
                    "issuer_name": inst.get("issuer_name"),
                    "maturity_date": maturity_dt,
                    "principal_amount": face_value * quantity,
                    "coupon_rate": inst.get("coupon_rate")
                })
        
        if not maturing_holdings:
            return {"sent": 0, "message": "No maturing bonds found"}
        
        # Group by client and send
        client_maturities = {}
        for m in maturing_holdings:
            client_id = m["client_id"]
            if client_id not in client_maturities:
                client_maturities[client_id] = []
            client_maturities[client_id].append(m)
        
        sent_count = 0
        
        for client_id, maturities in client_maturities.items():
            try:
                client = await db.clients.find_one({"id": client_id}, {"_id": 0})
                if not client or not client.get("email"):
                    continue
                
                total_principal = sum(m["principal_amount"] for m in maturities)
                
                subject = f"Bond Maturity Alert - ₹{total_principal:,.0f} maturing in {days_before} days"
                
                maturity_rows = ""
                for m in maturities:
                    maturity_rows += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{m['issuer_name']}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{m['isin']}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb;">{m['maturity_date'].strftime('%d %b %Y')}</td>
                        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: right;">₹{m['principal_amount']:,.0f}</td>
                    </tr>
                    """
                
                body = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #B45309;">Bond Maturity Notification</h2>
                    <p>Dear {client.get('name', 'Client')},</p>
                    <p>The following bonds in your portfolio are approaching maturity:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <thead>
                            <tr style="background-color: #B45309; color: white;">
                                <th style="padding: 10px; text-align: left;">Issuer</th>
                                <th style="padding: 10px; text-align: left;">ISIN</th>
                                <th style="padding: 10px; text-align: left;">Maturity</th>
                                <th style="padding: 10px; text-align: right;">Principal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {maturity_rows}
                        </tbody>
                    </table>
                    
                    <div style="background-color: #FEF3C7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #B45309; margin: 0 0 10px 0;">Reinvestment Opportunity</h3>
                        <p style="margin: 0;">
                            Contact your relationship manager to explore reinvestment options 
                            for the maturing principal amount of <strong>₹{total_principal:,.0f}</strong>.
                        </p>
                    </div>
                    
                    <p>Best regards,<br>Fixed Income Desk</p>
                </div>
                """
                
                await send_email(
                    to_email=client.get("email"),
                    subject=subject,
                    body=body,
                    template_key="fi_maturity_notification",
                    related_entity_type="fi_maturity_notification",
                    related_entity_id=f"{client_id}_{target_date.isoformat()}"
                )
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send maturity notification to {client_id}: {e}")
        
        return {
            "sent": sent_count,
            "maturing_bonds": len(maturing_holdings),
            "days_until_maturity": days_before
        }


# Singleton instance
coupon_notification_service = CouponNotificationService()


async def run_daily_notifications():
    """
    Run all daily notification tasks.
    Should be called by a scheduler (e.g., APScheduler, Celery).
    """
    logger.info("Running daily FI notification tasks")
    
    results = {}
    
    # Send 7-day reminders
    results["7_day_reminders"] = await coupon_notification_service.send_coupon_reminders(7)
    
    # Send 1-day reminders
    results["1_day_reminders"] = await coupon_notification_service.send_coupon_reminders(1)
    
    # Send same-day notifications
    results["same_day_notifications"] = await coupon_notification_service.send_coupon_reminders(0)
    
    # Send 30-day maturity notifications
    results["30_day_maturity"] = await coupon_notification_service.send_maturity_notifications(30)
    
    # Send 7-day maturity notifications
    results["7_day_maturity"] = await coupon_notification_service.send_maturity_notifications(7)
    
    logger.info(f"Daily FI notifications complete: {results}")
    
    return results
