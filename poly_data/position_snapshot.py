"""
Position Snapshot Logger - Logs position snapshots to Google Sheets periodically
"""
from datetime import datetime
from poly_data.gspread import get_spreadsheet
import poly_data.global_state as global_state
import traceback
import pandas as pd

# Cache the worksheet to avoid repeated lookups
_worksheet = None
_spreadsheet = None
_last_snapshot_time = 0

def log_position_snapshot():
    """
    Log a snapshot of all current positions to the 'Position Snapshots' tab in Google Sheets.
    This should be called periodically (e.g., every 5 minutes).
    """
    global _worksheet, _spreadsheet, _last_snapshot_time
    
    import time
    current_time = time.time()
    
    # Rate limit: only log every 5 minutes
    if current_time - _last_snapshot_time < 300:
        return
    _last_snapshot_time = current_time
    
    try:
        if global_state.client is None:
            return
        
        # Initialize spreadsheet and worksheet if not cached
        if _spreadsheet is None:
            _spreadsheet = get_spreadsheet()

        if _worksheet is None:
            # Try to get existing Position Snapshots worksheet
            try:
                _worksheet = _spreadsheet.worksheet('Position Snapshots')
            except:
                # Create new worksheet if it doesn't exist
                _worksheet = _spreadsheet.add_worksheet(title='Position Snapshots', rows=10000, cols=15)

                # Add headers
                headers = [
                    'Timestamp',
                    'Wallet',
                    'USDC Balance',
                    'Position Value',
                    'Total Balance',
                    'Market',
                    'Outcome',
                    'Token ID',
                    'Size',
                    'Avg Price',
                    'Market Price',
                    'P&L ($)',
                    'P&L (%)',
                    'Position Value',
                    'Order Count'
                ]
                _worksheet.update('A1', [headers])

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

        # Prepare rows to append
        rows_to_add = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if positions_df.empty:
            # Add summary row even if no positions
            rows_to_add.append([
                timestamp, wallet_address, f"{usdc_balance:.2f}", f"{pos_balance:.2f}",
                f"{total_balance:.2f}", "No Positions", "", "", "", "", "", "", "", "", int(order_count)
            ])
        else:
            # Add row for each position
            for idx, pos in positions_df.iterrows():
                size = float(pos.get('size', 0))
                avg_price = float(pos.get('averagePrice', 0))
                market_price = float(pos.get('marketPrice', 0))

                # Calculate P&L
                pnl_per_share = market_price - avg_price
                total_pnl = pnl_per_share * size
                pnl_percent = (pnl_per_share / avg_price * 100) if avg_price > 0 else 0

                outcome = pos.get('outcome', 'Unknown')
                market = pos.get('market', 'Unknown')
                token_id = pos.get('asset_id', 'Unknown')
                position_value = size * market_price

                rows_to_add.append([
                    timestamp, wallet_address, f"{usdc_balance:.2f}", f"{pos_balance:.2f}",
                    f"{total_balance:.2f}", market[:100], outcome, str(int(token_id)) if token_id else '', f"{size:.2f}",
                    f"{avg_price:.4f}", f"{market_price:.4f}", f"{total_pnl:.2f}",
                    f"{pnl_percent:.2f}", f"{position_value:.2f}", int(order_count)
                ])

        # Append all rows
        if rows_to_add:
            _worksheet.append_rows(rows_to_add)
            print(f"✓ Position snapshot logged: {len(rows_to_add)} position(s), {order_count} order(s)")

        return True

    except Exception as e:
        print(f"⚠️  Failed to log position snapshot: {e}")
        # Don't crash the bot if logging fails
        traceback.print_exc()
        return False


def reset_snapshot_cache():
    """Reset the cached worksheet (useful if spreadsheet structure changes)"""
    global _worksheet, _spreadsheet
    _worksheet = None
    _spreadsheet = None

