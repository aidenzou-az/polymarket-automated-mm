# GitHub Repository - Share Checklist

## ✅ **SAFE TO SHARE - Scripts & Files**

### **Core Application Scripts** (Python)
```
main.py
trading.py
update_markets.py
update_selected_markets.py
```

### **Core Modules** (`poly_data/`)
```
poly_data/__init__.py
poly_data/CONSTANTS.py
poly_data/data_processing.py
poly_data/data_utils.py
poly_data/global_state.py
poly_data/position_snapshot.py
poly_data/reward_tracker.py
poly_data/trade_logger.py
poly_data/trading_utils.py
poly_data/utils.py
poly_data/websocket_handlers.py
poly_data/abis.py
poly_data/polymarket_client.py
poly_data/gspread.py
```

### **Data Updater Module** (`data_updater/`)
```
data_updater/data_updater.py
data_updater/find_markets.py
data_updater/google_utils.py
data_updater/trading_utils.py
data_updater/erc20ABI.json
```

### **Utility Scripts**
```
cancel_all_orders.py
check_positions.py
approve_and_trade.py
export_trades_to_sheets.py
update_hyperparameters.py
validate_polymarket_bot.py
check_market_config.py
```

### **Market Selection Scripts**
```
select_markets.py
select_best_markets.py
update_selected_markets.py
```

### **Analysis Scripts**
```
analyze_performance.py
analyze_profitable_markets.py
update_stats.py
```

### **Test Scripts**
```
test_aggressive_trading.py
test_immediate_order.py
test_trade_logger.py
force_trade_test.py
quick_order_test.py
direct_order_test.py
```

### **Poly Merger** (Node.js)
```
poly_merger/merge.js
poly_merger/package.json
poly_merger/package-lock.json
poly_merger/README.md
poly_merger/safe-helpers.js
poly_merger/safeAbi.js
```

### **Other Modules**
```
poly_stats/__init__.py
poly_stats/account_stats.py
poly_utils/__init__.py
poly_utils/google_utils.py
```

### **Documentation**
```
README.md
BOT_OVERVIEW.md
QUICKSTART.md
CLAUDE.md
IMPROVEMENTS.md
SCRIPT_USAGE.md
SAFE_TO_SHARE.md
GITHUB_SHARE_CHECKLIST.md (this file)
EFFICIENCY_FIXES_APPLIED.md
ORDER_EFFICIENCY_ANALYSIS.md
```

### **Configuration Files**
```
requirements.txt          ✅ SAFE - All dependencies listed
.gitignore               ✅ SAFE - Git ignore rules
.claudeignore            ✅ SAFE - Claude ignore rules
recommended_hyperparameters.csv  ✅ SAFE - Sample data only
```

---

## ✅ **SAFE TO SHARE - Dependencies**

### **Python Dependencies** (`requirements.txt`)
All dependencies are safe to share:
- `py-clob-client==0.20.0` - Polymarket client
- `python-dotenv==1.0.0` - Environment variables
- `pandas` - Data processing
- `gspread` - Google Sheets API
- `gspread-dataframe` - Google Sheets DataFrame integration
- `sortedcontainers` - Data structures
- `eth-account>=0.11.0` - Ethereum account management
- `eth-utils>=4.0.0` - Ethereum utilities
- `web3>=6.0.0` - Web3.py for blockchain
- `websockets==12.0` - WebSocket client
- `requests==2.32.3` - HTTP requests
- `cryptography==42.0.8` - Cryptographic functions
- `google-auth` - Google authentication
- `schedule>=1.2.0` - Task scheduling
- `discord-webhook` - Discord notifications (optional)
- `streamlit>=1.28.0` - Dashboard (optional, not used in core bot)
- `plotly>=5.18.0` - Charts (optional, for dashboard)
- `psutil>=5.9.0` - System monitoring (optional, for dashboard)

**Note:** `streamlit`, `plotly`, and `psutil` are for dashboard functionality. You can include them in requirements.txt - users who don't want the dashboard simply won't use those features.

### **Node.js Dependencies** (`poly_merger/package.json`)
All dependencies are safe to share:
- `dotenv` - Environment variables
- `ethers` - Ethereum library

---

## ❌ **DO NOT SHARE**

### **Sensitive Files**
```
.env                    ❌ Contains private keys, wallet addresses
.env.*                  ❌ Any environment files
credentials.json        ❌ Google Service Account credentials
```

### **Log Files**
```
*.log                   ❌ May contain sensitive data
main.log
data_updater.log
websocket_handlers.log
data_processing.log
polymarket_validation.log
aggressive_bot.log
aggressive_test.log
bot_output.log
data_update_output.log
```

### **Data Directories**
```
data/                   ❌ Personal trading data
data_updater/data/      ❌ Market data
data_updater/data_*/    ❌ Historical data (data_20251010/, etc.)
positions/             ❌ Position snapshots
```

### **IDE & System Files**
```
.idea/                  ❌ IDE configuration
.DS_Store              ❌ macOS system file
__pycache__/           ❌ Python cache
*.pyc                  ❌ Compiled Python
node_modules/          ❌ Node.js dependencies (too large, use package.json)
```

### **Optional: Dashboard Files** (if you want to exclude)
```
dashboard.py            ⚠️ Optional - Dashboard functionality
dashboard_old.py        ⚠️ Optional - Old dashboard
```

---

## 📋 **Quick Copy Command**

To create a clean copy for GitHub (excluding sensitive files):

```bash
# Create new directory
mkdir poly-maker-clean
cd poly-maker-clean

# Copy all safe files (adjust paths as needed)
# This is a manual process - use the list above
```

---

## 🔍 **Verification Steps**

Before pushing to GitHub:

1. ✅ Check `.gitignore` includes:
   - `.env`
   - `credentials.json`
   - `*.log`
   - `data/`
   - `data_updater/data/`
   - `positions/`
   - `__pycache__/`
   - `.idea/`
   - `node_modules/`

2. ✅ Verify no hardcoded secrets:
   ```bash
   grep -r "0x[a-fA-F0-9]\{64\}" .  # Private keys
   grep -r "PK=" . | grep -v ".env"  # Hardcoded private keys
   ```

3. ✅ Check all scripts use environment variables:
   ```bash
   grep -r "os.getenv\|os.environ\|load_dotenv" .  # Should be present
   ```

4. ✅ Review log files (if any committed):
   - Ensure no wallet addresses
   - Ensure no private keys
   - Better to exclude all `*.log` files

---

## 📦 **Recommended Repository Structure**

```
poly-maker/
├── README.md
├── requirements.txt          ✅
├── .gitignore               ✅
├── main.py                  ✅
├── trading.py               ✅
├── update_markets.py        ✅
├── update_selected_markets.py ✅
├── poly_data/               ✅ (all .py files)
├── data_updater/            ✅ (all .py files, exclude data/)
├── poly_merger/             ✅ (all .js files, package.json)
├── poly_stats/              ✅
├── poly_utils/              ✅
├── [utility scripts]        ✅
├── [test scripts]           ✅
└── [documentation]          ✅
```

---

## 🎯 **Summary**

**Total Safe Scripts:** ~50+ Python scripts + Node.js files
**Dependencies:** All in `requirements.txt` and `package.json` are safe
**Exclusions:** `.env`, `credentials.json`, `*.log`, `data/`, `positions/`

All code reads secrets from environment variables - no hardcoded credentials!

