"""
Fixed Income - Market Data Integration Service

Provides real-time and historical market data for bonds/NCDs.
Integrates with:
- NSE Corporate Bonds data
- BSE Bond data
- RBI GSEC data (via CCIL)

Note: Actual API integration requires subscription to data providers.
This module provides the interface and mock data for development.
"""

import logging
import asyncio
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import httpx

from database import db

logger = logging.getLogger(__name__)


# ==================== MODELS ====================

class MarketQuote(BaseModel):
    """Single market quote for a bond"""
    isin: str
    symbol: Optional[str] = None
    last_price: Decimal
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_yield: Optional[Decimal] = None
    ask_yield: Optional[Decimal] = None
    last_yield: Optional[Decimal] = None
    volume: Optional[int] = None
    trade_date: Optional[date] = None
    trade_time: Optional[str] = None
    exchange: str = "NSE"


class MarketDataConfig(BaseModel):
    """Configuration for market data provider"""
    provider: str  # nse, bse, ccil, mock
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True


# ==================== MARKET DATA PROVIDERS ====================

class BaseMarketDataProvider:
    """Base class for market data providers"""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_quote(self, isin: str) -> Optional[MarketQuote]:
        """Get real-time quote for an ISIN"""
        raise NotImplementedError
    
    async def get_bulk_quotes(self, isins: List[str]) -> List[MarketQuote]:
        """Get quotes for multiple ISINs"""
        raise NotImplementedError
    
    async def get_historical_prices(self, isin: str, from_date: date, to_date: date) -> List[Dict]:
        """Get historical prices"""
        raise NotImplementedError


class MockMarketDataProvider(BaseMarketDataProvider):
    """Mock provider for development and testing"""
    
    async def get_quote(self, isin: str) -> Optional[MarketQuote]:
        """Generate mock quote based on stored instrument data"""
        instrument = await db.fi_instruments.find_one({"isin": isin}, {"_id": 0})
        
        if not instrument:
            return None
        
        # Use stored price or generate from face value
        base_price = Decimal(str(instrument.get("current_market_price") or instrument.get("face_value", 100)))
        
        # Add small random variation (±0.5%)
        import random
        variation = Decimal(str(random.uniform(-0.005, 0.005)))
        last_price = (base_price * (1 + variation)).quantize(Decimal("0.01"))
        
        bid_price = (last_price * Decimal("0.998")).quantize(Decimal("0.01"))
        ask_price = (last_price * Decimal("1.002")).quantize(Decimal("0.01"))
        
        # Calculate approximate yields
        coupon_rate = Decimal(str(instrument.get("coupon_rate", 8)))
        face_value = Decimal(str(instrument.get("face_value", 100)))
        
        # Simple current yield approximation
        last_yield = ((coupon_rate * face_value / 100) / last_price * 100).quantize(Decimal("0.01"))
        bid_yield = ((coupon_rate * face_value / 100) / bid_price * 100).quantize(Decimal("0.01"))
        ask_yield = ((coupon_rate * face_value / 100) / ask_price * 100).quantize(Decimal("0.01"))
        
        return MarketQuote(
            isin=isin,
            symbol=instrument.get("issuer_code"),
            last_price=last_price,
            bid_price=bid_price,
            ask_price=ask_price,
            last_yield=last_yield,
            bid_yield=bid_yield,
            ask_yield=ask_yield,
            volume=random.randint(100, 10000),
            trade_date=date.today(),
            trade_time=datetime.now().strftime("%H:%M:%S"),
            exchange="MOCK"
        )
    
    async def get_bulk_quotes(self, isins: List[str]) -> List[MarketQuote]:
        """Get quotes for multiple ISINs"""
        quotes = []
        for isin in isins:
            quote = await self.get_quote(isin)
            if quote:
                quotes.append(quote)
        return quotes
    
    async def get_historical_prices(self, isin: str, from_date: date, to_date: date) -> List[Dict]:
        """Generate mock historical prices"""
        instrument = await db.fi_instruments.find_one({"isin": isin}, {"_id": 0})
        
        if not instrument:
            return []
        
        base_price = Decimal(str(instrument.get("current_market_price") or instrument.get("face_value", 100)))
        
        prices = []
        current_date = from_date
        import random
        
        while current_date <= to_date:
            # Skip weekends
            if current_date.weekday() < 5:
                # Random walk
                change = Decimal(str(random.uniform(-0.01, 0.01)))
                base_price = (base_price * (1 + change)).quantize(Decimal("0.01"))
                
                prices.append({
                    "date": current_date.isoformat(),
                    "open": str(base_price * Decimal("0.998")),
                    "high": str(base_price * Decimal("1.005")),
                    "low": str(base_price * Decimal("0.995")),
                    "close": str(base_price),
                    "volume": random.randint(500, 5000)
                })
            
            current_date += timedelta(days=1)
        
        return prices


