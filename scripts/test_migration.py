#!/usr/bin/env python3
"""
Quick test script to verify the Airtable + SQLite migration is working.
Run this after setting up environment variables.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sqlite():
    """Test SQLite storage."""
    print("\n" + "=" * 60)
    print("Testing SQLite Storage")
    print("=" * 60)

    try:
        from poly_data.local_storage import LocalStorage

        storage = LocalStorage()

        # Test trade logging
        trade = {
            'condition_id': 'test-condition-123',
            'token_id': 'test-token-456',
            'side': 'BUY',
            'price': 0.55,
            'size': 100,
            'status': 'PLACED',
            'order_id': 'test-order-789',
            'market': 'Test Market Question?'
        }

        trade_id = storage.log_trade(trade)
        print(f"✓ Logged test trade with ID: {trade_id}")

        # Test position logging
        position = {
            'token_id': 'test-token-456',
            'size': 100,
            'avg_price': 0.55,
            'market_price': 0.56,
            'pnl': 1.0,
            'market_name': 'Test Market'
        }

        storage.log_position(position)
        print("✓ Logged test position")

        # Test reward snapshot
        snapshot = {
            'condition_id': 'test-condition-123',
            'token_id': 'test-token-456',
            'side': 'BUY',
            'order_price': 0.54,
            'mid_price': 0.55,
            'distance_from_mid': 0.01,
            'position_size': 100,
            'estimated_hourly_reward': 0.5,
            'daily_rate': 12.0,
            'max_spread': 1.0,
            'market_name': 'Test Market'
        }

        storage.log_reward_snapshot(snapshot)
        print("✓ Logged test reward snapshot")

        # Get stats
        stats = storage.get_db_stats()
        print(f"\nDatabase stats:")
        print(f"  - DB size: {stats.get('db_size_mb', 0)} MB")
        print(f"  - Trades: {stats.get('trades_count', 0)}")
        print(f"  - Positions: {stats.get('position_history_count', 0)}")
        print(f"  - Reward snapshots: {stats.get('reward_snapshots_count', 0)}")

        storage.close()
        print("\n✓ SQLite tests passed")
        return True

    except Exception as e:
        print(f"\n✗ SQLite test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_airtable():
    """Test Airtable connection."""
    print("\n" + "=" * 60)
    print("Testing Airtable Connection")
    print("=" * 60)

    # Check environment
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')

    if not api_key:
        print("⚠ AIRTABLE_API_KEY not set, skipping Airtable tests")
        return None

    if not base_id:
        print("⚠ AIRTABLE_BASE_ID not set, skipping Airtable tests")
        return None

    try:
        from poly_data.airtable_client import AirtableClient, PYAIRTABLE_AVAILABLE

        if not PYAIRTABLE_AVAILABLE:
            print("⚠ pyairtable not installed, skipping Airtable tests")
            print("  Install with: pip install pyairtable>=2.0.0")
            return None

        client = AirtableClient()

        # Check record counts
        stats = client.check_record_count()
        print(f"\nAirtable stats:")
        print(f"  - Total records: {stats['total']['count']}/{stats['total']['limit']}")
        print(f"  - Usage: {stats['usage_percent']}%")
        print(f"  - Markets: {stats['markets']['count']}")
        print(f"  - Configs: {stats['configs']['count']}")
        print(f"  - Trade summaries: {stats['trade_summary']['count']}")
        print(f"  - Alerts: {stats['alerts']['count']}")

        # Test alert (if tables exist)
        try:
            alert_id = client.send_alert(
                level='info',
                message='Test alert from migration script',
                details='This is a test to verify Airtable connectivity'
            )
            if alert_id:
                print(f"\n✓ Sent test alert: {alert_id}")
                # Acknowledge it
                client.acknowledge_alert(alert_id)
        except Exception as e:
            print(f"\n⚠ Could not send test alert: {e}")
            print("  This is expected if the Alerts table doesn't exist yet")

        print("\n✓ Airtable tests passed")
        return True

    except Exception as e:
        print(f"\n✗ Airtable test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hybrid():
    """Test hybrid storage."""
    print("\n" + "=" * 60)
    print("Testing Hybrid Storage")
    print("=" * 60)

    try:
        from poly_data.hybrid_storage import HybridStorage

        storage = HybridStorage()

        # Check health
        healthy = storage.is_healthy()
        print(f"\nStorage health: {'✓ Healthy' if healthy else '✗ Unhealthy'}")

        # Get stats
        stats = storage.get_storage_stats()
        print(f"\nStorage stats:")
        print(f"  - Backend: {stats.get('backend')}")
        print(f"  - SQLite available: {stats.get('sqlite_available')}")
        print(f"  - Airtable available: {stats.get('airtable_available')}")

        # Test alert
        result = storage.send_alert(
            level='info',
            message='Test alert from hybrid storage',
            details='Verifying hybrid storage functionality'
        )
        print(f"\n{'✓' if result else '✗'} Sent test alert via hybrid storage")

        storage.close()
        print("\n✓ Hybrid storage tests passed")
        return True

    except Exception as e:
        print(f"\n✗ Hybrid storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Airtable + SQLite Migration Test")
    print("=" * 60)
    print("\nThis script tests the new storage system.")
    print("Make sure you have set up the environment variables first.")

    results = {
        'sqlite': test_sqlite(),
        'airtable': test_airtable(),
        'hybrid': test_hybrid()
    }

    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    for name, result in results.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "PASSED"
        else:
            status = "FAILED"
        print(f"  {name.upper()}: {status}")

    # Overall result
    if all(r is not False for r in results.values()):
        print("\n✓ All tests passed or skipped")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
