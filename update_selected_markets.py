#!/usr/bin/env python3
"""
Update Selected Markets: Configure trading markets in Airtable
Selects markets from Airtable Markets table and creates Trading Configs
"""

# === HTTP Timeout Patch (MUST be before importing libraries that use requests) ===
import os
import requests
from functools import wraps

# Configuration from environment variables
CONNECT_TIMEOUT = float(os.getenv('REQUEST_CONNECT_TIMEOUT', '5'))
READ_TIMEOUT = float(os.getenv('REQUEST_READ_TIMEOUT', '15'))
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

_original_request = requests.request

@wraps(_original_request)
def _patched_request(method, url, **kwargs):
    """Add default timeout to all HTTP requests"""
    if 'timeout' not in kwargs:
        kwargs['timeout'] = REQUEST_TIMEOUT
    return _original_request(method, url, **kwargs)

requests.request = _patched_request

# Also patch Session.request (used internally by third-party libraries)
_original_session_request = requests.Session.request

@wraps(_original_session_request)
def _patched_session_request(self, method, url, **kwargs):
    """Add default timeout to all session requests"""
    if 'timeout' not in kwargs:
        kwargs['timeout'] = REQUEST_TIMEOUT
    return _original_session_request(self, method, url, **kwargs)

requests.Session.request = _patched_session_request
# ===================================================================

import pandas as pd
import sys
from dotenv import load_dotenv
from datetime import datetime
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poly_data.airtable_client import AirtableClient
from poly_data.local_storage import LocalStorage

load_dotenv()