class NSEMarketDataProvider(BaseMarketDataProvider):
    """
    NSE Corporate Bonds market data provider.
    
    Note: Requires NSE data subscription for production use.
    API documentation: https://www.nseindia.com/resources/exchange-communication
    """
    
    async def get_quote(self, isin: str) -> Optional[MarketQuote]:
        """
        Get quote from NSE.
        
        In production, this would call NSE's API.
        Currently returns None to fall back to mock.
        """
        if not self.config.api_key:
            logger.warning("NSE API key not configured")
            return None
        
        try:
            # NSE API endpoint (example - actual endpoint may differ)
            url = f"{self.config.base_url}/corporate-bonds/quote/{isin}"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Accept": "application/json"
            }
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            return MarketQuote(
                isin=isin,
                symbol=data.get("symbol"),
                last_price=Decimal(str(data.get("lastPrice", 0))),
                bid_price=Decimal(str(data.get("bidPrice", 0))),
                ask_price=Decimal(str(data.get("askPrice", 0))),
                last_yield=Decimal(str(data.get("yield", 0))),
                volume=data.get("volume"),
                trade_date=date.fromisoformat(data.get("tradeDate")) if data.get("tradeDate") else None,
                exchange="NSE"
            )
            
        except Exception as e:
            logger.error(f"Error fetching NSE quote for {isin}: {e}")
            return None
    
    async def get_bulk_quotes(self, isins: List[str]) -> List[MarketQuote]:
        """Get bulk quotes from NSE"""
        quotes = []
        # NSE typically has bulk endpoints, but implementation depends on subscription
        for isin in isins:
            quote = await self.get_quote(isin)
            if quote:
                quotes.append(quote)
        return quotes


class BSEMarketDataProvider(BaseMarketDataProvider):
    """
    BSE Bond market data provider.
    
    Note: Requires BSE data subscription for production use.
    """
    
    async def get_quote(self, isin: str) -> Optional[MarketQuote]:
        """Get quote from BSE"""
        if not self.config.api_key:
            return None
        
        # Similar implementation to NSE
        # BSE API endpoints differ
        return None


# ==================== MARKET DATA SERVICE ====================

