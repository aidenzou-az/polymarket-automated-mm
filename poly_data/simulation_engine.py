"""
Simulation Engine - Core matching engine for dry-run trading simulation.
"""
import os
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict

from poly_data.simulation_models import (
    VirtualOrder, Fill, VirtualPosition, SimulationBalance,
    OrderSide, OrderStatus
)
from poly_data.local_storage import LocalStorage

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Core simulation engine for dry-run trading.

    Manages virtual orders, positions, and balance without real money.
    Simulates order matching based on real-time market data.
    """

    def __init__(self, initial_balance: float = 10000.0, storage: Optional[LocalStorage] = None):
        """
        Initialize the simulation engine.

        Args:
            initial_balance: Starting virtual USDC balance (default: $10,000)
            storage: LocalStorage instance for persisting simulation data
        """
        self.initial_balance = initial_balance
        self.balance = SimulationBalance(usdc_balance=initial_balance)

        # Storage for persistence
        self.storage = storage or LocalStorage()

        # Virtual order book: {token_id: [VirtualOrder]}
        self.virtual_orders: Dict[str, List[VirtualOrder]] = defaultdict(list)

        # Virtual positions: {token_id: VirtualPosition}
        self.virtual_positions: Dict[str, VirtualPosition] = {}

        # Order ID counter for generating unique IDs
        self._order_counter = 0
        self._fill_counter = 0

        # Performance tracking
        self.filled_orders: List[VirtualOrder] = []
        self.all_fills: List[Fill] = []
        self.start_time = datetime.now()

        # Balance history for drawdown calculation
        self.balance_history: List[Tuple[datetime, float]] = []

        # Matching mode: 'aggressive' = immediate fill, 'conservative' = wait for touch
        self.matching_mode = os.getenv('SIMULATION_MATCHING_MODE', 'aggressive').lower()

        logger.info(f"🎮 Simulation Engine initialized with ${initial_balance:,.2f} virtual balance")
        logger.info(f"   Matching mode: {self.matching_mode}")

        # Initialize database tables
        self._init_simulation_tables()

    def _init_simulation_tables(self):
        """Initialize simulation-specific database tables."""
        import sqlite3

        conn = sqlite3.connect(self.storage.db_path)
        cursor = conn.cursor()

        # Simulation configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Simulation balance history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_balance (
                timestamp DATETIME PRIMARY KEY,
                usdc_balance REAL,
                position_value REAL,
                total_value REAL,
                unrealized_pnl REAL,
                realized_pnl REAL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_balance_time ON simulation_balance(timestamp)")

        # Store initial config
        cursor.execute("""
            INSERT OR REPLACE INTO simulation_config (key, value, updated_at)
            VALUES (?, ?, ?)
        """, ('initial_balance', str(self.initial_balance), datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def _generate_order_id(self) -> str:
        """Generate a unique order ID."""
        self._order_counter += 1
        return f"SIM-{self._order_counter:06d}"

    def _generate_fill_id(self) -> str:
        """Generate a unique fill ID."""
        self._fill_counter += 1
        return f"FILL-{self._fill_counter:06d}"

    def create_virtual_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        market_data: Optional[Dict[str, Any]] = None,
        condition_id: str = "",
        market_name: str = "",
        neg_risk: bool = False
    ) -> Dict[str, Any]:
        """
        Create a virtual order and immediately attempt to match it.

        Args:
            token_id: The token ID to trade
            side: 'BUY' or 'SELL'
            price: Order price
            size: Order size in USDC
            market_data: Current market data with bids/asks (optional)
            condition_id: Market condition ID
            market_name: Human-readable market name
            neg_risk: Whether this is a negative risk market

        Returns:
            Dictionary with order details and fill information
        """
        side_enum = OrderSide.BUY if side.upper() == 'BUY' else OrderSide.SELL

        # Create the virtual order
        order = VirtualOrder(
            order_id=self._generate_order_id(),
            token_id=str(token_id),
            condition_id=condition_id,
            side=side_enum,
            price=float(price),
            size=float(size),
            market_name=market_name,
            neg_risk=neg_risk
        )

        logger.info(f"📝 Virtual Order Created: {order.side.value} {order.size} @ {order.price:.4f} "
                   f"(ID: {order.order_id})")

        # Try to match if market data is available
        fills = []
        if market_data:
            fills = self.try_match_order(order, market_data)

        # Store the order
        self.virtual_orders[token_id].append(order)

        # Log to database
        self._log_order_to_db(order)

        # If there are fills, process them
        if fills:
            for fill in fills:
                self._process_fill(fill, order)

        return {
            'orderID': order.order_id,
            'status': order.status.value,
            'simulated': True,
            'fills': [fill.to_dict() for fill in fills],
            'order': order.to_dict()
        }

    def try_match_order(
        self,
        order: VirtualOrder,
        market_data: Dict[str, Any]
    ) -> List[Fill]:
        """
        Try to match an order against current market data.

        Args:
            order: The virtual order to match
            market_data: Current market data with 'best_bid', 'best_ask', etc.

        Returns:
            List of Fill objects (empty if no match)
        """
        fills = []

        # Extract market data
        best_bid = market_data.get('best_bid', 0)
        best_ask = market_data.get('best_ask', 1)
        bid_size = market_data.get('bid_size', 0) or market_data.get('best_bid_size', 0)
        ask_size = market_data.get('ask_size', 0) or market_data.get('best_ask_size', 0)

        if order.side == OrderSide.BUY:
            # Buy order fills if our price >= best_ask (we're willing to pay more than sellers ask)
            if order.price >= best_ask and best_ask > 0:
                fill_size = min(order.remaining_size, ask_size)
                if fill_size > 0:
                    fill = Fill(
                        fill_id=self._generate_fill_id(),
                        order_id=order.order_id,
                        token_id=order.token_id,
                        condition_id=order.condition_id,
                        side=order.side,
                        price=best_ask,  # Fill at market price (taker)
                        size=fill_size,
                        market_name=order.market_name
                    )
                    fills.append(fill)
                    logger.info(f"✅ Buy Order FILLED: {fill_size} @ {best_ask:.4f} "
                               f"(order: {order.order_id})")

        elif order.side == OrderSide.SELL:
            # Sell order fills if our price <= best_bid (we're willing to sell lower than buyers bid)
            if order.price <= best_bid and best_bid > 0:
                fill_size = min(order.remaining_size, bid_size)
                if fill_size > 0:
                    fill = Fill(
                        fill_id=self._generate_fill_id(),
                        order_id=order.order_id,
                        token_id=order.token_id,
                        condition_id=order.condition_id,
                        side=order.side,
                        price=best_bid,  # Fill at market price (taker)
                        size=fill_size,
                        market_name=order.market_name
                    )
                    fills.append(fill)
                    logger.info(f"✅ Sell Order FILLED: {fill_size} @ {best_bid:.4f} "
                               f"(order: {order.order_id})")

        return fills

    def process_market_update(self, token_id: str, market_data: Dict[str, Any]):
        """
        Process a market data update and check for fills on open orders.

        Args:
            token_id: The token that received an update
            market_data: Current market data
        """
        open_orders = [
            order for order in self.virtual_orders.get(token_id, [])
            if order.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)
        ]

        for order in open_orders:
            fills = self.try_match_order(order, market_data)
            for fill in fills:
                self._process_fill(fill, order)

    def _process_fill(self, fill: Fill, order: VirtualOrder):
        """
        Process a fill event.

        Args:
            fill: The fill event
            order: The order being filled
        """
        # Update order fill status
        order.filled_size += fill.size
        if order.filled_size >= order.size:
            order.status = OrderStatus.FILLED
            self.filled_orders.append(order)
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        # Get or create position
        position = self._get_or_create_position(fill.token_id, fill.condition_id, fill.market_name)

        # Calculate realized PnL
        realized_pnl = position.update_with_fill(fill)
        fill.pnl = realized_pnl

        # Update balance
        fill_value = fill.size * fill.price
        if fill.side == OrderSide.BUY:
            self.balance.usdc_balance -= fill_value
        else:
            self.balance.usdc_balance += fill_value

        if realized_pnl != 0:
            self.balance.realized_pnl += realized_pnl

        # Store fill
        self.all_fills.append(fill)

        # Log to database
        self._log_fill_to_db(fill)
        self._update_position_in_db(position)

        logger.info(f"💰 Fill processed: {fill.side.value} {fill.size} @ {fill.price:.4f} "
                   f"| Realized PnL: ${realized_pnl:.4f} | Balance: ${self.balance.usdc_balance:.2f}")

    def _get_or_create_position(
        self,
        token_id: str,
        condition_id: str = "",
        market_name: str = ""
    ) -> VirtualPosition:
        """Get existing position or create new one."""
        if token_id not in self.virtual_positions:
            self.virtual_positions[token_id] = VirtualPosition(
                token_id=token_id,
                condition_id=condition_id,
                market_name=market_name
            )
        return self.virtual_positions[token_id]

    def _log_order_to_db(self, order: VirtualOrder):
        """Log order to trades table."""
        try:
            # Map OrderStatus to database status
            status_map = {
                'OPEN': 'PLACED',
                'PARTIALLY_FILLED': 'PARTIALLY_FILLED',
                'FILLED': 'FILLED',
                'CANCELLED': 'CANCELLED'
            }
            db_status = status_map.get(order.status.value, 'PLACED')

            self.storage.log_trade({
                'timestamp': order.created_at.isoformat(),
                'condition_id': order.condition_id,
                'token_id': order.token_id,
                'side': order.side.value,
                'price': order.price,
                'size': order.size,
                'filled_size': order.filled_size,
                'status': db_status,
                'order_id': order.order_id,
                'market': order.market_name,
                'notes': f'SIMULATION: {self.matching_mode} mode'
            })
        except Exception as e:
            logger.warning(f"Failed to log order to DB: {e}")

    def _log_fill_to_db(self, fill: Fill):
        """Log fill to trades table as a completed trade."""
        try:
            self.storage.log_trade({
                'timestamp': fill.filled_at.isoformat(),
                'condition_id': fill.condition_id,
                'token_id': fill.token_id,
                'side': fill.side.value,
                'price': fill.price,
                'size': fill.size,
                'filled_size': fill.size,
                'status': 'FILLED',
                'order_id': fill.order_id,
                'pnl': fill.pnl,
                'market': fill.market_name,
                'notes': f'SIMULATION FILL: {fill.fill_id}'
            })
        except Exception as e:
            logger.warning(f"Failed to log fill to DB: {e}")

    def _update_position_in_db(self, position: VirtualPosition):
        """Update position in database."""
        try:
            self.storage.log_position({
                'timestamp': position.last_updated.isoformat(),
                'token_id': position.token_id,
                'size': position.size,
                'avg_price': position.avg_price,
                'market_price': 0,  # Will be updated with market data
                'pnl': position.calculate_unrealized_pnl(0),
                'market_name': position.market_name,
                'condition_id': position.condition_id
            })
        except Exception as e:
            logger.warning(f"Failed to update position in DB: {e}")

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a virtual order.

        Args:
            order_id: The order ID to cancel

        Returns:
            True if cancelled, False if not found or already filled
        """
        for token_id, orders in self.virtual_orders.items():
            for order in orders:
                if order.order_id == order_id:
                    if order.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
                        order.status = OrderStatus.CANCELLED
                        self._log_order_to_db(order)
                        logger.info(f"🚫 Order cancelled: {order_id}")
                        return True
                    return False
        return False

    def cancel_all_orders(self, token_id: Optional[str] = None):
        """
        Cancel all virtual orders, optionally filtered by token.

        Args:
            token_id: Optional token ID to filter by
        """
        tokens = [token_id] if token_id else list(self.virtual_orders.keys())

        for tid in tokens:
            for order in self.virtual_orders.get(tid, []):
                if order.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
                    order.status = OrderStatus.CANCELLED
                    self._log_order_to_db(order)

        logger.info(f"🚫 Cancelled all orders{' for ' + token_id if token_id else ''}")

    def get_virtual_positions(self) -> Dict[str, VirtualPosition]:
        """Get all virtual positions."""
        return self.virtual_positions.copy()

    def get_virtual_orders(self, token_id: Optional[str] = None) -> List[VirtualOrder]:
        """
        Get virtual orders.

        Args:
            token_id: Optional token ID to filter by

        Returns:
            List of VirtualOrder objects
        """
        if token_id:
            return list(self.virtual_orders.get(token_id, []))
        all_orders = []
        for orders in self.virtual_orders.values():
            all_orders.extend(orders)
        return all_orders

    def get_open_orders(self, token_id: Optional[str] = None) -> List[VirtualOrder]:
        """Get open (not filled/cancelled) orders."""
        orders = self.get_virtual_orders(token_id)
        return [o for o in orders if o.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)]

    def update_position_values(self, token_id: str, current_price: float):
        """
        Update position value calculations with current market price.

        Args:
            token_id: The token to update
            current_price: Current market price
        """
        position = self.virtual_positions.get(token_id)
        if position:
            position.last_updated = datetime.now()

    def get_balance_snapshot(self) -> Dict[str, Any]:
        """Get current balance snapshot."""
        # Calculate position value
        position_value = 0.0
        unrealized_pnl = 0.0

        for token_id, position in self.virtual_positions.items():
            if position.size != 0:
                # We'll need market price from caller
                # For now, just store the position size
                pass

        self.balance.position_value = position_value
        self.balance.unrealized_pnl = unrealized_pnl
        self.balance.timestamp = datetime.now()

        # Store in history
        self.balance_history.append((self.balance.timestamp, self.balance.total_value))

        # Log to database
        try:
            import sqlite3
            conn = sqlite3.connect(self.storage.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO simulation_balance
                (timestamp, usdc_balance, position_value, total_value, unrealized_pnl, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.balance.timestamp.isoformat(),
                self.balance.usdc_balance,
                position_value,
                self.balance.total_value,
                unrealized_pnl,
                self.balance.realized_pnl
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log balance to DB: {e}")

        return self.balance.to_dict()

    def calculate_max_drawdown(self) -> Tuple[float, float]:
        """
        Calculate maximum drawdown from balance history.

        Returns:
            Tuple of (max drawdown amount, max drawdown percentage)
        """
        if not self.balance_history:
            return 0.0, 0.0

        peak = self.initial_balance
        max_dd = 0.0
        max_dd_pct = 0.0

        for timestamp, value in self.balance_history:
            if value > peak:
                peak = value
            dd = peak - value
            dd_pct = (dd / peak) * 100 if peak > 0 else 0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        return max_dd, max_dd_pct

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive simulation report.

        Returns:
            Dictionary with performance metrics
        """
        # Count winning/losing trades
        winning_trades = sum(1 for f in self.all_fills if (f.pnl or 0) > 0)
        losing_trades = sum(1 for f in self.all_fills if (f.pnl or 0) < 0)
        total_trades = len(self.all_fills)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = (self.balance.realized_pnl / total_trades) if total_trades > 0 else 0

        max_dd, max_dd_pct = self.calculate_max_drawdown()

        open_pos_count = sum(1 for p in self.virtual_positions.values() if p.size != 0)

        total_pnl = self.balance.realized_pnl + self.balance.unrealized_pnl
        total_pnl_pct = (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0

        report = {
            'initial_balance': self.initial_balance,
            'current_balance': self.balance.total_value,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_trade_pnl': avg_pnl,
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'open_positions': open_pos_count,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'simulation_duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600
        }

        return report

    def print_status(self):
        """Print current simulation status to console."""
        report = self.generate_report()

        print("\n" + "=" * 60)
        print("🎮  DRY RUN SIMULATION STATUS")
        print("=" * 60)
        print(f"💰  Virtual Balance: ${self.balance.usdc_balance:,.2f}")
        print(f"📊  Position Value:  ${report['current_balance'] - self.balance.usdc_balance:,.2f}")
        print(f"💵  Total Value:     ${report['current_balance']:,.2f}")
        print(f"📈  Realized PnL:    ${self.balance.realized_pnl:,.2f}")
        print(f"📉  Unrealized PnL:  ${self.balance.unrealized_pnl:,.2f}")
        print(f"🎯  Total Trades:    {report['total_trades']}")
        print(f"✅  Winning: {report['winning_trades']} | ❌  Losing: {report['losing_trades']}")
        print(f"📊  Win Rate:        {report['win_rate']:.1f}%")
        print(f"📉  Max Drawdown:    ${report['max_drawdown']:.2f} ({report['max_drawdown_pct']:.2f}%)")
        print(f"📋  Open Orders:     {len(self.get_open_orders())}")
        print(f"📂  Open Positions:  {report['open_positions']}")
        print("=" * 60)

    def get_position_summary(self) -> Dict[str, Any]:
        """
        Get summary of positions formatted like Polymarket API response.

        Returns:
            Dictionary compatible with real position data format
        """
        positions_list = []
        for token_id, position in self.virtual_positions.items():
            if position.size != 0:
                positions_list.append({
                    'asset_id': token_id,
                    'position': position.size,
                    'avg_price': position.avg_price,
                    'market_name': position.market_name
                })

        return {
            'positions': positions_list,
            'usdc_balance': self.balance.usdc_balance,
            'total_value': self.balance.total_value
        }
