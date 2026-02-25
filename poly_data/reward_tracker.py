"""
Reward Tracker - Estimates and logs maker rewards to SQLite
"""

import time
from datetime import datetime
import poly_data.global_state as global_state
from poly_data.hybrid_storage import get_hybrid_storage
import traceback

# Cache storage client
_storage = None
_last_snapshot_time = {}


def estimate_order_reward(price, size, mid_price, max_spread, daily_rate):
    """Estimate maker rewards for a single order based on Polymarket's formula."""
    try:
        s = abs(price - mid_price)
        v = max_spread / 100
        if v == 0:
            return 0
        S = ((v - s) / v) ** 2
        Q = S * size
        hourly_rate = daily_rate / 24
        estimated_reward = (Q / (Q + 1000)) * hourly_rate
        return max(0, estimated_reward)
    except Exception as e:
        print(f"Error calculating reward: {e}")
        return 0


def log_market_snapshot(market_id, market_name):
    """Log a snapshot of current orders and estimate rewards for a market to SQLite."""
    global _storage, _last_snapshot_time

    try:
        current_time = time.time()
        last_snapshot = _last_snapshot_time.get(market_id, 0)
        if current_time - last_snapshot < 300:
            return
        _last_snapshot_time[market_id] = current_time

        if global_state.df is None:
            return

        market_row = global_state.df[global_state.df['condition_id'] == market_id]
        if market_row.empty:
            return
        market_row = market_row.iloc[0]

        # Initialize storage if needed
        if _storage is None:
            _storage = get_hybrid_storage()

        # Calculate mid price
        if market_id in global_state.all_data:
            bids = global_state.all_data[market_id]['bids']
            asks = global_state.all_data[market_id]['asks']
            if len(bids) > 0 and len(asks) > 0:
                best_bid = list(bids.keys())[-1]
                best_ask = list(asks.keys())[-1]
                mid_price = (best_bid + best_ask) / 2
            else:
                mid_price = 0.5
        else:
            mid_price = 0.5

        timestamp = datetime.now().isoformat()

        for token_name in ['token1', 'token2']:
            token_id = str(market_row[token_name])
            answer = market_row['answer1'] if token_name == 'token1' else market_row['answer2']
            orders = global_state.orders.get(token_id, {'buy': {'price': 0, 'size': 0}, 'sell': {'price': 0, 'size': 0}})
            position = global_state.positions.get(token_id, {'size': 0, 'avgPrice': 0})

            if orders['buy']['size'] > 0:
                buy_reward = estimate_order_reward(
                    orders['buy']['price'], orders['buy']['size'], mid_price,
                    market_row['max_spread'], market_row['rewards_daily_rate']
                )
                snapshot_data = {
                    'timestamp': timestamp,
                    'condition_id': market_id,
                    'token_id': token_id,
                    'side': 'BUY',
                    'order_price': float(orders['buy']['price']),
                    'mid_price': float(mid_price),
                    'distance_from_mid': float(abs(orders['buy']['price'] - mid_price)),
                    'position_size': float(position['size']),
                    'estimated_hourly_reward': float(round(buy_reward, 4)),
                    'daily_rate': float(market_row['rewards_daily_rate']),
                    'max_spread': float(market_row['max_spread']),
                    'market_name': str(market_name)[:80]
                }
                _storage.log_reward_snapshot(snapshot_data)

            if orders['sell']['size'] > 0:
                sell_reward = estimate_order_reward(
                    orders['sell']['price'], orders['sell']['size'], mid_price,
                    market_row['max_spread'], market_row['rewards_daily_rate']
                )
                snapshot_data = {
                    'timestamp': timestamp,
                    'condition_id': market_id,
                    'token_id': token_id,
                    'side': 'SELL',
                    'order_price': float(orders['sell']['price']),
                    'mid_price': float(mid_price),
                    'distance_from_mid': float(abs(orders['sell']['price'] - mid_price)),
                    'position_size': float(position['size']),
                    'estimated_hourly_reward': float(round(sell_reward, 4)),
                    'daily_rate': float(market_row['rewards_daily_rate']),
                    'max_spread': float(market_row['max_spread']),
                    'market_name': str(market_name)[:80]
                }
                _storage.log_reward_snapshot(snapshot_data)

        print(f"Logged reward snapshot for {market_name[:50]}...")
        return True

    except Exception as e:
        print(f"Failed to log reward snapshot: {e}")
        traceback.print_exc()
        return False


def get_reward_history(hours=24, condition_id=None):
    """
    Get reward history from SQLite.

    Args:
        hours: Number of hours to look back
        condition_id: Optional filter by market condition_id

    Returns:
        List of reward snapshot dictionaries
    """
    global _storage

    try:
        if _storage is None:
            _storage = get_hybrid_storage()

        # This would need to be implemented in local_storage.py
        # For now, return empty list
        return []
    except Exception as e:
        print(f"Failed to get reward history: {e}")
        return []


def reset_reward_cache():
    """Reset the cached storage"""
    global _storage, _last_snapshot_time
    _storage = None
    _last_snapshot_time = {}
