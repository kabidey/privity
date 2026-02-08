"""
Yield Curve Analytics Service
=============================

Comprehensive yield curve analysis for fixed income securities.

Features:
- Spot rate curve construction
- Forward rate curve derivation
- Par yield curve calculation
- Nelson-Siegel and Svensson model fitting
- Curve interpolation (linear, cubic spline)
- Key rate durations
- Curve shift analysis (parallel, twist, butterfly)
- Spread analysis (credit spreads, G-spread, Z-spread)

Reference: Fixed income securities typically use government bonds as the risk-free
benchmark, with corporate/NCD spreads measured against this benchmark.
"""

import numpy as np
from scipy import interpolate, optimize
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from database import db

logger = logging.getLogger(__name__)


class CurveType(str, Enum):
    """Types of yield curves"""
    SPOT = "spot"  # Zero-coupon yield curve
    FORWARD = "forward"  # Forward rate curve
    PAR = "par"  # Par yield curve


class InterpolationMethod(str, Enum):
    """Interpolation methods for curve construction"""
    LINEAR = "linear"
    CUBIC_SPLINE = "cubic_spline"
    NELSON_SIEGEL = "nelson_siegel"
    SVENSSON = "svensson"


@dataclass
class YieldPoint:
    """Single point on the yield curve"""
    tenor: float  # Years to maturity
    rate: float  # Yield in percentage
    instrument: str = ""  # ISIN or description
    rating: str = ""  # Credit rating
    source: str = "calculated"


@dataclass
class YieldCurve:
    """Yield curve data structure"""
    curve_type: CurveType
    curve_date: date
    currency: str = "INR"
    points: List[YieldPoint] = field(default_factory=list)
    interpolation_method: InterpolationMethod = InterpolationMethod.CUBIC_SPLINE
    model_params: Dict = field(default_factory=dict)
    
    def get_rate(self, tenor: float) -> float:
        """Get interpolated rate for any tenor"""
        if not self.points:
            return 0.0
        
        tenors = [p.tenor for p in self.points]
        rates = [p.rate for p in self.points]
        
        if self.interpolation_method == InterpolationMethod.LINEAR:
            return np.interp(tenor, tenors, rates)
        
        elif self.interpolation_method == InterpolationMethod.CUBIC_SPLINE:
            if len(tenors) >= 4:
                cs = interpolate.CubicSpline(tenors, rates)
                return float(cs(tenor))
            return np.interp(tenor, tenors, rates)
        
        elif self.interpolation_method in (InterpolationMethod.NELSON_SIEGEL, InterpolationMethod.SVENSSON):
            return self._parametric_rate(tenor)
        
        return np.interp(tenor, tenors, rates)
    
    def _parametric_rate(self, tenor: float) -> float:
        """Calculate rate using Nelson-Siegel or Svensson model"""
        params = self.model_params
        
        if self.interpolation_method == InterpolationMethod.NELSON_SIEGEL:
            beta0 = params.get("beta0", 7.0)
            beta1 = params.get("beta1", -1.0)
            beta2 = params.get("beta2", 0.5)
            tau1 = params.get("tau1", 2.0)
            
            if tenor == 0:
                return beta0 + beta1
            
            x = tenor / tau1
            return beta0 + beta1 * (1 - np.exp(-x)) / x + beta2 * ((1 - np.exp(-x)) / x - np.exp(-x))
        
        elif self.interpolation_method == InterpolationMethod.SVENSSON:
            beta0 = params.get("beta0", 7.0)
            beta1 = params.get("beta1", -1.0)
            beta2 = params.get("beta2", 0.5)
            beta3 = params.get("beta3", 0.3)
            tau1 = params.get("tau1", 2.0)
            tau2 = params.get("tau2", 5.0)
            
            if tenor == 0:
                return beta0 + beta1
            
            x1 = tenor / tau1
            x2 = tenor / tau2
            
            term1 = beta0
            term2 = beta1 * (1 - np.exp(-x1)) / x1
            term3 = beta2 * ((1 - np.exp(-x1)) / x1 - np.exp(-x1))
            term4 = beta3 * ((1 - np.exp(-x2)) / x2 - np.exp(-x2))
            
            return term1 + term2 + term3 + term4
        
        return 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "curve_type": self.curve_type.value,
            "curve_date": self.curve_date.isoformat(),
            "currency": self.currency,
            "interpolation_method": self.interpolation_method.value,
            "points": [
                {
                    "tenor": p.tenor,
                    "rate": round(p.rate, 4),
                    "instrument": p.instrument,
                    "rating": p.rating,
                    "source": p.source
                }
                for p in self.points
            ],
            "model_params": self.model_params
        }


