#!/usr/bin/env python3
"""
Script to check existing and historical positions on Polymarket.

This script helps you:
1. View current positions with P&L
2. Check USDC balance
3. View active orders
4. See recent trading history
"""

import os
import sys
from dotenv import load_dotenv
from poly_data.polymarket_client import PolymarketClient
import pandas as pd
import requests
from datetime import datetime
from poly_data.local_storage import LocalStorage
from poly_data.airtable_client import AirtableClient

load_dotenv()

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def check_balances(client):
    """Check USDC and position balances."""
    print_section("ACCOUNT BALANCES")

    try:
        usdc_balance = client.get_usdc_balance()
        print(f"💰 USDC Balance: ${usdc_balance:,.2f}")
    except Exception as e:
        print(f"❌ Error getting USDC balance: {e}")

    try:
        pos_balance = client.get_pos_balance()
        print(f"📊 Position Value: ${pos_balance:,.2f}")
    except Exception as e:
        print(f"❌ Error getting position balance: {e}")

    try:
        total_balance = client.get_total_balance()
        print(f"💵 Total Balance: ${total_balance:,.2f}")
    except Exception as e:
        print(f"❌ Error getting total balance: {e}")

def check_positions(client):
    """Check current positions."""
    print_section("CURRENT POSITIONS")

    try:
        positions = client.get_all_positions()

        if positions.empty:
            print("📭 No open positions")
            return

        # Filter to only positions with non-zero size
        positions = positions[positions['size'].astype(float) > 0]

        if positions.empty:
            print("📭 No open positions")
            return

        print(f"\n📈 You have {len(positions)} open position(s):\n")

        for idx, pos in positions.iterrows():
            size = float(pos.get('size', 0))
            avg_price = float(pos.get('averagePrice', 0))
            market_price = float(pos.get('marketPrice', 0))

            # Calculate P&L
            pnl_per_share = market_price - avg_price
            total_pnl = pnl_per_share * size
            pnl_percent = (pnl_per_share / avg_price * 100) if avg_price > 0 else 0

            outcome = pos.get('outcome', 'Unknown')
            market = pos.get('market', 'Unknown')

            print(f"  Market: {market[:60]}")
            print(f"  Outcome: {outcome}")
            print(f"  Size: {size:.2f} shares")
            print(f"  Avg Price: ${avg_price:.4f}")
            print(f"  Market Price: ${market_price:.4f}")

            pnl_symbol = "📈" if total_pnl >= 0 else "📉"
            print(f"  {pnl_symbol} P&L: ${total_pnl:+.2f} ({pnl_percent:+.2f}%)")
            print(f"  Position Value: ${size * market_price:.2f}")
            print()

    except Exception as e:
        print(f"❌ Error getting positions: {e}")
        import traceback
        traceback.print_exc()

def check_orders(client):
    """Check active orders."""
    print_section("ACTIVE ORDERS")

    try:
        orders = client.get_all_orders()

        if orders.empty:
            print("📭 No active orders")
            return

        print(f"\n📋 You have {len(orders)} active order(s):\n")

        for idx, order in orders.iterrows():
            side = order.get('side', 'Unknown')
            price = float(order.get('price', 0))
            original_size = float(order.get('original_size', 0))
            size_matched = float(order.get('size_matched', 0))
            remaining = original_size - size_matched

            token_id = order.get('asset_id', 'Unknown')
            order_id = order.get('id', 'Unknown')

            side_symbol = "🟢" if side == "BUY" else "🔴"
            print(f"  {side_symbol} {side} Order")
            print(f"  Token ID: {token_id[:20]}...")
            print(f"  Price: ${price:.4f}")
            print(f"  Size: {original_size:.2f} (Matched: {size_matched:.2f}, Remaining: {remaining:.2f})")
            print(f"  Order ID: {order_id}")
            print()

    except Exception as e:
        print(f"❌ Error getting orders: {e}")
        import traceback
        traceback.print_exc()

