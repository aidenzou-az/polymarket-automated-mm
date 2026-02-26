"""
Simulation Report - Report generation and utilities for simulation engine.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd

from poly_data.local_storage import LocalStorage


def generate_simulation_report(
    storage: LocalStorage,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive simulation report from database records.

    Args:
        storage: LocalStorage instance
        start_time: Optional start time filter
        end_time: Optional end time filter

    Returns:
        Dictionary with report data
    """
    import sqlite3

    conn = sqlite3.connect(storage.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Default to last 24 hours if no time range specified
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(days=1)

    start_str = start_time.isoformat()
    end_str = end_time.isoformat()

    report = {
        'period': {
            'start': start_str,
            'end': end_str
        }
    }

    # Get simulation trades
    cursor.execute("""
        SELECT * FROM trades
        WHERE order_id LIKE 'SIM-%'
        AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (start_str, end_str))

    sim_trades = [dict(row) for row in cursor.fetchall()]
    report['trades'] = sim_trades

    # Get balance history
    cursor.execute("""
        SELECT * FROM simulation_balance
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (start_str, end_str))

    balance_history = [dict(row) for row in cursor.fetchall()]
    report['balance_history'] = balance_history

    # Calculate metrics
    if sim_trades:
        filled_trades = [t for t in sim_trades if t['status'] == 'FILLED']
        report['metrics'] = {
            'total_orders': len(sim_trades),
            'filled_orders': len(filled_trades),
            'total_volume': sum(t['size'] for t in filled_trades),
            'total_pnl': sum(t['pnl'] or 0 for t in filled_trades),
            'avg_trade_size': sum(t['size'] for t in filled_trades) / len(filled_trades) if filled_trades else 0
        }
    else:
        report['metrics'] = {
            'total_orders': 0,
            'filled_orders': 0,
            'total_volume': 0,
            'total_pnl': 0,
            'avg_trade_size': 0
        }

    # Get latest balance
    if balance_history:
        latest = balance_history[-1]
        report['current_balance'] = {
            'usdc': latest['usdc_balance'],
            'position_value': latest['position_value'],
            'total': latest['total_value'],
            'realized_pnl': latest['realized_pnl'],
            'unrealized_pnl': latest['unrealized_pnl']
        }

    conn.close()
    return report


def export_report_to_json(report: Dict[str, Any], filepath: str):
    """Export report to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=str)


def export_report_to_csv(report: Dict[str, Any], directory: str):
    """Export report components to CSV files."""
    import os
    os.makedirs(directory, exist_ok=True)

    # Export trades
    if report.get('trades'):
        df_trades = pd.DataFrame(report['trades'])
        df_trades.to_csv(f"{directory}/simulation_trades.csv", index=False)

    # Export balance history
    if report.get('balance_history'):
        df_balance = pd.DataFrame(report['balance_history'])
        df_balance.to_csv(f"{directory}/simulation_balance.csv", index=False)


def print_simulation_summary(storage: LocalStorage):
    """Print a summary of simulation results."""
    report = generate_simulation_report(storage)

    print("\n" + "=" * 70)
    print("📊 SIMULATION REPORT")
    print("=" * 70)

    if report.get('current_balance'):
        bal = report['current_balance']
        print(f"\n💰 Current Balance:")
        print(f"   USDC Balance:    ${bal['usdc']:,.2f}")
        print(f"   Position Value:  ${bal['position_value']:,.2f}")
        print(f"   Total Value:     ${bal['total']:,.2f}")
        print(f"   Realized PnL:    ${bal['realized_pnl']:,.2f}")
        print(f"   Unrealized PnL:  ${bal['unrealized_pnl']:,.2f}")

    metrics = report.get('metrics', {})
    print(f"\n📈 Trading Metrics:")
    print(f"   Total Orders:    {metrics.get('total_orders', 0)}")
    print(f"   Filled Orders:   {metrics.get('filled_orders', 0)}")
    print(f"   Total Volume:    ${metrics.get('total_volume', 0):,.2f}")
    print(f"   Total PnL:       ${metrics.get('total_pnl', 0):,.2f}")
    print(f"   Avg Trade Size:  ${metrics.get('avg_trade_size', 0):,.2f}")

    print("\n" + "=" * 70)


def get_simulation_stats(storage: LocalStorage) -> Dict[str, Any]:
    """Get quick simulation statistics."""
    import sqlite3

    conn = sqlite3.connect(storage.db_path)
    cursor = conn.cursor()

    # Count simulation orders
    cursor.execute("SELECT COUNT(*) FROM trades WHERE order_id LIKE 'SIM-%'")
    total_orders = cursor.fetchone()[0]

    # Count filled orders
    cursor.execute("""
        SELECT COUNT(*) FROM trades
        WHERE order_id LIKE 'SIM-%' AND status = 'FILLED'
    """)
    filled_orders = cursor.fetchone()[0]

    # Get total PnL
    cursor.execute("""
        SELECT SUM(pnl) FROM trades
        WHERE order_id LIKE 'SIM-%' AND status = 'FILLED'
    """)
    total_pnl = cursor.fetchone()[0] or 0

    # Get latest balance
    cursor.execute("""
        SELECT * FROM simulation_balance
        ORDER BY timestamp DESC LIMIT 1
    """)
    row = cursor.fetchone()

    conn.close()

    return {
        'total_orders': total_orders,
        'filled_orders': filled_orders,
        'fill_rate': (filled_orders / total_orders * 100) if total_orders > 0 else 0,
        'total_pnl': total_pnl,
        'current_balance': row[3] if row else 0  # total_value column
    }