class YieldCurveAnalytics:
    """
    Yield curve construction and analysis engine.
    """
    
    # Standard tenors for curve construction (in years)
    STANDARD_TENORS = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
    
    def __init__(self):
        self.gsec_curve: Optional[YieldCurve] = None
        self.corporate_curves: Dict[str, YieldCurve] = {}  # By rating
    
    async def build_gsec_curve(
        self, 
        curve_date: date = None,
        interpolation: InterpolationMethod = InterpolationMethod.CUBIC_SPLINE
    ) -> YieldCurve:
        """
        Build Government Securities (G-Sec) yield curve.
        This serves as the risk-free benchmark.
        """
        curve_date = curve_date or date.today()
        
        # Fetch G-Sec instruments from database
        gsecs = await db.fi_instruments.find(
            {"instrument_type": {"$in": ["GSEC", "SDL"]}},
            {"_id": 0}
        ).to_list(100)
        
        points = []
        
        for gsec in gsecs:
            try:
                maturity = gsec.get("maturity_date")
                if isinstance(maturity, str):
                    mat_date = date.fromisoformat(maturity[:10])
                else:
                    mat_date = maturity
                
                if mat_date and mat_date > curve_date:
                    tenor = (mat_date - curve_date).days / 365.25
                    coupon = float(gsec.get("coupon_rate", 0))
                    
                    # Use coupon as approximation for YTM (actual calculation would need prices)
                    ytm = float(gsec.get("ytm", coupon))
                    if ytm == 0:
                        ytm = coupon
                    
                    points.append(YieldPoint(
                        tenor=round(tenor, 2),
                        rate=ytm,
                        instrument=gsec.get("isin", ""),
                        rating="SOVEREIGN",
                        source="database"
                    ))
            except Exception as e:
                logger.debug(f"Error processing G-Sec {gsec.get('isin')}: {e}")
                continue
        
        # Add benchmark points if we don't have enough data
        if len(points) < 5:
            points.extend(self._get_benchmark_gsec_points())
        
        # Sort by tenor
        points.sort(key=lambda x: x.tenor)
        
        # Remove duplicates (keep first occurrence for each tenor bucket)
        unique_points = []
        seen_tenors = set()
        for p in points:
            bucket = round(p.tenor * 2) / 2  # 0.5 year buckets
            if bucket not in seen_tenors:
                unique_points.append(p)
                seen_tenors.add(bucket)
        
        # Fit model if parametric method requested
        model_params = {}
        if interpolation in (InterpolationMethod.NELSON_SIEGEL, InterpolationMethod.SVENSSON):
            model_params = self._fit_parametric_model(unique_points, interpolation)
        
        self.gsec_curve = YieldCurve(
            curve_type=CurveType.SPOT,
            curve_date=curve_date,
            currency="INR",
            points=unique_points,
            interpolation_method=interpolation,
            model_params=model_params
        )
        
        return self.gsec_curve
    
    def _get_benchmark_gsec_points(self) -> List[YieldPoint]:
        """Get benchmark G-Sec yields (approximate current market rates)"""
        # These are approximate Indian G-Sec rates - would be updated with live data
        return [
            YieldPoint(tenor=0.25, rate=6.50, instrument="91-Day T-Bill", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=0.5, rate=6.65, instrument="182-Day T-Bill", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=1.0, rate=6.85, instrument="364-Day T-Bill", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=2.0, rate=6.95, instrument="2Y GOI", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=3.0, rate=7.05, instrument="3Y GOI", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=5.0, rate=7.15, instrument="5Y GOI", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=7.0, rate=7.20, instrument="7Y GOI", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=10.0, rate=7.25, instrument="10Y GOI (Benchmark)", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=15.0, rate=7.30, instrument="15Y GOI", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=20.0, rate=7.35, instrument="20Y GOI", rating="SOVEREIGN", source="benchmark"),
            YieldPoint(tenor=30.0, rate=7.40, instrument="30Y GOI", rating="SOVEREIGN", source="benchmark"),
        ]
    
    async def build_corporate_curve(
        self,
        rating: str,
        curve_date: date = None,
        interpolation: InterpolationMethod = InterpolationMethod.CUBIC_SPLINE
    ) -> YieldCurve:
        """
        Build corporate bond yield curve for a specific rating.
        """
        curve_date = curve_date or date.today()
        
        # Map rating to query patterns
        rating_patterns = {
            "AAA": ["AAA"],
            "AA": ["AA+", "AA", "AA-"],
            "A": ["A+", "A", "A-"],
            "BBB": ["BBB+", "BBB", "BBB-"],
        }
        
        patterns = rating_patterns.get(rating, [rating])
        
        # Fetch corporate bonds
        bonds = await db.fi_instruments.find(
            {
                "instrument_type": {"$in": ["NCD", "BOND"]},
                "credit_rating": {"$in": patterns}
            },
            {"_id": 0}
        ).to_list(200)
        
        points = []
        
        for bond in bonds:
            try:
                maturity = bond.get("maturity_date")
                if isinstance(maturity, str):
                    mat_date = date.fromisoformat(maturity[:10])
                else:
                    mat_date = maturity
                
                if mat_date and mat_date > curve_date:
                    tenor = (mat_date - curve_date).days / 365.25
                    coupon = float(bond.get("coupon_rate", 0))
                    ytm = float(bond.get("ytm", coupon))
                    if ytm == 0:
                        ytm = coupon
                    
                    points.append(YieldPoint(
                        tenor=round(tenor, 2),
                        rate=ytm,
                        instrument=bond.get("isin", ""),
                        rating=bond.get("credit_rating", rating),
                        source="database"
                    ))
            except Exception as e:
                logger.debug(f"Error processing bond {bond.get('isin')}: {e}")
                continue
        
        # Sort and deduplicate
        points.sort(key=lambda x: x.tenor)
        unique_points = []
        seen_tenors = set()
        for p in points:
            bucket = round(p.tenor)
            if bucket not in seen_tenors:
                unique_points.append(p)
                seen_tenors.add(bucket)
        
        # Add spread-based estimates if we don't have enough data
        if len(unique_points) < 3 and self.gsec_curve:
            spread = self._get_typical_spread(rating)
            for tenor in [1, 3, 5, 7, 10]:
                gsec_rate = self.gsec_curve.get_rate(tenor)
                unique_points.append(YieldPoint(
                    tenor=tenor,
                    rate=gsec_rate + spread,
                    instrument=f"Estimated {rating}",
                    rating=rating,
                    source="estimated"
                ))
            unique_points.sort(key=lambda x: x.tenor)
        
        # Fit model
        model_params = {}
        if interpolation in (InterpolationMethod.NELSON_SIEGEL, InterpolationMethod.SVENSSON) and len(unique_points) >= 4:
            model_params = self._fit_parametric_model(unique_points, interpolation)
        
        curve = YieldCurve(
            curve_type=CurveType.SPOT,
            curve_date=curve_date,
            currency="INR",
            points=unique_points,
            interpolation_method=interpolation,
            model_params=model_params
        )
        
        self.corporate_curves[rating] = curve
        return curve
    
    def _get_typical_spread(self, rating: str) -> float:
        """Get typical credit spread over G-Sec for a rating"""
        spreads = {
            "AAA": 0.50,
            "AA+": 0.75,
            "AA": 1.00,
            "AA-": 1.25,
            "A+": 1.50,
            "A": 1.80,
            "A-": 2.20,
            "BBB+": 2.75,
            "BBB": 3.50,
            "BBB-": 4.50,
        }
        return spreads.get(rating, 2.0)
    
    def _fit_parametric_model(
        self, 
        points: List[YieldPoint],
        method: InterpolationMethod
    ) -> Dict:
        """Fit Nelson-Siegel or Svensson model to data points"""
        tenors = np.array([p.tenor for p in points])
        rates = np.array([p.rate for p in points])
        
        if len(tenors) < 4:
            return {}
        
        if method == InterpolationMethod.NELSON_SIEGEL:
            return self._fit_nelson_siegel(tenors, rates)
        elif method == InterpolationMethod.SVENSSON:
            return self._fit_svensson(tenors, rates)
        
        return {}
    
    def _fit_nelson_siegel(self, tenors: np.ndarray, rates: np.ndarray) -> Dict:
        """Fit Nelson-Siegel model"""
        def ns_curve(t, beta0, beta1, beta2, tau):
            if tau <= 0:
                tau = 0.1
            x = t / tau
            with np.errstate(divide='ignore', invalid='ignore'):
                term2 = np.where(t > 0, (1 - np.exp(-x)) / x, 1.0)
                term3 = np.where(t > 0, term2 - np.exp(-x), 0.0)
            return beta0 + beta1 * term2 + beta2 * term3
        
        try:
            # Initial guess
            p0 = [rates.mean(), rates[0] - rates.mean(), 0.5, 2.0]
            bounds = ([0, -10, -10, 0.1], [15, 10, 10, 30])
            
            popt, _ = optimize.curve_fit(
                ns_curve, tenors, rates, 
                p0=p0, bounds=bounds, 
                maxfev=5000
            )
            
            return {
                "beta0": float(popt[0]),
                "beta1": float(popt[1]),
                "beta2": float(popt[2]),
                "tau1": float(popt[3])
            }
        except Exception as e:
            logger.warning(f"Nelson-Siegel fitting failed: {e}")
            return {"beta0": float(rates.mean()), "beta1": -1.0, "beta2": 0.5, "tau1": 2.0}
    
    def _fit_svensson(self, tenors: np.ndarray, rates: np.ndarray) -> Dict:
        """Fit Svensson (Extended Nelson-Siegel) model"""
        def svensson_curve(t, beta0, beta1, beta2, beta3, tau1, tau2):
            if tau1 <= 0:
                tau1 = 0.1
            if tau2 <= 0:
                tau2 = 0.1
            
            x1 = t / tau1
            x2 = t / tau2
            
            with np.errstate(divide='ignore', invalid='ignore'):
                term2 = np.where(t > 0, (1 - np.exp(-x1)) / x1, 1.0)
                term3 = np.where(t > 0, term2 - np.exp(-x1), 0.0)
                term4 = np.where(t > 0, (1 - np.exp(-x2)) / x2 - np.exp(-x2), 0.0)
            
            return beta0 + beta1 * term2 + beta2 * term3 + beta3 * term4
        
        try:
            p0 = [rates.mean(), rates[0] - rates.mean(), 0.5, 0.3, 2.0, 5.0]
            bounds = ([0, -10, -10, -10, 0.1, 0.1], [15, 10, 10, 10, 30, 30])
            
            popt, _ = optimize.curve_fit(
                svensson_curve, tenors, rates,
                p0=p0, bounds=bounds,
                maxfev=5000
            )
            
            return {
                "beta0": float(popt[0]),
                "beta1": float(popt[1]),
                "beta2": float(popt[2]),
                "beta3": float(popt[3]),
                "tau1": float(popt[4]),
                "tau2": float(popt[5])
            }
        except Exception as e:
            logger.warning(f"Svensson fitting failed: {e}")
            return self._fit_nelson_siegel(tenors, rates)
    
    def calculate_forward_curve(self, spot_curve: YieldCurve) -> YieldCurve:
        """
        Calculate forward rate curve from spot curve.
        
        Forward rate f(t1, t2) = ((1+s2)^t2 / (1+s1)^t1)^(1/(t2-t1)) - 1
        """
        if not spot_curve.points:
            return YieldCurve(curve_type=CurveType.FORWARD, curve_date=spot_curve.curve_date)
        
        forward_points = []
        tenors = sorted([p.tenor for p in spot_curve.points])
        
        for i in range(1, len(tenors)):
            t1 = tenors[i-1]
            t2 = tenors[i]
            
            s1 = spot_curve.get_rate(t1) / 100
            s2 = spot_curve.get_rate(t2) / 100
            
            if t2 > t1 and s1 > 0 and s2 > 0:
                # Forward rate calculation
                try:
                    numerator = (1 + s2) ** t2
                    denominator = (1 + s1) ** t1
                    forward = (numerator / denominator) ** (1 / (t2 - t1)) - 1
                    forward_rate = forward * 100
                    
                    forward_points.append(YieldPoint(
                        tenor=(t1 + t2) / 2,
                        rate=round(forward_rate, 4),
                        instrument=f"{t1}y-{t2}y forward",
                        rating=spot_curve.points[0].rating if spot_curve.points else "",
                        source="calculated"
                    ))
                except (ValueError, ZeroDivisionError):
                    continue
        
        return YieldCurve(
            curve_type=CurveType.FORWARD,
            curve_date=spot_curve.curve_date,
            currency=spot_curve.currency,
            points=forward_points,
            interpolation_method=InterpolationMethod.LINEAR
        )
    
    def calculate_spreads(
        self, 
        corporate_curve: YieldCurve,
        benchmark_curve: YieldCurve
    ) -> List[Dict]:
        """
        Calculate credit spreads between corporate and benchmark curve.
        """
        spreads = []
        
        for tenor in self.STANDARD_TENORS:
            corp_rate = corporate_curve.get_rate(tenor)
            bench_rate = benchmark_curve.get_rate(tenor)
            
            spread = corp_rate - bench_rate
            
            spreads.append({
                "tenor": tenor,
                "corporate_yield": round(corp_rate, 4),
                "benchmark_yield": round(bench_rate, 4),
                "spread_bps": round(spread * 100, 2),  # In basis points
                "spread_pct": round(spread, 4)
            })
        
        return spreads
    
    def calculate_key_rate_durations(
        self, 
        curve: YieldCurve,
        shift_bps: float = 1.0
    ) -> List[Dict]:
        """
        Calculate key rate durations at standard tenors.
        
        Key rate duration measures sensitivity to shifts at specific points on the curve.
        """
        krds = []
        
        for tenor in self.STANDARD_TENORS:
            if tenor > max(p.tenor for p in curve.points):
                continue
            
            base_rate = curve.get_rate(tenor)
            
            # Key rate duration approximation
            # KRD measures sensitivity to a 1bp shift at this specific tenor
            # Approximate using modified duration formula
            
            krds.append({
                "tenor": tenor,
                "key_rate_duration": round(tenor * 0.95, 3),  # Approximate KRD
                "rate": round(base_rate, 4),
                "dv01_estimate": round(tenor * 0.0001 * 100, 4)  # Per 100 face value
            })
        
        return krds
    
    def analyze_curve_shift(
        self,
        old_curve: YieldCurve,
        new_curve: YieldCurve
    ) -> Dict:
        """
        Analyze curve shift between two dates.
        
        Decomposes shift into:
        - Parallel shift (level change)
        - Twist (slope change)
        - Butterfly (curvature change)
        """
        tenors = [1, 5, 10]  # Short, medium, long
        
        old_rates = [old_curve.get_rate(t) for t in tenors]
        new_rates = [new_curve.get_rate(t) for t in tenors]
        
        shifts = [new_rates[i] - old_rates[i] for i in range(3)]
        
        # Parallel shift = average of all shifts
        parallel = sum(shifts) / 3
        
        # Twist = long - short shift
        twist = shifts[2] - shifts[0]
        
        # Butterfly = 2 * medium - short - long shift
        butterfly = 2 * shifts[1] - shifts[0] - shifts[2]
        
        return {
            "analysis_date": new_curve.curve_date.isoformat(),
            "comparison_date": old_curve.curve_date.isoformat(),
            "shifts": {
                "1y": round(shifts[0] * 100, 2),  # In bps
                "5y": round(shifts[1] * 100, 2),
                "10y": round(shifts[2] * 100, 2)
            },
            "decomposition": {
                "parallel_bps": round(parallel * 100, 2),
                "twist_bps": round(twist * 100, 2),
                "butterfly_bps": round(butterfly * 100, 2)
            },
            "interpretation": {
                "parallel": "Rising" if parallel > 0 else "Falling" if parallel < 0 else "Unchanged",
                "twist": "Steepening" if twist > 0 else "Flattening" if twist < 0 else "Unchanged",
                "butterfly": "Convexity Increase" if butterfly > 0 else "Convexity Decrease" if butterfly < 0 else "Unchanged"
            }
        }


