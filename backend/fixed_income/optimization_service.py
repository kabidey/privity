"""
Fixed Income - Portfolio Optimization Service

Provides intelligent suggestions for:
1. Duration Matching - Match portfolio duration to investment horizon
2. Yield Optimization - Maximize yield while managing risk
3. Diversification Analysis - Issuer and rating concentration
4. Rebalancing Recommendations
5. Risk Assessment

Uses quantitative models for bond portfolio management.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from database import db
from .calculations import (
    calculate_duration, calculate_modified_duration,
    calculate_ytm, calculate_accrued_interest
)
from .models import CouponFrequency, DayCountConvention

logger = logging.getLogger(__name__)


@dataclass
class OptimizationSuggestion:
    """Single optimization suggestion"""
    category: str  # duration, yield, diversification, risk
    priority: str  # high, medium, low
    title: str
    description: str
    action: str
    potential_benefit: str
    instruments_involved: List[str] = None


class PortfolioOptimizer:
    """Portfolio optimization engine"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.holdings = []
        self.instruments = {}
        self.portfolio_value = Decimal("0")
        self.suggestions = []
    
    async def load_portfolio(self):
        """Load client's portfolio data"""
        # Get holdings
        self.holdings = await db.fi_holdings.find(
            {"client_id": self.client_id},
            {"_id": 0}
        ).to_list(length=1000)
        
        if not self.holdings:
            return False
        
        # Get instrument details
        isins = [h.get("isin") for h in self.holdings]
        instruments = await db.fi_instruments.find(
            {"isin": {"$in": isins}},
            {"_id": 0}
        ).to_list(length=1000)
        
        self.instruments = {i["isin"]: i for i in instruments}
        
        # Calculate portfolio value
        for h in self.holdings:
            qty = h.get("quantity", 0)
            price = Decimal(str(h.get("average_cost", 0)))
            self.portfolio_value += qty * price
        
        return True
    
    async def analyze_duration(self, target_duration: Optional[Decimal] = None) -> List[OptimizationSuggestion]:
        """
        Analyze portfolio duration and suggest adjustments.
        
        Duration measures interest rate sensitivity.
        Higher duration = more sensitive to rate changes.
        """
        suggestions = []
        today = date.today()
        
        # Calculate portfolio duration
        weighted_duration = Decimal("0")
        duration_details = []
        
        for h in self.holdings:
            isin = h.get("isin")
            inst = self.instruments.get(isin, {})
            
            qty = h.get("quantity", 0)
            price = Decimal(str(h.get("average_cost", 0)))
            value = qty * price
            weight = value / self.portfolio_value if self.portfolio_value > 0 else Decimal("0")
            
            # Parse dates
            try:
                maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst.get("maturity_date", today)
            except:
                maturity_dt = today + timedelta(days=365)
            
            # Calculate duration
            face_value = Decimal(str(inst.get("face_value", 100)))
            coupon_rate = Decimal(str(inst.get("coupon_rate", 0)))
            ytm = Decimal(str(inst.get("ytm", coupon_rate)))
            freq = CouponFrequency(inst.get("coupon_frequency", "annual"))
            
            duration = calculate_duration(
                clean_price=price,
                face_value=face_value,
                coupon_rate=coupon_rate,
                ytm=ytm,
                settlement_date=today,
                maturity_date=maturity_dt,
                frequency=freq
            )
            
            weighted_duration += duration * weight
            
            duration_details.append({
                "isin": isin,
                "issuer": inst.get("issuer_name", "Unknown"),
                "duration": duration,
                "weight": weight,
                "years_to_maturity": (maturity_dt - today).days / 365
            })
        
        # Sort by duration
        duration_details.sort(key=lambda x: x["duration"], reverse=True)
        
        # Generate suggestions
        if target_duration:
            duration_gap = weighted_duration - target_duration
            
            if abs(duration_gap) > Decimal("0.5"):
                if duration_gap > 0:
                    # Duration too high - suggest selling long-duration bonds
                    long_bonds = [d for d in duration_details if d["duration"] > weighted_duration]
                    suggestions.append(OptimizationSuggestion(
                        category="duration",
                        priority="high",
                        title="Duration Mismatch - Too High",
                        description=f"Portfolio duration ({weighted_duration:.2f} years) exceeds target ({target_duration:.2f} years)",
                        action="Consider reducing exposure to long-duration bonds",
                        potential_benefit=f"Reduce interest rate risk by {duration_gap:.2f} years",
                        instruments_involved=[d["isin"] for d in long_bonds[:3]]
                    ))
                else:
                    # Duration too low
                    short_bonds = [d for d in duration_details if d["duration"] < weighted_duration]
                    suggestions.append(OptimizationSuggestion(
                        category="duration",
                        priority="medium",
                        title="Duration Mismatch - Too Low",
                        description=f"Portfolio duration ({weighted_duration:.2f} years) is below target ({target_duration:.2f} years)",
                        action="Consider adding longer-duration bonds to match your investment horizon",
                        potential_benefit="Better match between investment horizon and portfolio duration",
                        instruments_involved=[d["isin"] for d in short_bonds[:3]]
                    ))
        
        # Check for duration concentration
        high_duration_weight = sum(d["weight"] for d in duration_details if d["duration"] > Decimal("5"))
        if high_duration_weight > Decimal("0.6"):
            suggestions.append(OptimizationSuggestion(
                category="duration",
                priority="medium",
                title="High Duration Concentration",
                description=f"{float(high_duration_weight)*100:.1f}% of portfolio in bonds with duration > 5 years",
                action="Diversify with shorter-duration instruments to reduce rate sensitivity",
                potential_benefit="Lower volatility in rising rate environment",
                instruments_involved=[d["isin"] for d in duration_details if d["duration"] > Decimal("5")][:3]
            ))
        
        return suggestions
    
    async def analyze_yield(self) -> List[OptimizationSuggestion]:
        """
        Analyze yield optimization opportunities.
        Identify underperforming positions and yield enhancement possibilities.
        """
        suggestions = []
        
        # Calculate yield statistics
        yields = []
        for h in self.holdings:
            isin = h.get("isin")
            inst = self.instruments.get(isin, {})
            
            ytm = Decimal(str(inst.get("ytm", 0)))
            rating = inst.get("credit_rating", "UNRATED")
            
            qty = h.get("quantity", 0)
            price = Decimal(str(h.get("average_cost", 0)))
            value = qty * price
            weight = value / self.portfolio_value if self.portfolio_value > 0 else Decimal("0")
            
            yields.append({
                "isin": isin,
                "issuer": inst.get("issuer_name", "Unknown"),
                "ytm": ytm,
                "rating": rating,
                "weight": weight,
                "value": value
            })
        
        # Calculate weighted average yield
        avg_yield = sum(y["ytm"] * y["weight"] for y in yields)
        
        # Find low-yield positions
        low_yield_threshold = avg_yield * Decimal("0.85")  # 15% below average
        low_yield_positions = [y for y in yields if y["ytm"] < low_yield_threshold and y["weight"] > Decimal("0.05")]
        
        if low_yield_positions:
            suggestions.append(OptimizationSuggestion(
                category="yield",
                priority="medium",
                title="Underperforming Positions",
                description=f"{len(low_yield_positions)} positions yielding significantly below portfolio average",
                action="Review these positions for potential swap to higher-yielding alternatives",
                potential_benefit=f"Potential yield pickup of {float(avg_yield - low_yield_positions[0]['ytm']):.2f}% on swapped amount",
                instruments_involved=[y["isin"] for y in low_yield_positions[:3]]
            ))
        
        # Check for yield vs risk mismatch
        high_yield_low_rating = [y for y in yields if y["ytm"] > avg_yield * Decimal("1.3") and y["rating"] in ["BBB", "BBB-", "BB", "B", "C", "D"]]
        if high_yield_low_rating:
            suggestions.append(OptimizationSuggestion(
                category="yield",
                priority="high",
                title="High Yield, High Risk Positions",
                description="Some high-yield positions carry elevated credit risk",
                action="Evaluate if the yield premium adequately compensates for credit risk",
                potential_benefit="Better risk-adjusted returns",
                instruments_involved=[y["isin"] for y in high_yield_low_rating[:3]]
            ))
        
        # Suggest ladder strategy if not present
        maturities = []
        for h in self.holdings:
            inst = self.instruments.get(h.get("isin"), {})
            try:
                mat_date = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst.get("maturity_date")
                if mat_date:
                    years = (mat_date - date.today()).days / 365
                    maturities.append(years)
            except:
                pass
        
        if maturities:
            # Check maturity distribution
            avg_maturity = sum(maturities) / len(maturities)
            maturity_spread = max(maturities) - min(maturities) if len(maturities) > 1 else 0
            
            if maturity_spread < 2 and len(self.holdings) >= 3:
                suggestions.append(OptimizationSuggestion(
                    category="yield",
                    priority="low",
                    title="Consider Bond Ladder Strategy",
                    description="Portfolio maturities are concentrated in a narrow range",
                    action="Spread maturities across different years to reduce reinvestment risk",
                    potential_benefit="Smoother cash flows and reduced reinvestment timing risk"
                ))
        
        return suggestions
    
    async def analyze_diversification(self) -> List[OptimizationSuggestion]:
        """
        Analyze diversification and concentration risks.
        """
        suggestions = []
        
        # Issuer concentration
        issuer_exposure = {}
        rating_exposure = {}
        sector_exposure = {}
        
        for h in self.holdings:
            isin = h.get("isin")
            inst = self.instruments.get(isin, {})
            
            qty = h.get("quantity", 0)
            price = Decimal(str(h.get("average_cost", 0)))
            value = qty * price
            weight = value / self.portfolio_value if self.portfolio_value > 0 else Decimal("0")
            
            # Issuer
            issuer = inst.get("issuer_name", "Unknown")
            issuer_exposure[issuer] = issuer_exposure.get(issuer, Decimal("0")) + weight
            
            # Rating
            rating = inst.get("credit_rating", "UNRATED")
            rating_exposure[rating] = rating_exposure.get(rating, Decimal("0")) + weight
        
        # Check issuer concentration
        max_issuer = max(issuer_exposure.items(), key=lambda x: x[1]) if issuer_exposure else (None, 0)
        if max_issuer[1] > Decimal("0.25"):
            suggestions.append(OptimizationSuggestion(
                category="diversification",
                priority="high",
                title="High Issuer Concentration",
                description=f"{max_issuer[0]} represents {float(max_issuer[1])*100:.1f}% of portfolio",
                action="Reduce single issuer exposure to below 25%",
                potential_benefit="Lower idiosyncratic risk from single issuer default"
            ))
        
        # Check rating concentration
        investment_grade = sum(v for k, v in rating_exposure.items() if k in ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"])
        below_investment_grade = Decimal("1") - investment_grade
        
        if below_investment_grade > Decimal("0.20"):
            suggestions.append(OptimizationSuggestion(
                category="diversification",
                priority="high",
                title="High Below-Investment-Grade Exposure",
                description=f"{float(below_investment_grade)*100:.1f}% of portfolio in below-investment-grade bonds",
                action="Rebalance towards higher-rated securities",
                potential_benefit="Reduced credit risk and potential default losses"
            ))
        
        # Check for too many issuers (over-diversification)
        if len(issuer_exposure) > 20:
            suggestions.append(OptimizationSuggestion(
                category="diversification",
                priority="low",
                title="Portfolio May Be Over-Diversified",
                description=f"Portfolio has {len(issuer_exposure)} different issuers",
                action="Consider consolidating into fewer, well-researched positions",
                potential_benefit="Easier portfolio monitoring and potentially better returns"
            ))
        
        return suggestions
    
    async def generate_suggestions(self, target_duration: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Generate all optimization suggestions for the portfolio.
        """
        if not await self.load_portfolio():
            return {
                "error": "No holdings found for client",
                "suggestions": []
            }
        
        all_suggestions = []
        
        # Run all analyses
        duration_suggestions = await self.analyze_duration(target_duration)
        yield_suggestions = await self.analyze_yield()
        diversification_suggestions = await self.analyze_diversification()
        
        all_suggestions.extend(duration_suggestions)
        all_suggestions.extend(yield_suggestions)
        all_suggestions.extend(diversification_suggestions)
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_suggestions.sort(key=lambda x: priority_order.get(x.priority, 3))
        
        # Convert to dict
        suggestions_list = [
            {
                "category": s.category,
                "priority": s.priority,
                "title": s.title,
                "description": s.description,
                "action": s.action,
                "potential_benefit": s.potential_benefit,
                "instruments_involved": s.instruments_involved
            }
            for s in all_suggestions
        ]
        
        return {
            "client_id": self.client_id,
            "portfolio_value": str(self.portfolio_value.quantize(Decimal("0.01"))),
            "holdings_count": len(self.holdings),
            "suggestions": suggestions_list,
            "summary": {
                "total_suggestions": len(suggestions_list),
                "high_priority": len([s for s in all_suggestions if s.priority == "high"]),
                "medium_priority": len([s for s in all_suggestions if s.priority == "medium"]),
                "low_priority": len([s for s in all_suggestions if s.priority == "low"])
            },
            "generated_at": datetime.now().isoformat()
        }


# ==================== ROUTER FUNCTION ====================

async def get_portfolio_optimization(client_id: str, target_duration: Optional[float] = None) -> Dict[str, Any]:
    """
    Get portfolio optimization suggestions for a client.
    
    Args:
        client_id: Client ID
        target_duration: Optional target duration in years
    
    Returns:
        Dictionary with suggestions and analysis
    """
    optimizer = PortfolioOptimizer(client_id)
    target = Decimal(str(target_duration)) if target_duration else None
    return await optimizer.generate_suggestions(target)
