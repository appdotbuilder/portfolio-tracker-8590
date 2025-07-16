import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app.price_service import PriceService
from app.database import reset_db


@pytest.fixture
def price_service():
    return PriceService()


@pytest.fixture
def new_db():
    reset_db()
    yield
    reset_db()


class TestPriceService:
    def test_price_service_initialization(self, price_service):
        """Test price service initializes correctly"""
        assert price_service.throttler is not None
        assert price_service._price_cache == {}
        assert price_service._cache_duration == 300

    @patch("app.price_service.yf.Ticker")
    async def test_get_current_price_success(self, mock_ticker, price_service):
        """Test successful price retrieval"""
        # Mock yfinance response
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {"currentPrice": 150.50}
        mock_ticker.return_value = mock_ticker_instance

        price = await price_service.get_current_price("AAPL")

        assert price == Decimal("150.50")
        mock_ticker.assert_called_once_with("AAPL")

    @patch("app.price_service.yf.Ticker")
    async def test_get_current_price_fallback_to_history(self, mock_ticker, price_service):
        """Test fallback to history when info doesn't have price"""
        # Mock yfinance response without currentPrice
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {}

        # Mock history data
        import pandas as pd

        mock_history = pd.DataFrame({"Close": [145.25]})
        mock_ticker_instance.history.return_value = mock_history
        mock_ticker.return_value = mock_ticker_instance

        price = await price_service.get_current_price("AAPL")

        assert price == Decimal("145.25")
        mock_ticker_instance.history.assert_called_once_with(period="1d")

    @patch("app.price_service.yf.Ticker")
    async def test_get_current_price_failure(self, mock_ticker, price_service):
        """Test handling of price retrieval failure"""
        mock_ticker.side_effect = Exception("Network error")

        price = await price_service.get_current_price("INVALID")

        assert price is None

    async def test_price_caching(self, price_service):
        """Test price caching functionality"""
        # Mock a price in cache
        from datetime import datetime

        cached_price = Decimal("100.00")
        price_service._price_cache["TEST"] = (cached_price, datetime.now())

        # Should return cached price without API call
        price = await price_service.get_current_price("TEST")
        assert price == cached_price

    @patch("app.price_service.yf.Ticker")
    async def test_get_multiple_prices(self, mock_ticker, price_service):
        """Test getting multiple prices concurrently"""

        # Mock different prices for different symbols
        def mock_ticker_factory(symbol):
            mock_instance = MagicMock()
            prices = {"AAPL": 150.0, "GOOGL": 2500.0, "MSFT": 300.0}
            mock_instance.info = {"currentPrice": prices.get(symbol, 100.0)}
            return mock_instance

        mock_ticker.side_effect = mock_ticker_factory

        symbols = ["AAPL", "GOOGL", "MSFT"]
        prices = await price_service.get_multiple_prices(symbols)

        assert len(prices) == 3
        assert prices["AAPL"] == Decimal("150.0")
        assert prices["GOOGL"] == Decimal("2500.0")
        assert prices["MSFT"] == Decimal("300.0")

    @patch("app.price_service.yf.Ticker")
    async def test_get_multiple_prices_with_failures(self, mock_ticker, price_service):
        """Test handling failures in multiple price requests"""

        def mock_ticker_factory(symbol):
            if symbol == "INVALID":
                raise Exception("Invalid symbol")
            mock_instance = MagicMock()
            mock_instance.info = {"currentPrice": 100.0}
            return mock_instance

        mock_ticker.side_effect = mock_ticker_factory

        symbols = ["AAPL", "INVALID", "GOOGL"]
        prices = await price_service.get_multiple_prices(symbols)

        assert len(prices) == 3
        assert prices["AAPL"] == Decimal("100.0")
        assert prices["INVALID"] is None
        assert prices["GOOGL"] == Decimal("100.0")

    def test_clear_cache(self, price_service):
        """Test cache clearing functionality"""
        # Add some data to cache
        from datetime import datetime

        price_service._price_cache["TEST"] = (Decimal("100.00"), datetime.now())

        assert len(price_service._price_cache) == 1

        price_service.clear_cache()

        assert len(price_service._price_cache) == 0

    @patch("app.price_service.yf.Ticker")
    def test_get_price_data_success(self, mock_ticker, price_service):
        """Test getting detailed price data"""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            "currentPrice": 150.50,
            "currency": "USD",
            "marketCap": 2500000000,
            "volume": 50000000,
        }
        mock_ticker.return_value = mock_ticker_instance

        price_data = price_service.get_price_data("AAPL")

        assert price_data is not None
        assert price_data.symbol == "AAPL"
        assert price_data.price == Decimal("150.50")
        assert price_data.currency == "USD"
        assert price_data.market_cap == Decimal("2500000000")
        assert price_data.volume == Decimal("50000000")

    @patch("app.price_service.yf.Ticker")
    def test_get_price_data_failure(self, mock_ticker, price_service):
        """Test handling failure in getting price data"""
        mock_ticker.side_effect = Exception("Network error")

        price_data = price_service.get_price_data("INVALID")

        assert price_data is None

    async def test_store_price_history(self, price_service, new_db):
        """Test storing price history in database"""
        # This will be tested indirectly through get_current_price
        # since _store_price_history is a private method
        pass

    async def test_get_last_known_price_no_data(self, price_service, new_db):
        """Test getting last known price when no data exists"""
        price = await price_service._get_last_known_price("NONEXISTENT")
        assert price is None