class MarketDataService:
    """
    Main service for fetching and updating market data.
    Uses multiple providers with fallback.
    """
    
    def __init__(self):
        self.providers: List[BaseMarketDataProvider] = []
        self.mock_provider = None
    
    async def initialize(self):
        """Initialize providers from configuration"""
        # Always have mock provider as fallback
        mock_config = MarketDataConfig(provider="mock", enabled=True)
        self.mock_provider = MockMarketDataProvider(mock_config)
        
        # Load provider configs from database
        configs = await db.system_settings.find_one({"setting": "market_data_providers"})
        
        if configs and configs.get("providers"):
            for provider_config in configs.get("providers", []):
                if not provider_config.get("enabled"):
                    continue
                
                config = MarketDataConfig(**provider_config)
                
                if config.provider == "nse":
                    self.providers.append(NSEMarketDataProvider(config))
                elif config.provider == "bse":
                    self.providers.append(BSEMarketDataProvider(config))
        
        logger.info(f"Initialized {len(self.providers)} market data providers (+ mock fallback)")
    
    async def get_quote(self, isin: str) -> Optional[MarketQuote]:
        """
        Get quote from providers with fallback.
        Tries each provider in order, falls back to mock.
        """
        for provider in self.providers:
            try:
                quote = await provider.get_quote(isin)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(f"Provider {provider.config.provider} failed: {e}")
                continue
        
        # Fall back to mock
        return await self.mock_provider.get_quote(isin)
    
    async def update_all_prices(self) -> Dict[str, Any]:
        """
        Update market prices for all active instruments.
        Should be called periodically (e.g., every 15 minutes during market hours).
        """
        instruments = await db.fi_instruments.find(
            {"is_active": True},
            {"_id": 0, "isin": 1}
        ).to_list(length=10000)
        
        if not instruments:
            return {"updated": 0, "errors": 0}
        
        isins = [i["isin"] for i in instruments]
        
        updated = 0
        errors = 0
        
        # Try bulk first
        for provider in self.providers:
            try:
                quotes = await provider.get_bulk_quotes(isins)
                for quote in quotes:
                    await self._save_quote(quote)
                    updated += 1
                    # Remove from list
                    if quote.isin in isins:
                        isins.remove(quote.isin)
            except Exception as e:
                logger.error(f"Bulk quote fetch failed: {e}")
        
        # Fetch remaining individually
        for isin in isins:
            try:
                quote = await self.get_quote(isin)
                if quote:
                    await self._save_quote(quote)
                    updated += 1
            except Exception as e:
                logger.error(f"Error fetching {isin}: {e}")
                errors += 1
        
        logger.info(f"Market data update complete: {updated} updated, {errors} errors")
        
        return {
            "updated": updated,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _save_quote(self, quote: MarketQuote):
        """Save quote to database"""
        await db.fi_instruments.update_one(
            {"isin": quote.isin},
            {
                "$set": {
                    "current_market_price": str(quote.last_price),
                    "last_traded_price": str(quote.last_price),
                    "last_traded_date": quote.trade_date.isoformat() if quote.trade_date else None,
                    "market_data": {
                        "bid_price": str(quote.bid_price) if quote.bid_price else None,
                        "ask_price": str(quote.ask_price) if quote.ask_price else None,
                        "bid_yield": str(quote.bid_yield) if quote.bid_yield else None,
                        "ask_yield": str(quote.ask_yield) if quote.ask_yield else None,
                        "last_yield": str(quote.last_yield) if quote.last_yield else None,
                        "volume": quote.volume,
                        "exchange": quote.exchange,
                        "updated_at": datetime.now().isoformat()
                    },
                    "updated_at": datetime.now()
                }
            }
        )
        
        # Also save to price history
        await db.fi_price_history.insert_one({
            "isin": quote.isin,
            "date": quote.trade_date.isoformat() if quote.trade_date else date.today().isoformat(),
            "price": str(quote.last_price),
            "yield": str(quote.last_yield) if quote.last_yield else None,
            "volume": quote.volume,
            "exchange": quote.exchange,
            "recorded_at": datetime.now()
        })


# Singleton instance
market_data_service = MarketDataService()


# ==================== ROUTER ENDPOINTS ====================

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from utils.auth import get_current_user
from services.permission_service import require_permission

router = APIRouter(prefix="/fixed-income/market-data", tags=["Fixed Income - Market Data"])


@router.get("/quote/{isin}")
async def get_market_quote(
    isin: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view market quote"))
):
    """Get real-time market quote for an ISIN"""
    if not market_data_service.mock_provider:
        await market_data_service.initialize()
    
    quote = await market_data_service.get_quote(isin)
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {
        "isin": quote.isin,
        "symbol": quote.symbol,
        "last_price": str(quote.last_price),
        "bid_price": str(quote.bid_price) if quote.bid_price else None,
        "ask_price": str(quote.ask_price) if quote.ask_price else None,
        "last_yield": str(quote.last_yield) if quote.last_yield else None,
        "volume": quote.volume,
        "trade_date": quote.trade_date.isoformat() if quote.trade_date else None,
        "exchange": quote.exchange
    }


@router.post("/refresh")
async def refresh_market_data(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.edit", "refresh market data"))
):
    """Trigger market data refresh for all instruments"""
    if not market_data_service.mock_provider:
        await market_data_service.initialize()
    
    # Run in background
    background_tasks.add_task(market_data_service.update_all_prices)
    
    return {"message": "Market data refresh initiated"}


@router.get("/history/{isin}")
async def get_price_history(
    isin: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view price history"))
):
    """Get historical price data for an ISIN"""
    from_date = date.today() - timedelta(days=days)
    
    # Check stored history first
    history = await db.fi_price_history.find(
        {
            "isin": isin,
            "date": {"$gte": from_date.isoformat()}
        },
        {"_id": 0}
    ).sort("date", 1).to_list(length=1000)
    
    if not history:
        # Generate mock history
        if not market_data_service.mock_provider:
            await market_data_service.initialize()
        
        history = await market_data_service.mock_provider.get_historical_prices(
            isin, from_date, date.today()
        )
    
    return {"isin": isin, "history": history, "days": days}
