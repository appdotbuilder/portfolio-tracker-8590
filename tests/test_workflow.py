import pytest
from decimal import Decimal
from unittest.mock import patch
from app.database import reset_db
from app.portfolio_service import portfolio_service
from app.models import PortfolioCreate, HoldingCreate, AssetType


@pytest.fixture
def new_db():
    reset_db()
    yield
    reset_db()


class TestWorkflow:
    def test_complete_portfolio_workflow(self, new_db):
        """Test the complete workflow from creating portfolio to adding holdings"""
        # Step 1: Create portfolio
        portfolio_data = PortfolioCreate(name="Investment Portfolio", description="My investment portfolio")
        portfolio = portfolio_service.create_portfolio(portfolio_data)

        assert portfolio.id is not None
        assert portfolio.name == "Investment Portfolio"

        # Step 2: Add stock holding
        stock_holding_data = HoldingCreate(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            quantity=Decimal("10.0"),
            purchase_price=Decimal("150.0"),
            notes="Apple stock",
        )
        stock_holding = portfolio_service.add_holding(stock_holding_data)

        assert stock_holding.symbol == "AAPL"
        assert stock_holding.quantity == Decimal("10.0")

        # Step 3: Add crypto holding
        crypto_holding_data = HoldingCreate(
            portfolio_id=portfolio.id,
            symbol="BTC-USD",
            asset_type=AssetType.CRYPTOCURRENCY,
            quantity=Decimal("0.5"),
            purchase_price=Decimal("50000.0"),
            notes="Bitcoin",
        )
        crypto_holding = portfolio_service.add_holding(crypto_holding_data)

        assert crypto_holding.symbol == "BTC-USD"
        assert crypto_holding.asset_type == AssetType.CRYPTOCURRENCY

        # Step 4: Get all holdings
        holdings = portfolio_service.get_portfolio_holdings(portfolio.id)
        assert len(holdings) == 2

        # Step 5: Test calculations
        stock_cost = Decimal("10.0") * Decimal("150.0")  # 1500
        crypto_cost = Decimal("0.5") * Decimal("50000.0")  # 25000
        total_cost = stock_cost + crypto_cost  # 26500

        assert stock_cost == Decimal("1500.0")
        assert crypto_cost == Decimal("25000.0")
        assert total_cost == Decimal("26500.0")

    @patch("app.portfolio_service.price_service.get_multiple_prices")
    async def test_portfolio_metrics_calculation(self, mock_get_prices, new_db):
        """Test portfolio metrics calculation with mock prices"""
        # Create portfolio and holdings
        portfolio = portfolio_service.create_portfolio(PortfolioCreate(name="Test Portfolio"))

        if portfolio.id is not None:
            portfolio_service.add_holding(
                HoldingCreate(
                    portfolio_id=portfolio.id,
                    symbol="AAPL",
                    asset_type=AssetType.STOCK,
                    quantity=Decimal("10.0"),
                    purchase_price=Decimal("150.0"),
                )
            )

            portfolio_service.add_holding(
                HoldingCreate(
                    portfolio_id=portfolio.id,
                    symbol="GOOGL",
                    asset_type=AssetType.STOCK,
                    quantity=Decimal("5.0"),
                    purchase_price=Decimal("2000.0"),
                )
            )

        # Mock prices
        mock_get_prices.return_value = {
            "AAPL": Decimal("160.0"),  # +6.67% return
            "GOOGL": Decimal("2200.0"),  # +10% return
        }

        # Get metrics
        if portfolio.id is not None:
            holdings = await portfolio_service.get_holdings_with_metrics(portfolio.id)
            summary = await portfolio_service.get_portfolio_summary(portfolio.id)

            # Verify holdings metrics
            assert len(holdings) == 2

            aapl_holding = next(h for h in holdings if h.symbol == "AAPL")
            assert aapl_holding.current_price == Decimal("160.0")
            assert aapl_holding.total_cost == Decimal("1500.0")
            assert aapl_holding.current_value == Decimal("1600.0")
            assert aapl_holding.absolute_return == Decimal("100.0")

            googl_holding = next(h for h in holdings if h.symbol == "GOOGL")
            assert googl_holding.current_price == Decimal("2200.0")
            assert googl_holding.total_cost == Decimal("10000.0")
            assert googl_holding.current_value == Decimal("11000.0")
            assert googl_holding.absolute_return == Decimal("1000.0")

            # Verify summary
            assert summary is not None
            assert summary.total_holdings == 2
            assert summary.total_cost == Decimal("11500.0")  # 1500 + 10000
            assert summary.total_current_value == Decimal("12600.0")  # 1600 + 11000
            assert summary.total_absolute_return == Decimal("1100.0")  # 12600 - 11500
            assert summary.best_performer == "GOOGL"  # Higher percentage return

    def test_portfolio_crud_operations(self, new_db):
        """Test basic CRUD operations for portfolios"""
        # Create
        portfolio = portfolio_service.create_portfolio(PortfolioCreate(name="Test Portfolio"))
        assert portfolio.id is not None

        # Read
        retrieved = portfolio_service.get_portfolio(portfolio.id)
        assert retrieved is not None
        assert retrieved.name == "Test Portfolio"

        # Update
        from app.models import PortfolioUpdate

        updated = portfolio_service.update_portfolio(portfolio.id, PortfolioUpdate(name="Updated Portfolio"))
        assert updated is not None
        assert updated.name == "Updated Portfolio"

        # Delete
        result = portfolio_service.delete_portfolio(portfolio.id)
        assert result is True

        deleted = portfolio_service.get_portfolio(portfolio.id)
        assert deleted is None

    def test_holding_crud_operations(self, new_db):
        """Test basic CRUD operations for holdings"""
        # Create portfolio first
        portfolio = portfolio_service.create_portfolio(PortfolioCreate(name="Test Portfolio"))

        # Create holding
        if portfolio.id is not None:
            holding = portfolio_service.add_holding(
                HoldingCreate(
                    portfolio_id=portfolio.id,
                    symbol="AAPL",
                    asset_type=AssetType.STOCK,
                    quantity=Decimal("10.0"),
                    purchase_price=Decimal("150.0"),
                )
            )
            assert holding.id is not None

            # Read
            retrieved = portfolio_service.get_holding(holding.id)
            assert retrieved is not None
            assert retrieved.symbol == "AAPL"

            # Update
            from app.models import HoldingUpdate

            updated = portfolio_service.update_holding(holding.id, HoldingUpdate(quantity=Decimal("20.0")))
            assert updated is not None
            assert updated.quantity == Decimal("20.0")

            # Delete
            result = portfolio_service.delete_holding(holding.id)
            assert result is True

            deleted = portfolio_service.get_holding(holding.id)
            assert deleted is None
