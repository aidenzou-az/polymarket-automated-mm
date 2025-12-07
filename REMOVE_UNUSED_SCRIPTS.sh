#!/bin/bash
# Script to remove unused/deprecated scripts from clean copy

echo "Removing unused scripts..."

# Test scripts (not used in production)
echo "Removing test scripts..."
rm -f test_aggressive_trading.py
rm -f test_immediate_order.py
rm -f test_trade_logger.py
rm -f force_trade_test.py
rm -f quick_order_test.py
rm -f direct_order_test.py

# Analysis scripts (not used in production)
echo "Removing analysis scripts..."
rm -f analyze_performance.py
rm -f analyze_profitable_markets.py

# Potentially deprecated scripts
echo "Removing deprecated/alternative scripts..."
rm -f select_markets.py          # Replaced by update_selected_markets.py
rm -f select_best_markets.py      # Alternative market selection
rm -f fix_trade_sizes.py          # One-time fix script
rm -f check_market_config.py      # Config checker (unclear usage)
rm -f update_stats.py             # Statistics (unclear usage)
rm -f dashboard_old.py            # Old dashboard version

# Optional: Remove dashboard if you don't want it
# rm -f dashboard.py

echo "✅ Unused scripts removed!"
echo ""
echo "Remaining core scripts:"
ls -1 *.py 2>/dev/null | grep -v "^_" | sort

