# =� Quick Start Guide

## Prerequisites

1.  Python 3.8+ installed
2.  `.env` file configured with:
   - `PK` (Private key)
   - `BROWSER_ADDRESS` (Wallet address)
   - `SPREADSHEET_URL` (Google Sheets URL)
3.  `credentials.json` (Google service account) in project root
4.  Google Sheets with proper structure (see CLAUDE.md)

---

## Option 1: Fully Automated Setup (Recommended) >

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start Everything
```bash
# Terminal 1: Data updater (fetches market data continuously)
python data_updater/data_updater.py

# Terminal 2: Trading Bot
python main.py
```

### Step 3: Access Dashboard
Open browser to: **http://localhost:8501**

---

## Option 2: Manual Step-by-Step =�

### Step 1: Update Market Data
```bash
# This fetches all Polymarket markets and calculates rewards
python update_markets.py
```
� Takes ~5-10 minutes to complete

### Step 2: Select Markets
```bash
# Auto-select top 5 markets by composite score
python select_markets.py --top 5 --min-reward 0.75 --max-volatility 20
```

Or use the dashboard:
```bash
streamlit run dashboard.py
# Go to "Market Selection" tab � set parameters � click "Auto-Select Markets"
```

### Step 3: Start Trading
```bash
python main.py
```

Monitor with:
```bash
tail -f main.log
```

---

## Option 3: One-Time Data Update =�

If you just want to update market data once without scheduling:

```bash
# Update market data (run once)
python data_updater/data_updater.py

# Then select markets
python update_selected_markets.py
```

---

## Stopping the Bot

### Stop Main Bot
```bash
# Find process
ps aux | grep "python main.py"

# Kill by PID
kill <PID>

# Or kill all instances
pkill -f "python.*main.py"
```

### Stop Data Updater
```bash
# Graceful shutdown
Ctrl+C (in terminal running data_updater)

# Force kill
pkill -f "python.*data_updater"
```

### Stop Dashboard
```bash
# In terminal running streamlit
Ctrl+C
```

---

## Common Commands

### View Market Statistics
```bash
python select_markets.py --stats
```

### Preview Market Selection (Dry Run)
```bash
python select_markets.py --top 10 --dry-run
```

### Check Bot Status
```bash
ps aux | grep -i "python.*main.py"
```

### View Logs
```bash
# Main bot
tail -f main.log

# Data updater
tail -f data_updater.log

# Data updater
tail -f data_updater.log
```

---

## Typical Workflow

### Morning:
```bash
# Start data updater (run in background)
python data_updater/data_updater.py &

# Start trading bot
python main.py &
```

### During Day:
- Monitor via dashboard at `http://localhost:8501`
- Check "Maker Rewards" tab to see estimated earnings
- Adjust market selection if needed via dashboard

### Evening:
- Review "Trade Log" for fills
- Check positions in "Positions & Orders"
- Stop bot if desired: `pkill -f "python.*main.py"`

---

## Troubleshooting

### "No markets in Volatility Markets sheet"
� Run `python update_markets.py` first

### "Bot not starting"
� Check `.env` file has `PK`, `BROWSER_ADDRESS`, `SPREADSHEET_URL`

### "Orders being cancelled too often"
� Check main.log - rate limiting should show "cooldown" messages

### "No reward data in dashboard"
� Bot must run for 5+ minutes first

### "Dashboard won't load"
� `pip install streamlit plotly psutil`

---

## Next Steps

1. Read `IMPROVEMENTS.md` for detailed feature documentation
2. Read `CLAUDE.md` for trading logic details
3. Customize parameters in Google Sheets "Hyperparameters" tab
4. Set up Discord webhook for notifications (optional)

---

## Support

Check logs first:
```bash
tail -100 main.log
tail -100 data_updater.log
```

Common issues documented in `IMPROVEMENTS.md` � Troubleshooting section.
