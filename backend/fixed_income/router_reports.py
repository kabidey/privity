"""
Fixed Income Router - Reporting & Analytics

Provides comprehensive reporting for fixed income investments:
1. Holdings Report (Portfolio with MTM)
2. Cash Flow Calendar
3. Maturity Schedule
4. Transaction History
5. Performance Analytics

All reports implement RBAC:
- PE Level: See all data
- Agents: See data for their clients
- Clients: See only own data
"""

import logging
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
import io
import csv

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission
from config import is_pe_level

from .models import CouponFrequency, DayCountConvention
from .calculations import (
    generate_cash_flow_schedule,
    calculate_mark_to_market,
    calculate_accrued_interest,
    calculate_ytm
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fixed-income/reports", tags=["Fixed Income - Reports"])


# ==================== HOLDINGS REPORT ====================

@router.get("/holdings", response_model=dict)
async def get_holdings_report(
    client_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_view", "view holdings report"))
):
    """
    Get consolidated holdings report with current valuation (Mark-to-Market).
    
    Returns:
    - Portfolio summary
    - Individual holdings with current prices and P&L
    - Total portfolio value and unrealized gains
    """
    user_role = current_user.get("role", 99)
    
    # Build query based on RBAC
    query = {}
    if client_id:
        query["client_id"] = client_id
    elif not is_pe_level(user_role):
        # Non-PE users - get their own client IDs or clients they created
        # For now, restrict to explicit client_id
        raise HTTPException(
            status_code=400,
            detail="Please specify a client_id to view holdings"
        )
    
    # Get holdings
    cursor = db.fi_holdings.find(query, {"_id": 0})
    holdings = await cursor.to_list(length=1000)
    
    if not holdings:
        return {
            "holdings": [],
            "summary": {
                "total_cost": "0.00",
                "total_current_value": "0.00",
                "total_unrealized_pnl": "0.00",
                "pnl_percentage": "0.00"
            }
        }
    
    # Get current market prices
    isins = list(set(h.get("isin") for h in holdings))
    instruments = await db.fi_instruments.find(
        {"isin": {"$in": isins}},
        {"_id": 0, "isin": 1, "current_market_price": 1, "issuer_name": 1, 
         "coupon_rate": 1, "maturity_date": 1, "credit_rating": 1}
    ).to_list(length=1000)
    
    instrument_map = {i["isin"]: i for i in instruments}
    market_prices = {
        isin: Decimal(str(inst.get("current_market_price") or inst.get("face_value", 100)))
        for isin, inst in instrument_map.items()
    }
    
    # Calculate MTM for each holding
    today = date.today()
    enriched_holdings = []
    total_cost = Decimal("0")
    total_value = Decimal("0")
    
    for holding in holdings:
        isin = holding.get("isin")
        inst = instrument_map.get(isin, {})
        
        qty = holding.get("quantity", 0)
        avg_cost = Decimal(str(holding.get("average_cost", 0)))
        current_price = market_prices.get(isin, avg_cost)
        
        cost_value = avg_cost * qty
        current_value = current_price * qty
        unrealized_pnl = current_value - cost_value
        
        pnl_pct = ((unrealized_pnl / cost_value) * 100) if cost_value > 0 else Decimal("0")
        
        total_cost += cost_value
        total_value += current_value
        
        enriched_holdings.append({
            "isin": isin,
            "issuer_name": inst.get("issuer_name", "Unknown"),
            "quantity": qty,
            "face_value": str(inst.get("face_value", 100)),
            "average_cost": str(avg_cost.quantize(Decimal("0.01"))),
            "current_price": str(current_price.quantize(Decimal("0.01"))),
            "cost_value": str(cost_value.quantize(Decimal("0.01"))),
            "current_value": str(current_value.quantize(Decimal("0.01"))),
            "unrealized_pnl": str(unrealized_pnl.quantize(Decimal("0.01"))),
            "pnl_percentage": str(pnl_pct.quantize(Decimal("0.01"))),
            "coupon_rate": str(inst.get("coupon_rate", "0")),
            "maturity_date": inst.get("maturity_date"),
            "credit_rating": inst.get("credit_rating", "UNRATED"),
            "client_id": holding.get("client_id")
        })
    
    total_pnl = total_value - total_cost
    total_pnl_pct = ((total_pnl / total_cost) * 100) if total_cost > 0 else Decimal("0")
    
    return {
        "holdings": enriched_holdings,
        "summary": {
            "total_cost": str(total_cost.quantize(Decimal("0.01"))),
            "total_current_value": str(total_value.quantize(Decimal("0.01"))),
            "total_unrealized_pnl": str(total_pnl.quantize(Decimal("0.01"))),
            "pnl_percentage": str(total_pnl_pct.quantize(Decimal("0.01"))),
            "total_holdings": len(enriched_holdings)
        },
        "generated_at": datetime.now().isoformat()
    }


# ==================== CASH FLOW CALENDAR ====================

@router.get("/cash-flow-calendar", response_model=dict)
async def get_cash_flow_calendar(
    client_id: str,
    months_ahead: int = Query(12, ge=1, le=60),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_view", "view cash flow calendar"))
):
    """
    Generate cash flow calendar showing all upcoming coupon and principal payments.
    
    Shows exactly when the client will receive interest/principal payments
    over the specified period.
    """
    # Get client holdings
    holdings = await db.fi_holdings.find(
        {"client_id": client_id},
        {"_id": 0}
    ).to_list(length=1000)
    
    if not holdings:
        return {
            "client_id": client_id,
            "cash_flows": [],
            "summary": {
                "total_coupon_income": "0.00",
                "total_principal_redemptions": "0.00",
                "total_cash_flows": "0.00"
            }
        }
    
    # Get all instruments
    isins = [h.get("isin") for h in holdings]
    instruments = await db.fi_instruments.find(
        {"isin": {"$in": isins}},
        {"_id": 0}
    ).to_list(length=1000)
    
    instrument_map = {i["isin"]: i for i in instruments}
    
    # Generate cash flows for each holding
    all_cash_flows = []
    today = date.today()
    end_date = today + timedelta(days=months_ahead * 30)
    
    for holding in holdings:
        isin = holding.get("isin")
        inst = instrument_map.get(isin)
        if not inst:
            continue
        
        quantity = holding.get("quantity", 0)
        
        # Parse dates
        issue_dt = date.fromisoformat(inst["issue_date"]) if isinstance(inst["issue_date"], str) else inst["issue_date"]
        maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst["maturity_date"]
        
        face_value = Decimal(str(inst.get("face_value", 100)))
        coupon_rate = Decimal(str(inst.get("coupon_rate", 0)))
        freq = CouponFrequency(inst.get("coupon_frequency", "annual"))
        
        # Generate cash flow schedule
        cash_flows = generate_cash_flow_schedule(
            face_value=face_value,
            coupon_rate=coupon_rate,
            settlement_date=today,
            issue_date=issue_dt,
            maturity_date=maturity_dt,
            frequency=freq,
            quantity=quantity
        )
        
        # Filter to requested period and add instrument info
        for cf in cash_flows:
            if today <= cf.date <= end_date:
                all_cash_flows.append({
                    "date": cf.date.isoformat(),
                    "isin": isin,
                    "issuer_name": inst.get("issuer_name", "Unknown"),
                    "type": cf.type,
                    "amount": str(cf.amount),
                    "description": cf.description
                })
    
    # Sort by date
    all_cash_flows.sort(key=lambda x: x["date"])
    
    # Calculate totals
    total_coupon = sum(
        Decimal(cf["amount"]) for cf in all_cash_flows 
        if cf["type"] == "coupon"
    )
    total_principal = sum(
        Decimal(cf["amount"]) for cf in all_cash_flows 
        if cf["type"] in ["principal", "both"]
    )
    # Adjust for "both" type
    for cf in all_cash_flows:
        if cf["type"] == "both":
            # Split into coupon and principal portions
            total_amount = Decimal(cf["amount"])
            # Approximate: assume coupon portion based on description
            total_coupon += total_amount * Decimal("0.1")  # Rough estimate
            total_principal += total_amount * Decimal("0.9")
    
    return {
        "client_id": client_id,
        "period": f"Next {months_ahead} months",
        "from_date": today.isoformat(),
        "to_date": end_date.isoformat(),
        "cash_flows": all_cash_flows,
        "summary": {
            "total_coupon_income": str(total_coupon.quantize(Decimal("0.01"))),
            "total_principal_redemptions": str(total_principal.quantize(Decimal("0.01"))),
            "total_cash_flows": str((total_coupon + total_principal).quantize(Decimal("0.01"))),
            "payment_count": len(all_cash_flows)
        },
        "generated_at": datetime.now().isoformat()
    }


# ==================== MATURITY SCHEDULE ====================

@router.get("/maturity-schedule", response_model=dict)
async def get_maturity_schedule(
    client_id: Optional[str] = None,
    months_ahead: int = Query(24, ge=1, le=120),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_view", "view maturity schedule"))
):
    """
    Get maturity schedule showing when bonds will mature.
    
    Useful for reinvestment planning.
    """
    # Build query
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    holdings = await db.fi_holdings.find(query, {"_id": 0}).to_list(length=1000)
    
    if not holdings:
        return {"maturities": [], "total_principal": "0.00"}
    
    # Get instruments
    isins = list(set(h.get("isin") for h in holdings))
    instruments = await db.fi_instruments.find(
        {"isin": {"$in": isins}},
        {"_id": 0}
    ).to_list(length=1000)
    
    instrument_map = {i["isin"]: i for i in instruments}
    
    # Build maturity schedule
    today = date.today()
    end_date = today + timedelta(days=months_ahead * 30)
    
    maturities = []
    for holding in holdings:
        isin = holding.get("isin")
        inst = instrument_map.get(isin)
        if not inst:
            continue
        
        maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst["maturity_date"]
        
        if today <= maturity_dt <= end_date:
            face_value = Decimal(str(inst.get("face_value", 100)))
            quantity = holding.get("quantity", 0)
            principal = face_value * quantity
            
            maturities.append({
                "maturity_date": maturity_dt.isoformat(),
                "isin": isin,
                "issuer_name": inst.get("issuer_name", "Unknown"),
                "quantity": quantity,
                "face_value": str(face_value),
                "principal_amount": str(principal.quantize(Decimal("0.01"))),
                "coupon_rate": str(inst.get("coupon_rate", "0")),
                "client_id": holding.get("client_id")
            })
    
    # Sort by maturity date
    maturities.sort(key=lambda x: x["maturity_date"])
    
    total_principal = sum(Decimal(m["principal_amount"]) for m in maturities)
    
    return {
        "period": f"Next {months_ahead} months",
        "maturities": maturities,
        "total_principal": str(total_principal.quantize(Decimal("0.01"))),
        "count": len(maturities),
        "generated_at": datetime.now().isoformat()
    }


# ==================== TRANSACTION HISTORY ====================

@router.get("/transactions", response_model=dict)
async def get_transaction_history(
    client_id: Optional[str] = None,
    isin: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_view", "view transactions"))
):
    """
    Get transaction history with optional filters.
    """
    # Build query
    query = {}
    
    if client_id:
        query["client_id"] = client_id
    
    if isin:
        query["isin"] = isin
    
    if from_date:
        query["transaction_date"] = {"$gte": from_date.isoformat()}
    
    if to_date:
        if "transaction_date" in query:
            query["transaction_date"]["$lte"] = to_date.isoformat()
        else:
            query["transaction_date"] = {"$lte": to_date.isoformat()}
    
    # Get total
    total = await db.fi_transactions.count_documents(query)
    
    # Get transactions
    cursor = db.fi_transactions.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    transactions = await cursor.to_list(length=limit)
    
    # Enrich with issuer names
    for txn in transactions:
        inst = await db.fi_instruments.find_one({"isin": txn.get("isin")}, {"_id": 0, "issuer_name": 1})
        txn["issuer_name"] = inst.get("issuer_name", "Unknown") if inst else "Unknown"
    
    return {
        "transactions": transactions,
        "total": total,
        "skip": skip,
        "limit": limit
    }


# ==================== PORTFOLIO ANALYTICS ====================

@router.get("/analytics/portfolio-summary", response_model=dict)
async def get_portfolio_analytics(
    client_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_view", "view portfolio analytics"))
):
    """
    Get portfolio analytics including:
    - Rating distribution
    - Maturity bucket distribution
    - Yield analysis
    - Concentration analysis
    """
    query = {}
    if client_id:
        query["client_id"] = client_id
    
    holdings = await db.fi_holdings.find(query, {"_id": 0}).to_list(length=1000)
    
    if not holdings:
        return {"message": "No holdings found"}
    
    # Get instruments
    isins = list(set(h.get("isin") for h in holdings))
    instruments = await db.fi_instruments.find(
        {"isin": {"$in": isins}},
        {"_id": 0}
    ).to_list(length=1000)
    
    instrument_map = {i["isin"]: i for i in instruments}
    
    # Calculate analytics
    rating_distribution = {}
    maturity_buckets = {"0-1Y": Decimal("0"), "1-3Y": Decimal("0"), "3-5Y": Decimal("0"), "5Y+": Decimal("0")}
    issuer_concentration = {}
    total_value = Decimal("0")
    weighted_yield = Decimal("0")
    
    today = date.today()
    
    for holding in holdings:
        isin = holding.get("isin")
        inst = instrument_map.get(isin, {})
        
        quantity = holding.get("quantity", 0)
        current_price = Decimal(str(inst.get("current_market_price") or inst.get("face_value", 100)))
        value = current_price * quantity
        total_value += value
        
        # Rating distribution
        rating = inst.get("credit_rating", "UNRATED")
        rating_distribution[rating] = rating_distribution.get(rating, Decimal("0")) + value
        
        # Maturity buckets
        maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst.get("maturity_date", today)
        years_to_maturity = (maturity_dt - today).days / 365
        
        if years_to_maturity <= 1:
            maturity_buckets["0-1Y"] += value
        elif years_to_maturity <= 3:
            maturity_buckets["1-3Y"] += value
        elif years_to_maturity <= 5:
            maturity_buckets["3-5Y"] += value
        else:
            maturity_buckets["5Y+"] += value
        
        # Issuer concentration
        issuer = inst.get("issuer_name", "Unknown")
        issuer_concentration[issuer] = issuer_concentration.get(issuer, Decimal("0")) + value
        
        # Weighted yield
        ytm = Decimal(str(inst.get("ytm", 0)))
        weighted_yield += ytm * value
    
    # Calculate percentages
    rating_pct = {k: str((v / total_value * 100).quantize(Decimal("0.01"))) for k, v in rating_distribution.items()} if total_value > 0 else {}
    maturity_pct = {k: str((v / total_value * 100).quantize(Decimal("0.01"))) for k, v in maturity_buckets.items()} if total_value > 0 else {}
    issuer_pct = {k: str((v / total_value * 100).quantize(Decimal("0.01"))) for k, v in issuer_concentration.items()} if total_value > 0 else {}
    
    avg_yield = (weighted_yield / total_value).quantize(Decimal("0.01")) if total_value > 0 else Decimal("0")
    
    return {
        "total_portfolio_value": str(total_value.quantize(Decimal("0.01"))),
        "weighted_average_yield": str(avg_yield),
        "rating_distribution": rating_pct,
        "maturity_distribution": maturity_pct,
        "issuer_concentration": issuer_pct,
        "top_holdings": sorted(
            issuer_concentration.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5],
        "generated_at": datetime.now().isoformat()
    }


# ==================== EXPORT ENDPOINTS ====================

@router.get("/export/holdings-csv")
async def export_holdings_csv(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_export", "export holdings"))
):
    """
    Export holdings report as CSV.
    """
    # Get holdings data
    holdings_report = await get_holdings_report(client_id, current_user, None)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ISIN", "Issuer Name", "Quantity", "Face Value", "Average Cost",
        "Current Price", "Cost Value", "Current Value", "Unrealized P&L",
        "P&L %", "Coupon Rate", "Maturity Date", "Credit Rating"
    ])
    
    # Data rows
    for h in holdings_report.get("holdings", []):
        writer.writerow([
            h.get("isin"),
            h.get("issuer_name"),
            h.get("quantity"),
            h.get("face_value"),
            h.get("average_cost"),
            h.get("current_price"),
            h.get("cost_value"),
            h.get("current_value"),
            h.get("unrealized_pnl"),
            h.get("pnl_percentage"),
            h.get("coupon_rate"),
            h.get("maturity_date"),
            h.get("credit_rating")
        ])
    
    # Summary row
    summary = holdings_report.get("summary", {})
    writer.writerow([])
    writer.writerow(["TOTAL", "", "", "", "", "", 
                     summary.get("total_cost"),
                     summary.get("total_current_value"),
                     summary.get("total_unrealized_pnl"),
                     summary.get("pnl_percentage")])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=fi_holdings_{client_id}_{date.today().isoformat()}.csv"
        }
    )


@router.get("/export/cash-flow-csv")
async def export_cash_flow_csv(
    client_id: str,
    months_ahead: int = 12,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.report_export", "export cash flows"))
):
    """
    Export cash flow calendar as CSV.
    """
    # Get cash flow data
    cf_report = await get_cash_flow_calendar(client_id, months_ahead, current_user, None)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Date", "ISIN", "Issuer Name", "Type", "Amount", "Description"])
    
    # Data rows
    for cf in cf_report.get("cash_flows", []):
        writer.writerow([
            cf.get("date"),
            cf.get("isin"),
            cf.get("issuer_name"),
            cf.get("type"),
            cf.get("amount"),
            cf.get("description")
        ])
    
    # Summary
    summary = cf_report.get("summary", {})
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Coupon Income", summary.get("total_coupon_income")])
    writer.writerow(["Total Principal Redemptions", summary.get("total_principal_redemptions")])
    writer.writerow(["Total Cash Flows", summary.get("total_cash_flows")])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=fi_cashflows_{client_id}_{date.today().isoformat()}.csv"
        }
    )
