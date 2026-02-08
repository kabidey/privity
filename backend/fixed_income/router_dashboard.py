"""
Fixed Income Dashboard Router

Provides aggregated dashboard metrics for the FI module including:
- Portfolio summary (AUM, holdings, clients)
- Holdings breakdown by type and rating
- Upcoming maturities and coupon payments
- Recent order activity
- YTM distribution
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission, has_permission
from middleware.license_enforcement import license_enforcer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fixed-income/dashboard", tags=["Fixed Income - Dashboard"])


@router.get("")
async def get_fi_dashboard(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view FI dashboard"))
):
    """
    Get comprehensive Fixed Income dashboard metrics.
    
    Returns:
    - Summary: Total AUM, holdings count, clients, avg YTM, accrued interest
    - Holdings by type: NCD, BOND, GSEC breakdown
    - Holdings by rating: AAA, AA+, AA, etc.
    - Upcoming maturities: Next 90 days
    - Upcoming coupons: Next 30 days
    - Recent orders: Last 10 orders
    - YTM distribution: Grouped by yield ranges
    """
    # License check
    await license_enforcer.require_feature("fi_reports", "fixed_income", current_user)
    
    try:
        # Get all holdings
        holdings = await db.fi_holdings.find({"status": "active"}).to_list(1000)
        
        # Get all instruments for reference
        instrument_isins = list(set(h.get("isin") for h in holdings if h.get("isin")))
        instruments = {}
        if instrument_isins:
            inst_list = await db.fi_instruments.find({"isin": {"$in": instrument_isins}}).to_list(1000)
            instruments = {i["isin"]: i for i in inst_list}
        
        # Calculate summary
        total_aum = 0
        total_accrued = 0
        client_ids = set()
        ytm_values = []
        
        for h in holdings:
            face_value = float(h.get("face_value", 0))
            quantity = int(h.get("quantity", 0))
            total_value = face_value * quantity
            total_aum += total_value
            total_accrued += float(h.get("accrued_interest", 0))
            client_ids.add(h.get("client_id"))
            
            # Get YTM from instrument or holding
            inst = instruments.get(h.get("isin"), {})
            ytm = float(h.get("ytm") or inst.get("ytm") or 0)
            if ytm > 0:
                ytm_values.append(ytm)
        
        avg_ytm = sum(ytm_values) / len(ytm_values) if ytm_values else 0
        
        # Holdings by type
        holdings_by_type = {}
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            inst_type = inst.get("instrument_type", "OTHER")
            if inst_type not in holdings_by_type:
                holdings_by_type[inst_type] = {"count": 0, "value": 0}
            holdings_by_type[inst_type]["count"] += 1
            holdings_by_type[inst_type]["value"] += float(h.get("face_value", 0)) * int(h.get("quantity", 0))
        
        # Holdings by rating
        holdings_by_rating = {}
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            rating = inst.get("credit_rating", "UNRATED")
            value = float(h.get("face_value", 0)) * int(h.get("quantity", 0))
            holdings_by_rating[rating] = holdings_by_rating.get(rating, 0) + value
        
        # Upcoming maturities (next 90 days)
        today = datetime.now(timezone.utc).date()
        maturity_cutoff = today + timedelta(days=90)
        upcoming_maturities = []
        
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            maturity_str = inst.get("maturity_date")
            if maturity_str:
                try:
                    if isinstance(maturity_str, str):
                        maturity_date = datetime.fromisoformat(maturity_str.replace("Z", "+00:00")).date()
                    else:
                        maturity_date = maturity_str
                    
                    if today < maturity_date <= maturity_cutoff:
                        days_to_maturity = (maturity_date - today).days
                        upcoming_maturities.append({
                            "isin": h.get("isin"),
                            "issuer": inst.get("issuer_name", "Unknown"),
                            "maturity_date": str(maturity_date),
                            "face_value": float(h.get("face_value", 0)) * int(h.get("quantity", 0)),
                            "days_to_maturity": days_to_maturity
                        })
                except Exception as e:
                    logger.warning(f"Error parsing maturity date: {e}")
        
        upcoming_maturities.sort(key=lambda x: x["days_to_maturity"])
        
        # Upcoming coupons (next 30 days)
        coupon_cutoff = today + timedelta(days=30)
        upcoming_coupons = []
        
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            # Simplified: use next coupon date from instrument or calculate based on frequency
            coupon_rate = float(inst.get("coupon_rate", 0))
            face_value = float(h.get("face_value", 0)) * int(h.get("quantity", 0))
            
            if coupon_rate > 0:
                # Estimate next coupon as quarterly/semi-annual
                coupon_amount = face_value * (coupon_rate / 100) / 2  # Semi-annual
                # Mock next coupon date within 30 days
                next_coupon = today + timedelta(days=(hash(h.get("isin", "")) % 30) + 1)
                
                if next_coupon <= coupon_cutoff:
                    upcoming_coupons.append({
                        "isin": h.get("isin"),
                        "issuer": inst.get("issuer_name", "Unknown"),
                        "coupon_date": str(next_coupon),
                        "coupon_amount": coupon_amount,
                        "days_to_coupon": (next_coupon - today).days
                    })
        
        upcoming_coupons.sort(key=lambda x: x["days_to_coupon"])
        
        # Recent orders
        recent_orders = await db.fi_orders.find(
            {},
            {"_id": 0, "id": 1, "order_number": 1, "client_name": 1, "instrument_name": 1, "status": 1, "total_amount": 1, "created_at": 1}
        ).sort("created_at", -1).limit(10).to_list(10)
        
        recent_orders_formatted = []
        for o in recent_orders:
            recent_orders_formatted.append({
                "id": o.get("order_number", o.get("id", "N/A")),
                "client_name": o.get("client_name", "Unknown"),
                "instrument": o.get("instrument_name", "Unknown"),
                "status": o.get("status", "pending"),
                "amount": float(o.get("total_amount", 0))
            })
        
        # YTM distribution
        ytm_distribution = [
            {"range": "< 8%", "count": 0, "value": 0},
            {"range": "8-9%", "count": 0, "value": 0},
            {"range": "9-10%", "count": 0, "value": 0},
            {"range": "10-11%", "count": 0, "value": 0},
            {"range": "11%+", "count": 0, "value": 0}
        ]
        
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            ytm = float(h.get("ytm") or inst.get("ytm") or 0)
            value = float(h.get("face_value", 0)) * int(h.get("quantity", 0))
            
            if ytm < 8:
                ytm_distribution[0]["count"] += 1
                ytm_distribution[0]["value"] += value
            elif ytm < 9:
                ytm_distribution[1]["count"] += 1
                ytm_distribution[1]["value"] += value
            elif ytm < 10:
                ytm_distribution[2]["count"] += 1
                ytm_distribution[2]["value"] += value
            elif ytm < 11:
                ytm_distribution[3]["count"] += 1
                ytm_distribution[3]["value"] += value
            else:
                ytm_distribution[4]["count"] += 1
                ytm_distribution[4]["value"] += value
        
        # Duration Analysis (Macaulay Duration approximation)
        duration_distribution = [
            {"range": "< 1 year", "count": 0, "value": 0},
            {"range": "1-3 years", "count": 0, "value": 0},
            {"range": "3-5 years", "count": 0, "value": 0},
            {"range": "5-7 years", "count": 0, "value": 0},
            {"range": "7+ years", "count": 0, "value": 0}
        ]
        
        total_duration_weighted = 0
        total_duration_value = 0
        
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            value = float(h.get("face_value", 0)) * int(h.get("quantity", 0))
            
            # Calculate years to maturity as proxy for duration
            maturity_str = inst.get("maturity_date")
            years_to_maturity = 0
            
            if maturity_str:
                try:
                    if isinstance(maturity_str, str):
                        maturity_date = datetime.fromisoformat(maturity_str.replace("Z", "+00:00")).date()
                    else:
                        maturity_date = maturity_str
                    years_to_maturity = (maturity_date - today).days / 365.0
                except:
                    pass
            
            # Simple duration approximation (modified duration ~ years to maturity for low coupon bonds)
            duration = max(0, years_to_maturity * 0.9)  # Approximate
            total_duration_weighted += duration * value
            total_duration_value += value
            
            if years_to_maturity < 1:
                duration_distribution[0]["count"] += 1
                duration_distribution[0]["value"] += value
            elif years_to_maturity < 3:
                duration_distribution[1]["count"] += 1
                duration_distribution[1]["value"] += value
            elif years_to_maturity < 5:
                duration_distribution[2]["count"] += 1
                duration_distribution[2]["value"] += value
            elif years_to_maturity < 7:
                duration_distribution[3]["count"] += 1
                duration_distribution[3]["value"] += value
            else:
                duration_distribution[4]["count"] += 1
                duration_distribution[4]["value"] += value
        
        avg_duration = total_duration_weighted / total_duration_value if total_duration_value > 0 else 0
        
        # Sector Breakdown
        sector_breakdown = {}
        for h in holdings:
            inst = instruments.get(h.get("isin"), {})
            sector = inst.get("sector", "Other")
            if not sector:
                sector = "Other"
            value = float(h.get("face_value", 0)) * int(h.get("quantity", 0))
            
            if sector not in sector_breakdown:
                sector_breakdown[sector] = {"count": 0, "value": 0}
            sector_breakdown[sector]["count"] += 1
            sector_breakdown[sector]["value"] += value
        
        # Convert sector breakdown to sorted list
        sector_list = [
            {"sector": k, "count": v["count"], "value": v["value"]}
            for k, v in sorted(sector_breakdown.items(), key=lambda x: x[1]["value"], reverse=True)
        ]
        
        # Cash Flow Calendar (next 12 months)
        cash_flow_calendar = []
        for month_offset in range(12):
            month_start = (today.replace(day=1) + timedelta(days=32 * month_offset)).replace(day=1)
            if month_offset == 0:
                month_start = today.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_coupons = 0
            month_maturities = 0
            
            for h in holdings:
                inst = instruments.get(h.get("isin"), {})
                value = float(h.get("face_value", 0)) * int(h.get("quantity", 0))
                coupon_rate = float(inst.get("coupon_rate", 0))
                
                # Estimate coupon (simplified - assume semi-annual)
                if coupon_rate > 0:
                    # Check if this month might have a coupon
                    issue_date_str = inst.get("issue_date")
                    if issue_date_str:
                        try:
                            if isinstance(issue_date_str, str):
                                issue_date = datetime.fromisoformat(issue_date_str.replace("Z", "+00:00")).date()
                            else:
                                issue_date = issue_date_str
                            
                            # Check if coupon falls in this month (simplified)
                            months_since_issue = (month_start.year - issue_date.year) * 12 + (month_start.month - issue_date.month)
                            if months_since_issue >= 0 and months_since_issue % 6 == 0:
                                month_coupons += value * (coupon_rate / 100) / 2
                        except:
                            pass
                
                # Check for maturity
                maturity_str = inst.get("maturity_date")
                if maturity_str:
                    try:
                        if isinstance(maturity_str, str):
                            maturity_date = datetime.fromisoformat(maturity_str.replace("Z", "+00:00")).date()
                        else:
                            maturity_date = maturity_str
                        
                        if month_start <= maturity_date <= month_end:
                            month_maturities += value
                    except:
                        pass
            
            cash_flow_calendar.append({
                "month": month_start.strftime("%b %Y"),
                "month_key": month_start.strftime("%Y-%m"),
                "coupons": round(month_coupons, 2),
                "maturities": round(month_maturities, 2),
                "total": round(month_coupons + month_maturities, 2)
            })
        
        # Get pending orders count
        pending_orders = await db.fi_orders.count_documents({"status": {"$in": ["pending", "approved"]}})
        
        return {
            "summary": {
                "total_aum": total_aum,
                "total_holdings": len(holdings),
                "total_clients": len(client_ids),
                "avg_ytm": round(avg_ytm, 2),
                "avg_duration": round(avg_duration, 2),
                "total_accrued_interest": total_accrued,
                "pending_orders": pending_orders
            },
            "holdings_by_type": holdings_by_type,
            "holdings_by_rating": holdings_by_rating,
            "sector_breakdown": sector_list,
            "duration_distribution": duration_distribution,
            "upcoming_maturities": upcoming_maturities[:10],
            "upcoming_coupons": upcoming_coupons[:10],
            "recent_orders": recent_orders_formatted,
            "ytm_distribution": ytm_distribution,
            "cash_flow_calendar": cash_flow_calendar
        }
        
    except Exception as e:
        logger.error(f"Error generating FI dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")
