"""
Trade Logger - Logs all trades to SQLite (primary) and Airtable (significant trades)
"""
from datetime import datetime
from poly_data.hybrid_storage import get_hybrid_storage
import traceback

# Cache the storage client
_storage = None

def log_trade_to_sheets(trade_data):
    """
    Log a trade to SQLite (and significant trades to Airtable).
    This function maintains backward compatibility with the old interface.

    Args:
        trade_data (dict): Trade information with keys:
            - timestamp: Trade timestamp
            - action: 'BUY' or 'SELL'
            - token_id: Token ID
            - market: Market name/question
            - price: Order price
            - size: Order size in USDC
            - order_id: Order ID (if available)
            - status: 'PLACED', 'FILLED', 'CANCELED', etc.
            - neg_risk: Whether it's a neg_risk market
            - position_before, position_after: Position tracking
    """
    global _storage

    try:
        # Initialize storage if not cached
        if _storage is None:
            _storage = get_hybrid_storage()

        # Convert trade_data format if needed
        converted_data = {
            'timestamp': trade_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'side': trade_data.get('action', 'N/A'),
            'token_id': str(trade_data.get('token_id', 'N/A')),
            'market': str(trade_data.get('market', 'Unknown'))[:100],
            'price': float(trade_data.get('price', 0)),
            'size': float(trade_data.get('size', 0)),
            'order_id': str(trade_data.get('order_id', 'N/A')),
            'status': trade_data.get('status', 'PLACED'),
            'neg_risk': bool(trade_data.get('neg_risk', False)),
            'position_before': trade_data.get('position_before', 0),
            'position_after': trade_data.get('position_after', 0),
            'notes': str(trade_data.get('notes', '')),
            'condition_id': trade_data.get('condition_id', ''),
        }

        # Log to hybrid storage (SQLite + significant to Airtable)
        _storage.log_trade(converted_data)

        print(f"✓ Trade logged: {trade_data.get('action')} {trade_data.get('size')} @ ${trade_data.get('price', 0):.4f}")

        return True

    except Exception as e:
        print(f"⚠️  Failed to log trade: {e}")
        # Don't crash the bot if logging fails
        traceback.print_exc()
        return False


def log_trade(trade_data):
    """
    Alias for log_trade_to_sheets for new code.
    Logs a trade to SQLite (primary storage).

    Args:
        trade_data (dict): Trade information
    """
    return log_trade_to_sheets(trade_data)


def get_recent_trades(hours=24, condition_id=None):
    """
    Get recent trades from SQLite.

    Args:
        hours: Number of hours to look back
        condition_id: Optional filter by market condition_id

    Returns:
        List of trade dictionaries
    """
    global _storage

    try:
        if _storage is None:
            _storage = get_hybrid_storage()

        return _storage.get_recent_trades(hours, condition_id)
    except Exception as e:
        print(f"⚠️  Failed to get recent trades: {e}")
        return []


def reset_worksheet_cache():
    """Reset the cached storage (useful if configuration changes)"""
    global _storage
    _storage = None
