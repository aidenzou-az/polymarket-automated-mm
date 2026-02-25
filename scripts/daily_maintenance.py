#!/usr/bin/env python3
"""
Daily Maintenance Script
Performs cleanup, summarization, and reporting tasks.
Should be run once per day via cron or scheduler.
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from poly_data.hybrid_storage import HybridStorage, get_hybrid_storage
from poly_data.local_storage import LocalStorage
from poly_data.airtable_client import AirtableClient, PYAIRTABLE_AVAILABLE


def export_daily_summary(storage: HybridStorage, date: datetime = None):
    """Export daily trade summary to Airtable.

    Args:
        storage: HybridStorage instance
        date: Date to summarize (defaults to yesterday)
    """
    if date is None:
        date = datetime.now() - timedelta(days=1)

    print(f"\nExporting daily summary for {date.strftime('%Y-%m-%d')}...")

    summary = storage.export_daily_summary(date)

    if summary:
        print(f"  ✓ Total trades: {summary['total_trades']}")
        print(f"  ✓ Total volume: ${summary['total_volume']:.2f}")
        print(f"  ✓ Total P&L: ${summary['total_pnl']:.2f}")
    else:
        print("  ℹ No trades found for this date")

    return summary


def cleanup_old_data(storage: HybridStorage):
    """Clean up old data from both storages.

    Args:
        storage: HybridStorage instance
    """
    print("\nCleaning up old data...")

    results = storage.cleanup_old_data()

    # SQLite cleanup results
    if 'sqlite' in results:
        sqlite_results = results['sqlite']
        if 'error' in sqlite_results:
            print(f"  ⚠ SQLite cleanup error: {sqlite_results['error']}")
        else:
            total_deleted = sum(sqlite_results.values())
            if total_deleted > 0:
                print(f"  ✓ SQLite: Deleted {total_deleted} old records")
                for table, count in sqlite_results.items():
                    if count > 0:
                        print(f"    - {table}: {count}")
            else:
                print("  ℹ SQLite: No old records to delete")

    # Airtable cleanup results
    if 'airtable' in results:
        airtable_results = results['airtable']
        if 'error' in airtable_results:
            print(f"  ⚠ Airtable cleanup error: {airtable_results['error']}")
        else:
            alerts_deleted = airtable_results.get('alerts_deleted', 0)
            summaries_deleted = airtable_results.get('summaries_deleted', 0)
            if alerts_deleted > 0 or summaries_deleted > 0:
                print(f"  ✓ Airtable: Deleted {alerts_deleted} alerts, {summaries_deleted} summaries")
            else:
                print("  ℹ Airtable: No old records to delete")

    return results


def check_storage_health(storage: HybridStorage):
    """Check storage health and report any issues.

    Args:
        storage: HybridStorage instance
    """
    print("\nChecking storage health...")

    stats = storage.get_storage_stats()

    # SQLite health
    if stats.get('sqlite_available'):
        sqlite_stats = stats.get('sqlite', {})
        if 'error' in sqlite_stats:
            print(f"  ⚠ SQLite error: {sqlite_stats['error']}")
        else:
            db_size = sqlite_stats.get('db_size_mb', 0)
            print(f"  ✓ SQLite: {db_size} MB")

            # Warn if database is getting large
            if db_size > 500:
                print(f"  ⚠ Warning: Database size is {db_size} MB (>500 MB)")
    else:
        print("  ✗ SQLite not available")

    # Airtable health
    if stats.get('airtable_available'):
        airtable_stats = stats.get('airtable', {})
        if 'error' in airtable_stats:
            print(f"  ⚠ Airtable error: {airtable_stats['error']}")
        else:
            usage = airtable_stats.get('usage_percent', 0)
            print(f"  ✓ Airtable: {usage}% used ({airtable_stats.get('total', {}).get('count', 0)}/1200)")

            # Warn if approaching limit
            if usage > 80:
                print(f"  ⚠ Warning: Airtable usage at {usage}% (>80%)")
    else:
        print("  ✗ Airtable not available")

    return stats


def send_maintenance_report(storage: HybridStorage, report_data: dict):
    """Send maintenance report as an alert.

    Args:
        storage: HybridStorage instance
        report_data: Dictionary with report information
    """
    print("\nSending maintenance report...")

    # Build report message
    date_str = datetime.now().strftime('%Y-%m-%d')
    message = f"Daily maintenance report for {date_str}"

    details = f"""
Daily Maintenance Summary ({date_str})
================================

