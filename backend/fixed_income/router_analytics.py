"""
Fixed Income Analytics Router
==============================

API endpoints for:
- Yield Curve Analytics
- Portfolio Optimization
- Risk Metrics
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

from utils.auth import get_current_user
from services.permission_service import require_permission

from .yield_curve_analytics import (
    get_yield_curves,
    get_spread_analysis,
    get_curve_chart_data
)
from .advanced_portfolio_optimizer import (
    get_portfolio_analysis,
    optimize_portfolio,
    get_efficient_frontier
)

router = APIRouter(prefix="/analytics", tags=["FI Analytics"])


# ==================== Pydantic Models ====================

class YieldCurveRequest(BaseModel):
    curve_date: Optional[str] = Field(None, description="Date for curve (YYYY-MM-DD)")
    ratings: List[str] = Field(default=["AAA", "AA", "A"], description="Corporate ratings to include")
    interpolation: str = Field(default="cubic_spline", description="Interpolation method")


class SpreadAnalysisRequest(BaseModel):
    rating: str = Field(..., description="Credit rating (AAA, AA, A, BBB)")
    curve_date: Optional[str] = Field(None, description="Date for analysis")


class OptimizationRequest(BaseModel):
    client_id: str = Field(..., description="Client ID for portfolio")
    objective: str = Field(default="maximize_yield", description="Optimization objective")
    parameters: dict = Field(default={}, description="Optimization parameters")


class EfficientFrontierRequest(BaseModel):
    n_points: int = Field(default=20, ge=5, le=50, description="Number of frontier points")
    max_duration: float = Field(default=10.0, ge=1, le=30, description="Maximum portfolio duration")
    filters: dict = Field(default={}, description="Instrument filters")


# ==================== Yield Curve Endpoints ====================

@router.get("/yield-curves")
async def api_get_yield_curves(
    curve_date: Optional[str] = Query(None, description="Date for curve (YYYY-MM-DD)"),
    ratings: str = Query("AAA,AA,A", description="Comma-separated ratings"),
    interpolation: str = Query("cubic_spline", description="Interpolation method"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view yield curves"))
):
    """
    Get yield curves for analysis.
    
    Returns G-Sec (risk-free) curve and corporate curves by rating.
    
    Interpolation methods:
    - linear: Simple linear interpolation
    - cubic_spline: Smooth cubic spline
    - nelson_siegel: Nelson-Siegel parametric model
    - svensson: Svensson (extended Nelson-Siegel) model
    """
    try:
        cd = date.fromisoformat(curve_date) if curve_date else None
    except ValueError:
        cd = None
    
    rating_list = [r.strip() for r in ratings.split(",")]
    
    return await get_yield_curves(
        curve_date=cd,
        ratings=rating_list,
        interpolation=interpolation
    )


@router.get("/yield-curves/chart")
async def api_get_curve_chart(
    curve_date: Optional[str] = Query(None, description="Date for curve"),
    ratings: str = Query("AAA,AA,A", description="Comma-separated ratings"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view yield curve chart"))
):
    """
    Get yield curve data formatted for chart visualization.
    
    Returns series data suitable for line charts (Recharts/ApexCharts).
    """
    try:
        cd = date.fromisoformat(curve_date) if curve_date else None
    except ValueError:
        cd = None
    
    rating_list = [r.strip() for r in ratings.split(",")]
    
    return await get_curve_chart_data(curve_date=cd, ratings=rating_list)


@router.get("/spread-analysis/{rating}")
async def api_get_spread_analysis(
    rating: str,
    curve_date: Optional[str] = Query(None, description="Date for analysis"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view spread analysis"))
):
    """
    Get credit spread analysis for a specific rating vs G-Sec.
    
    Returns:
    - Spreads at standard tenors
    - Key rate durations
    - Summary statistics
    """
    try:
        cd = date.fromisoformat(curve_date) if curve_date else None
    except ValueError:
        cd = None
    
    valid_ratings = ["AAA", "AA", "A", "BBB"]
    if rating.upper() not in valid_ratings:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rating. Must be one of: {valid_ratings}"
        )
    
    return await get_spread_analysis(rating.upper(), cd)


# ==================== Portfolio Analysis Endpoints ====================

@router.get("/portfolio/{client_id}")
async def api_get_portfolio_analysis(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view portfolio analysis"))
):
    """
    Get comprehensive portfolio analysis for a client.
    
    Returns:
    - Portfolio metrics (duration, yield, convexity, VaR)
    - Position breakdown
    - Risk distributions by rating and maturity
    """
    result = await get_portfolio_analysis(client_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/portfolio/optimize")
async def api_optimize_portfolio(
    request: OptimizationRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.instrument_edit", "optimize portfolio"))
):
    """
    Run portfolio optimization.
    
    Objectives:
    - maximize_yield: Maximize yield subject to duration/risk constraints
    - target_duration: Match a specific target duration (immunization)
    - minimize_risk: Minimize credit risk while maintaining yield floor
    
    Parameters vary by objective:
    - maximize_yield: max_duration, max_single_issuer, min_rating
    - target_duration: target_duration, tolerance, max_single_issuer
    - minimize_risk: min_yield, max_duration
    """
    valid_objectives = ["maximize_yield", "target_duration", "minimize_risk"]
    if request.objective not in valid_objectives:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid objective. Must be one of: {valid_objectives}"
        )
    
    result = await optimize_portfolio(
        client_id=request.client_id,
        objective=request.objective,
        parameters=request.parameters
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/efficient-frontier")
async def api_get_efficient_frontier(
    request: EfficientFrontierRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view efficient frontier"))
):
    """
    Calculate the efficient frontier (risk-return tradeoff).
    
    Returns points representing optimal portfolios at different risk levels.
    Useful for understanding the best achievable yield for a given risk tolerance.
    """
    return await get_efficient_frontier(
        n_points=request.n_points,
        max_duration=request.max_duration,
        filters=request.filters
    )


@router.get("/risk-metrics/{client_id}")
async def api_get_risk_metrics(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view risk metrics"))
):
    """
    Get detailed risk metrics for a portfolio.
    
    Returns:
    - Duration and modified duration
    - Convexity
    - VaR (95% and 99%)
    - Spread duration
    - Key rate durations
    """
    from .advanced_portfolio_optimizer import AdvancedPortfolioOptimizer
    
    optimizer = AdvancedPortfolioOptimizer(client_id)
    
    if not await optimizer.load_portfolio():
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    metrics = optimizer.calculate_portfolio_metrics()
    
    # Additional risk breakdown
    position_risks = []
    for p in optimizer.positions:
        risk_score = AdvancedPortfolioOptimizer.RATING_RISK.get(p.rating, 8.0)
        position_risks.append({
            "isin": p.isin,
            "issuer": p.issuer,
            "weight_pct": round(p.weight * 100, 2),
            "duration": round(p.duration, 3),
            "modified_duration": round(p.modified_duration, 3),
            "convexity": round(p.convexity, 3),
            "rating": p.rating,
            "risk_score": risk_score,
            "contribution_to_duration": round(p.weight * p.duration, 3),
            "contribution_to_risk": round(p.weight * risk_score, 3)
        })
    
    # Sort by risk contribution
    position_risks.sort(key=lambda x: x["contribution_to_risk"], reverse=True)
    
    return {
        "client_id": client_id,
        "portfolio_metrics": metrics.to_dict(),
        "position_risks": position_risks,
        "risk_summary": {
            "total_duration_risk": round(metrics.weighted_duration, 3),
            "total_credit_risk": round(sum(p["contribution_to_risk"] for p in position_risks), 2),
            "var_95_pct_of_portfolio": round(metrics.var_95 / metrics.total_value * 100, 2) if metrics.total_value > 0 else 0,
            "var_99_pct_of_portfolio": round(metrics.var_99 / metrics.total_value * 100, 2) if metrics.total_value > 0 else 0
        },
        "generated_at": datetime.now().isoformat()
    }


# Export
__all__ = ['router']
