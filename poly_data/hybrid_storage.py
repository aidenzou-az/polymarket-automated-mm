"""
Hybrid Storage Layer - Unified interface for Airtable + SQLite
Routes data to appropriate storage based on frequency and importance.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dotenv import load_dotenv
import threading
import time

from poly_data.local_storage import LocalStorage
from poly_data.airtable_client import AirtableClient, PYAIRTABLE_AVAILABLE

load_dotenv()


class HybridStorage:
    """Hybrid storage combining Airtable (config/summary) + SQLite (high-frequency).

    Data routing strategy:
    - High-frequency writes (trades, snapshots) -> SQLite
    - Configuration (markets, trading params) -> Airtable
    - Aggregated data (daily summaries) -> Airtable
    - Alerts -> Both (Airtable for UI, SQLite for backup)
    """

    def __init__(self, use_airtable: bool = True, use_sqlite: bool = True):
        """Initialize hybrid storage.

        Args:
            use_airtable: Whether to use Airtable
            use_sqlite: Whether to use SQLite
        """
        self.backend = os.getenv('STORAGE_BACKEND', 'hybrid')

        # Initialize SQLite storage
        self.sqlite = LocalStorage() if use_sqlite else None

        # Initialize Airtable storage (with fallback)
        self.airtable = None
        if use_airtable and self.backend in ('airtable', 'hybrid'):
            try:
                if PYAIRTABLE_AVAILABLE:
                    self.airtable = AirtableClient()
                else:
                    print("Warning: pyairtable not installed. Airtable features disabled.")
            except Exception as e:
                print(f"Warning: Failed to initialize Airtable: {e}")
                print("Falling back to SQLite-only mode.")

        # Configuration cache
        self._config_cache = {}
        self._config_cache_time = 0
        self._config_refresh_interval = 60  # Refresh every 60 seconds
        self._config_lock = threading.Lock()

        # Async batch queue for Airtable writes
        self._pending_alerts = []
        self._pending_summaries = []

    def log_trade(self, trade_data: Dict[str, Any], significant_only: bool = False) -> bool:
        """Log a trade.

        Strategy:
        1. Always write to SQLite (fast, reliable)
        2. Important trades also written to Airtable (if enabled)

        Args:
            trade_data: Trade information dictionary
            significant_only: If True, only log significant trades to Airtable

        Returns:
            True if SQLite write successful
        """
        # Always log to SQLite
        if self.sqlite:
            try:
                self.sqlite.log_trade(trade_data)
            except Exception as e:
                print(f"Error logging trade to SQLite: {e}")
                return False

        # Log significant trades to Airtable
        if self.airtable and not significant_only:
            if self._is_significant_trade(trade_data):
                try:
                    # Create alert for significant trades
                    message = f"Trade: {trade_data.get('side')} {trade_data.get('size')} @ ${trade_data.get('price', 0):.4f}"
                    self.airtable.send_alert(
                        level='info',
                        message=message,
                        details=str(trade_data),
                        condition_id=trade_data.get('condition_id', '')
                    )
                except Exception as e:
                    print(f"Error sending trade alert to Airtable: {e}")

        return True

    def _is_significant_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Determine if a trade is significant enough for Airtable.

        Args:
            trade_data: Trade information

        Returns:
            True if significant
        """
        # Large trades (> $500)
        if trade_data.get('size', 0) > 500:
            return True

        # High P&L trades (|PnL| > $50)
        pnl = abs(trade_data.get('pnl', 0))
        if pnl > 50:
            return True

        # Error trades
        if 'error' in str(trade_data.get('notes', '')).lower():
            return True

        return False

    def log_trades_batch(self, trades: List[Dict[str, Any]]) -> int:
        """Log multiple trades in batch.

        Args:
            trades: List of trade dictionaries

        Returns:
            Number of trades logged
        """
        if not trades:
            return 0

        if self.sqlite:
            return self.sqlite.log_trades_batch(trades)

        return 0

    def get_recent_trades(self, hours: int = 24, condition_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent trades.

        Args:
            hours: Hours to look back
            condition_id: Optional market filter

        Returns:
            List of trade dictionaries
        """
        if self.sqlite:
            return self.sqlite.get_recent_trades(hours, condition_id)
        return []

    def log_reward_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """Log reward snapshot to SQLite only.

        Args:
            snapshot_data: Snapshot information

        Returns:
            True if successful
        """
        if self.sqlite:
            return self.sqlite.log_reward_snapshot(snapshot_data)
        return False

    def log_position(self, position_data: Dict[str, Any]) -> bool:
        """Log position snapshot to SQLite.

        Args:
            position_data: Position information

        Returns:
            True if successful
        """
        if self.sqlite:
            return self.sqlite.log_position(position_data)
        return False

    def log_positions_batch(self, positions: List[Dict[str, Any]]) -> int:
        """Log multiple positions in batch.

        Args:
            positions: List of position dictionaries

        Returns:
            Number of positions logged
        """
        if self.sqlite:
            return self.sqlite.log_positions_batch(positions)
        return 0

    def update_order_lifecycle(self, order_data: Dict[str, Any]) -> bool:
        """Update order lifecycle in SQLite.

        Args:
            order_data: Order lifecycle information

        Returns:
            True if successful
        """
        if self.sqlite:
            return self.sqlite.update_order_lifecycle(order_data)
        return False

    def get_trading_configs(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get trading configurations from Airtable with caching.

        Args:
            force_refresh: Force refresh from Airtable

        Returns:
            List of trading config dictionaries
        """
        with self._config_lock:
            current_time = time.time()

            # Return cached configs if fresh
            if not force_refresh and self._config_cache:
                if current_time - self._config_cache_time < self._config_refresh_interval:
                    return self._config_cache.get('configs', [])

            # Fetch from Airtable
            if self.airtable:
                try:
                    configs = self.airtable.get_trading_configs()
                    self._config_cache['configs'] = configs
                    self._config_cache_time = current_time
                    return configs
                except Exception as e:
                    print(f"Error fetching configs from Airtable: {e}")
                    # Return cached if available
                    if self._config_cache.get('configs'):
                        return self._config_cache['configs']

            return []

    def get_markets_df(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Get markets as DataFrame with parameters.

        Args:
            force_refresh: Force refresh from Airtable

        Returns:
            Tuple of (DataFrame, params dict)
        """
        import pandas as pd

        configs = self.get_trading_configs(force_refresh)

        if not configs:
            return pd.DataFrame(), {}

        # Convert to DataFrame
        df = pd.DataFrame(configs)

        # Build params dict
        params = {}
        for config in configs:
            condition_id = config.get('condition_id')
            if condition_id:
                params[condition_id] = {
                    'trade_size': config.get('trade_size', 50),
                    'max_size': config.get('max_size', 100),
                    'param_type': config.get('param_type', 'default'),
                }

        return df, params

    def upsert_trading_config(self, config: Dict[str, Any]) -> bool:
        """Upsert a trading configuration.

        Args:
            config: Trading configuration

        Returns:
            True if successful
        """
        if self.airtable:
            try:
                return self.airtable.upsert_trading_config(config)
            except Exception as e:
                print(f"Error upserting config to Airtable: {e}")
                return False
        return False

    def get_active_markets(self) -> List[Dict[str, Any]]:
        """Get active markets from Airtable.

        Returns:
            List of market dictionaries
        """
        if self.airtable:
            try:
                return self.airtable.get_active_markets()
            except Exception as e:
                print(f"Error fetching markets from Airtable: {e}")
        return []

    def upsert_markets_batch(self, markets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch upsert markets to Airtable.

        Args:
            markets: List of market dictionaries

        Returns:
            Dictionary with operation results
        """
        if self.airtable:
            try:
                return self.airtable.upsert_markets_batch(markets)
            except Exception as e:
                print(f"Error upserting markets to Airtable: {e}")
                return {'success': 0, 'errors': len(markets), 'error_details': [str(e)]}
        return {'success': 0, 'errors': len(markets), 'error_details': ['Airtable not available']}

    def archive_market(self, market_data: Dict[str, Any]) -> bool:
        """Archive market data to SQLite.

        Args:
            market_data: Market information

        Returns:
            True if successful
        """
        if self.sqlite:
            return self.sqlite.archive_market(market_data)
        return False

    def log_trade_summary(self, summary: Dict[str, Any]) -> bool:
        """Log daily trade summary to Airtable.

        Args:
            summary: Daily summary data

        Returns:
            True if successful
        """
        if self.airtable:
            try:
                return self.airtable.log_trade_summary(summary)
            except Exception as e:
                print(f"Error logging trade summary to Airtable: {e}")
        return False

    def export_daily_summary(self, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Export daily summary from SQLite and sync to Airtable.

        Args:
            date: Date to summarize. Defaults to yesterday.

        Returns:
            Summary dictionary or None
        """
        if not self.sqlite:
            return None

        summary = self.sqlite.export_daily_summary(date)

        if summary and self.airtable:
            try:
                self.airtable.log_trade_summary(summary)
            except Exception as e:
                print(f"Error syncing summary to Airtable: {e}")

        return summary

    def send_alert(self, level: str, message: str, details: str = "",
                   condition_id: str = "") -> bool:
        """Send alert to both Airtable and SQLite.

        Args:
            level: Alert level (info/warning/error/critical)
            message: Alert message
            details: Detailed information
            condition_id: Related market condition ID

        Returns:
            True if at least one storage succeeded
        """
        success = False

        # Log to SQLite
        if self.sqlite:
            try:
                self.sqlite.log_alert(level, message, details, condition_id)
                success = True
            except Exception as e:
                print(f"Error logging alert to SQLite: {e}")

        # Send to Airtable
        if self.airtable:
            try:
                self.airtable.send_alert(level, message, details, condition_id)
                success = True
            except Exception as e:
                print(f"Error sending alert to Airtable: {e}")

        return success

    def get_unacknowledged_alerts(self) -> List[Dict[str, Any]]:
        """Get unacknowledged alerts from Airtable.

        Returns:
            List of alert dictionaries
        """
        if self.airtable:
            try:
                return self.airtable.get_unacknowledged_alerts()
            except Exception as e:
                print(f"Error fetching alerts from Airtable: {e}")
        return []

    def cleanup_old_data(self) -> Dict[str, Any]:
        """Cleanup old data from both storages.

        Returns:
            Dictionary with cleanup statistics
        """
        results = {
            'sqlite': {},
            'airtable': {}
        }

        # Cleanup SQLite
        if self.sqlite:
            try:
                results['sqlite'] = self.sqlite.cleanup_old_data()
            except Exception as e:
                results['sqlite']['error'] = str(e)

        # Cleanup Airtable
        if self.airtable:
            try:
                alerts_deleted = self.airtable.cleanup_old_alerts()
                summaries_deleted = self.airtable.cleanup_old_trade_summaries()
                results['airtable'] = {
                    'alerts_deleted': alerts_deleted,
                    'summaries_deleted': summaries_deleted
                }
            except Exception as e:
                results['airtable']['error'] = str(e)

        return results

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'backend': self.backend,
            'sqlite_available': self.sqlite is not None,
            'airtable_available': self.airtable is not None,
        }

        if self.sqlite:
            try:
                stats['sqlite'] = self.sqlite.get_db_stats()
            except Exception as e:
                stats['sqlite'] = {'error': str(e)}

        if self.airtable:
            try:
                stats['airtable'] = self.airtable.check_record_count()
            except Exception as e:
                stats['airtable'] = {'error': str(e)}

        return stats

    def is_healthy(self) -> bool:
        """Check if storage is healthy.

        Returns:
            True if at least one storage backend is working
        """
        sqlite_ok = False
        airtable_ok = False

        if self.sqlite:
            try:
                stats = self.sqlite.get_db_stats()
                sqlite_ok = 'error' not in stats
            except:
                pass

        if self.airtable:
            try:
                self.airtable.check_record_count()
                airtable_ok = True
            except:
                pass

        return sqlite_ok or airtable_ok

    def close(self):
        """Close storage connections."""
        if self.sqlite:
            self.sqlite.close()


# Import pandas for type hints
import pandas as pd

# Singleton instance
_storage_instance = None


def get_hybrid_storage(use_airtable: bool = True, use_sqlite: bool = True) -> 'HybridStorage':
    """Get singleton hybrid storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = HybridStorage(use_airtable, use_sqlite)
    return _storage_instance