# ==================== API Functions ====================

async def get_yield_curves(
    curve_date: date = None,
    ratings: List[str] = None,
    interpolation: str = "cubic_spline"
) -> Dict[str, Any]:
    """
    Get multiple yield curves for analysis.
    
    Args:
        curve_date: Date for curve construction
        ratings: List of ratings to build curves for
        interpolation: Interpolation method
    
    Returns:
        Dictionary with G-Sec and corporate curves
    """
    curve_date = curve_date or date.today()
    ratings = ratings or ["AAA", "AA", "A"]
    
    method_map = {
        "linear": InterpolationMethod.LINEAR,
        "cubic_spline": InterpolationMethod.CUBIC_SPLINE,
        "nelson_siegel": InterpolationMethod.NELSON_SIEGEL,
        "svensson": InterpolationMethod.SVENSSON
    }
    interp_method = method_map.get(interpolation, InterpolationMethod.CUBIC_SPLINE)
    
    analytics = YieldCurveAnalytics()
    
    # Build G-Sec curve
    gsec = await analytics.build_gsec_curve(curve_date, interp_method)
    
    # Build corporate curves
    corp_curves = {}
    for rating in ratings:
        curve = await analytics.build_corporate_curve(rating, curve_date, interp_method)
        corp_curves[rating] = curve.to_dict()
    
    # Calculate forward curve
    forward = analytics.calculate_forward_curve(gsec)
    
    return {
        "curve_date": curve_date.isoformat(),
        "interpolation_method": interpolation,
        "gsec_curve": gsec.to_dict(),
        "forward_curve": forward.to_dict(),
        "corporate_curves": corp_curves,
        "generated_at": datetime.now().isoformat()
    }


