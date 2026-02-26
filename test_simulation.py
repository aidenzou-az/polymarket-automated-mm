#!/usr/bin/env python3
"""
Test script for the simulation engine.
Run this to verify the simulation engine works correctly.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dry run mode
os.environ['DRY_RUN'] = 'true'
os.environ['SIMULATION_INITIAL_BALANCE'] = '10000'

from poly_data.simulation_engine import SimulationEngine
from poly_data.simulation_models import OrderSide


def test_basic_order_creation():
    """Test basic order creation."""
    print("\n=== Test: Basic Order Creation ===")

    engine = SimulationEngine(initial_balance=10000.0)

    # Simulate market data
    market_data = {
        'best_bid': 0.45,
        'best_ask': 0.55,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    # Create a buy order (below ask, shouldn't fill immediately)
    result = engine.create_virtual_order(
        token_id='test-token-1',
        side='BUY',
        price=0.40,
        size=100,
        market_data=market_data,
        condition_id='test-condition',
        market_name='Test Market'
    )

    print(f"Order created: {result['orderID']}")
    print(f"Status: {result['status']}")
    print(f"Fills: {len(result['fills'])}")

    assert result['simulated'] == True
    assert result['orderID'].startswith('SIM-')
    print("✅ Basic order creation test passed")


def test_immediate_fill():
    """Test order that fills immediately."""
    print("\n=== Test: Immediate Fill ===")

    engine = SimulationEngine(initial_balance=10000.0)

    # Market data where bid >= ask (our buy price >= market ask)
    market_data = {
        'best_bid': 0.45,
        'best_ask': 0.50,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    # Buy order above ask price - should fill
    result = engine.create_virtual_order(
        token_id='test-token-2',
        side='BUY',
        price=0.55,  # Higher than ask
        size=100,
        market_data=market_data,
        condition_id='test-condition',
        market_name='Test Market'
    )

    print(f"Order created: {result['orderID']}")
    print(f"Status: {result['status']}")
    print(f"Fills: {len(result['fills'])}")

    if result['fills']:
        fill = result['fills'][0]
        print(f"Fill: {fill['size']} @ {fill['price']}")

    print("✅ Immediate fill test passed")


def test_position_tracking():
    """Test position tracking."""
    print("\n=== Test: Position Tracking ===")

    engine = SimulationEngine(initial_balance=10000.0)

    # Buy order
    market_data = {
        'best_bid': 0.45,
        'best_ask': 0.50,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    # Create buy order that fills
    result1 = engine.create_virtual_order(
        token_id='test-token-3',
        side='BUY',
        price=0.55,
        size=100,
        market_data=market_data,
        condition_id='test-condition',
        market_name='Test Market'
    )

    position = engine.virtual_positions.get('test-token-3')
    print(f"Position after buy: size={position.size}, avg_price={position.avg_price}")

    assert position.size == 100
    assert position.avg_price == 0.50  # Filled at market ask

    # Now sell at higher price
    market_data2 = {
        'best_bid': 0.60,
        'best_ask': 0.65,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    result2 = engine.create_virtual_order(
        token_id='test-token-3',
        side='SELL',
        price=0.55,  # Lower than bid, should fill
        size=50,
        market_data=market_data2,
        condition_id='test-condition',
        market_name='Test Market'
    )

    position = engine.virtual_positions.get('test-token-3')
    print(f"Position after sell: size={position.size}, avg_price={position.avg_price}")
    print(f"Realized PnL: ${engine.balance.realized_pnl:.2f}")

    assert position.size == 50  # 100 - 50
    assert engine.balance.realized_pnl > 0  # Made profit

    print("✅ Position tracking test passed")


def test_balance_tracking():
    """Test balance tracking."""
    print("\n=== Test: Balance Tracking ===")

    engine = SimulationEngine(initial_balance=10000.0)

    market_data = {
        'best_bid': 0.45,
        'best_ask': 0.50,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    initial_balance = engine.balance.usdc_balance

    # Buy order that fills
    result = engine.create_virtual_order(
        token_id='test-token-4',
        side='BUY',
        price=0.55,
        size=100,
        market_data=market_data,
        condition_id='test-condition',
        market_name='Test Market'
    )

    print(f"Initial balance: ${initial_balance:.2f}")
    print(f"Balance after buy: ${engine.balance.usdc_balance:.2f}")
    print(f"Cost: ${initial_balance - engine.balance.usdc_balance:.2f}")

    assert engine.balance.usdc_balance < initial_balance
    assert abs(engine.balance.usdc_balance - (initial_balance - 50)) < 0.01  # 100 * 0.50 = 50

    print("✅ Balance tracking test passed")


def test_report_generation():
    """Test report generation."""
    print("\n=== Test: Report Generation ===")

    engine = SimulationEngine(initial_balance=10000.0)

    # Create some trades
    market_data = {
        'best_bid': 0.45,
        'best_ask': 0.50,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    for i in range(3):
        engine.create_virtual_order(
            token_id=f'test-token-{i}',
            side='BUY',
            price=0.55,
            size=100,
            market_data=market_data,
            condition_id='test-condition',
            market_name=f'Test Market {i}'
        )

    report = engine.generate_report()

    print(f"Total trades: {report['total_trades']}")
    print(f"Win rate: {report['win_rate']:.1f}%")
    print(f"Current balance: ${report['current_balance']:.2f}")

    assert report['total_trades'] == 3
    assert 'initial_balance' in report

    print("✅ Report generation test passed")


def test_market_update_processing():
    """Test processing market updates for pending orders."""
    print("\n=== Test: Market Update Processing ===")

    engine = SimulationEngine(initial_balance=10000.0)

    # Create order that doesn't fill (price too low)
    market_data1 = {
        'best_bid': 0.45,
        'best_ask': 0.50,
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    result = engine.create_virtual_order(
        token_id='test-token-5',
        side='BUY',
        price=0.40,  # Below ask, won't fill
        size=100,
        market_data=market_data1,
        condition_id='test-condition',
        market_name='Test Market'
    )

    print(f"Order status after creation: {result['status']}")
    assert result['status'] == 'OPEN'

    # Now market moves - our price becomes competitive
    market_data2 = {
        'best_bid': 0.38,
        'best_ask': 0.40,  # Ask dropped to our price
        'best_bid_size': 1000,
        'best_ask_size': 1000
    }

    engine.process_market_update('test-token-5', market_data2)

    # Check if order was filled
    order = engine.virtual_orders['test-token-5'][0]
    print(f"Order status after market update: {order.status.value}")

    assert order.status.value == 'FILLED'

    print("✅ Market update processing test passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("🧪 SIMULATION ENGINE TEST SUITE")
    print("=" * 70)

    try:
        test_basic_order_creation()
        test_immediate_fill()
        test_position_tracking()
        test_balance_tracking()
        test_report_generation()
        test_market_update_processing()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
