#!/usr/bin/env python3
"""
Cancel All Orders and Optionally Close Positions

This script:
1. Cancels all active orders on Polymarket
2. Optionally sells all positions at market price
"""
from dotenv import load_dotenv
from poly_data.polymarket_client import PolymarketClient
import pandas as pd

load_dotenv()

def cancel_all_orders():
    print("🛑 CANCEL ALL ORDERS\n")
    print("=" * 80)

    # Initialize client
    print("\n1. Initializing Polymarket client...")
    client = PolymarketClient()
    print("   ✓ Client initialized")

    # Get all active orders
    print("\n2. Fetching all active orders...")
    try:
        orders_df = client.get_all_orders()

        if len(orders_df) == 0:
            print("   ✓ No active orders found")
            return client

        print(f"   Found {len(orders_df)} active order(s):\n")

        # Display order details
        for idx, order in orders_df.iterrows():
            print(f"   Order #{idx + 1}:")
            print(f"     - Asset ID: {order['asset_id']}")
            print(f"     - Side: {order['side']}")
            print(f"     - Price: ${order['price']:.4f}")
            print(f"     - Size: ${order['original_size']:.2f}")
            print(f"     - Order ID: {order.get('id', 'N/A')}")

        # Get unique asset IDs
        asset_ids = orders_df['asset_id'].unique()

        print(f"\n3. Canceling orders for {len(asset_ids)} unique asset(s)...")

        canceled_count = 0
        for asset_id in asset_ids:
            try:
                print(f"   Canceling orders for asset {asset_id}...")
                client.cancel_all_asset(asset_id)
                canceled_count += 1
                print(f"   ✓ Canceled")
            except Exception as e:
                print(f"   ❌ Error: {e}")

        print(f"\n✅ Canceled orders for {canceled_count}/{len(asset_ids)} assets")

        # Verify cancellation
        print("\n4. Verifying cancellation...")
        remaining_orders = client.get_all_orders()
        if len(remaining_orders) == 0:
            print("   ✓ All orders successfully canceled")
        else:
            print(f"   ⚠️  {len(remaining_orders)} order(s) still active")

        return client

    except Exception as e:
        print(f"   ❌ Error fetching orders: {e}")
        return client


def close_all_positions(client):
    print("\n\n🔄 CLOSE ALL POSITIONS\n")
    print("=" * 80)

    print("\n1. Fetching all positions...")
    try:
        positions_df = client.get_all_positions()

        if len(positions_df) == 0:
            print("   ✓ No open positions found")
            return

        print(f"   Found {len(positions_df)} position(s):\n")

        # Filter for positions with shares > 0
        active_positions = positions_df[positions_df['size'] > 0].copy()

        if len(active_positions) == 0:
            print("   ✓ No active positions to close")
            return

        for idx, pos in active_positions.iterrows():
            print(f"   Position #{idx + 1}:")
            print(f"     - Market: {pos.get('title', pos.get('market', 'Unknown'))}")
            print(f"     - Size: {pos['size']:.2f} shares")
            print(f"     - Avg Price: ${pos.get('avgPrice', pos.get('avg_price', 0)):.4f}")
            print(f"     - Current Price: ${pos.get('curPrice', 0):.4f}")
            print(f"     - Token ID: {pos.get('asset', pos.get('asset_id', 'N/A'))}")

        print(f"\n⚠️  Selling ALL {len(active_positions)} position(s) at market price...")

        print("\n2. Closing positions...")

        for idx, pos in active_positions.iterrows():
            try:
                token_id = str(pos.get('asset', pos.get('asset_id')))
                size = float(pos['size'])
                cur_price = float(pos.get('curPrice', 0))

                print(f"\n   Processing position {idx + 1}/{len(active_positions)}...")
                print(f"   Token: {token_id}")
                print(f"   Size: {size:.2f} shares")

                # Check if market has resolved (price = 0)
                if cur_price == 0:
                    print(f"   ⚠️  Market has resolved (current price = $0.00)")
                    print(f"   Shares are likely worthless or need to be redeemed")
                    print(f"   Skipping...")
                    continue

                # Get current best bid price
                bids, asks = client.get_order_book(token_id)

                if len(bids) == 0:
                    print(f"   ⚠️  No bids available, skipping...")
                    continue

                best_bid = float(bids.iloc[0]['price'])
                print(f"   Best Bid: ${best_bid:.4f}")

                # Determine if neg_risk market
                is_neg_risk = bool(pos.get('negativeRisk', pos.get('neg_risk', False)))

                print(f"   Placing SELL order...")

                result = client.create_order(
                    marketId=token_id,
                    action='SELL',
                    price=best_bid,
                    size=size,
                    neg_risk=is_neg_risk
                )

                if result and 'orderID' in result:
                    print(f"   ✅ Position closed - Order ID: {result['orderID']}")
                else:
                    print(f"   ❌ Failed to close position: {result}")

            except Exception as e:
                print(f"   ❌ Error closing position: {e}")

        print("\n✅ Position closure complete")

    except Exception as e:
        print(f"   ❌ Error fetching positions: {e}")


def main():
    print("\n" + "=" * 80)
    print("CANCEL ALL ORDERS & CLOSE POSITIONS")
    print("=" * 80)

    # Cancel all orders first
    client = cancel_all_orders()

    # Automatically close all positions
    close_all_positions(client)

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    try:
        usdc_balance = client.get_usdc_balance()
        pos_balance = client.get_pos_balance()
        total_balance = usdc_balance + pos_balance

        print(f"\n💰 USDC Balance: ${usdc_balance:.2f}")
        print(f"📊 Position Value: ${pos_balance:.2f}")
        print(f"💎 Total Balance: ${total_balance:.2f}")

        remaining_orders = client.get_all_orders()
        print(f"\n📝 Active Orders: {len(remaining_orders)}")

        positions_df = client.get_all_positions()
        active_positions = len(positions_df[positions_df['size'] > 0]) if len(positions_df) > 0 else 0
        print(f"📈 Open Positions: {active_positions}")

    except Exception as e:
        print(f"\n⚠️  Could not fetch final summary: {e}")

    print("\n" + "=" * 80)
    print("✅ DONE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