def update_selected_markets(min_daily_reward=None, max_markets=None, replace_existing=False):
    """
    Select markets from Airtable Markets table and create Trading Configs

    Args:
        min_daily_reward: If set, filter markets by minimum daily reward (in dollars)
        max_markets: Maximum number of markets to select
        replace_existing: If True, replace all existing configs. If False, append.
    """

    print("=" * 100)
    print("UPDATING SELECTED MARKETS")
    print("=" * 100)
    print()

    # Connect to Airtable
    print("Connecting to Airtable...")
    try:
        client = AirtableClient()
        print("✓ Airtable connected")
    except Exception as e:
        print(f"❌ Failed to connect to Airtable: {e}")
        return

    # Get existing configs
    print("\nLoading existing trading configs...")
    try:
        current_configs = client.get_trading_configs()
        print(f"Current configs: {len(current_configs)}")
        if current_configs:
            for c in current_configs[:5]:
                print(f"  - {c.get('question', 'N/A')[:70]}")
    except Exception as e:
        print(f"Warning: Could not load configs: {e}")
        current_configs = []

    # Get all markets from Airtable
    print("\nLoading markets from Airtable...")
    try:
        all_markets = client.get_all_markets()
        if not all_markets:
            print("❌ No markets found in Airtable")
            print("   Please run: python data_updater/data_updater.py")
            return
        print(f"✓ Loaded {len(all_markets)} markets")
    except Exception as e:
        print(f"❌ Failed to load markets: {e}")
        return

    # Convert to DataFrame for processing
    markets_df = pd.DataFrame(all_markets)

    # Filter by minimum daily reward if specified
    if min_daily_reward is not None:
        print(f"\n{'=' * 100}")
        print(f"HIGH REWARD MODE: Filtering by rewards_daily_rate >= ${min_daily_reward}")
        print("=" * 100)

        filtered = markets_df[
            (markets_df['rewards_daily_rate'] >= min_daily_reward) &
            (markets_df['rewards_daily_rate'].notna())
        ].copy()

        if len(filtered) == 0:
            print(f"❌ No markets found with rewards_daily_rate >= ${min_daily_reward}")
            print(f"   Highest reward: ${markets_df['rewards_daily_rate'].max():.2f}")
            return

        print(f"✓ Found {len(filtered)} markets with rewards >= ${min_daily_reward}/day\n")

        # Quality filters
        quality_filters = (
            (filtered['best_bid'] >= 0.1) &
            (filtered['best_bid'] <= 0.9) &
            (filtered['spread'] < 0.15)
        )
        filtered = filtered[quality_filters].copy()
        print(f"✓ {len(filtered)} markets after quality filters\n")

        # Sort by rewards
        filtered = filtered.sort_values('rewards_daily_rate', ascending=False)
        target_count = max_markets if max_markets else 10

    else:
        # Profitability mode
        print(f"\n{'=' * 100}")
        print("PROFITABILITY MODE: Selecting by reward/volatility ratio")
        print("=" * 100)

        # Calculate profitability score
        markets_df['profitability_score'] = markets_df['gm_reward_per_100'] / (markets_df['volatility_sum'] + 1)

        # Filter for good markets
        filtered = markets_df[
            (markets_df['gm_reward_per_100'] >= 1.0) &
            (markets_df['volatility_sum'] < 20) &
            (markets_df['spread'] < 0.1) &
            (markets_df['best_bid'] >= 0.1) &
            (markets_df['best_bid'] <= 0.9)
        ].copy()

        # Sort by profitability
        filtered = filtered.sort_values('profitability_score', ascending=False)
        target_count = max_markets if max_markets else 5

    # Get current condition_ids to exclude (if not replacing)
    if not replace_existing and current_configs:
        current_ids = {c.get('condition_id') for c in current_configs}
        filtered = filtered[~filtered['condition_id'].isin(current_ids)].copy()
        needed = max(0, target_count - len(current_configs))
    else:
        needed = target_count

    if needed <= 0:
        print("\n✓ Already have enough markets configured")
        return

    # Select top markets
    selected = filtered.head(needed)

    print(f"\n{'=' * 100}")
    print(f"SELECTING {len(selected)} NEW MARKETS:")
    print("=" * 100)

    # Create configs for selected markets
    new_configs = []
    for _, row in selected.iterrows():
        reward = row.get('gm_reward_per_100', 0)
        volatility = row.get('volatility_sum', 0)
        daily_reward = row.get('rewards_daily_rate', 0)
        min_size = row.get('min_size', 50)

        # Determine trade parameters
        if min_daily_reward and daily_reward >= 200:
            trade_size = 100
            max_size = 200
            param_type = 'aggressive'
        elif min_daily_reward and daily_reward >= 150:
            trade_size = 80
            max_size = 160
            param_type = 'aggressive'
        elif volatility > 15:
            trade_size = 30
            max_size = 60
            param_type = 'aggressive'
        elif volatility > 10:
            trade_size = 40
            max_size = 80
            param_type = 'default'
        else:
            trade_size = 50
            max_size = 100
            param_type = 'conservative'

        # Ensure trade_size >= min_size
        if trade_size < min_size:
            trade_size = min_size
            max_size = max(trade_size * 2, max_size)

        # Generate rationale
        rationale_parts = []
        if daily_reward >= 200:
            rationale_parts.append(f"Very high daily reward (${daily_reward:.0f}/day)")
        elif daily_reward >= 100:
            rationale_parts.append(f"High daily reward (${daily_reward:.0f}/day)")
        elif daily_reward >= 50:
            rationale_parts.append(f"Good daily reward (${daily_reward:.0f}/day)")

        if reward >= 2.0:
            rationale_parts.append(f"High reward ({reward:.2f}% daily)")
        elif reward >= 1.0:
            rationale_parts.append(f"Good reward ({reward:.2f}% daily)")

        if volatility < 10:
            rationale_parts.append(f"Low volatility ({volatility:.1f}) - safer")
        elif volatility < 15:
            rationale_parts.append(f"Moderate volatility ({volatility:.1f})")

        spread_val = row.get('spread', 0)
        if spread_val < 0.02:
            rationale_parts.append("Tight spread")
        elif spread_val < 0.05:
            rationale_parts.append("Reasonable spread")

        rationale = " | ".join(rationale_parts) if rationale_parts else f"Reward: {reward:.2f}%, Vol: {volatility:.1f}"
        comments = f"Reward: ${daily_reward:.0f}/day, Vol: {volatility:.1f}, Spread: {spread_val:.3f}"

        config = {
            'condition_id': row['condition_id'],
            'question': row['question'],
            'trade_size': int(trade_size),
            'max_size': int(max_size),
            'param_type': param_type,
            'enabled': True,
            'comments': comments,
            'rationale': rationale
        }
        new_configs.append(config)

        print(f"\n{len(new_configs)}. {row['question'][:75]}")
        print(f"   Daily Reward: ${daily_reward:.2f} | Volatility: {volatility:.1f} | Spread: {spread_val:.4f}")
        print(f"   Trade Size: ${trade_size} | Max Size: ${max_size} | Param: {param_type}")

    # Upload to Airtable
    print(f"\n{'=' * 100}")
    print("UPLOADING TO AIRTABLE...")
    print("=" * 100)

    success_count = 0
    error_count = 0

    for config in new_configs:
        try:
            client.upsert_trading_config(config)
            success_count += 1
        except Exception as e:
            print(f"❌ Error uploading config: {e}")
            error_count += 1

    print(f"\n✓ Successfully created {success_count} trading configs")
    if error_count > 0:
        print(f"⚠️  {error_count} errors")

    # Show final list
    print(f"\n{'=' * 100}")
    print("FINAL CONFIGURATION")
    print("=" * 100)

    final_configs = client.get_trading_configs()
    print(f"\nTotal configured markets: {len(final_configs)}\n")

    for i, config in enumerate(final_configs, 1):
        print(f"{i}. {config.get('question', 'N/A')[:70]}")
        print(f"   Trade: ${config.get('trade_size', 0)}, Max: ${config.get('max_size', 0)}, "
              f"Param: {config.get('param_type', 'default')}, Enabled: {config.get('enabled', False)}")
        print()

    print("\n✓ Done! The bot will start trading these markets within 60 seconds.")
    print("  Monitor with: tail -f main.log")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Update Selected Markets in Airtable',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: Profitability-based selection (5-6 markets)
  python update_selected_markets.py

  # High reward mode: Select markets with >= $100/day
  python update_selected_markets.py --min-reward 100

  # High reward mode: Select top 15 markets with >= $150/day, replace existing
  python update_selected_markets.py --min-reward 150 --max-markets 15 --replace
        """
    )

    parser.add_argument('--min-reward', type=float, default=None,
                       help='Minimum daily reward in dollars (enables high reward mode)')
    parser.add_argument('--max-markets', type=int, default=None,
                       help='Maximum number of markets to select')
    parser.add_argument('--replace', action='store_true',
                       help='Replace all existing configs instead of appending')

    args = parser.parse_args()

    update_selected_markets(
        min_daily_reward=args.min_reward,
        max_markets=args.max_markets,
        replace_existing=args.replace
    )