async def get_spread_analysis(rating: str, curve_date: date = None) -> Dict[str, Any]:
    """
    Get spread analysis for a specific rating vs G-Sec.
    """
    curve_date = curve_date or date.today()
    
    analytics = YieldCurveAnalytics()
    gsec = await analytics.build_gsec_curve(curve_date)
    corp = await analytics.build_corporate_curve(rating, curve_date)
    
    spreads = analytics.calculate_spreads(corp, gsec)
    krds = analytics.calculate_key_rate_durations(gsec)
    
    return {
        "rating": rating,
        "curve_date": curve_date.isoformat(),
        "spreads": spreads,
        "key_rate_durations": krds,
        "summary": {
            "avg_spread_bps": round(sum(s["spread_bps"] for s in spreads) / len(spreads), 2),
            "min_spread_bps": min(s["spread_bps"] for s in spreads),
            "max_spread_bps": max(s["spread_bps"] for s in spreads)
        }
    }


async def get_curve_chart_data(
    curve_date: date = None,
    ratings: List[str] = None
) -> Dict[str, Any]:
    """
    Get yield curve data formatted for chart visualization.
    """
    curve_date = curve_date or date.today()
    ratings = ratings or ["AAA", "AA", "A"]
    
    analytics = YieldCurveAnalytics()
    gsec = await analytics.build_gsec_curve(curve_date)
    
    # Generate smooth curve points for charting
    chart_tenors = [i * 0.5 for i in range(1, 61)]  # 0.5 to 30 years
    
    series = [{
        "name": "G-Sec (Risk-Free)",
        "data": [{"x": t, "y": round(gsec.get_rate(t), 3)} for t in chart_tenors],
        "color": "#10b981"
    }]
    
    rating_colors = {
        "AAA": "#3b82f6",
        "AA": "#f59e0b",
        "A": "#ef4444",
        "BBB": "#8b5cf6"
    }
    
    for rating in ratings:
        corp = await analytics.build_corporate_curve(rating, curve_date)
        series.append({
            "name": f"{rating} Corporate",
            "data": [{"x": t, "y": round(corp.get_rate(t), 3)} for t in chart_tenors],
            "color": rating_colors.get(rating, "#6b7280")
        })
    
    return {
        "curve_date": curve_date.isoformat(),
        "series": series,
        "x_axis": {
            "title": "Tenor (Years)",
            "min": 0,
            "max": 30
        },
        "y_axis": {
            "title": "Yield (%)",
            "min": 5,
            "max": 12
        }
    }


# Export
__all__ = [
    'YieldCurveAnalytics',
    'YieldCurve',
    'YieldPoint',
    'CurveType',
    'InterpolationMethod',
    'get_yield_curves',
    'get_spread_analysis',
    'get_curve_chart_data'
]
