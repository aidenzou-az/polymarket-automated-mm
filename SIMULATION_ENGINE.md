# 撮合模拟器 (Dry Run Simulation Engine) - Implementation Summary

## Overview
A complete simulation engine has been implemented for testing the Polymarket trading bot without using real funds. The simulation engine intercepts orders in DRY_RUN mode, simulates order matching based on real-time market data, and maintains virtual positions and PnL.

## Files Created

### 1. `poly_data/simulation_models.py`
Data models for the simulation engine:
- `VirtualOrder`: Represents a virtual order with status tracking
- `Fill`: Represents a fill event with PnL calculation
- `VirtualPosition`: Tracks virtual position size and average price
- `SimulationBalance`: Tracks virtual USDC balance and PnL
- `SimulationReport`: Performance metrics report

### 2. `poly_data/simulation_engine.py`
Core simulation engine with:
- Order creation and matching logic
- Position tracking with PnL calculation
- Balance management
- SQLite persistence for orders, fills, and positions
- Report generation with drawdown calculation
- Market update processing for pending orders

### 3. `poly_data/simulation_report.py`
Report generation utilities:
- `generate_simulation_report()`: Generate comprehensive reports from DB
- `export_report_to_json()`: Export reports to JSON
- `export_report_to_csv()`: Export to CSV files
- `print_simulation_summary()`: Print summary to console

### 4. `test_simulation.py`
Test suite covering:
- Basic order creation
- Immediate fill matching
- Position tracking (buy/sell/average price)
- Balance tracking
- Report generation
- Market update processing for pending orders

## Files Modified

### 1. `poly_data/polymarket_client.py`
- Modified `create_order()`: Routes to simulation engine in DRY_RUN mode
- Modified `cancel_all_asset()`: Supports simulation cancellation
- Modified `cancel_all_market()`: Supports simulation cancellation

### 2. `poly_data/data_processing.py`
- Modified `process_data()`: Triggers simulation matching on market updates

### 3. `poly_data/global_state.py`
- Added `simulation_engine`: Reference to simulation engine instance
- Added `local_storage`: Reference to LocalStorage instance

### 4. `poly_data/local_storage.py`
- Added `simulation_config` table: Stores simulation settings
- Added `simulation_balance` table: Tracks balance history

### 5. `main.py`
- Added import for `LocalStorage` and `os`
- Added initialization of `local_storage`
- Added initialization of `simulation_engine` when DRY_RUN=true

## Usage

### Enable Dry Run Mode
```bash
# .env file
DRY_RUN=true
SIMULATION_INITIAL_BALANCE=10000
SIMULATION_MATCHING_MODE=aggressive  # aggressive or conservative
```

### Run the Bot
```bash
python main.py
```

In dry run mode, the bot will:
1. Show "🎮 DRY RUN MODE: 使用虚拟资金 $10,000" on startup
2. Create virtual orders instead of real orders
3. Simulate fills based on market price movements
4. Track virtual positions and PnL
5. Log all activity to SQLite

### View Simulation Status
The simulation engine logs status messages:
```
📝 Virtual Order Created: BUY 100 @ 0.4500 (ID: SIM-000001)
✅ Buy Order FILLED: 100 @ 0.5000 (order: SIM-000001)
💰 Fill processed: BUY 100 @ 0.5000 | Realized PnL: $0.00 | Balance: $9950.00
```

### Generate Reports
```python
from poly_data.simulation_report import print_simulation_summary
from poly_data.local_storage import LocalStorage

storage = LocalStorage()
print_simulation_summary(storage)
```

## Matching Logic

### Buy Orders
- Fill condition: `order.price >= market.best_ask`
- Fill price: `market.best_ask` (taker price)
- Fill size: `min(order.remaining_size, market.ask_size)`

### Sell Orders
- Fill condition: `order.price <= market.best_bid`
- Fill price: `market.best_bid` (taker price)
- Fill size: `min(order.remaining_size, market.bid_size)`

### Market Updates
When market data changes, pending orders are checked:
```python
engine.process_market_update(token_id, new_market_data)
```

## PnL Calculation

### Realized PnL
- Long position sold: `(sell_price - avg_price) * size`
- Short position bought: `(avg_price - buy_price) * size`

### Unrealized PnL
- `(current_price - avg_price) * position_size`

## Database Schema

### simulation_config
```sql
CREATE TABLE simulation_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### simulation_balance
```sql
CREATE TABLE simulation_balance (
    timestamp DATETIME PRIMARY KEY,
    usdc_balance REAL,
    position_value REAL,
    total_value REAL,
    unrealized_pnl REAL,
    realized_pnl REAL
);
```

### trades (existing, extended for simulation)
- Orders with `order_id` starting with `SIM-` are simulation orders
- Stores order status, fills, and PnL

## Testing
Run the test suite:
```bash
python test_simulation.py
```

All tests verify:
- Order creation and storage
- Immediate matching logic
- Position tracking with average price updates
- Balance deduction on buys
- PnL calculation on sells
- Report generation
- Market update triggering fills

## Integration with Trading Strategy
The simulation engine integrates seamlessly with the existing trading strategy:
- Same entry points (`create_order`)
- Same market data processing
- Same position and balance tracking (virtual)
- Same logging to SQLite
- Can switch between real and simulated trading via environment variable
