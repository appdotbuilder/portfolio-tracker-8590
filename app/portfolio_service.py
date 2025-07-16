from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from sqlmodel import select
from app.database import get_session
from app.models import (
    Portfolio,
    Holding,
    HoldingCreate,
    HoldingUpdate,
    HoldingWithMetrics,
    PortfolioSummary,
    PortfolioCreate,
    PortfolioUpdate,
)
from app.price_service import price_service


class PortfolioService:
    def create_portfolio(self, portfolio_data: PortfolioCreate) -> Portfolio:
        """Create a new portfolio"""
        with get_session() as session:
            portfolio = Portfolio(name=portfolio_data.name, description=portfolio_data.description)
            session.add(portfolio)
            session.commit()
            session.refresh(portfolio)
            return portfolio

    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        with get_session() as session:
            return session.get(Portfolio, portfolio_id)

    def get_all_portfolios(self) -> List[Portfolio]:
        """Get all portfolios"""
        with get_session() as session:
            statement = select(Portfolio).order_by(Portfolio.name)
            return list(session.exec(statement))

    def update_portfolio(self, portfolio_id: int, portfolio_data: PortfolioUpdate) -> Optional[Portfolio]:
        """Update portfolio"""
        with get_session() as session:
            portfolio = session.get(Portfolio, portfolio_id)
            if portfolio is None:
                return None

            if portfolio_data.name is not None:
                portfolio.name = portfolio_data.name
            if portfolio_data.description is not None:
                portfolio.description = portfolio_data.description

            portfolio.updated_at = datetime.utcnow()
            session.add(portfolio)
            session.commit()
            session.refresh(portfolio)
            return portfolio

    def delete_portfolio(self, portfolio_id: int) -> bool:
        """Delete portfolio and all its holdings"""
        with get_session() as session:
            portfolio = session.get(Portfolio, portfolio_id)
            if portfolio is None:
                return False

            # Delete all holdings first
            statement = select(Holding).where(Holding.portfolio_id == portfolio_id)
            holdings = session.exec(statement)
            for holding in holdings:
                session.delete(holding)

            # Delete portfolio
            session.delete(portfolio)
            session.commit()
            return True

    def add_holding(self, holding_data: HoldingCreate) -> Holding:
        """Add a new holding to a portfolio"""
        with get_session() as session:
            holding = Holding(
                portfolio_id=holding_data.portfolio_id,
                symbol=holding_data.symbol.upper(),
                asset_type=holding_data.asset_type,
                quantity=holding_data.quantity,
                purchase_price=holding_data.purchase_price,
                purchase_date=holding_data.purchase_date or datetime.utcnow(),
                notes=holding_data.notes,
            )
            session.add(holding)
            session.commit()
            session.refresh(holding)
            return holding

    def get_holding(self, holding_id: int) -> Optional[Holding]:
        """Get holding by ID"""
        with get_session() as session:
            return session.get(Holding, holding_id)

    def get_portfolio_holdings(self, portfolio_id: int) -> List[Holding]:
        """Get all holdings for a portfolio"""
        with get_session() as session:
            statement = select(Holding).where(Holding.portfolio_id == portfolio_id).order_by(Holding.symbol)
            return list(session.exec(statement))

    def update_holding(self, holding_id: int, holding_data: HoldingUpdate) -> Optional[Holding]:
        """Update a holding"""
        with get_session() as session:
            holding = session.get(Holding, holding_id)
            if holding is None:
                return None

            if holding_data.symbol is not None:
                holding.symbol = holding_data.symbol.upper()
            if holding_data.asset_type is not None:
                holding.asset_type = holding_data.asset_type
            if holding_data.quantity is not None:
                holding.quantity = holding_data.quantity
            if holding_data.purchase_price is not None:
                holding.purchase_price = holding_data.purchase_price
            if holding_data.purchase_date is not None:
                holding.purchase_date = holding_data.purchase_date
            if holding_data.notes is not None:
                holding.notes = holding_data.notes

            holding.updated_at = datetime.utcnow()
            session.add(holding)
            session.commit()
            session.refresh(holding)
            return holding

    def delete_holding(self, holding_id: int) -> bool:
        """Delete a holding"""
        with get_session() as session:
            holding = session.get(Holding, holding_id)
            if holding is None:
                return False

            session.delete(holding)
            session.commit()
            return True

    async def get_holdings_with_metrics(self, portfolio_id: int) -> List[HoldingWithMetrics]:
        """Get holdings with calculated metrics including current prices"""
        holdings = self.get_portfolio_holdings(portfolio_id)

        if not holdings:
            return []

        # Get current prices for all symbols
        symbols = [h.symbol for h in holdings]
        prices = await price_service.get_multiple_prices(symbols)

        holdings_with_metrics = []
        for holding in holdings:
            if holding.id is None:
                continue

            current_price = prices.get(holding.symbol)

            # Calculate metrics
            total_cost = holding.quantity * holding.purchase_price
            current_value = None
            absolute_return = None
            percentage_return = None

            if current_price is not None:
                current_value = holding.quantity * current_price
                absolute_return = current_value - total_cost
                if total_cost > 0:
                    percentage_return = (absolute_return / total_cost) * Decimal("100")

            holding_with_metrics = HoldingWithMetrics(
                id=holding.id,
                portfolio_id=holding.portfolio_id,
                symbol=holding.symbol,
                asset_type=holding.asset_type,
                quantity=holding.quantity,
                purchase_price=holding.purchase_price,
                purchase_date=holding.purchase_date,
                notes=holding.notes,
                created_at=holding.created_at,
                updated_at=holding.updated_at,
                current_price=current_price,
                current_value=current_value,
                total_cost=total_cost,
                absolute_return=absolute_return,
                percentage_return=percentage_return,
                last_updated=datetime.now(),
            )
            holdings_with_metrics.append(holding_with_metrics)

        return holdings_with_metrics

    async def get_portfolio_summary(self, portfolio_id: int) -> Optional[PortfolioSummary]:
        """Get portfolio summary with aggregated metrics"""
        portfolio = self.get_portfolio(portfolio_id)
        if portfolio is None:
            return None

        holdings_with_metrics = await self.get_holdings_with_metrics(portfolio_id)

        if not holdings_with_metrics:
            return PortfolioSummary(
                portfolio_id=portfolio_id,
                portfolio_name=portfolio.name,
                total_holdings=0,
                total_cost=Decimal("0"),
                total_current_value=Decimal("0"),
                total_absolute_return=Decimal("0"),
                total_percentage_return=Decimal("0"),
                last_updated=datetime.now(),
            )

        # Calculate aggregated metrics
        total_cost = Decimal("0")
        total_current_value = Decimal("0")

        for h in holdings_with_metrics:
            if h.total_cost is not None:
                total_cost += h.total_cost
            if h.current_value is not None:
                total_current_value += h.current_value

        total_absolute_return = total_current_value - total_cost
        total_percentage_return = (
            (total_absolute_return / total_cost * Decimal("100")) if total_cost > 0 else Decimal("0")
        )

        # Find best and worst performers
        best_performer = None
        worst_performer = None
        best_return = None
        worst_return = None

        for holding in holdings_with_metrics:
            if holding.percentage_return is not None:
                if best_return is None or holding.percentage_return > best_return:
                    best_return = holding.percentage_return
                    best_performer = holding.symbol
                if worst_return is None or holding.percentage_return < worst_return:
                    worst_return = holding.percentage_return
                    worst_performer = holding.symbol

        return PortfolioSummary(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            total_holdings=len(holdings_with_metrics),
            total_cost=total_cost,
            total_current_value=total_current_value,
            total_absolute_return=total_absolute_return,
            total_percentage_return=total_percentage_return,
            best_performer=best_performer,
            worst_performer=worst_performer,
            last_updated=datetime.now(),
        )


# Global instance
portfolio_service = PortfolioService()
