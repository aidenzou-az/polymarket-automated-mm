"""
Trade Logger - Logs all trades to Google Sheets in real-time
"""
from datetime import datetime
from poly_data.gspread import get_spreadsheet
import traceback

# Cache the worksheet to avoid repeated lookups
_worksheet = None
_spreadsheet = None

def log_trade_to_sheets(trade_data):
    """
    Log a trade to the 'Trade Log' tab in Google Sheets.

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
    """
    global _worksheet, _spreadsheet

    try:
        # Initialize spreadsheet and worksheet if not cached
        if _spreadsheet is None:
            _spreadsheet = get_spreadsheet()

        if _worksheet is None:
            # Try to get existing Trade Log worksheet
            try:
                _worksheet = _spreadsheet.worksheet('Trade Log')
            except:
                # Create new worksheet if it doesn't exist
                _worksheet = _spreadsheet.add_worksheet(title='Trade Log', rows=10000, cols=15)

                # Add headers
                headers = [
                    'Timestamp',
                    'Action',
                    'Market',
                    'Price',
                    'Size ($)',
                    'Order ID',
                    'Status',
                    'Token ID',
                    'Neg Risk',
                    'Position Before',
                    'Position After',
                    'Notes'
                ]
                _worksheet.update('A1', [headers])

                # Format header
                _worksheet.format('A1:L1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.8},
                    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })

        # Prepare row data - convert all values to native Python types for JSON serialization
        def to_native_type(val):
            """Convert numpy/pandas types to native Python types"""
            import numpy as np
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            elif isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            return val
        
        row = [
            trade_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            trade_data.get('action', 'N/A'),
            str(trade_data.get('market', 'Unknown'))[:100],  # Truncate long market names
            float(trade_data.get('price', 0)),
            float(trade_data.get('size', 0)),
            str(trade_data.get('order_id', 'N/A')),
            trade_data.get('status', 'PLACED'),
            str(trade_data.get('token_id', 'N/A')),
            'Yes' if trade_data.get('neg_risk', False) else 'No',
            to_native_type(trade_data.get('position_before', 0)),
            to_native_type(trade_data.get('position_after', 0)),
            str(trade_data.get('notes', ''))
        ]

        # Append row to worksheet
        _worksheet.append_row(row, value_input_option='USER_ENTERED')

        print(f"✓ Trade logged to Google Sheets: {trade_data.get('action')} {trade_data.get('size')} @ ${trade_data.get('price'):.4f}")

        return True

    except Exception as e:
        print(f"⚠️  Failed to log trade to Google Sheets: {e}")
        # Don't crash the bot if logging fails
        traceback.print_exc()
        return False


def reset_worksheet_cache():
    """Reset the cached worksheet (useful if spreadsheet structure changes)"""
    global _worksheet, _spreadsheet
    _worksheet = None
    _spreadsheet = None
