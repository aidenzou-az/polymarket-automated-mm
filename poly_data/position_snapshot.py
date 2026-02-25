"""
Position Snapshot Logger - Logs position snapshots to SQLite periodically
"""
from datetime import datetime
from poly_data.hybrid_storage import get_hybrid_storage
import poly_data.global_state as global_state
import traceback
import pandas as pd

# Cache the storage client
_storage = None
_last_snapshot_time = 0


def log_position_snapshot():
    """
    Log a snapshot of all current positions to SQLite.
    This should be called periodically (e.g., every 5 minutes).
    """
    global _storage, _last_snapshot_time

    import time
    current_time = time.time()

    # Rate limit: only log every 5 minutes
    if current_time - _last_snapshot_time < 300:
        return
    _last_snapshot_time = current_time

    try:
        if global_state.client is None:
            return

        # Initialize storage if not cached
        if _storage is None:
            _storage = get_hybrid_storage()

        # Get balances
        try:
            usdc_balance = global_state.client.get_usdc_balance()
            pos_balance = global_state.client.get_pos_balance()
            total_balance = global_state.client.get_total_balance()
        except Exception as e:
            print(f"⚠️  Warning: Could not get balances: {e}")
            usdc_balance = pos_balance = total_balance = 0

        # Get positions
        try:
            positions_df = global_state.client.get_all_positions()
            positions_df = positions_df[positions_df['size'].astype(float) > 0] if not positions_df.empty else pd.DataFrame()
        except Exception as e:
            print(f"⚠️  Warning: Could not get positions: {e}")
            positions_df = pd.DataFrame()

        # Get active orders count
        try:
            orders_df = global_state.client.get_all_orders()
            order_count = len(orders_df) if not orders_df.empty else 0
        except:
            order_count = 0

        # Get wallet address
        wallet_address = global_state.client.browser_address if hasattr(global_state.client, 'browser_address') else 'N/A'

        # Prepare positions to log
        timestamp = datetime.now().isoformat()
        positions_to_log = []

        if positions_df.empty:
            # Log summary even if no positions
            print(f"Position snapshot: No positions, {order_count} orders, ${total_balance:.2f} total")
        else:
            # Log each position
            for idx, pos in positions_df.iterrows():
                size = float(pos.get('size', 0))
                avg_price = float(pos.get('averagePrice', 0))
                market_price = float(pos.get('marketPrice', 0))

                # Calculate P&L
                pnl_per_share = market_price - avg_price
                total_pnl = pnl_per_share * size

                outcome = pos.get('outcome', 'Unknown')
                market = pos.get('market', 'Unknown')
                token_id = pos.get('asset_id', 'Unknown')

                position_data = {
                    'timestamp': timestamp,
                    'token_id': str(int(token_id)) if token_id else '',
                    'size': size,
                    'avg_price': avg_price,
                    'market_price': market_price,
                    'pnl': total_pnl,
                    'market_name': str(market)[:100],
                    'condition_id': ''  # Will be populated if available in global_state
                }
                positions_to_log.append(position_data)

        # Batch log positions to SQLite
        if positions_to_log:
            _storage.log_positions_batch(positions_to_log)
            print(f"✓ Position snapshot logged: {len(positions_to_log)} position(s), {order_count} order(s)")

        return True

    except Exception as e:
        print(f"⚠️  Failed to log position snapshot: {e}")
        # Don't crash the bot if logging fails
        traceback.print_exc()
        return False


def get_position_history(hours=24, token_id=None):
    """
    Get position history from SQLite.

    Args:
        hours: Number of hours to look back
        token_id: Optional filter by token ID

    Returns:
        List of position dictionaries
    """
    global _storage

    try:
        if _storage is None:
            _storage = get_hybrid_storage()

        # This would need to be implemented in local_storage.py
        # For now, return empty list
        return []
    except Exception as e:
        print(f"⚠️  Failed to get position history: {e}")
        return []


def reset_snapshot_cache():
    """Reset the cached storage (useful if configuration changes)"""
    global _storage, _last_snapshot_time
    _storage = None
    _last_snapshot_time = 0

