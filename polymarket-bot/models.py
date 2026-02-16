"""
Polymarket Bot Core Data Models

This module defines all the core data models for the Polymarket trading bot including:
- BotState: Bot operational state and configuration
- Trade: Trading transaction records
- Position: Open/closed position tracking
- MarketData: Market information and pricing data

All models use Pydantic for validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class BotStatus(str, Enum):
    """Bot operational status enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"


class TradeStatus(str, Enum):
    """Trade execution status."""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PositionStatus(str, Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"


class OutcomeType(str, Enum):
    """Market outcome type."""
    YES = "yes"
    NO = "no"


class BotState(BaseModel):
    """
    Bot operational state and configuration tracking.

    Tracks the current state of the bot including status, configuration,
    performance metrics, and runtime information.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bot_id": "bot_001",
                "status": "running",
                "strategy_name": "momentum_v1",
                "max_position_size": 1000.00,
                "max_total_exposure": 5000.00,
                "risk_per_trade": 100.00,
                "active_markets": ["market_123", "market_456"],
                "total_trades": 42,
                "winning_trades": 28,
                "total_pnl": 350.50,
                "current_exposure": 2500.00,
                "api_key_active": True,
                "last_heartbeat": "2024-01-15T10:30:00Z",
                "error_message": None
            }
        }
    )

    # Bot Identity
    bot_id: str = Field(
        ...,
        description="Unique identifier for the bot instance",
        min_length=1
    )

    # Operational Status
    status: BotStatus = Field(
        default=BotStatus.INITIALIZING,
        description="Current operational status of the bot"
    )

    # Strategy Configuration
    strategy_name: str = Field(
        ...,
        description="Name of the trading strategy being used",
        min_length=1
    )

    # Risk Management
    max_position_size: Decimal = Field(
        ...,
        description="Maximum size for a single position in USD",
        gt=0
    )

    max_total_exposure: Decimal = Field(
        ...,
        description="Maximum total exposure across all positions in USD",
        gt=0
    )

    risk_per_trade: Decimal = Field(
        ...,
        description="Maximum risk per individual trade in USD",
        gt=0
    )

    # Active Trading State
    active_markets: List[str] = Field(
        default_factory=list,
        description="List of currently active market IDs"
    )

    # Performance Metrics
    total_trades: int = Field(
        default=0,
        description="Total number of trades executed",
        ge=0
    )

    winning_trades: int = Field(
        default=0,
        description="Number of profitable trades",
        ge=0
    )

    total_pnl: Decimal = Field(
        default=Decimal("0.00"),
        description="Total profit and loss in USD"
    )

    current_exposure: Decimal = Field(
        default=Decimal("0.00"),
        description="Current total exposure in USD",
        ge=0
    )

    # System Status
    api_key_active: bool = Field(
        default=True,
        description="Whether the API key is active and valid"
    )

    last_heartbeat: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last bot heartbeat"
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Last error message if status is ERROR"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Bot creation timestamp"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    @field_validator('current_exposure')
    @classmethod
    def validate_exposure(cls, v, info):
        """Validate that current exposure doesn't exceed max exposure."""
        if 'max_total_exposure' in info.data and v > info.data['max_total_exposure']:
            raise ValueError(f"Current exposure {v} exceeds max total exposure {info.data['max_total_exposure']}")
        return v

    @field_validator('winning_trades')
    @classmethod
    def validate_winning_trades(cls, v, info):
        """Validate that winning trades don't exceed total trades."""
        if 'total_trades' in info.data and v > info.data['total_trades']:
            raise ValueError(f"Winning trades {v} cannot exceed total trades {info.data['total_trades']}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize bot state to dictionary.

        Returns:
            Dictionary representation of the bot state
        """
        return {
            "bot_id": self.bot_id,
            "status": self.status.value,
            "strategy_name": self.strategy_name,
            "max_position_size": float(self.max_position_size),
            "max_total_exposure": float(self.max_total_exposure),
            "risk_per_trade": float(self.risk_per_trade),
            "active_markets": self.active_markets,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "total_pnl": float(self.total_pnl),
            "current_exposure": float(self.current_exposure),
            "api_key_active": self.api_key_active,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def get_win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class Trade(BaseModel):
    """
    Trading transaction record.

    Represents a single trade execution on the Polymarket platform,
    including order details, execution information, and outcome.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trade_id": "trade_001",
                "market_id": "market_123",
                "order_id": "order_456",
                "side": "buy",
                "order_type": "limit",
                "outcome": "yes",
                "price": 0.65,
                "quantity": 100,
                "filled_quantity": 100,
                "status": "executed",
                "executed_at": "2024-01-15T10:30:00Z",
                "fee": 0.50
            }
        }
    )

    # Trade Identity
    trade_id: str = Field(
        ...,
        description="Unique identifier for the trade",
        min_length=1
    )

    market_id: str = Field(
        ...,
        description="Polymarket market identifier",
        min_length=1
    )

    order_id: str = Field(
        ...,
        description="Order identifier from Polymarket API",
        min_length=1
    )

    # Order Details
    side: OrderSide = Field(
        ...,
        description="Buy or sell side"
    )

    order_type: OrderType = Field(
        ...,
        description="Market or limit order"
    )

    outcome: OutcomeType = Field(
        ...,
        description="Outcome being traded (yes/no)"
    )

    # Pricing and Quantity
    price: Decimal = Field(
        ...,
        description="Order price (0.00 to 1.00 for probability)",
        ge=0,
        le=1
    )

    quantity: Decimal = Field(
        ...,
        description="Order quantity (number of shares)",
        gt=0
    )

    filled_quantity: Decimal = Field(
        default=Decimal("0.00"),
        description="Quantity that has been filled",
        ge=0
    )

    # Execution Status
    status: TradeStatus = Field(
        default=TradeStatus.PENDING,
        description="Current status of the trade"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Trade creation timestamp"
    )

    executed_at: Optional[datetime] = Field(
        default=None,
        description="Trade execution timestamp"
    )

    # Cost and Fees
    fee: Decimal = Field(
        default=Decimal("0.00"),
        description="Trading fee paid in USD",
        ge=0
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional trade metadata"
    )

    @field_validator('filled_quantity')
    @classmethod
    def validate_filled_quantity(cls, v, info):
        """Validate that filled quantity doesn't exceed total quantity."""
        if 'quantity' in info.data and v > info.data['quantity']:
            raise ValueError(f"Filled quantity {v} cannot exceed total quantity {info.data['quantity']}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize trade to dictionary.

        Returns:
            Dictionary representation of the trade
        """
        return {
            "trade_id": self.trade_id,
            "market_id": self.market_id,
            "order_id": self.order_id,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "outcome": self.outcome.value,
            "price": float(self.price),
            "quantity": float(self.quantity),
            "filled_quantity": float(self.filled_quantity),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "fee": float(self.fee),
            "metadata": self.metadata
        }

    def get_total_cost(self) -> Decimal:
        """Calculate total cost including fees."""
        base_cost = self.price * self.filled_quantity
        return base_cost + self.fee

    def is_filled(self) -> bool:
        """Check if the trade is fully filled."""
        return self.filled_quantity == self.quantity and self.status == TradeStatus.EXECUTED


class Position(BaseModel):
    """
    Trading position tracking.

    Tracks open and closed positions in specific markets,
    including entry/exit details and profit/loss calculations.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position_id": "pos_001",
                "market_id": "market_123",
                "outcome": "yes",
                "status": "open",
                "quantity": 100,
                "entry_price": 0.65,
                "current_price": 0.70,
                "realized_pnl": 0.00,
                "unrealized_pnl": 5.00,
                "trade_ids": ["trade_001", "trade_002"]
            }
        }
    )

    # Position Identity
    position_id: str = Field(
        ...,
        description="Unique identifier for the position",
        min_length=1
    )

    market_id: str = Field(
        ...,
        description="Polymarket market identifier",
        min_length=1
    )

    outcome: OutcomeType = Field(
        ...,
        description="Outcome being traded (yes/no)"
    )

    # Position Status
    status: PositionStatus = Field(
        default=PositionStatus.OPEN,
        description="Current status of the position"
    )

    # Position Details
    quantity: Decimal = Field(
        ...,
        description="Current position quantity (shares held)"
    )

    entry_price: Decimal = Field(
        ...,
        description="Average entry price",
        ge=0,
        le=1
    )

    current_price: Decimal = Field(
        ...,
        description="Current market price",
        ge=0,
        le=1
    )

    exit_price: Optional[Decimal] = Field(
        default=None,
        description="Average exit price for closed positions",
        ge=0,
        le=1
    )

    # Profit and Loss
    realized_pnl: Decimal = Field(
        default=Decimal("0.00"),
        description="Realized profit and loss in USD"
    )

    unrealized_pnl: Decimal = Field(
        default=Decimal("0.00"),
        description="Unrealized profit and loss in USD"
    )

    # Related Trades
    trade_ids: List[str] = Field(
        default_factory=list,
        description="List of trade IDs that make up this position"
    )

    # Timestamps
    opened_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Position open timestamp"
    )

    closed_at: Optional[datetime] = Field(
        default=None,
        description="Position close timestamp"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional position metadata"
    )

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Validate quantity is appropriate for position status."""
        # Quantity can be 0 or negative for closed/short positions
        return v

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize position to dictionary.

        Returns:
            Dictionary representation of the position
        """
        return {
            "position_id": self.position_id,
            "market_id": self.market_id,
            "outcome": self.outcome.value,
            "status": self.status.value,
            "quantity": float(self.quantity),
            "entry_price": float(self.entry_price),
            "current_price": float(self.current_price),
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "trade_ids": self.trade_ids,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

    def update_pnl(self, current_market_price: Decimal) -> None:
        """
        Update profit/loss calculations based on current market price.

        Args:
            current_market_price: Current market price for the outcome
        """
        self.current_price = current_market_price

        if self.status == PositionStatus.OPEN:
            # Calculate unrealized PnL
            price_diff = current_market_price - self.entry_price
            self.unrealized_pnl = price_diff * self.quantity
        elif self.status == PositionStatus.CLOSED and self.exit_price:
            # Calculate realized PnL
            price_diff = self.exit_price - self.entry_price
            self.realized_pnl = price_diff * self.quantity
            self.unrealized_pnl = Decimal("0.00")

        self.updated_at = datetime.utcnow()

    def get_total_pnl(self) -> Decimal:
        """Calculate total profit/loss (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    def get_position_value(self) -> Decimal:
        """Calculate current position value at market price."""
        return self.quantity * self.current_price


class MarketData(BaseModel):
    """
    Market information and pricing data.

    Represents current market state including pricing, volume,
    and metadata from the Polymarket platform.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "market_id": "market_123",
                "question": "Will Bitcoin reach $100k in 2024?",
                "end_date": "2024-12-31T23:59:59Z",
                "yes_price": 0.65,
                "no_price": 0.35,
                "yes_volume": 150000.00,
                "no_volume": 85000.00,
                "total_liquidity": 50000.00,
                "is_active": True,
                "resolution": None
            }
        }
    )

    # Market Identity
    market_id: str = Field(
        ...,
        description="Unique Polymarket market identifier",
        min_length=1
    )

    # Market Question
    question: str = Field(
        ...,
        description="Market question or title",
        min_length=1
    )

    description: Optional[str] = Field(
        default=None,
        description="Detailed market description"
    )

    # Market Timing
    created_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Market creation timestamp"
    )

    end_date: datetime = Field(
        ...,
        description="Market end/resolution timestamp"
    )

    # Pricing Data
    yes_price: Decimal = Field(
        ...,
        description="Current YES outcome price (probability)",
        ge=0,
        le=1
    )

    no_price: Decimal = Field(
        ...,
        description="Current NO outcome price (probability)",
        ge=0,
        le=1
    )

    # Volume and Liquidity
    yes_volume: Decimal = Field(
        default=Decimal("0.00"),
        description="Total volume for YES outcome in USD",
        ge=0
    )

    no_volume: Decimal = Field(
        default=Decimal("0.00"),
        description="Total volume for NO outcome in USD",
        ge=0
    )

    total_liquidity: Decimal = Field(
        default=Decimal("0.00"),
        description="Total market liquidity in USD",
        ge=0
    )

    # Market Status
    is_active: bool = Field(
        default=True,
        description="Whether the market is active for trading"
    )

    is_closed: bool = Field(
        default=False,
        description="Whether the market is closed"
    )

    resolution: Optional[OutcomeType] = Field(
        default=None,
        description="Market resolution outcome (if resolved)"
    )

    # Metadata
    category: Optional[str] = Field(
        default=None,
        description="Market category"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Market tags"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional market metadata"
    )

    # Update Tracking
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last data update timestamp"
    )

    @field_validator('yes_price', 'no_price')
    @classmethod
    def validate_prices(cls, v):
        """Validate price is within valid probability range."""
        if not (0 <= v <= 1):
            raise ValueError(f"Price {v} must be between 0 and 1")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize market data to dictionary.

        Returns:
            Dictionary representation of the market data
        """
        return {
            "market_id": self.market_id,
            "question": self.question,
            "description": self.description,
            "created_date": self.created_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "yes_price": float(self.yes_price),
            "no_price": float(self.no_price),
            "yes_volume": float(self.yes_volume),
            "no_volume": float(self.no_volume),
            "total_liquidity": float(self.total_liquidity),
            "is_active": self.is_active,
            "is_closed": self.is_closed,
            "resolution": self.resolution.value if self.resolution else None,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
            "last_updated": self.last_updated.isoformat()
        }

    def get_total_volume(self) -> Decimal:
        """Calculate total market volume."""
        return self.yes_volume + self.no_volume

    def get_price_spread(self) -> Decimal:
        """Calculate spread between yes and no prices."""
        return abs(self.yes_price - self.no_price)

    def validate_prices_sum(self) -> bool:
        """Validate that yes and no prices approximately sum to 1."""
        total = self.yes_price + self.no_price
        # Allow small tolerance for rounding
        return abs(total - Decimal("1.0")) < Decimal("0.01")
