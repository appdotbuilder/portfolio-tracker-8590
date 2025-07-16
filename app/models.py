from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum


class AssetType(str, Enum):
    STOCK = "stock"
    CRYPTOCURRENCY = "crypto"


# Persistent models (stored in database)
class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    holdings: List["Holding"] = Relationship(back_populates="portfolio")


class Holding(SQLModel, table=True):
    __tablename__ = "holdings"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id")
    symbol: str = Field(max_length=20, index=True)  # e.g., "AAPL", "BTC-USD"
    asset_type: AssetType = Field(default=AssetType.STOCK)
    quantity: Decimal = Field(gt=0, decimal_places=8)  # Support crypto precision
    purchase_price: Decimal = Field(gt=0, decimal_places=8)
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    notes: str = Field(default="", max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    portfolio: Portfolio = Relationship(back_populates="holdings")


class PriceHistory(SQLModel, table=True):
    __tablename__ = "price_history"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(max_length=20, index=True)
    price: Decimal = Field(gt=0, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    source: str = Field(default="yfinance", max_length=50)  # Track data source


# Non-persistent schemas (for validation, forms, API requests/responses)
class PortfolioCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)


class PortfolioUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class HoldingCreate(SQLModel, table=False):
    portfolio_id: int
    symbol: str = Field(max_length=20)
    asset_type: AssetType = Field(default=AssetType.STOCK)
    quantity: Decimal = Field(gt=0, decimal_places=8)
    purchase_price: Decimal = Field(gt=0, decimal_places=8)
    purchase_date: Optional[datetime] = Field(default=None)
    notes: str = Field(default="", max_length=1000)


class HoldingUpdate(SQLModel, table=False):
    symbol: Optional[str] = Field(default=None, max_length=20)
    asset_type: Optional[AssetType] = Field(default=None)
    quantity: Optional[Decimal] = Field(default=None, gt=0, decimal_places=8)
    purchase_price: Optional[Decimal] = Field(default=None, gt=0, decimal_places=8)
    purchase_date: Optional[datetime] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=1000)


class HoldingWithMetrics(SQLModel, table=False):
    """Schema for holding with calculated metrics"""

    id: int
    portfolio_id: int
    symbol: str
    asset_type: AssetType
    quantity: Decimal
    purchase_price: Decimal
    purchase_date: datetime
    notes: str
    created_at: datetime
    updated_at: datetime

    # Calculated fields
    current_price: Optional[Decimal] = Field(default=None)
    current_value: Optional[Decimal] = Field(default=None)
    total_cost: Optional[Decimal] = Field(default=None)
    absolute_return: Optional[Decimal] = Field(default=None)
    percentage_return: Optional[Decimal] = Field(default=None)
    last_updated: Optional[datetime] = Field(default=None)


class PortfolioSummary(SQLModel, table=False):
    """Schema for portfolio summary with aggregated metrics"""

    portfolio_id: int
    portfolio_name: str
    total_holdings: int
    total_cost: Decimal
    total_current_value: Decimal
    total_absolute_return: Decimal
    total_percentage_return: Decimal
    best_performer: Optional[str] = Field(default=None)
    worst_performer: Optional[str] = Field(default=None)
    last_updated: datetime


class PriceData(SQLModel, table=False):
    """Schema for price data response"""

    symbol: str
    price: Decimal
    timestamp: datetime
    source: str = Field(default="yfinance")
    currency: str = Field(default="USD")
    market_cap: Optional[Decimal] = Field(default=None)
    volume: Optional[Decimal] = Field(default=None)