Data Export:
- Daily summary: {'✓ Success' if report_data.get('summary') else '✗ No data'}

Cleanup Results:
- SQLite records deleted: {sum(report_data.get('cleanup', {}).get('sqlite', {}).values())}
- Airtable alerts deleted: {report_data.get('cleanup', {}).get('airtable', {}).get('alerts_deleted', 0)}
- Airtable summaries deleted: {report_data.get('cleanup', {}).get('airtable', {}).get('summaries_deleted', 0)}

Storage Status:
- SQLite available: {'Yes' if report_data.get('health', {}).get('sqlite_available') else 'No'}
- Airtable available: {'Yes' if report_data.get('health', {}).get('airtable_available') else 'No'}
"""

    storage.send_alert('info', message, details)
    print("  ✓ Report sent")


def archive_ended_markets(storage: HybridStorage):
    """Archive markets that have ended.

    Args:
        storage: HybridStorage instance
    """
    print("\nArchiving ended markets...")

    if not PYAIRTABLE_AVAILABLE or not storage.airtable:
        print("  ℹ Airtable not available, skipping")
        return

    try:
        # Get ended markets from Airtable
        ended_markets = storage.airtable.get_active_markets(status='ended')

        if not ended_markets:
            print("  ℹ No ended markets to archive")
            return

        print(f"  Found {len(ended_markets)} ended markets")

        # Archive in SQLite
        archived_count = 0
        for market in ended_markets:
            if storage.archive_market(market):
                archived_count += 1

        print(f"  ✓ Archived {archived_count} markets to SQLite")

        # Update status to archived in Airtable
        archived_in_airtable = storage.airtable.archive_ended_markets()
        print(f"  ✓ Archived {len(archived_in_airtable)} markets in Airtable")

    except Exception as e:
        print(f"  ⚠ Error archiving markets: {e}")


def generate_summary_csv(storage: HybridStorage, days: int = 30):
    """Generate summary CSV files for analysis.

    Args:
        storage: HybridStorage instance
        days: Number of days to include
    """
    print(f"\nGenerating summary CSVs (last {days} days)...")

    try:
        # Get recent trades
        if storage.sqlite:
            trades = storage.sqlite.get_recent_trades(hours=days*24)

            if trades:
                import pandas as pd
                df = pd.DataFrame(trades)

                # Save to CSV
                os.makedirs('data/reports', exist_ok=True)
                date_str = datetime.now().strftime('%Y%m%d')
                csv_file = f'data/reports/trades_{date_str}.csv'
                df.to_csv(csv_file, index=False)
                print(f"  ✓ Saved {len(df)} trades to {csv_file}")
            else:
                print("  ℹ No trades to export")

        # Get Airtable summaries
        if storage.airtable:
            summaries = storage.airtable.get_trade_summaries(days=days)

            if summaries:
                import pandas as pd
                df = pd.DataFrame(summaries)

                csv_file = f'data/reports/daily_summaries_{date_str}.csv'
                df.to_csv(csv_file, index=False)
                print(f"  ✓ Saved {len(df)} daily summaries to {csv_file}")
            else:
                print("  ℹ No summaries to export")

    except Exception as e:
        print(f"  ⚠ Error generating CSVs: {e}")


def main():
    """Run daily maintenance tasks."""
    print("=" * 80)
    print("DAILY MAINTENANCE")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")

    # Initialize storage
    storage = get_hybrid_storage()

    report_data = {
        'start_time': datetime.now().isoformat(),
        'summary': None,
        'cleanup': {},
        'health': {},
    }

    try:
        # 1. Export daily summary
        report_data['summary'] = export_daily_summary(storage)

        # 2. Cleanup old data
        report_data['cleanup'] = cleanup_old_data(storage)

        # 3. Check storage health
        report_data['health'] = check_storage_health(storage)

        # 4. Archive ended markets
        archive_ended_markets(storage)

        # 5. Generate summary CSVs
        generate_summary_csv(storage, days=30)

        # 6. Send maintenance report
        send_maintenance_report(storage, report_data)

        print("\n" + "=" * 80)
        print("✓ Maintenance completed successfully")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n✗ Maintenance failed: {e}")
        import traceback
        traceback.print_exc()

        # Send error alert
        try:
            storage.send_alert(
                level='error',
                message='Daily maintenance failed',
                details=str(e)
            )
        except:
            pass

        return 1

    finally:
        storage.close()


if __name__ == "__main__":
    sys.exit(main())
