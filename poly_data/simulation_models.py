"""
Simulation Models - Data structures for the dry-run simulation engine.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class OrderStatus(Enum):
    """Order status enumeration."""
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class VirtualOrder:
    """Represents a virtual order in the simulation."""
    order_id: str
    token_id: str
    condition_id: str
    side: OrderSide
    price: float
    size: float
    filled_size: float = 0.0
    status: OrderStatus = OrderStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    market_name: str = ""
    neg_risk: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary."""
        return {
            'order_id': self.order_id,
            'token_id': self.token_id,
            'condition_id': self.condition_id,
            'side': self.side.value,
            'price': self.price,
            'size': self.size,
            'filled_size': self.filled_size,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'market_name': self.market_name,
            'neg_risk': self.neg_risk
        }

    @property
    def remaining_size(self) -> float:
        """Get remaining size to fill."""
        return self.size - self.filled_size

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.filled_size >= self.size


@dataclass
class Fill:
    """Represents a fill event for an order."""
    fill_id: str
    order_id: str
    token_id: str
    condition_id: str
    side: OrderSide
    price: float
    size: float
    filled_at: datetime = field(default_factory=datetime.now)
    pnl: Optional[float] = None
    market_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert fill to dictionary."""
        return {
            'fill_id': self.fill_id,
            'order_id': self.order_id,
            'token_id': self.token_id,
            'condition_id': self.condition_id,
            'side': self.side.value,
            'price': self.price,
            'size': self.size,
            'filled_at': self.filled_at.isoformat(),
            'pnl': self.pnl,
            'market_name': self.market_name
        }


@dataclass
class VirtualPosition:
    """Represents a virtual position in the simulation."""
    token_id: str
    condition_id: str
    size: float = 0.0
    avg_price: float = 0.0
    market_name: str = ""
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary."""
        return {
            'token_id': self.token_id,
            'condition_id': self.condition_id,
            'size': self.size,
            'avg_price': self.avg_price,
            'market_name': self.market_name,
            'last_updated': self.last_updated.isoformat()
        }

    def update_with_fill(self, fill: Fill) -> float:
        """
        Update position with a new fill.

        Args:
            fill: The fill event to process

        Returns:
            Realized PnL from this fill (if any)
        """
        realized_pnl = 0.0

        if fill.side == OrderSide.BUY:
            if self.size < 0:
                # Buying to close a short position
                close_size = min(abs(self.size), fill.size)
                realized_pnl = (self.avg_price - fill.price) * close_size

                if fill.size > abs(self.size):
                    # Switching from short to long
                    self.size = fill.size - abs(self.size)
                    self.avg_price = fill.price
                elif fill.size == abs(self.size):
                    # Exactly closed the short
                    self.size = 0
                    self.avg_price = 0
                else:
                    # Partially closed the short
                    self.size += fill.size  # size is negative
            else:
                # Adding to long position
                total_value = self.size * self.avg_price + fill.size * fill.price
                self.size += fill.size
                self.avg_price = total_value / self.size if self.size > 0 else 0

        elif fill.side == OrderSide.SELL:
            if self.size > 0:
                # Selling to close a long position
                close_size = min(self.size, fill.size)
                realized_pnl = (fill.price - self.avg_price) * close_size

                if fill.size > self.size:
                    # Switching from long to short
                    self.size = -(fill.size - self.size)
                    self.avg_price = fill.price
                elif fill.size == self.size:
                    # Exactly closed the long
                    self.size = 0
                    self.avg_price = 0
                else:
                    # Partially closed the long
                    self.size -= fill.size
            else:
                # Adding to short position
                total_value = abs(self.size) * self.avg_price + fill.size * fill.price
                self.size -= fill.size
                self.avg_price = total_value / abs(self.size) if self.size < 0 else 0

        self.last_updated = datetime.now()
        return realized_pnl

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL at current market price."""
        if self.size == 0:
            return 0.0
        return (current_price - self.avg_price) * self.size


@dataclass
class SimulationBalance:
    """Represents the virtual balance state."""
    usdc_balance: float = 10000.0
    position_value: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_value(self) -> float:
        """Get total account value."""
        return self.usdc_balance + self.position_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert balance to dictionary."""
        return {
            'usdc_balance': self.usdc_balance,
            'position_value': self.position_value,
            'total_value': self.total_value,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class SimulationReport:
    """Represents a simulation performance report."""
    initial_balance: float
    current_balance: float
    total_pnl: float
    total_pnl_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_trade_pnl: float
    max_drawdown: float
    max_drawdown_pct: float
    open_positions: int
    start_time: datetime
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_trade_pnl': self.avg_trade_pnl,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'open_positions': self.open_positions,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None
        }
