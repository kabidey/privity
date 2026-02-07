"""
Fixed Income Calculation Engine

Implements precise financial calculations for bonds and NCDs.
Uses Decimal throughout for financial accuracy - NO floating point arithmetic.

Key Calculations:
- Accrued Interest (multiple day count conventions)
- Clean Price / Dirty Price
- Yield to Maturity (YTM) using Newton-Raphson
- Price from Yield
- Duration & Modified Duration
- Cash Flow Projections
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from datetime import date, timedelta
from typing import List, Tuple, Optional, Dict, Any
from dateutil.relativedelta import relativedelta
from .models import CouponFrequency, DayCountConvention, CashFlowEntry

# Set high precision for financial calculations
getcontext().prec = 28


# ==================== HELPER FUNCTIONS ====================

def _coupon_periods_per_year(frequency: CouponFrequency) -> int:
    """Get number of coupon payments per year"""
    mapping = {
        CouponFrequency.MONTHLY: 12,
        CouponFrequency.QUARTERLY: 4,
        CouponFrequency.SEMI_ANNUAL: 2,
        CouponFrequency.ANNUAL: 1,
        CouponFrequency.ZERO_COUPON: 0
    }
    return mapping.get(frequency, 1)


def _months_between_coupons(frequency: CouponFrequency) -> int:
    """Get months between coupon payments"""
    mapping = {
        CouponFrequency.MONTHLY: 1,
        CouponFrequency.QUARTERLY: 3,
        CouponFrequency.SEMI_ANNUAL: 6,
        CouponFrequency.ANNUAL: 12,
        CouponFrequency.ZERO_COUPON: 0
    }
    return mapping.get(frequency, 12)


def _get_last_coupon_date(
    settlement_date: date,
    issue_date: date,
    maturity_date: date,
    frequency: CouponFrequency
) -> date:
    """
    Calculate the last coupon date before settlement date.
    Coupons are assumed to be paid on the same day of month as issue date.
    """
    if frequency == CouponFrequency.ZERO_COUPON:
        return issue_date
    
    months = _months_between_coupons(frequency)
    if months == 0:
        return issue_date
    
    # Start from issue date and find all coupon dates until maturity
    coupon_day = issue_date.day
    current = issue_date
    last_coupon = issue_date
    
    while current <= maturity_date:
        if current <= settlement_date:
            last_coupon = current
        else:
            break
        current = current + relativedelta(months=months)
        # Handle month-end issues
        try:
            current = current.replace(day=coupon_day)
        except ValueError:
            # Day doesn't exist in target month (e.g., 31st)
            pass
    
    return last_coupon


def _get_next_coupon_date(
    settlement_date: date,
    issue_date: date,
    maturity_date: date,
    frequency: CouponFrequency
) -> date:
    """
    Calculate the next coupon date after settlement date.
    """
    if frequency == CouponFrequency.ZERO_COUPON:
        return maturity_date
    
    months = _months_between_coupons(frequency)
    if months == 0:
        return maturity_date
    
    last_coupon = _get_last_coupon_date(settlement_date, issue_date, maturity_date, frequency)
    next_coupon = last_coupon + relativedelta(months=months)
    
    # Handle month-end
    coupon_day = issue_date.day
    try:
        next_coupon = next_coupon.replace(day=coupon_day)
    except ValueError:
        pass
    
    return min(next_coupon, maturity_date)


def _days_in_year(year: int, convention: DayCountConvention) -> int:
    """Get days in year based on convention"""
    if convention == DayCountConvention.THIRTY_360:
        return 360
    elif convention == DayCountConvention.ACTUAL_360:
        return 360
    elif convention == DayCountConvention.ACTUAL_365:
        return 365
    else:  # ACTUAL_ACTUAL
        # Check if leap year
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        return 366 if is_leap else 365


def _day_count(
    start_date: date,
    end_date: date,
    convention: DayCountConvention
) -> Tuple[int, int]:
    """
    Calculate days between dates and days in period based on day count convention.
    Returns (days_in_numerator, days_in_denominator)
    """
    if convention == DayCountConvention.THIRTY_360:
        # 30/360 convention
        d1 = min(start_date.day, 30)
        d2 = end_date.day if d1 < 30 else min(end_date.day, 30)
        
        days = (
            360 * (end_date.year - start_date.year) +
            30 * (end_date.month - start_date.month) +
            (d2 - d1)
        )
        return days, 360
    
    elif convention == DayCountConvention.ACTUAL_360:
        days = (end_date - start_date).days
        return days, 360
    
    elif convention == DayCountConvention.ACTUAL_365:
        days = (end_date - start_date).days
        return days, 365
    
    else:  # ACTUAL_ACTUAL
        days = (end_date - start_date).days
        year_days = _days_in_year(end_date.year, convention)
        return days, year_days


# ==================== ACCRUED INTEREST ====================

def calculate_accrued_interest(
    face_value: Decimal,
    coupon_rate: Decimal,
    settlement_date: date,
    issue_date: date,
    maturity_date: date,
    frequency: CouponFrequency,
    convention: DayCountConvention = DayCountConvention.ACTUAL_365
) -> Decimal:
    """
    Calculate accrued interest from last coupon date to settlement date.
    
    Formula: AI = (Face Value × Coupon Rate × Days Since Last Coupon) / Days in Year
    
    Args:
        face_value: Face value of the bond
        coupon_rate: Annual coupon rate as percentage (e.g., 8.5 for 8.5%)
        settlement_date: Date of settlement
        issue_date: Issue date of the bond
        maturity_date: Maturity date of the bond
        frequency: Coupon payment frequency
        convention: Day count convention
    
    Returns:
        Decimal: Accrued interest per unit
    """
    # Zero coupon bonds have no accrued interest
    if frequency == CouponFrequency.ZERO_COUPON or coupon_rate == 0:
        return Decimal("0")
    
    # Get last coupon date
    last_coupon = _get_last_coupon_date(settlement_date, issue_date, maturity_date, frequency)
    
    # If settlement is on coupon date, no accrued interest
    if last_coupon == settlement_date:
        return Decimal("0")
    
    # Calculate days
    days_since_coupon, days_in_year = _day_count(last_coupon, settlement_date, convention)
    
    # Coupon rate to decimal (8.5% -> 0.085)
    coupon_decimal = coupon_rate / Decimal("100")
    
    # Accrued interest calculation
    accrued = (face_value * coupon_decimal * Decimal(days_since_coupon)) / Decimal(days_in_year)
    
    return accrued.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ==================== DIRTY PRICE ====================

def calculate_dirty_price(
    clean_price: Decimal,
    face_value: Decimal,
    coupon_rate: Decimal,
    settlement_date: date,
    issue_date: date,
    maturity_date: date,
    frequency: CouponFrequency,
    convention: DayCountConvention = DayCountConvention.ACTUAL_365
) -> Tuple[Decimal, Decimal]:
    """
    Calculate dirty price (also called full price or invoice price).
    
    Formula: Dirty Price = Clean Price + Accrued Interest
    
    Returns:
        Tuple of (dirty_price, accrued_interest)
    """
    accrued = calculate_accrued_interest(
        face_value=face_value,
        coupon_rate=coupon_rate,
        settlement_date=settlement_date,
        issue_date=issue_date,
        maturity_date=maturity_date,
        frequency=frequency,
        convention=convention
    )
    
    dirty_price = clean_price + accrued
    
    return (
        dirty_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        accrued
    )


# ==================== YIELD TO MATURITY (YTM) ====================

def calculate_ytm(
    clean_price: Decimal,
    face_value: Decimal,
    coupon_rate: Decimal,
    settlement_date: date,
    maturity_date: date,
    frequency: CouponFrequency,
    convention: DayCountConvention = DayCountConvention.ACTUAL_365,
    max_iterations: int = 100,
    tolerance: Decimal = Decimal("0.0000001")
) -> Decimal:
    """
    Calculate Yield to Maturity using Newton-Raphson iterative method.
    
    YTM is the discount rate that makes the present value of all future
    cash flows equal to the current clean price.
    
    For a bond:
    Price = Σ [C / (1 + y/n)^t] + [F / (1 + y/n)^T]
    
    Where:
        C = Coupon payment
        y = YTM (what we're solving for)
        n = Number of coupon periods per year
        t = Period number
        T = Total periods
        F = Face value
    
    Args:
        clean_price: Current clean price
        face_value: Face value of bond
        coupon_rate: Annual coupon rate (percentage)
        settlement_date: Settlement date
        maturity_date: Maturity date
        frequency: Coupon frequency
        convention: Day count convention
        max_iterations: Maximum iterations for Newton-Raphson
        tolerance: Convergence tolerance
    
    Returns:
        Decimal: YTM as annual percentage (e.g., 8.5 for 8.5%)
    """
    # Handle zero coupon bonds
    if frequency == CouponFrequency.ZERO_COUPON:
        return _calculate_zero_coupon_ytm(
            clean_price, face_value, settlement_date, maturity_date, convention
        )
    
    periods_per_year = _coupon_periods_per_year(frequency)
    if periods_per_year == 0:
        return Decimal("0")
    
    # Coupon payment per period
    coupon_decimal = coupon_rate / Decimal("100")
    coupon_payment = (face_value * coupon_decimal) / Decimal(periods_per_year)
    
    # Calculate number of remaining periods
    days_to_maturity = (maturity_date - settlement_date).days
    months_per_period = _months_between_coupons(frequency)
    
    # Approximate periods remaining
    remaining_periods = int(days_to_maturity / (30.4375 * months_per_period)) + 1
    
    # Initial guess: use current yield as starting point
    current_yield = (coupon_payment * periods_per_year) / clean_price
    ytm_guess = float(current_yield)
    
    # Newton-Raphson iteration
    for _ in range(max_iterations):
        price = Decimal("0")
        derivative = Decimal("0")
        
        y = Decimal(str(ytm_guess)) / Decimal(periods_per_year)  # Period yield
        
        for t in range(1, remaining_periods + 1):
            discount = (1 + y) ** t
            
            if t < remaining_periods:
                # Coupon payment
                price += coupon_payment / discount
                derivative -= Decimal(t) * coupon_payment / (discount * (1 + y))
            else:
                # Final coupon + principal
                price += (coupon_payment + face_value) / discount
                derivative -= Decimal(t) * (coupon_payment + face_value) / (discount * (1 + y))
        
        # Adjust derivative for annual rate
        derivative = derivative / Decimal(periods_per_year)
        
        # Calculate error
        error = price - clean_price
        
        if abs(error) < tolerance:
            break
        
        # Newton-Raphson update
        if derivative != 0:
            ytm_guess = ytm_guess - float(error / derivative)
        else:
            break
    
    # Convert to percentage
    ytm = Decimal(str(ytm_guess)) * Decimal("100")
    
    return ytm.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _calculate_zero_coupon_ytm(
    clean_price: Decimal,
    face_value: Decimal,
    settlement_date: date,
    maturity_date: date,
    convention: DayCountConvention
) -> Decimal:
    """
    Calculate YTM for zero-coupon bond.
    
    Formula: YTM = (FV / Price)^(1/n) - 1
    Where n = years to maturity
    """
    days_to_maturity, days_in_year = _day_count(settlement_date, maturity_date, convention)
    years_to_maturity = Decimal(days_to_maturity) / Decimal(days_in_year)
    
    if years_to_maturity <= 0 or clean_price <= 0:
        return Decimal("0")
    
    # YTM = (FV / Price)^(1/years) - 1
    price_ratio = face_value / clean_price
    ytm = (price_ratio ** (Decimal("1") / years_to_maturity)) - Decimal("1")
    
    return (ytm * Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ==================== PRICE FROM YIELD ====================

def price_from_yield(
    target_ytm: Decimal,
    face_value: Decimal,
    coupon_rate: Decimal,
    settlement_date: date,
    maturity_date: date,
    frequency: CouponFrequency,
    convention: DayCountConvention = DayCountConvention.ACTUAL_365
) -> Decimal:
    """
    Calculate clean price given a target YTM.
    
    This is the reverse calculation: input desired yield, output price.
    
    Formula: Price = Σ [C / (1 + y/n)^t] + [F / (1 + y/n)^T]
    
    Args:
        target_ytm: Desired yield to maturity (percentage, e.g., 8.5)
        face_value: Face value of bond
        coupon_rate: Annual coupon rate (percentage)
        settlement_date: Settlement date
        maturity_date: Maturity date
        frequency: Coupon frequency
        convention: Day count convention
    
    Returns:
        Decimal: Clean price that gives the target YTM
    """
    # Handle zero coupon bonds
    if frequency == CouponFrequency.ZERO_COUPON:
        return _price_from_yield_zero_coupon(
            target_ytm, face_value, settlement_date, maturity_date, convention
        )
    
    periods_per_year = _coupon_periods_per_year(frequency)
    if periods_per_year == 0:
        return face_value
    
    # Convert rates to decimals
    ytm_decimal = target_ytm / Decimal("100")
    coupon_decimal = coupon_rate / Decimal("100")
    
    # Coupon payment per period
    coupon_payment = (face_value * coupon_decimal) / Decimal(periods_per_year)
    
    # Period yield
    period_yield = ytm_decimal / Decimal(periods_per_year)
    
    # Calculate number of remaining periods
    days_to_maturity = (maturity_date - settlement_date).days
    months_per_period = _months_between_coupons(frequency)
    remaining_periods = int(days_to_maturity / (30.4375 * months_per_period)) + 1
    
    # Calculate present value of all cash flows
    price = Decimal("0")
    
    for t in range(1, remaining_periods + 1):
        discount = (1 + period_yield) ** t
        
        if t < remaining_periods:
            # Regular coupon payment
            price += coupon_payment / discount
        else:
            # Final coupon + principal
            price += (coupon_payment + face_value) / discount
    
    return price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _price_from_yield_zero_coupon(
    target_ytm: Decimal,
    face_value: Decimal,
    settlement_date: date,
    maturity_date: date,
    convention: DayCountConvention
) -> Decimal:
    """
    Calculate price for zero-coupon bond given target YTM.
    
    Formula: Price = FV / (1 + y)^n
    """
    days_to_maturity, days_in_year = _day_count(settlement_date, maturity_date, convention)
    years_to_maturity = Decimal(days_to_maturity) / Decimal(days_in_year)
    
    if years_to_maturity <= 0:
        return face_value
    
    ytm_decimal = target_ytm / Decimal("100")
    
    price = face_value / ((1 + ytm_decimal) ** years_to_maturity)
    
    return price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ==================== CASH FLOW SCHEDULE ====================

def generate_cash_flow_schedule(
    face_value: Decimal,
    coupon_rate: Decimal,
    settlement_date: date,
    issue_date: date,
    maturity_date: date,
    frequency: CouponFrequency,
    quantity: int = 1
) -> List[CashFlowEntry]:
    """
    Generate complete schedule of all future cash flows.
    
    Args:
        face_value: Face value per unit
        coupon_rate: Annual coupon rate (percentage)
        settlement_date: Settlement/purchase date
        issue_date: Bond issue date
        maturity_date: Bond maturity date
        frequency: Coupon frequency
        quantity: Number of units held
    
    Returns:
        List of CashFlowEntry objects for all future payments
    """
    cash_flows = []
    
    # Handle zero coupon - only principal at maturity
    if frequency == CouponFrequency.ZERO_COUPON or coupon_rate == 0:
        principal_amount = face_value * quantity
        cash_flows.append(CashFlowEntry(
            date=maturity_date,
            type="principal",
            amount=principal_amount,
            description=f"Principal redemption at maturity",
            is_projected=True
        ))
        return cash_flows
    
    # Calculate coupon payment per period
    periods_per_year = _coupon_periods_per_year(frequency)
    coupon_decimal = coupon_rate / Decimal("100")
    coupon_per_period = (face_value * coupon_decimal * quantity) / Decimal(periods_per_year)
    coupon_per_period = coupon_per_period.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Generate coupon dates
    months_between = _months_between_coupons(frequency)
    coupon_day = issue_date.day
    
    # Find next coupon date after settlement
    current_date = _get_next_coupon_date(settlement_date, issue_date, maturity_date, frequency)
    
    while current_date <= maturity_date:
        if current_date < maturity_date:
            # Regular coupon payment
            cash_flows.append(CashFlowEntry(
                date=current_date,
                type="coupon",
                amount=coupon_per_period,
                description=f"Coupon payment @ {coupon_rate}% p.a.",
                is_projected=True
            ))
        else:
            # Final payment: coupon + principal
            principal_amount = face_value * quantity
            cash_flows.append(CashFlowEntry(
                date=current_date,
                type="both",
                amount=coupon_per_period + principal_amount,
                description=f"Final coupon + Principal redemption",
                is_projected=True
            ))
        
        # Move to next coupon date
        current_date = current_date + relativedelta(months=months_between)
        try:
            current_date = current_date.replace(day=coupon_day)
        except ValueError:
            pass
    
    return cash_flows


# ==================== DURATION ====================

def calculate_duration(
    clean_price: Decimal,
    face_value: Decimal,
    coupon_rate: Decimal,
    ytm: Decimal,
    settlement_date: date,
    maturity_date: date,
    frequency: CouponFrequency,
    convention: DayCountConvention = DayCountConvention.ACTUAL_365
) -> Decimal:
    """
    Calculate Macaulay Duration.
    
    Duration = Σ [t × PV(CF_t)] / Price
    
    Where:
        t = time to cash flow (in years)
        PV(CF_t) = present value of cash flow at time t
    
    Returns:
        Duration in years
    """
    if frequency == CouponFrequency.ZERO_COUPON:
        # Duration of zero coupon = time to maturity
        days_to_maturity, days_in_year = _day_count(settlement_date, maturity_date, convention)
        return Decimal(days_to_maturity) / Decimal(days_in_year)
    
    periods_per_year = _coupon_periods_per_year(frequency)
    if periods_per_year == 0:
        return Decimal("0")
    
    ytm_decimal = ytm / Decimal("100")
    coupon_decimal = coupon_rate / Decimal("100")
    
    coupon_payment = (face_value * coupon_decimal) / Decimal(periods_per_year)
    period_yield = ytm_decimal / Decimal(periods_per_year)
    
    days_to_maturity = (maturity_date - settlement_date).days
    months_per_period = _months_between_coupons(frequency)
    remaining_periods = int(days_to_maturity / (30.4375 * months_per_period)) + 1
    
    weighted_pv = Decimal("0")
    total_pv = Decimal("0")
    
    for t in range(1, remaining_periods + 1):
        discount = (1 + period_yield) ** t
        time_in_years = Decimal(t) / Decimal(periods_per_year)
        
        if t < remaining_periods:
            pv = coupon_payment / discount
        else:
            pv = (coupon_payment + face_value) / discount
        
        weighted_pv += time_in_years * pv
        total_pv += pv
    
    if total_pv == 0:
        return Decimal("0")
    
    duration = weighted_pv / total_pv
    
    return duration.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calculate_modified_duration(
    duration: Decimal,
    ytm: Decimal,
    frequency: CouponFrequency
) -> Decimal:
    """
    Calculate Modified Duration.
    
    Modified Duration = Macaulay Duration / (1 + y/n)
    
    This measures price sensitivity to yield changes.
    
    Args:
        duration: Macaulay duration in years
        ytm: Yield to maturity (percentage)
        frequency: Coupon frequency
    
    Returns:
        Modified duration
    """
    periods_per_year = _coupon_periods_per_year(frequency)
    if periods_per_year == 0:
        return duration
    
    ytm_decimal = ytm / Decimal("100")
    period_yield = ytm_decimal / Decimal(periods_per_year)
    
    modified_duration = duration / (1 + period_yield)
    
    return modified_duration.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ==================== PORTFOLIO VALUATION ====================

def calculate_mark_to_market(
    holdings: List[Dict[str, Any]],
    market_prices: Dict[str, Decimal]
) -> List[Dict[str, Any]]:
    """
    Calculate mark-to-market valuation for a portfolio of holdings.
    
    Args:
        holdings: List of holding dictionaries with quantity and cost
        market_prices: Dictionary of ISIN -> current market price
    
    Returns:
        Holdings with MTM values and P&L
    """
    result = []
    
    for holding in holdings:
        isin = holding.get("isin")
        quantity = holding.get("quantity", 0)
        avg_cost = Decimal(str(holding.get("average_cost", 0)))
        face_value = Decimal(str(holding.get("face_value", 100)))
        
        # Get current market price
        current_price = market_prices.get(isin, avg_cost)
        
        # Calculate values
        cost_value = avg_cost * quantity
        current_value = current_price * quantity
        unrealized_pnl = current_value - cost_value
        
        pnl_percentage = Decimal("0")
        if cost_value != 0:
            pnl_percentage = (unrealized_pnl / cost_value) * Decimal("100")
        
        result.append({
            **holding,
            "current_price": current_price.quantize(Decimal("0.0001")),
            "cost_value": cost_value.quantize(Decimal("0.01")),
            "current_value": current_value.quantize(Decimal("0.01")),
            "unrealized_pnl": unrealized_pnl.quantize(Decimal("0.01")),
            "pnl_percentage": pnl_percentage.quantize(Decimal("0.01"))
        })
    
    return result
