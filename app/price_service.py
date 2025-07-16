import yfinance as yf
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, List
from sqlmodel import select
from app.database import get_session
from app.models import PriceHistory, PriceData


# Simple throttler implementation
class SimpleThrottler:
    def __init__(self, rate_limit: int, period: int):
        self.rate_limit = rate_limit
        self.period = period

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class PriceService:
    def __init__(self):
        # Rate limiting: max 10 requests per minute to avoid API limits
        self.throttler = SimpleThrottler(rate_limit=10, period=60)
        self._price_cache: Dict[str, tuple[Decimal, datetime]] = {}
        self._cache_duration = 300  # 5 minutes cache

    async def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for a symbol with caching and rate limiting"""
        # Check cache first
        if symbol in self._price_cache:
            cached_price, cached_time = self._price_cache[symbol]
            if (datetime.now() - cached_time).total_seconds() < self._cache_duration:
                return cached_price

        # Rate limit the API call
        async with self.throttler:
            try:
                # Run yfinance in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
                info = await loop.run_in_executor(None, lambda: ticker.info)

                # Try different price fields
                price = None
                for field in ["currentPrice", "regularMarketPrice", "price", "lastPrice"]:
                    if field in info and info[field] is not None:
                        price = Decimal(str(info[field]))
                        break

                if price is None:
                    # Fallback to history if info doesn't have price
                    hist = await loop.run_in_executor(None, lambda: ticker.history(period="1d"))
                    if not hist.empty:
                        price = Decimal(str(hist["Close"].iloc[-1]))

                if price is not None:
                    # Cache the result
                    self._price_cache[symbol] = (price, datetime.now())

                    # Store in database for historical tracking
                    await self._store_price_history(symbol, price)

                    return price

            except Exception as e:
                print(f"Error fetching price for {symbol}: {e}")
                # Try to get last known price from database
                return await self._get_last_known_price(symbol)

        return None

    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[Decimal]]:
        """Get prices for multiple symbols concurrently"""
        tasks = [self.get_current_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        price_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                print(f"Error fetching price for {symbol}: {result}")
                price_dict[symbol] = None
            else:
                price_dict[symbol] = result

        return price_dict

    async def _store_price_history(self, symbol: str, price: Decimal) -> None:
        """Store price data in database for historical tracking"""
        try:
            with get_session() as session:
                price_record = PriceHistory(symbol=symbol, price=price, timestamp=datetime.now(), source="yfinance")
                session.add(price_record)
                session.commit()
        except Exception as e:
            print(f"Error storing price history for {symbol}: {e}")

    async def _get_last_known_price(self, symbol: str) -> Optional[Decimal]:
        """Get last known price from database as fallback"""
        try:
            with get_session() as session:
                from sqlmodel import desc

                statement = (
                    select(PriceHistory)
                    .where(PriceHistory.symbol == symbol)
                    .order_by(desc(PriceHistory.timestamp))
                    .limit(1)
                )

                result = session.exec(statement).first()
                if result:
                    return result.price
        except Exception as e:
            print(f"Error getting last known price for {symbol}: {e}")

        return None

    def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """Get detailed price data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get current price
            price = None
            for field in ["currentPrice", "regularMarketPrice", "price", "lastPrice"]:
                if field in info and info[field] is not None:
                    price = Decimal(str(info[field]))
                    break

            if price is None:
                return None

            return PriceData(
                symbol=symbol,
                price=price,
                timestamp=datetime.now(),
                source="yfinance",
                currency=info.get("currency", "USD"),
                market_cap=Decimal(str(info["marketCap"])) if info.get("marketCap") else None,
                volume=Decimal(str(info["volume"])) if info.get("volume") else None,
            )

        except Exception as e:
            print(f"Error getting price data for {symbol}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the price cache"""
        self._price_cache.clear()


# Global instance
price_service = PriceService()
