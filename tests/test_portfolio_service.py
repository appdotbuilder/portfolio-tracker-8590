import pytest
from decimal import Decimal
from unittest.mock import patch
from app.portfolio_service import PortfolioService
from app.models import PortfolioCreate, PortfolioUpdate, HoldingCreate, HoldingUpdate, AssetType
from app.database import reset_db


@pytest.fixture
def portfolio_service():
    return PortfolioService()


@pytest.fixture
def new_db():
    reset_db()
    yield
    reset_db()


@pytest.fixture
def sample_portfolio(new_db, portfolio_service):
    """Create a sample portfolio for testing"""
    portfolio_data = PortfolioCreate(name="Test Portfolio", description="A test portfolio")
    return portfolio_service.create_portfolio(portfolio_data)


@pytest.fixture
def sample_holding(sample_portfolio, portfolio_service):
    """Create a sample holding for testing"""
    holding_data = HoldingCreate(
        portfolio_id=sample_portfolio.id,
        symbol="AAPL",
        asset_type=AssetType.STOCK,
        quantity=Decimal("10.0"),
        purchase_price=Decimal("150.0"),
        notes="Test holding",
    )
    return portfolio_service.add_holding(holding_data)


class TestPortfolioService:
    def test_create_portfolio(self, portfolio_service, new_db):
        """Test creating a new portfolio"""
        portfolio_data = PortfolioCreate(name="My Portfolio", description="Investment portfolio")

        portfolio = portfolio_service.create_portfolio(portfolio_data)

        assert portfolio.id is not None
        assert portfolio.name == "My Portfolio"
        assert portfolio.description == "Investment portfolio"
        assert portfolio.created_at is not None
        assert portfolio.updated_at is not None

    def test_create_portfolio_minimal(self, portfolio_service, new_db):
        """Test creating portfolio with minimal data"""
        portfolio_data = PortfolioCreate(name="Simple Portfolio")

        portfolio = portfolio_service.create_portfolio(portfolio_data)

        assert portfolio.id is not None
        assert portfolio.name == "Simple Portfolio"
        assert portfolio.description == ""

    def test_get_portfolio_exists(self, portfolio_service, sample_portfolio):
        """Test getting an existing portfolio"""
        portfolio = portfolio_service.get_portfolio(sample_portfolio.id)

        assert portfolio is not None
        assert portfolio.id == sample_portfolio.id
        assert portfolio.name == sample_portfolio.name

    def test_get_portfolio_not_exists(self, portfolio_service, new_db):
        """Test getting non-existent portfolio"""
        portfolio = portfolio_service.get_portfolio(999)

        assert portfolio is None

    def test_get_all_portfolios(self, portfolio_service, new_db):
        """Test getting all portfolios"""
        # Create multiple portfolios
        portfolio_service.create_portfolio(PortfolioCreate(name="Portfolio 1"))
        portfolio_service.create_portfolio(PortfolioCreate(name="Portfolio 2"))

        portfolios = portfolio_service.get_all_portfolios()

        assert len(portfolios) == 2
        portfolio_names = [p.name for p in portfolios]
        assert "Portfolio 1" in portfolio_names
        assert "Portfolio 2" in portfolio_names

    def test_get_all_portfolios_empty(self, portfolio_service, new_db):
        """Test getting all portfolios when none exist"""
        portfolios = portfolio_service.get_all_portfolios()

        assert portfolios == []

    def test_update_portfolio(self, portfolio_service, sample_portfolio):
        """Test updating a portfolio"""
        update_data = PortfolioUpdate(name="Updated Portfolio", description="Updated description")

        updated_portfolio = portfolio_service.update_portfolio(sample_portfolio.id, update_data)

        assert updated_portfolio is not None
        assert updated_portfolio.name == "Updated Portfolio"
        assert updated_portfolio.description == "Updated description"
        assert updated_portfolio.updated_at > sample_portfolio.updated_at

    def test_update_portfolio_partial(self, portfolio_service, sample_portfolio):
        """Test partial portfolio update"""
        update_data = PortfolioUpdate(name="New Name Only")

        updated_portfolio = portfolio_service.update_portfolio(sample_portfolio.id, update_data)

        assert updated_portfolio is not None
        assert updated_portfolio.name == "New Name Only"
        assert updated_portfolio.description == sample_portfolio.description

    def test_update_portfolio_not_exists(self, portfolio_service, new_db):
        """Test updating non-existent portfolio"""
        update_data = PortfolioUpdate(name="Non-existent")

        result = portfolio_service.update_portfolio(999, update_data)

        assert result is None

    def test_delete_portfolio(self, portfolio_service, sample_portfolio):
        """Test deleting a portfolio"""
        result = portfolio_service.delete_portfolio(sample_portfolio.id)

        assert result is True

        # Verify portfolio is deleted
        portfolio = portfolio_service.get_portfolio(sample_portfolio.id)
        assert portfolio is None

    def test_delete_portfolio_not_exists(self, portfolio_service, new_db):
        """Test deleting non-existent portfolio"""
        result = portfolio_service.delete_portfolio(999)

        assert result is False

    def test_add_holding(self, portfolio_service, sample_portfolio):
        """Test adding a holding to portfolio"""
        holding_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="GOOGL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("5.0"),
            purchase_price=Decimal("2800.0"),
            notes="Google stock",
        )

        holding = portfolio_service.add_holding(holding_data)

        assert holding.id is not None
        assert holding.portfolio_id == sample_portfolio.id
        assert holding.symbol == "GOOGL"
        assert holding.asset_type == AssetType.STOCK
        assert holding.quantity == Decimal("5.0")
        assert holding.purchase_price == Decimal("2800.0")
        assert holding.notes == "Google stock"

    def test_add_holding_symbol_uppercase(self, portfolio_service, sample_portfolio):
        """Test that symbol is converted to uppercase"""
        holding_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="aapl",
            asset_type=AssetType.STOCK,
            quantity=Decimal("1.0"),
            purchase_price=Decimal("150.0"),
        )

        holding = portfolio_service.add_holding(holding_data)

        assert holding.symbol == "AAPL"

    def test_add_holding_crypto(self, portfolio_service, sample_portfolio):
        """Test adding cryptocurrency holding"""
        holding_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="BTC-USD",
            asset_type=AssetType.CRYPTOCURRENCY,
            quantity=Decimal("0.5"),
            purchase_price=Decimal("45000.0"),
        )

        holding = portfolio_service.add_holding(holding_data)

        assert holding.symbol == "BTC-USD"
        assert holding.asset_type == AssetType.CRYPTOCURRENCY
        assert holding.quantity == Decimal("0.5")

    def test_get_holding_exists(self, portfolio_service, sample_holding):
        """Test getting an existing holding"""
        holding = portfolio_service.get_holding(sample_holding.id)

        assert holding is not None
        assert holding.id == sample_holding.id
        assert holding.symbol == sample_holding.symbol

    def test_get_holding_not_exists(self, portfolio_service, new_db):
        """Test getting non-existent holding"""
        holding = portfolio_service.get_holding(999)

        assert holding is None

    def test_get_portfolio_holdings(self, portfolio_service, sample_portfolio):
        """Test getting all holdings for a portfolio"""
        # Add multiple holdings
        holding1_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("10.0"),
            purchase_price=Decimal("150.0"),
        )
        holding2_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="GOOGL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("5.0"),
            purchase_price=Decimal("2800.0"),
        )

        portfolio_service.add_holding(holding1_data)
        portfolio_service.add_holding(holding2_data)

        holdings = portfolio_service.get_portfolio_holdings(sample_portfolio.id)

        assert len(holdings) == 2
        symbols = [h.symbol for h in holdings]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols

    def test_get_portfolio_holdings_empty(self, portfolio_service, sample_portfolio):
        """Test getting holdings for portfolio with no holdings"""
        holdings = portfolio_service.get_portfolio_holdings(sample_portfolio.id)

        assert holdings == []

    def test_update_holding(self, portfolio_service, sample_holding):
        """Test updating a holding"""
        update_data = HoldingUpdate(quantity=Decimal("15.0"), purchase_price=Decimal("160.0"), notes="Updated holding")

        updated_holding = portfolio_service.update_holding(sample_holding.id, update_data)

        assert updated_holding is not None
        assert updated_holding.quantity == Decimal("15.0")
        assert updated_holding.purchase_price == Decimal("160.0")
        assert updated_holding.notes == "Updated holding"
        assert updated_holding.updated_at > sample_holding.updated_at

    def test_update_holding_not_exists(self, portfolio_service, new_db):
        """Test updating non-existent holding"""
        update_data = HoldingUpdate(quantity=Decimal("1.0"))

        result = portfolio_service.update_holding(999, update_data)

        assert result is None

    def test_delete_holding(self, portfolio_service, sample_holding):
        """Test deleting a holding"""
        result = portfolio_service.delete_holding(sample_holding.id)

        assert result is True

        # Verify holding is deleted
        holding = portfolio_service.get_holding(sample_holding.id)
        assert holding is None

    def test_delete_holding_not_exists(self, portfolio_service, new_db):
        """Test deleting non-existent holding"""
        result = portfolio_service.delete_holding(999)

        assert result is False

    @patch("app.portfolio_service.price_service.get_multiple_prices")
    async def test_get_holdings_with_metrics(self, mock_get_prices, portfolio_service, sample_portfolio):
        """Test getting holdings with calculated metrics"""
        # Add holdings
        holding1_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("10.0"),
            purchase_price=Decimal("150.0"),
        )
        holding2_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="GOOGL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("5.0"),
            purchase_price=Decimal("2800.0"),
        )

        portfolio_service.add_holding(holding1_data)
        portfolio_service.add_holding(holding2_data)

        # Mock price service
        mock_get_prices.return_value = {"AAPL": Decimal("160.0"), "GOOGL": Decimal("2900.0")}

        holdings = await portfolio_service.get_holdings_with_metrics(sample_portfolio.id)

        assert len(holdings) == 2

        # Check AAPL metrics
        aapl_holding = next(h for h in holdings if h.symbol == "AAPL")
        assert aapl_holding.current_price == Decimal("160.0")
        assert aapl_holding.total_cost == Decimal("1500.0")  # 10 * 150
        assert aapl_holding.current_value == Decimal("1600.0")  # 10 * 160
        assert aapl_holding.absolute_return == Decimal("100.0")  # 1600 - 1500
        assert abs(aapl_holding.percentage_return - Decimal("6.67")) < Decimal("0.01")  # 100/1500 * 100

        # Check GOOGL metrics
        googl_holding = next(h for h in holdings if h.symbol == "GOOGL")
        assert googl_holding.current_price == Decimal("2900.0")
        assert googl_holding.total_cost == Decimal("14000.0")  # 5 * 2800
        assert googl_holding.current_value == Decimal("14500.0")  # 5 * 2900
        assert googl_holding.absolute_return == Decimal("500.0")  # 14500 - 14000

    async def test_get_holdings_with_metrics_empty_portfolio(self, portfolio_service, sample_portfolio):
        """Test getting metrics for empty portfolio"""
        holdings = await portfolio_service.get_holdings_with_metrics(sample_portfolio.id)

        assert holdings == []

    @patch("app.portfolio_service.price_service.get_multiple_prices")
    async def test_get_holdings_with_metrics_no_prices(self, mock_get_prices, portfolio_service, sample_portfolio):
        """Test getting holdings when prices are unavailable"""
        # Add holding
        holding_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("10.0"),
            purchase_price=Decimal("150.0"),
        )
        portfolio_service.add_holding(holding_data)

        # Mock price service to return None
        mock_get_prices.return_value = {"AAPL": None}

        holdings = await portfolio_service.get_holdings_with_metrics(sample_portfolio.id)

        assert len(holdings) == 1
        holding = holdings[0]
        assert holding.current_price is None
        assert holding.current_value is None
        assert holding.absolute_return is None
        assert holding.percentage_return is None
        assert holding.total_cost == Decimal("1500.0")

    @patch("app.portfolio_service.price_service.get_multiple_prices")
    async def test_get_portfolio_summary(self, mock_get_prices, portfolio_service, sample_portfolio):
        """Test getting portfolio summary"""
        # Add holdings
        holding1_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("10.0"),
            purchase_price=Decimal("150.0"),
        )
        holding2_data = HoldingCreate(
            portfolio_id=sample_portfolio.id,
            symbol="GOOGL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("5.0"),
            purchase_price=Decimal("2800.0"),
        )

        portfolio_service.add_holding(holding1_data)
        portfolio_service.add_holding(holding2_data)

        # Mock price service
        mock_get_prices.return_value = {
            "AAPL": Decimal("160.0"),  # +6.67% return
            "GOOGL": Decimal("2700.0"),  # -3.57% return
        }

        summary = await portfolio_service.get_portfolio_summary(sample_portfolio.id)

        assert summary is not None
        assert summary.portfolio_id == sample_portfolio.id
        assert summary.portfolio_name == sample_portfolio.name
        assert summary.total_holdings == 2
        assert summary.total_cost == Decimal("15500.0")  # 1500 + 14000
        assert summary.total_current_value == Decimal("15100.0")  # 1600 + 13500
        assert summary.total_absolute_return == Decimal("-400.0")  # 15100 - 15500
        assert summary.best_performer == "AAPL"
        assert summary.worst_performer == "GOOGL"

    async def test_get_portfolio_summary_empty_portfolio(self, portfolio_service, sample_portfolio):
        """Test getting summary for empty portfolio"""
        summary = await portfolio_service.get_portfolio_summary(sample_portfolio.id)

        assert summary is not None
        assert summary.portfolio_id == sample_portfolio.id
        assert summary.total_holdings == 0
        assert summary.total_cost == Decimal("0")
        assert summary.total_current_value == Decimal("0")
        assert summary.total_absolute_return == Decimal("0")
        assert summary.total_percentage_return == Decimal("0")
        assert summary.best_performer is None
        assert summary.worst_performer is None

    async def test_get_portfolio_summary_not_exists(self, portfolio_service, new_db):
        """Test getting summary for non-existent portfolio"""
        summary = await portfolio_service.get_portfolio_summary(999)

        assert summary is None
