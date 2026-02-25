"""
Airtable Client - Handles all Airtable API interactions
Supports Free plan with 1,200 record limit per base.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import pyairtable, provide helpful error if not installed
try:
    from pyairtable import Api
    from pyairtable.formulas import match
    PYAIRTABLE_AVAILABLE = True
except ImportError:
    PYAIRTABLE_AVAILABLE = False


class AirtableClient:
    """Airtable API client for trading data storage.

    Tables:
    - Markets: Active markets (500 record limit)
    - Trading Configs: Trading configuration (20 records)
    - Trade Summary: Daily aggregated trades (90 records - 90 days)
    - Alerts: Alert notifications (100 records)
    """

    # Record limits for Free plan
    FREE_PLAN_LIMIT = 1200
    MARKETS_LIMIT = 500
    CONFIGS_LIMIT = 20
    TRADE_SUMMARY_LIMIT = 90
    ALERTS_LIMIT = 100

    def __init__(self, api_key: Optional[str] = None, base_id: Optional[str] = None):
        """Initialize Airtable client.

        Args:
            api_key: Airtable API key. Defaults to AIRTABLE_API_KEY env var.
            base_id: Airtable base ID. Defaults to AIRTABLE_BASE_ID env var.
        """
        if not PYAIRTABLE_AVAILABLE:
            raise ImportError(
                "pyairtable is not installed. "
                "Install it with: pip install pyairtable>=2.0.0"
            )

        self.api_key = api_key or os.getenv('AIRTABLE_API_KEY')
        self.base_id = base_id or os.getenv('AIRTABLE_BASE_ID')

        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY not set in environment")
        if not self.base_id:
            raise ValueError("AIRTABLE_BASE_ID not set in environment")

        self.api = Api(self.api_key)
        self.base = self.api.base(self.base_id)

        # Table references
        self._markets_table = None
        self._configs_table = None
        self._trade_summary_table = None
        self._alerts_table = None

    def _get_markets_table(self):
        """Lazy load Markets table."""
        if self._markets_table is None:
            self._markets_table = self.base.table('Markets')
        return self._markets_table

    def _get_configs_table(self):
        """Lazy load Trading Configs table."""
        if self._configs_table is None:
            self._configs_table = self.base.table('Trading Configs')
        return self._configs_table

    def _get_trade_summary_table(self):
        """Lazy load Trade Summary table."""
        if self._trade_summary_table is None:
            self._trade_summary_table = self.base.table('Trade Summary')
        return self._trade_summary_table

    def _get_alerts_table(self):
        """Lazy load Alerts table."""
        if self._alerts_table is None:
            self._alerts_table = self.base.table('Alerts')
        return self._alerts_table

    def check_record_count(self) -> Dict[str, Any]:
        """Check current record counts across all tables.

        Returns:
            Dictionary with record counts and limits
        """
        try:
            markets_count = len(self._get_markets_table().all())
        except:
            markets_count = 0

        try:
            configs_count = len(self._get_configs_table().all())
        except:
            configs_count = 0

        try:
            summary_count = len(self._get_trade_summary_table().all())
        except:
            summary_count = 0

        try:
            alerts_count = len(self._get_alerts_table().all())
        except:
            alerts_count = 0

        total = markets_count + configs_count + summary_count + alerts_count

        return {
            'markets': {'count': markets_count, 'limit': self.MARKETS_LIMIT},
            'configs': {'count': configs_count, 'limit': self.CONFIGS_LIMIT},
            'trade_summary': {'count': summary_count, 'limit': self.TRADE_SUMMARY_LIMIT},
            'alerts': {'count': alerts_count, 'limit': self.ALERTS_LIMIT},
            'total': {'count': total, 'limit': self.FREE_PLAN_LIMIT},
            'usage_percent': round(total / self.FREE_PLAN_LIMIT * 100, 1)
        }

    def upsert_markets_batch(self, markets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch upsert markets to Airtable.

        Args:
            markets: List of market dictionaries with condition_id as key field

        Returns:
            Dictionary with success count and errors
        """
        if not markets:
            return {'success': 0, 'errors': 0, 'error_details': []}

        table = self._get_markets_table()
        result = {'success': 0, 'errors': 0, 'error_details': []}

        # Prepare records for batch upsert
        records = []
        for market in markets:
            record = {
                'fields': {
                    'condition_id': str(market.get('condition_id', '')),
                    'question': str(market.get('question', ''))[:200],
                    'answer1': str(market.get('answer1', '')),
                    'answer2': str(market.get('answer2', '')),
                    'token1': str(market.get('token1', '')),
                    'token2': str(market.get('token2', '')),
                    'neg_risk': bool(market.get('neg_risk', False)),
                    'best_bid': float(market.get('best_bid', 0)),
                    'best_ask': float(market.get('best_ask', 0)),
                    'spread': float(market.get('spread', 0)),
                    'gm_reward_per_100': float(market.get('gm_reward_per_100', 0)),
                    'rewards_daily_rate': float(market.get('rewards_daily_rate', 0)),
                    'volatility_sum': float(market.get('volatility_sum', 0)),
                    'min_size': float(market.get('min_size', 50)),
                    'max_spread': float(market.get('max_spread', 1.0)),
                    'tick_size': float(market.get('tick_size', 0.01)),
                    'market_slug': str(market.get('market_slug', '')),
                    'status': market.get('status', 'active'),
                }
            }
            records.append(record)

        try:
            # Use batch_upsert with condition_id as key field
            response = table.batch_upsert(records, key_fields=['condition_id'])
            created = len(response.get('createdRecords', []))
            updated = len(response.get('updatedRecords', []))
            result['success'] = created + updated
            result['created'] = created
            result['updated'] = updated
            result['response'] = response
        except Exception as e:
            result['errors'] = len(records)
            result['error_details'].append(str(e))
            import traceback
            result['traceback'] = traceback.format_exc()

        return result

    def get_active_markets(self, status: str = 'active') -> List[Dict[str, Any]]:
        """Get active markets from Airtable.

        Args:
            status: Filter by status (active/ended/paused/archived)

        Returns:
            List of market dictionaries
        """
        table = self._get_markets_table()
        formula = match({'status': status})
        records = table.all(formula=formula)

        return [
            {
                'condition_id': r['fields'].get('condition_id', ''),
                'question': r['fields'].get('question', ''),
                'answer1': r['fields'].get('answer1', ''),
                'answer2': r['fields'].get('answer2', ''),
                'token1': r['fields'].get('token1', ''),
                'token2': r['fields'].get('token2', ''),
                'neg_risk': r['fields'].get('neg_risk', False),
                'best_bid': r['fields'].get('best_bid', 0),
                'best_ask': r['fields'].get('best_ask', 0),
                'spread': r['fields'].get('spread', 0),
                'gm_reward_per_100': r['fields'].get('gm_reward_per_100', 0),
                'rewards_daily_rate': r['fields'].get('rewards_daily_rate', 0),
                'volatility_sum': r['fields'].get('volatility_sum', 0),
                'min_size': r['fields'].get('min_size', 50),
                'max_spread': r['fields'].get('max_spread', 1.0),
                'tick_size': r['fields'].get('tick_size', 0.01),
                'market_slug': r['fields'].get('market_slug', ''),
                'status': r['fields'].get('status', 'active'),
                'last_updated': r['fields'].get('last_updated'),
                'record_id': r['id']
            }
            for r in records
        ]

    def get_all_markets(self) -> List[Dict[str, Any]]:
        """Get all markets from Airtable.

        Returns:
            List of market dictionaries
        """
        table = self._get_markets_table()
        records = table.all()

        return [
            {
                'condition_id': r['fields'].get('condition_id', ''),
                'question': r['fields'].get('question', ''),
                'answer1': r['fields'].get('answer1', ''),
                'answer2': r['fields'].get('answer2', ''),
                'token1': r['fields'].get('token1', ''),
                'token2': r['fields'].get('token2', ''),
                'neg_risk': r['fields'].get('neg_risk', False),
                'best_bid': r['fields'].get('best_bid', 0),
                'best_ask': r['fields'].get('best_ask', 0),
                'spread': r['fields'].get('spread', 0),
                'gm_reward_per_100': r['fields'].get('gm_reward_per_100', 0),
                'rewards_daily_rate': r['fields'].get('rewards_daily_rate', 0),
                'volatility_sum': r['fields'].get('volatility_sum', 0),
                'min_size': r['fields'].get('min_size', 50),
                'max_spread': r['fields'].get('max_spread', 1.0),
                'tick_size': r['fields'].get('tick_size', 0.01),
                'market_slug': r['fields'].get('market_slug', ''),
                'status': r['fields'].get('status', 'active'),
                'last_updated': r['fields'].get('last_updated'),
                'record_id': r['id']
            }
            for r in records
        ]

    def update_market_status(self, condition_id: str, status: str) -> bool:
        """Update market status.

        Args:
            condition_id: Market condition ID
            status: New status (active/ended/paused/archived)

        Returns:
            True if successful
        """
        table = self._get_markets_table()

        # Find record by condition_id
        formula = match({'condition_id': condition_id})
        records = table.all(formula=formula)

        if records:
            table.update(records[0]['id'], {'status': status})
            return True
        return False

    def archive_ended_markets(self) -> List[str]:
        """Archive markets that have ended (status changed to ended).

        Returns:
            List of archived condition_ids
        """
        table = self._get_markets_table()

        # Find ended markets
        formula = match({'status': 'ended'})
        records = table.all(formula=formula)

        archived = []
        for r in records:
            table.update(r['id'], {'status': 'archived'})
            archived.append(r['fields'].get('condition_id'))

        return archived

    def get_trading_configs(self) -> List[Dict[str, Any]]:
        """Get all trading configurations.

        Returns:
            List of trading config dictionaries
        """
        table = self._get_configs_table()
        records = table.all()

        configs = []
        for r in records:
            fields = r['fields']
            configs.append({
                'condition_id': fields.get('condition_id', ''),
                'question': fields.get('question', ''),
                'trade_size': fields.get('trade_size', 50),
                'max_size': fields.get('max_size', 100),
                'param_type': fields.get('param_type', 'default'),
                'enabled': fields.get('enabled', True),
                'comments': fields.get('comments', ''),
                'last_updated': fields.get('last_updated'),
                'record_id': r['id']
            })

        return configs

    def upsert_trading_config(self, config: Dict[str, Any]) -> bool:
        """Upsert a trading configuration.

        Args:
            config: Trading configuration dictionary

        Returns:
            True if successful
        """
        table = self._get_configs_table()

        record = {
            'condition_id': str(config.get('condition_id', '')),
            'question': str(config.get('question', ''))[:200],
            'trade_size': int(config.get('trade_size', 50)),
            'max_size': int(config.get('max_size', 100)),
            'param_type': config.get('param_type', 'default'),
            'enabled': bool(config.get('enabled', True)),
            'comments': str(config.get('comments', ''))[:500],
        }

        # Check if config exists
        formula = match({'condition_id': record['condition_id']})
        existing = table.all(formula=formula)

        if existing:
            table.update(existing[0]['id'], record)
        else:
            table.create(record)

        return True

    def log_trade_summary(self, summary: Dict[str, Any]) -> bool:
        """Log daily trade summary to Airtable.

        Args:
            summary: Dictionary with daily summary data

        Returns:
            True if successful
        """
        table = self._get_trade_summary_table()

        record = {
            'date': summary.get('date'),
            'total_trades': int(summary.get('total_trades', 0)),
            'buy_count': int(summary.get('buy_count', 0)),
            'sell_count': int(summary.get('sell_count', 0)),
            'total_volume': float(summary.get('total_volume', 0)),
            'total_pnl': float(summary.get('total_pnl', 0)),
            'avg_trade_size': float(summary.get('avg_trade_size', 0)),
        }

        # Check if summary for this date already exists
        formula = match({'date': record['date']})
        existing = table.all(formula=formula)

        if existing:
            table.update(existing[0]['id'], record)
        else:
            table.create(record)

        return True

    def get_trade_summaries(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get trade summaries for the last N days.

        Args:
            days: Number of days to retrieve

        Returns:
            List of summary dictionaries
        """
        table = self._get_trade_summary_table()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Use formula to filter by date
        formula = f"IS_AFTER({{date}}, '{cutoff_date}')"
        records = table.all(formula=formula, sort=['-date'])

        return [
            {
                'date': r['fields'].get('date'),
                'total_trades': r['fields'].get('total_trades', 0),
                'buy_count': r['fields'].get('buy_count', 0),
                'sell_count': r['fields'].get('sell_count', 0),
                'total_volume': r['fields'].get('total_volume', 0),
                'total_pnl': r['fields'].get('total_pnl', 0),
                'avg_trade_size': r['fields'].get('avg_trade_size', 0),
            }
            for r in records
        ]

    def send_alert(self, level: str, message: str, details: str = "",
                   condition_id: str = "", retry_count: int = 3) -> Optional[str]:
        """Send an alert to Airtable.

        Args:
            level: Alert level (info/warning/error/critical)
            message: Alert message
            details: Detailed information
            condition_id: Related market condition ID
            retry_count: Number of retries on failure

        Returns:
            Record ID if successful, None otherwise
        """
        table = self._get_alerts_table()

        record = {
            'level': level,
            'message': message[:200],
            'details': details[:2000],
            'acknowledged': False,
        }

        if condition_id:
            record['related_market'] = [condition_id] if condition_id else []

        for attempt in range(retry_count):
            try:
                result = table.create(record)
                return result['id']
            except Exception as e:
                if attempt == retry_count - 1:
                    print(f"Failed to send alert after {retry_count} attempts: {e}")
                    return None

        return None

    def get_unacknowledged_alerts(self) -> List[Dict[str, Any]]:
        """Get all unacknowledged alerts.

        Returns:
            List of alert dictionaries
        """
        table = self._get_alerts_table()
        formula = match({'acknowledged': False})
        records = table.all(formula=formula, sort=['-created_at'])

        return [
            {
                'id': r['id'],
                'level': r['fields'].get('level', 'info'),
                'message': r['fields'].get('message', ''),
                'details': r['fields'].get('details', ''),
                'created_at': r['fields'].get('created_at'),
                'acknowledged': r['fields'].get('acknowledged', False),
            }
            for r in records
        ]

    def acknowledge_alert(self, record_id: str) -> bool:
        """Acknowledge an alert.

        Args:
            record_id: Airtable record ID

        Returns:
            True if successful
        """
        table = self._get_alerts_table()
        try:
            table.update(record_id, {'acknowledged': True})
            return True
        except Exception as e:
            print(f"Failed to acknowledge alert: {e}")
            return False

    def cleanup_old_alerts(self, days: int = 30) -> int:
        """Delete old acknowledged alerts.

        Args:
            days: Delete alerts older than this many days

        Returns:
            Number of deleted alerts
        """
        table = self._get_alerts_table()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Get old acknowledged alerts
        formula = f"AND({{acknowledged}} = TRUE, IS_BEFORE({{created_at}}, '{cutoff_date}'))"
        records = table.all(formula=formula)

        deleted = 0
        for r in records:
            try:
                table.delete(r['id'])
                deleted += 1
            except Exception as e:
                print(f"Failed to delete alert {r['id']}: {e}")

        return deleted

    def cleanup_old_trade_summaries(self, days: int = 90) -> int:
        """Delete old trade summaries beyond retention period.

        Args:
            days: Delete summaries older than this many days

        Returns:
            Number of deleted summaries
        """
        table = self._get_trade_summary_table()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Get old summaries
        formula = f"IS_BEFORE({{date}}, '{cutoff_date}')"
        records = table.all(formula=formula)

        deleted = 0
        for r in records:
            try:
                table.delete(r['id'])
                deleted += 1
            except Exception as e:
                print(f"Failed to delete summary {r['id']}: {e}")

        return deleted

    def is_near_limit(self, threshold_percent: float = 90.0) -> bool:
        """Check if approaching record limit.

        Args:
            threshold_percent: Percentage threshold to trigger warning

        Returns:
            True if near limit
        """
        stats = self.check_record_count()
        return stats['usage_percent'] >= threshold_percent


# Singleton instance
_airtable_client = None


def get_airtable_client() -> AirtableClient:
    """Get singleton Airtable client instance."""
    global _airtable_client
    if _airtable_client is None:
        _airtable_client = AirtableClient()
    return _airtable_client
