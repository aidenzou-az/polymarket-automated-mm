#!/usr/bin/env python3
"""
Script to show trading parameter presets.
In Airtable architecture, parameters are stored per-market in Trading Configs table.

Usage:
    python update_hyperparameters.py --show  # Show parameter presets
"""

import argparse

# Recommended parameter sets (for reference)
PARAMETER_SETS = {
    'conservative': {
        'description': 'SAFEST - For volatile markets or beginners',
        'stop_loss_threshold': -3,
        'take_profit_threshold': 3,
        'spread_threshold': 0.06,
        'vol_window': 30,
        'sleep_period': 2,
        'volatility_threshold': 10,
    },
    'default': {
        'description': 'BALANCED - Good starting point for most traders',
        'stop_loss_threshold': -2,
        'take_profit_threshold': 2,
        'spread_threshold': 0.05,
        'vol_window': 30,
        'sleep_period': 1,
        'volatility_threshold': 15,
    },
    'aggressive': {
        'description': 'AGGRESSIVE - For experienced traders in stable markets',
        'stop_loss_threshold': -1.5,
        'take_profit_threshold': 1.5,
        'spread_threshold': 0.04,
        'vol_window': 20,
        'sleep_period': 1,
        'volatility_threshold': 25,
    },
}


def show_parameters():
    """Display available parameter presets."""
    print("=" * 80)
    print("TRADING PARAMETER PRESETS")
    print("=" * 80)
    print("\nIn Airtable architecture, parameters are set per-market in Trading Configs table.")
    print("The 'param_type' field can be: conservative, default, or aggressive\n")

    for name, params in PARAMETER_SETS.items():
        print(f"\n{name.upper()}")
        print("-" * 80)
        print(f"  Description: {params['description']}")
        print(f"  Stop Loss: {params['stop_loss_threshold']}%")
        print(f"  Take Profit: {params['take_profit_threshold']}%")
        print(f"  Spread Threshold: {params['spread_threshold']}")
        print(f"  Volatility Threshold: {params['volatility_threshold']}")

    print("\n" + "=" * 80)
    print("\nTo apply these parameters:")
    print("  1. Open Airtable 'Trading Configs' table")
    print("  2. Set 'param_type' field to conservative/default/aggressive")
    print("  3. The bot will automatically use the corresponding parameters")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Show trading parameter presets')
    parser.add_argument('--show', action='store_true', default=True,
                       help='Show parameter presets (default)')

    args = parser.parse_args()

    if args.show:
        show_parameters()