def check_trade_history(wallet_address):
    """Check recent trade history from Polymarket API."""
    print_section("RECENT TRADE HISTORY")

    try:
        # Get recent trades from Polymarket data API
        url = f"https://data-api.polymarket.com/trades?user={wallet_address}&limit=20"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"❌ Could not fetch trade history (status {response.status_code})")
            return

        trades = response.json()

        if not trades:
            print("📭 No recent trades found")
            return

        print(f"\n📜 Showing last {len(trades)} trade(s):\n")

        for trade in trades[:10]:  # Show last 10 trades
            side = trade.get('side', 'Unknown')
            size = float(trade.get('size', 0))
            price = float(trade.get('price', 0))
            timestamp = trade.get('timestamp', '')
            market = trade.get('market', 'Unknown')

            # Convert timestamp to readable format
            if timestamp:
                try:
                    dt = datetime.fromtimestamp(int(timestamp) / 1000)
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = timestamp
            else:
                time_str = 'Unknown'

            side_symbol = "🟢" if side == "BUY" else "🔴"
            print(f"  {side_symbol} {side} - {size:.2f} @ ${price:.4f} ({time_str})")
            print(f"     Market: {market[:60]}")
            print()

    except Exception as e:
        print(f"❌ Error getting trade history: {e}")


def export_to_storage(client, wallet_address):
    """Export position data to SQLite and Airtable."""
    print_section("EXPORTING POSITION DATA")

    try:
        # Initialize storage
        sqlite = LocalStorage()
        airtable = AirtableClient()

        # Get balances
        try:
            usdc_balance = client.get_usdc_balance()
            pos_balance = client.get_pos_balance()
            total_balance = client.get_total_balance()
        except Exception as e:
            print(f"⚠️  Warning: Could not get balances: {e}")
            usdc_balance = pos_balance = total_balance = 0

        # Get positions
        positions = client.get_all_positions()
        positions = positions[positions['size'].astype(float) > 0] if not positions.empty else pd.DataFrame()

        # Get active orders count
        try:
            orders = client.get_all_orders()
            order_count = len(orders) if not orders.empty else 0
        except:
            order_count = 0

        # Log positions to SQLite
        timestamp = datetime.now().isoformat()
        positions_logged = 0

        if positions.empty:
            print("ℹ️  No positions to log")
        else:
            for idx, pos in positions.iterrows():
                position_data = {
                    'timestamp': timestamp,
                    'token_id': str(pos.get('asset_id', '')),
                    'size': float(pos.get('size', 0)),
                    'avg_price': float(pos.get('averagePrice', 0)),
                    'market_price': float(pos.get('marketPrice', 0)),
                    'pnl': float(pos.get('pnl', 0)),
                    'market_name': str(pos.get('market', ''))[:100],
                    'condition_id': ''
                }
                sqlite.log_position(position_data)
                positions_logged += 1

            print(f"✅ Logged {positions_logged} positions to SQLite")

        # Send alert to Airtable
        message = f"Position check: {positions_logged} positions, ${total_balance:.2f} total"
        airtable.send_alert('info', message, f"USDC: ${usdc_balance:.2f}, Positions: ${pos_balance:.2f}")
        print(f"✅ Sent alert to Airtable")

        sqlite.close()

    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to check all positions and balances."""
    print("\n🔍 POLYMARKET POSITION CHECKER")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize client
    try:
        client = PolymarketClient()
        wallet_address = os.getenv('BROWSER_ADDRESS')
        print(f"   Wallet: {wallet_address}")
    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        sys.exit(1)

    # Run all checks
    check_balances(client)
    check_positions(client)
    check_orders(client)
    check_trade_history(wallet_address)

    # Export to Google Sheets
    export_to_storage(client, wallet_address)

    print_section("DONE")
    print()

if __name__ == "__main__":
    main()
