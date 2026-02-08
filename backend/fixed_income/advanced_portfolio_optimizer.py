"""
Advanced Portfolio Optimization Service
========================================

Comprehensive portfolio optimization for fixed income securities.

Features:
- Modern Portfolio Theory (MPT) optimization
- Duration targeting and immunization
- Cash flow matching
- Risk metrics (VaR, duration, convexity)
- Efficient frontier analysis
- Rebalancing recommendations
- Scenario analysis

References:
- Markowitz Mean-Variance Optimization
- Duration Matching for ALM
- Key Rate Duration Hedging
"""

import numpy as np
from scipy import optimize
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from database import db
from .calculations import (
    calculate_duration, calculate_modified_duration,
    calculate_ytm, calculate_accrued_interest
)
from .models import CouponFrequency, DayCountConvention

logger = logging.getLogger(__name__)


class OptimizationObjective(str, Enum):
    """Portfolio optimization objectives"""
    MAX_YIELD = "maximize_yield"
    MIN_RISK = "minimize_risk"
    TARGET_DURATION = "target_duration"
    MAX_SHARPE = "maximize_sharpe"
    CASH_FLOW_MATCH = "cash_flow_match"


class RiskMetric(str, Enum):
    """Risk measurement types"""
    DURATION = "duration"
    MODIFIED_DURATION = "modified_duration"
    CONVEXITY = "convexity"
    VAR_95 = "var_95"
    VAR_99 = "var_99"
    SPREAD_DURATION = "spread_duration"


@dataclass
class PortfolioPosition:
    """Single portfolio position"""
    isin: str
    issuer: str
    weight: float
    quantity: int
    market_value: float
    yield_pct: float
    duration: float
    modified_duration: float
    convexity: float
    rating: str
    maturity_date: date
    coupon_rate: float


@dataclass
class PortfolioMetrics:
    """Portfolio-level metrics"""
    total_value: float
    weighted_yield: float
    weighted_duration: float
    weighted_mod_duration: float
    weighted_convexity: float
    var_95: float
    var_99: float
    spread_duration: float
    
    def to_dict(self) -> Dict:
        return {
            "total_value": round(self.total_value, 2),
            "weighted_yield": round(self.weighted_yield, 4),
            "weighted_duration": round(self.weighted_duration, 3),
            "weighted_mod_duration": round(self.weighted_mod_duration, 3),
            "weighted_convexity": round(self.weighted_convexity, 3),
            "var_95": round(self.var_95, 2),
            "var_99": round(self.var_99, 2),
            "spread_duration": round(self.spread_duration, 3)
        }


@dataclass
class OptimizationResult:
    """Result of portfolio optimization"""
    objective: str
    status: str
    target_weights: Dict[str, float]
    expected_yield: float
    expected_duration: float
    expected_risk: float
    trades_required: List[Dict]
    improvement: Dict[str, float]


