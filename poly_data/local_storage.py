"""
Local SQLite Storage Manager
Handles high-frequency data writes with connection pooling and WAL mode.
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
import threading
import numpy as np


class LocalStorage:
    """SQLite storage for high-frequency trading data."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite storage with connection pooling.

        Args:
            db_path: Path to SQLite database file. Defaults to data/trading_local.db
        """
        if db_path is None:
            db_path = os.getenv('SQLITE_DB_PATH', 'data/trading_local.db')

        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def _init_db(self):
        """Initialize database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")

            # Trades table - complete trade records (30 days retention)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    condition_id TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    side TEXT CHECK(side IN ('BUY', 'SELL')),
                    price REAL NOT NULL,
                    size REAL NOT NULL,
                    filled_size REAL DEFAULT 0,
                    status TEXT CHECK(status IN ('PLACED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED')),
                    order_id TEXT,
                    pnl REAL,
                    notes TEXT,
                    synced_to_airtable BOOLEAN DEFAULT FALSE,
                    market_name TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_condition ON trades(condition_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_synced ON trades(synced_to_airtable)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_order ON trades(order_id)")

            # Reward snapshots table - 5 minute snapshots (7 days retention)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_snapshots (
                    timestamp DATETIME,
                    condition_id TEXT,
                    token_id TEXT,
                    side TEXT,
                    order_price REAL,
                    mid_price REAL,
                    distance_from_mid REAL,
                    position_size REAL,
                    estimated_hourly_reward REAL,
                    daily_rate REAL,
                    max_spread REAL,
                    market_name TEXT,
                    PRIMARY KEY (timestamp, token_id, side)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rewards_time ON reward_snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rewards_condition ON reward_snapshots(condition_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rewards_token ON reward_snapshots(token_id)")

            # Position history table - position snapshots (30 days retention)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_history (
                    timestamp DATETIME,
                    token_id TEXT,
                    size REAL,
                    avg_price REAL,
                    market_price REAL,
                    pnl REAL,
                    market_name TEXT,
                    condition_id TEXT,
                    PRIMARY KEY (timestamp, token_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_time ON position_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_position_token ON position_history(token_id)")

            # Order lifecycle table - track order states
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_lifecycle (
                    order_id TEXT PRIMARY KEY,
                    condition_id TEXT,
                    token_id TEXT,
                    side TEXT,
                    price REAL,
                    original_size REAL,
                    created_at DATETIME,
                    updated_at DATETIME,
                    status TEXT,
                    filled_size REAL DEFAULT 0,
                    cancelled_size REAL DEFAULT 0,
                    market_name TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_condition ON order_lifecycle(condition_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_status ON order_lifecycle(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_created ON order_lifecycle(created_at)")

            # Market archive table - archived market data for ended markets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_archive (
                    timestamp DATETIME,
                    condition_id TEXT,
                    question TEXT,
                    answer1 TEXT,
                    answer2 TEXT,
                    token1 TEXT,
                    token2 TEXT,
                    best_bid REAL,
                    best_ask REAL,
                    spread REAL,
                    gm_reward_per_100 REAL,
                    volatility_sum REAL,
                    end_date DATE,
                    PRIMARY KEY (condition_id, end_date)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_archive_condition ON market_archive(condition_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_archive_time ON market_archive(timestamp)")

            # Market data history table - for backtesting
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_history (
                    timestamp DATETIME,
                    condition_id TEXT,
                    token_id TEXT,
                    best_bid REAL,
                    best_ask REAL,
                    mid_price REAL,
                    spread REAL,
                    volume_24h REAL,
                    PRIMARY KEY (timestamp, token_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_history_time ON market_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_history_condition ON market_history(condition_id)")

            # Trade summary cache - daily aggregated data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_summary_cache (
                    date DATE PRIMARY KEY,
                    condition_id TEXT,
                    total_trades INTEGER,
                    buy_count INTEGER,
                    sell_count INTEGER,
                    total_volume REAL,
                    total_pnl REAL,
                    avg_trade_size REAL,
                    synced_to_airtable BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Alerts backup table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT CHECK(level IN ('info', 'warning', 'error', 'critical')),
                    message TEXT,
                    details TEXT,
                    condition_id TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level)")

            # Simulation balance history table - for dry run mode
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_balance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    usdc_balance REAL NOT NULL,
                    position_value REAL NOT NULL DEFAULT 0,
                    total_value REAL NOT NULL,
                    realized_pnl REAL NOT NULL DEFAULT 0,
                    unrealized_pnl REAL NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_balance_time ON simulation_balance(timestamp)")

            conn.commit()
            conn.close()

    def log_trade(self, trade_data: Dict[str, Any]) -> int:
        """Log a trade to SQLite.

        Args:
            trade_data: Dictionary containing trade information

        Returns:
            ID of the inserted trade record
        """
        def to_native_type(val):
            """Convert numpy/pandas types to native Python types"""
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            return val

        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    timestamp, condition_id, token_id, side, price, size,
                    filled_size, status, order_id, pnl, notes, market_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data.get('condition_id', ''),
                trade_data.get('token_id', ''),
                trade_data.get('side', ''),
                float(trade_data.get('price', 0)),
                float(trade_data.get('size', 0)),
                float(to_native_type(trade_data.get('filled_size', 0))),
                trade_data.get('status', 'PLACED'),
                str(trade_data.get('order_id', '')),
                float(to_native_type(trade_data.get('pnl', 0))),
                trade_data.get('notes', ''),
                trade_data.get('market', '')[:100] if trade_data.get('market') else ''
            ))
            return cursor.lastrowid

    def log_trades_batch(self, trades: List[Dict[str, Any]]) -> int:
        """Log multiple trades in a batch for better performance.

        Args:
            trades: List of trade data dictionaries

        Returns:
            Number of trades inserted
        """
        if not trades:
            return 0

        def to_native_type(val):
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            return val

        with self._transaction() as conn:
            cursor = conn.cursor()
            records = []
            for trade in trades:
                records.append((
                    trade.get('timestamp', datetime.now().isoformat()),
                    trade.get('condition_id', ''),
                    trade.get('token_id', ''),
                    trade.get('side', ''),
                    float(trade.get('price', 0)),
                    float(trade.get('size', 0)),
                    float(to_native_type(trade.get('filled_size', 0))),
                    trade.get('status', 'PLACED'),
                    str(trade.get('order_id', '')),
                    float(to_native_type(trade.get('pnl', 0))),
                    trade.get('notes', ''),
                    trade.get('market', '')[:100] if trade.get('market') else ''
                ))

            cursor.executemany("""
                INSERT INTO trades (
                    timestamp, condition_id, token_id, side, price, size,
                    filled_size, status, order_id, pnl, notes, market_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            return len(records)

    def log_reward_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """Log a reward snapshot.

        Args:
            snapshot_data: Dictionary containing reward snapshot information

        Returns:
            True if successful
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO reward_snapshots (
                    timestamp, condition_id, token_id, side, order_price,
                    mid_price, distance_from_mid, position_size, estimated_hourly_reward,
                    daily_rate, max_spread, market_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot_data.get('timestamp', datetime.now().isoformat()),
                snapshot_data.get('condition_id', ''),
                snapshot_data.get('token_id', ''),
                snapshot_data.get('side', ''),
                float(snapshot_data.get('order_price', 0)),
                float(snapshot_data.get('mid_price', 0)),
                float(snapshot_data.get('distance_from_mid', 0)),
                float(snapshot_data.get('position_size', 0)),
                float(snapshot_data.get('estimated_hourly_reward', 0)),
                float(snapshot_data.get('daily_rate', 0)),
                float(snapshot_data.get('max_spread', 0)),
                snapshot_data.get('market_name', '')[:80]
            ))
            return True

    def log_position(self, position_data: Dict[str, Any]) -> bool:
        """Log a position snapshot.

        Args:
            position_data: Dictionary containing position information

        Returns:
            True if successful
        """
        def to_native_type(val):
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            return val

        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO position_history (
                    timestamp, token_id, size, avg_price, market_price, pnl,
                    market_name, condition_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data.get('timestamp', datetime.now().isoformat()),
                str(position_data.get('token_id', '')),
                float(to_native_type(position_data.get('size', 0))),
                float(to_native_type(position_data.get('avg_price', 0))),
                float(to_native_type(position_data.get('market_price', 0))),
                float(to_native_type(position_data.get('pnl', 0))),
                position_data.get('market_name', '')[:100],
                position_data.get('condition_id', '')
            ))
            return True

    def log_positions_batch(self, positions: List[Dict[str, Any]]) -> int:
        """Log multiple positions in a batch.

        Args:
            positions: List of position data dictionaries

        Returns:
            Number of positions inserted
        """
        if not positions:
            return 0

        def to_native_type(val):
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            return val

        with self._transaction() as conn:
            cursor = conn.cursor()
            records = []
            timestamp = datetime.now().isoformat()
            for pos in positions:
                records.append((
                    pos.get('timestamp', timestamp),
                    str(pos.get('token_id', '')),
                    float(to_native_type(pos.get('size', 0))),
                    float(to_native_type(pos.get('avg_price', 0))),
                    float(to_native_type(pos.get('market_price', 0))),
                    float(to_native_type(pos.get('pnl', 0))),
                    pos.get('market_name', '')[:100],
                    pos.get('condition_id', '')
                ))

            cursor.executemany("""
                INSERT OR REPLACE INTO position_history (
                    timestamp, token_id, size, avg_price, market_price, pnl,
                    market_name, condition_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            return len(records)

    def update_order_lifecycle(self, order_data: Dict[str, Any]) -> bool:
        """Update order lifecycle information.

        Args:
            order_data: Dictionary containing order lifecycle information

        Returns:
            True if successful
        """
        with self._transaction() as conn:
            cursor = conn.cursor()

            # Check if order exists
            cursor.execute("SELECT order_id FROM order_lifecycle WHERE order_id = ?",
                          (str(order_data.get('order_id')),))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE order_lifecycle SET
                        updated_at = ?,
                        status = ?,
                        filled_size = ?,
                        cancelled_size = ?
                    WHERE order_id = ?
                """, (
                    datetime.now().isoformat(),
                    order_data.get('status', ''),
                    float(order_data.get('filled_size', 0)),
                    float(order_data.get('cancelled_size', 0)),
                    str(order_data.get('order_id'))
                ))
            else:
                cursor.execute("""
                    INSERT INTO order_lifecycle (
                        order_id, condition_id, token_id, side, price,
                        original_size, created_at, updated_at, status,
                        filled_size, cancelled_size, market_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(order_data.get('order_id')),
                    order_data.get('condition_id', ''),
                    order_data.get('token_id', ''),
                    order_data.get('side', ''),
                    float(order_data.get('price', 0)),
                    float(order_data.get('original_size', 0)),
                    order_data.get('created_at', datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    order_data.get('status', 'PLACED'),
                    float(order_data.get('filled_size', 0)),
                    float(order_data.get('cancelled_size', 0)),
                    order_data.get('market_name', '')[:100]
                ))
            return True

    def archive_market(self, market_data: Dict[str, Any]) -> bool:
        """Archive market data for an ended market.

        Args:
            market_data: Dictionary containing market information

        Returns:
            True if successful
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_archive (
                    timestamp, condition_id, question, answer1, answer2,
                    token1, token2, best_bid, best_ask, spread,
                    gm_reward_per_100, volatility_sum, end_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                market_data.get('condition_id', ''),
                market_data.get('question', ''),
                market_data.get('answer1', ''),
                market_data.get('answer2', ''),
                market_data.get('token1', ''),
                market_data.get('token2', ''),
                float(market_data.get('best_bid', 0)),
                float(market_data.get('best_ask', 0)),
                float(market_data.get('spread', 0)),
                float(market_data.get('gm_reward_per_100', 0)),
                float(market_data.get('volatility_sum', 0)),
                market_data.get('end_date')
            ))
            return True

    def log_market_history(self, history_data: Dict[str, Any]) -> bool:
        """Log market data for backtesting.

        Args:
            history_data: Dictionary containing market history information

        Returns:
            True if successful
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_history (
                    timestamp, condition_id, token_id, best_bid, best_ask,
                    mid_price, spread, volume_24h
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                history_data.get('timestamp', datetime.now().isoformat()),
                history_data.get('condition_id', ''),
                history_data.get('token_id', ''),
                float(history_data.get('best_bid', 0)),
                float(history_data.get('best_ask', 0)),
                float(history_data.get('mid_price', 0)),
                float(history_data.get('spread', 0)),
                float(history_data.get('volume_24h', 0))
            ))
            return True

    def log_alert(self, level: str, message: str, details: str = "",
                  condition_id: str = "") -> int:
        """Log an alert to local storage.

        Args:
            level: Alert level (info/warning/error/critical)
            message: Alert message
            details: Detailed information
            condition_id: Related market condition ID

        Returns:
            ID of the inserted alert
        """
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (level, message, details, condition_id)
                VALUES (?, ?, ?, ?)
            """, (level, message, details, condition_id))
            return cursor.lastrowid

    def cleanup_old_data(self, retention_days: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """Clean up old data according to retention policies.

        Args:
            retention_days: Dictionary mapping table names to retention days.
                          Defaults to environment variable settings.

        Returns:
            Dictionary with number of rows deleted per table
        """
        if retention_days is None:
            retention_days = {
                'trades': int(os.getenv('TRADE_RETENTION_DAYS', 30)),
                'reward_snapshots': int(os.getenv('REWARD_SNAPSHOT_RETENTION_DAYS', 7)),
                'position_history': int(os.getenv('POSITION_HISTORY_RETENTION_DAYS', 30)),
                'market_history': int(os.getenv('MARKET_HISTORY_RETENTION_DAYS', 30)),
                'alerts': int(os.getenv('ALERT_RETENTION_DAYS', 30)),
            }

        deleted_counts = {}

        with self._transaction() as conn:
            cursor = conn.cursor()

            for table, days in retention_days.items():
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

                # Get count before deletion
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timestamp < ?", (cutoff_date,))
                count = cursor.fetchone()[0]

                if count > 0:
                    cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_date,))
                    deleted_counts[table] = count

            # Clean up old order lifecycle records (completed orders older than 7 days)
            cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM order_lifecycle
                WHERE updated_at < ? AND status IN ('FILLED', 'CANCELLED')
            """, (cutoff_date,))
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("""
                    DELETE FROM order_lifecycle
                    WHERE updated_at < ? AND status IN ('FILLED', 'CANCELLED')
                """, (cutoff_date,))
                deleted_counts['order_lifecycle'] = count

            # Vacuum to reclaim space
            conn.execute("VACUUM")

        return deleted_counts

    def export_daily_summary(self, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Export daily trade summary for Airtable sync.

        Args:
            date: Date to summarize. Defaults to yesterday.

        Returns:
            Dictionary with summary data or None if no trades
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)

        date_str = date.strftime('%Y-%m-%d')
        next_date_str = (date + timedelta(days=1)).strftime('%Y-%m-%d')

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get summary for the day
            cursor.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                    SUM(size) as total_volume,
                    SUM(pnl) as total_pnl,
                    AVG(size) as avg_trade_size
                FROM trades
                WHERE timestamp >= ? AND timestamp < ?
            """, (date_str, next_date_str))

            row = cursor.fetchone()
            if row and row[0] > 0:
                summary = {
                    'date': date_str,
                    'total_trades': row[0],
                    'buy_count': row[1],
                    'sell_count': row[2],
                    'total_volume': row[3] or 0,
                    'total_pnl': row[4] or 0,
                    'avg_trade_size': row[5] or 0
                }

                # Cache the summary
                with self._transaction() as txn_conn:
                    txn_cursor = txn_conn.cursor()
                    txn_cursor.execute("""
                        INSERT OR REPLACE INTO trade_summary_cache
                        (date, total_trades, buy_count, sell_count, total_volume, total_pnl, avg_trade_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (summary['date'], summary['total_trades'], summary['buy_count'],
                          summary['sell_count'], summary['total_volume'],
                          summary['total_pnl'], summary['avg_trade_size']))

                return summary

            return None

    def get_unsynced_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trades that haven't been synced to Airtable.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trade dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE synced_to_airtable = FALSE
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

    def mark_trades_synced(self, trade_ids: List[int]) -> bool:
        """Mark trades as synced to Airtable.

        Args:
            trade_ids: List of trade IDs to mark as synced

        Returns:
            True if successful
        """
        if not trade_ids:
            return True

        with self._transaction() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(trade_ids))
            cursor.execute(f"""
                UPDATE trades
                SET synced_to_airtable = TRUE
                WHERE id IN ({placeholders})
            """, trade_ids)
            return True

    def get_recent_trades(self, hours: int = 24, condition_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent trades from SQLite.

        Args:
            hours: Number of hours to look back
            condition_id: Optional filter by condition_id

        Returns:
            List of trade dictionaries
        """
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if condition_id:
                cursor.execute("""
                    SELECT * FROM trades
                    WHERE timestamp > ? AND condition_id = ?
                    ORDER BY timestamp DESC
                """, (cutoff, condition_id))
            else:
                cursor.execute("""
                    SELECT * FROM trades
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (cutoff,))

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

    def get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}
            tables = ['trades', 'reward_snapshots', 'position_history',
                     'order_lifecycle', 'market_archive', 'market_history', 'alerts']

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f'{table}_count'] = cursor.fetchone()[0]

            # Get database file size
            stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)

            return stats

    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