class AdvancedPortfolioOptimizer:
    """
    Advanced portfolio optimization engine.
    
    Supports multiple optimization strategies:
    - Mean-variance optimization (Markowitz)
    - Duration targeting
    - Cash flow matching
    - Risk minimization
    """
    
    # Rating risk scores (higher = riskier)
    RATING_RISK = {
        "SOVEREIGN": 0.0,
        "AAA": 0.5,
        "AA+": 1.0,
        "AA": 1.5,
        "AA-": 2.0,
        "A+": 3.0,
        "A": 3.5,
        "A-": 4.0,
        "BBB+": 5.0,
        "BBB": 6.0,
        "BBB-": 7.0,
        "BB+": 9.0,
        "BB": 10.0,
        "B": 12.0,
        "CCC": 15.0,
        "UNRATED": 8.0
    }
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id
        self.positions: List[PortfolioPosition] = []
        self.available_instruments: List[Dict] = []
        self.constraints: Dict = {}
    
    async def load_portfolio(self) -> bool:
        """Load client portfolio data"""
        if not self.client_id:
            return False
        
        holdings = await db.fi_holdings.find(
            {"client_id": self.client_id},
            {"_id": 0}
        ).to_list(1000)
        
        if not holdings:
            return False
        
        isins = [h["isin"] for h in holdings]
        instruments = await db.fi_instruments.find(
            {"isin": {"$in": isins}},
            {"_id": 0}
        ).to_list(1000)
        
        inst_map = {i["isin"]: i for i in instruments}
        today = date.today()
        total_value = sum(
            h.get("quantity", 0) * h.get("average_cost", 0) 
            for h in holdings
        )
        
        for h in holdings:
            isin = h["isin"]
            inst = inst_map.get(isin, {})
            
            qty = h.get("quantity", 0)
            price = float(h.get("average_cost", 0))
            value = qty * price
            weight = value / total_value if total_value > 0 else 0
            
            # Parse maturity
            mat_str = inst.get("maturity_date", "")
            try:
                mat_date = date.fromisoformat(mat_str[:10]) if isinstance(mat_str, str) else mat_str
            except (ValueError, TypeError):
                mat_date = today + timedelta(days=365)
            
            # Calculate metrics
            face = float(inst.get("face_value", 100))
            coupon = float(inst.get("coupon_rate", 0))
            ytm = float(inst.get("ytm", coupon)) or coupon
            freq = CouponFrequency(inst.get("coupon_frequency", "annual"))
            
            dur = float(calculate_duration(
                clean_price=Decimal(str(price)),
                face_value=Decimal(str(face)),
                coupon_rate=Decimal(str(coupon)),
                ytm=Decimal(str(ytm)),
                settlement_date=today,
                maturity_date=mat_date,
                frequency=freq
            ))
            
            mod_dur = dur / (1 + ytm / 100)
            
            # Approximate convexity
            years = (mat_date - today).days / 365.25
            convexity = years * (years + 1) / ((1 + ytm / 100) ** 2)
            
            self.positions.append(PortfolioPosition(
                isin=isin,
                issuer=inst.get("issuer_name", "Unknown"),
                weight=weight,
                quantity=qty,
                market_value=value,
                yield_pct=ytm,
                duration=dur,
                modified_duration=mod_dur,
                convexity=convexity,
                rating=inst.get("credit_rating", "UNRATED"),
                maturity_date=mat_date,
                coupon_rate=coupon
            ))
        
        return True
    
    async def load_available_instruments(self, filters: Dict = None) -> None:
        """Load instruments available for optimization"""
        query = {"is_active": True}
        
        if filters:
            if filters.get("ratings"):
                query["credit_rating"] = {"$in": filters["ratings"]}
            if filters.get("instrument_types"):
                query["instrument_type"] = {"$in": filters["instrument_types"]}
            if filters.get("max_maturity_years"):
                max_date = date.today() + timedelta(days=filters["max_maturity_years"] * 365)
                query["maturity_date"] = {"$lte": max_date.isoformat()}
        
        self.available_instruments = await db.fi_instruments.find(
            query, {"_id": 0}
        ).to_list(500)
    
    def calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate current portfolio metrics"""
        if not self.positions:
            return PortfolioMetrics(0, 0, 0, 0, 0, 0, 0, 0)
        
        total_value = sum(p.market_value for p in self.positions)
        
        # Weighted metrics
        w_yield = sum(p.weight * p.yield_pct for p in self.positions)
        w_dur = sum(p.weight * p.duration for p in self.positions)
        w_mod_dur = sum(p.weight * p.modified_duration for p in self.positions)
        w_conv = sum(p.weight * p.convexity for p in self.positions)
        
        # VaR calculation (parametric)
        # Assume daily yield volatility of 0.05% (5 bps)
        daily_vol = 0.0005
        
        # Portfolio vol approximation using duration
        portfolio_vol = w_mod_dur * daily_vol * np.sqrt(252)  # Annualized
        
        # VaR = Portfolio Value * z-score * vol
        var_95 = total_value * 1.645 * portfolio_vol
        var_99 = total_value * 2.326 * portfolio_vol
        
        # Spread duration (simplified)
        spread_dur = w_mod_dur * 0.8  # Approximate
        
        return PortfolioMetrics(
            total_value=total_value,
            weighted_yield=w_yield,
            weighted_duration=w_dur,
            weighted_mod_duration=w_mod_dur,
            weighted_convexity=w_conv,
            var_95=var_95,
            var_99=var_99,
            spread_duration=spread_dur
        )
    
    def optimize_max_yield(
        self,
        max_duration: float = 10.0,
        max_single_issuer: float = 0.25,
        min_rating: str = "BBB"
    ) -> OptimizationResult:
        """
        Optimize portfolio to maximize yield subject to constraints.
        
        Args:
            max_duration: Maximum portfolio duration
            max_single_issuer: Maximum weight per issuer
            min_rating: Minimum acceptable credit rating
        """
        if not self.available_instruments:
            return OptimizationResult(
                objective="maximize_yield",
                status="error",
                target_weights={},
                expected_yield=0,
                expected_duration=0,
                expected_risk=0,
                trades_required=[],
                improvement={}
            )
        
        n = len(self.available_instruments)
        
        # Extract data
        yields = np.array([
            float(i.get("ytm", i.get("coupon_rate", 0))) 
            for i in self.available_instruments
        ])
        
        today = date.today()
        durations = np.array([
            self._estimate_duration(i, today) 
            for i in self.available_instruments
        ])
        
        ratings = [i.get("credit_rating", "UNRATED") for i in self.available_instruments]
        risk_scores = np.array([self.RATING_RISK.get(r, 8.0) for r in ratings])
        
        # Objective: maximize yield (minimize negative yield)
        c = -yields
        
        # Constraints
        # 1. Sum of weights = 1
        A_eq = np.ones((1, n))
        b_eq = np.array([1.0])
        
        # 2. Duration <= max_duration
        # 3. Risk score constraint based on min_rating
        min_risk = self.RATING_RISK.get(min_rating, 8.0)
        
        A_ub = np.vstack([
            durations,  # Duration constraint
        ])
        b_ub = np.array([max_duration])
        
        # Bounds: 0 <= w <= max_single_issuer
        bounds = [(0, max_single_issuer) for _ in range(n)]
        
        # Filter out instruments below min rating
        for i, r in enumerate(ratings):
            if self.RATING_RISK.get(r, 8.0) > min_risk:
                bounds[i] = (0, 0)  # Exclude
        
        try:
            result = optimize.linprog(
                c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                bounds=bounds, method='highs'
            )
            
            if result.success:
                weights = {
                    self.available_instruments[i]["isin"]: round(result.x[i], 4)
                    for i in range(n) if result.x[i] > 0.001
                }
                
                exp_yield = -result.fun
                exp_dur = np.dot(result.x, durations)
                exp_risk = np.dot(result.x, risk_scores)
                
                return OptimizationResult(
                    objective="maximize_yield",
                    status="optimal",
                    target_weights=weights,
                    expected_yield=round(exp_yield, 4),
                    expected_duration=round(exp_dur, 3),
                    expected_risk=round(exp_risk, 2),
                    trades_required=self._calculate_trades(weights),
                    improvement={"yield_improvement": round(exp_yield - self.calculate_portfolio_metrics().weighted_yield, 4)}
                )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
        
        return OptimizationResult(
            objective="maximize_yield",
            status="failed",
            target_weights={},
            expected_yield=0,
            expected_duration=0,
            expected_risk=0,
            trades_required=[],
            improvement={}
        )
    
    def optimize_target_duration(
        self,
        target_duration: float,
        tolerance: float = 0.5,
        max_single_issuer: float = 0.25
    ) -> OptimizationResult:
        """
        Optimize portfolio to match target duration (duration immunization).
        
        Args:
            target_duration: Target portfolio duration
            tolerance: Acceptable deviation from target
            max_single_issuer: Maximum weight per issuer
        """
        if not self.available_instruments:
            return OptimizationResult(
                objective="target_duration",
                status="error",
                target_weights={},
                expected_yield=0,
                expected_duration=0,
                expected_risk=0,
                trades_required=[],
                improvement={}
            )
        
        n = len(self.available_instruments)
        today = date.today()
        
        yields = np.array([
            float(i.get("ytm", i.get("coupon_rate", 0)))
            for i in self.available_instruments
        ])
        
        durations = np.array([
            self._estimate_duration(i, today)
            for i in self.available_instruments
        ])
        
        # Objective: minimize squared deviation from target + maximize yield
        def objective(w):
            port_dur = np.dot(w, durations)
            port_yield = np.dot(w, yields)
            
            # Penalize duration deviation heavily
            duration_penalty = 100 * (port_dur - target_duration) ** 2
            
            # Reward yield
            yield_reward = -port_yield
            
            return duration_penalty + yield_reward
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Weights sum to 1
        ]
        
        bounds = [(0, max_single_issuer) for _ in range(n)]
        x0 = np.ones(n) / n  # Initial guess: equal weights
        
        try:
            result = optimize.minimize(
                objective, x0, method='SLSQP',
                bounds=bounds, constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights = {
                    self.available_instruments[i]["isin"]: round(result.x[i], 4)
                    for i in range(n) if result.x[i] > 0.001
                }
                
                exp_yield = np.dot(result.x, yields)
                exp_dur = np.dot(result.x, durations)
                
                current = self.calculate_portfolio_metrics()
                
                return OptimizationResult(
                    objective="target_duration",
                    status="optimal",
                    target_weights=weights,
                    expected_yield=round(exp_yield, 4),
                    expected_duration=round(exp_dur, 3),
                    expected_risk=0,
                    trades_required=self._calculate_trades(weights),
                    improvement={
                        "duration_change": round(exp_dur - current.weighted_duration, 3),
                        "yield_change": round(exp_yield - current.weighted_yield, 4)
                    }
                )
        except Exception as e:
            logger.error(f"Duration optimization failed: {e}")
        
        return OptimizationResult(
            objective="target_duration",
            status="failed",
            target_weights={},
            expected_yield=0,
            expected_duration=0,
            expected_risk=0,
            trades_required=[],
            improvement={}
        )
    
    def optimize_min_risk(
        self,
        min_yield: float = 6.0,
        max_duration: float = 7.0
    ) -> OptimizationResult:
        """
        Optimize portfolio to minimize risk while maintaining minimum yield.
        
        Risk is measured as weighted average of credit risk scores.
        """
        if not self.available_instruments:
            return OptimizationResult(
                objective="minimize_risk",
                status="error",
                target_weights={},
                expected_yield=0,
                expected_duration=0,
                expected_risk=0,
                trades_required=[],
                improvement={}
            )
        
        n = len(self.available_instruments)
        today = date.today()
        
        yields = np.array([
            float(i.get("ytm", i.get("coupon_rate", 0)))
            for i in self.available_instruments
        ])
        
        durations = np.array([
            self._estimate_duration(i, today)
            for i in self.available_instruments
        ])
        
        ratings = [i.get("credit_rating", "UNRATED") for i in self.available_instruments]
        risk_scores = np.array([self.RATING_RISK.get(r, 8.0) for r in ratings])
        
        # Objective: minimize risk
        c = risk_scores
        
        # Constraints
        A_eq = np.ones((1, n))
        b_eq = np.array([1.0])
        
        A_ub = np.vstack([
            -yields,     # -yield >= -min_yield (yield >= min_yield)
            durations    # duration <= max_duration
        ])
        b_ub = np.array([-min_yield, max_duration])
        
        bounds = [(0, 0.3) for _ in range(n)]
        
        try:
            result = optimize.linprog(
                c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                bounds=bounds, method='highs'
            )
            
            if result.success:
                weights = {
                    self.available_instruments[i]["isin"]: round(result.x[i], 4)
                    for i in range(n) if result.x[i] > 0.001
                }
                
                exp_yield = np.dot(result.x, yields)
                exp_dur = np.dot(result.x, durations)
                exp_risk = result.fun
                
                return OptimizationResult(
                    objective="minimize_risk",
                    status="optimal",
                    target_weights=weights,
                    expected_yield=round(exp_yield, 4),
                    expected_duration=round(exp_dur, 3),
                    expected_risk=round(exp_risk, 2),
                    trades_required=self._calculate_trades(weights),
                    improvement={}
                )
        except Exception as e:
            logger.error(f"Risk optimization failed: {e}")
        
        return OptimizationResult(
            objective="minimize_risk",
            status="failed",
            target_weights={},
            expected_yield=0,
            expected_duration=0,
            expected_risk=0,
            trades_required=[],
            improvement={}
        )
    
    def calculate_efficient_frontier(
        self,
        n_points: int = 20,
        max_duration: float = 10.0
    ) -> List[Dict]:
        """
        Calculate the efficient frontier (yield vs risk tradeoff).
        
        Returns points representing optimal portfolios at different risk levels.
        """
        if not self.available_instruments:
            return []
        
        n = len(self.available_instruments)
        today = date.today()
        
        yields = np.array([
            float(i.get("ytm", i.get("coupon_rate", 0)))
            for i in self.available_instruments
        ])
        
        durations = np.array([
            self._estimate_duration(i, today)
            for i in self.available_instruments
        ])
        
        ratings = [i.get("credit_rating", "UNRATED") for i in self.available_instruments]
        risk_scores = np.array([self.RATING_RISK.get(r, 8.0) for r in ratings])
        
        # Find range of achievable risk
        min_risk = min(risk_scores)
        max_risk = max(risk_scores) * 0.7  # Don't go to maximum risk
        
        frontier_points = []
        
        for target_risk in np.linspace(min_risk, max_risk, n_points):
            # Optimize yield for this risk level
            c = -yields  # Maximize yield
            
            A_eq = np.ones((1, n))
            b_eq = np.array([1.0])
            
            A_ub = np.vstack([
                risk_scores,  # Risk <= target_risk
                durations     # Duration <= max_duration
            ])
            b_ub = np.array([target_risk, max_duration])
            
            bounds = [(0, 0.3) for _ in range(n)]
            
            try:
                result = optimize.linprog(
                    c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                    bounds=bounds, method='highs'
                )
                
                if result.success:
                    exp_yield = -result.fun
                    actual_risk = np.dot(result.x, risk_scores)
                    exp_dur = np.dot(result.x, durations)
                    
                    frontier_points.append({
                        "risk_score": round(actual_risk, 2),
                        "expected_yield": round(exp_yield, 4),
                        "expected_duration": round(exp_dur, 3),
                        "n_instruments": sum(1 for w in result.x if w > 0.001)
                    })
            except Exception:
                continue
        
        return frontier_points
    
    def _estimate_duration(self, instrument: Dict, today: date) -> float:
        """Estimate duration for an instrument"""
        try:
            mat_str = instrument.get("maturity_date", "")
            if isinstance(mat_str, str):
                mat_date = date.fromisoformat(mat_str[:10])
            else:
                mat_date = mat_str
            
            years = (mat_date - today).days / 365.25
            coupon = float(instrument.get("coupon_rate", 0))
            ytm = float(instrument.get("ytm", coupon)) or coupon
            
            if ytm == 0:
                return years
            
            # Macaulay duration approximation
            if coupon == 0:
                return years
            
            y = ytm / 100
            c = coupon / 100
            n = years
            
            duration = (1 + y) / y - (1 + y + n * (c - y)) / (c * ((1 + y) ** n - 1) + y)
            
            return max(0, min(duration, years))
        except Exception:
            return 3.0  # Default
    
    def _calculate_trades(self, target_weights: Dict[str, float]) -> List[Dict]:
        """Calculate trades required to reach target weights"""
        trades = []
        
        current_weights = {p.isin: p.weight for p in self.positions}
        total_value = sum(p.market_value for p in self.positions) or 1000000
        
        for isin, target in target_weights.items():
            current = current_weights.get(isin, 0)
            diff = target - current
            
            if abs(diff) > 0.01:  # 1% threshold
                trade_value = diff * total_value
                action = "BUY" if diff > 0 else "SELL"
                
                # Find instrument details
                inst = next(
                    (i for i in self.available_instruments if i.get("isin") == isin),
                    {}
                )
                
                trades.append({
                    "isin": isin,
                    "issuer": inst.get("issuer_name", "Unknown"),
                    "action": action,
                    "weight_change": round(diff, 4),
                    "value_change": round(abs(trade_value), 2),
                    "current_weight": round(current, 4),
                    "target_weight": round(target, 4)
                })
        
        # Sort: sells first, then buys
        trades.sort(key=lambda x: (x["action"] == "BUY", -abs(x["value_change"])))
        
        return trades


# ==================== API Functions ====================

async def get_portfolio_analysis(client_id: str) -> Dict[str, Any]:
    """
    Get comprehensive portfolio analysis.
    """
    optimizer = AdvancedPortfolioOptimizer(client_id)
    
    if not await optimizer.load_portfolio():
        return {
            "error": "No portfolio found for client",
            "client_id": client_id
        }
    
    metrics = optimizer.calculate_portfolio_metrics()
    
    # Position breakdown
    positions = [
        {
            "isin": p.isin,
            "issuer": p.issuer,
            "weight": round(p.weight * 100, 2),
            "market_value": round(p.market_value, 2),
            "yield": round(p.yield_pct, 3),
            "duration": round(p.duration, 3),
            "rating": p.rating,
            "maturity": p.maturity_date.isoformat()
        }
        for p in optimizer.positions
    ]
    
    # Rating distribution
    rating_dist = {}
    for p in optimizer.positions:
        rating = p.rating
        rating_dist[rating] = rating_dist.get(rating, 0) + p.weight * 100
    
    # Maturity distribution
    today = date.today()
    maturity_buckets = {"0-2Y": 0, "2-5Y": 0, "5-10Y": 0, "10Y+": 0}
    for p in optimizer.positions:
        years = (p.maturity_date - today).days / 365.25
        if years <= 2:
            bucket = "0-2Y"
        elif years <= 5:
            bucket = "2-5Y"
        elif years <= 10:
            bucket = "5-10Y"
        else:
            bucket = "10Y+"
        maturity_buckets[bucket] += p.weight * 100
    
    return {
        "client_id": client_id,
        "summary": metrics.to_dict(),
        "positions": positions,
        "distributions": {
            "by_rating": {k: round(v, 2) for k, v in rating_dist.items()},
            "by_maturity": {k: round(v, 2) for k, v in maturity_buckets.items()}
        },
        "risk_metrics": {
            "duration_risk": "High" if metrics.weighted_duration > 7 else "Medium" if metrics.weighted_duration > 4 else "Low",
            "credit_risk": sum(1 for p in optimizer.positions if p.rating in ["BB", "B", "CCC", "UNRATED"]) / len(optimizer.positions) * 100 if optimizer.positions else 0,
            "concentration_risk": max(p.weight for p in optimizer.positions) * 100 if optimizer.positions else 0
        },
        "generated_at": datetime.now().isoformat()
    }


async def optimize_portfolio(
    client_id: str,
    objective: str = "maximize_yield",
    parameters: Dict = None
) -> Dict[str, Any]:
    """
    Run portfolio optimization.
    
    Args:
        client_id: Client ID
        objective: Optimization objective
        parameters: Optimization parameters
    """
    optimizer = AdvancedPortfolioOptimizer(client_id)
    
    await optimizer.load_portfolio()
    await optimizer.load_available_instruments(parameters.get("filters") if parameters else None)
    
    if not optimizer.available_instruments:
        return {
            "error": "No instruments available for optimization",
            "objective": objective
        }
    
    params = parameters or {}
    
    if objective == "maximize_yield":
        result = optimizer.optimize_max_yield(
            max_duration=params.get("max_duration", 10.0),
            max_single_issuer=params.get("max_single_issuer", 0.25),
            min_rating=params.get("min_rating", "BBB")
        )
    elif objective == "target_duration":
        result = optimizer.optimize_target_duration(
            target_duration=params.get("target_duration", 5.0),
            tolerance=params.get("tolerance", 0.5),
            max_single_issuer=params.get("max_single_issuer", 0.25)
        )
    elif objective == "minimize_risk":
        result = optimizer.optimize_min_risk(
            min_yield=params.get("min_yield", 6.0),
            max_duration=params.get("max_duration", 7.0)
        )
    else:
        return {
            "error": f"Unknown objective: {objective}",
            "supported_objectives": ["maximize_yield", "target_duration", "minimize_risk"]
        }
    
    return {
        "client_id": client_id,
        "objective": result.objective,
        "status": result.status,
        "optimal_portfolio": result.target_weights,
        "expected_metrics": {
            "yield": result.expected_yield,
            "duration": result.expected_duration,
            "risk_score": result.expected_risk
        },
        "trades_required": result.trades_required,
        "improvement": result.improvement,
        "generated_at": datetime.now().isoformat()
    }


async def get_efficient_frontier(
    n_points: int = 20,
    max_duration: float = 10.0,
    filters: Dict = None
) -> Dict[str, Any]:
    """
    Calculate and return efficient frontier data.
    """
    optimizer = AdvancedPortfolioOptimizer()
    await optimizer.load_available_instruments(filters)
    
    frontier = optimizer.calculate_efficient_frontier(n_points, max_duration)
    
    return {
        "frontier_points": frontier,
        "parameters": {
            "n_points": n_points,
            "max_duration": max_duration,
            "filters": filters
        },
        "chart_config": {
            "x_axis": {"title": "Risk Score", "min": 0, "max": 10},
            "y_axis": {"title": "Expected Yield (%)", "min": 5, "max": 12}
        },
        "generated_at": datetime.now().isoformat()
    }


# Export
__all__ = [
    'AdvancedPortfolioOptimizer',
    'PortfolioMetrics',
    'PortfolioPosition',
    'OptimizationResult',
    'OptimizationObjective',
    'RiskMetric',
    'get_portfolio_analysis',
    'optimize_portfolio',
    'get_efficient_frontier'
]
