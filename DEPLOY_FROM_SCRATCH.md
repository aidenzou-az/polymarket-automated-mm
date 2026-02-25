# 从零开始部署指南

适用于：没有历史数据需要迁移，直接使用 Airtable + SQLite 新系统

## 前置要求

- Python 3.8+
- Airtable 账号（免费版即可）

## 部署步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建 Airtable Base

1. 访问 https://airtable.com 并登录
2. 点击 "Create a base" → "Build a new base from scratch"
3. 命名为 "Polymarket Trading"

#### 创建表结构

**表 1: Markets**
- 字段：
  - `condition_id` (Single line text) - 设为主字段
  - `question` (Single line text)
  - `answer1`, `answer2` (Single line text)
  - `token1`, `token2` (Single line text)
  - `neg_risk` (Checkbox)
  - `best_bid`, `best_ask` (Number)
  - `spread` (Number)
  - `gm_reward_per_100` (Percent)
  - `rewards_daily_rate` (Number)
  - `volatility_sum` (Number)
  - `min_size`, `max_spread`, `tick_size` (Number)
  - `market_slug` (Single line text)
  - `status` (Single select: active/ended/paused/archived)

**表 2: Trading Configs**
- 字段：
  - `market` (Link to Markets)
  - `condition_id` (Lookup from Markets)
  - `question` (Lookup from Markets)
  - `trade_size`, `max_size` (Number)
  - `param_type` (Single select: conservative/default/aggressive)
  - `enabled` (Checkbox)
  - `comments` (Long text)

**表 3: Trade Summary**
- 字段：
  - `date` (Date)
  - `total_trades`, `buy_count`, `sell_count` (Number)
  - `total_volume`, `total_pnl`, `avg_trade_size` (Number)

**表 4: Alerts**
- 字段：
  - `level` (Single select: info/warning/error/critical)
  - `message` (Single line text)
  - `details` (Long text)
  - `related_market` (Link to Markets)
  - `acknowledged` (Checkbox)

### 3. 获取 Airtable API 凭证

1. 获取 API Key：
   - 访问 https://airtable.com/create/tokens
   - 点击 "Create new token"
   - 名称：Polymarket Bot
   - 权限：data.records:read, data.records:write, schema.bases:read
   - 复制 token

2. 获取 Base ID：
   - 打开你的 Airtable Base
   - 看 URL: https://airtable.com/appXXXXXX/...
   - `appXXXXXX` 就是 Base ID

### 4. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
# 必需
PK=your_polymarket_private_key_here

# Airtable 配置
AIRTABLE_API_KEY=keyXXXXXXXXXXXXXX      # 从上一步获取
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX      # 从上一步获取

# 存储后端（默认即可）
STORAGE_BACKEND=hybrid

# SQLite 路径（默认即可）
SQLITE_DB_PATH=data/trading_local.db

# 可选
DISCORD_WEBHOOK_URL=your_discord_webhook_url  # 如果需要 Discord 告警
```

### 5. 运行初始化检查

```bash
python scripts/init_new_system.py
```

这会检查：
- 环境变量是否正确设置
- Airtable 连接是否正常
- SQLite 数据库是否能正常写入
- 表结构是否正确

### 6. 获取市场数据

运行数据更新器，将市场数据写入 Airtable：

```bash
python data_updater/data_updater.py
```

这会将 Polymarket 的市场数据抓取并写入 Airtable 的 Markets 表。

### 7. 选择交易的市场

在 Airtable 中配置要交易的市场：

1. 打开 Airtable 的 "Trading Configs" 表
2. 点击 "Add record"
3. 在 `market` 字段中，选择你要交易的市场（从 Markets 表关联）
4. 设置参数：
   - `trade_size`: 每次交易金额（如 50）
   - `max_size`: 最大持仓金额（如 100）
   - `param_type`: 策略类型（conservative/default/aggressive）
   - `enabled`: 勾选启用
5. 保存

### 8. 启动机器人

```bash
python main.py
```

机器人会自动：
- 从 Airtable 读取配置
- 连接到 Polymarket WebSocket
- 开始交易选定的市场
- 将交易记录写入本地 SQLite

### 9. 设置定时维护任务（可选）

添加到 crontab：

```bash
# 编辑 crontab
crontab -e

# 添加行（每天凌晨1点运行维护）
0 1 * * * cd /path/to/your/bot && python scripts/daily_maintenance.py >> data/maintenance.log 2>&1
```

或使用 Python schedule（已在 requirements.txt 中）：

```python
# 在 main.py 中添加
import schedule
import time

def run_maintenance():
    import subprocess
    subprocess.run(['python', 'scripts/daily_maintenance.py'])

schedule.every().day.at("01:00").do(run_maintenance)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 监控与维护

### 查看交易记录（SQLite）

```bash
# 使用 sqlite3 命令行
sqlite3 data/trading_local.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

或使用 Python：

```python
from poly_data.local_storage import LocalStorage

storage = LocalStorage()
trades = storage.get_recent_trades(hours=24)
for t in trades:
    print(t)
```

### 查看 Airtable 中的数据

直接访问 Airtable 网页界面查看：
- Markets: 市场列表
- Trading Configs: 交易配置
- Trade Summary: 每日汇总（由 daily_maintenance.py 生成）
- Alerts: 系统告警

### 手动触发数据更新

```bash
python data_updater/data_updater.py
```

### 清理旧数据

```bash
python scripts/daily_maintenance.py
```

## 常见问题

### Q: 启动时提示 "No module named 'pyairtable'"
```bash
pip install pyairtable>=2.0.0
```

### Q: Airtable 连接失败
- 检查 API Key 是否正确
- 检查 Base ID 是否正确
- 检查网络连接

### Q: 机器人找不到要交易的市场
- 确保 Trading Configs 表中有记录
- 确保 `enabled` 字段已勾选
- 确保关联的 Markets 记录存在

### Q: 如何添加新的交易市场？
1. 运行 `python data_updater/data_updater.py` 更新市场列表
2. 在 Trading Configs 表中添加新记录
3. 关联到 Markets 表中的市场
4. 设置参数并启用

### Q: 如何修改交易参数？
直接在 Airtable 的 Trading Configs 表中修改，机器人会在 60 秒内自动同步。

## 架构说明

```
┌─────────────────┐      ┌─────────────────┐
│   Polymarket    │      │   Airtable      │
│   (交易执行)     │      │   (配置/汇总)    │
└────────┬────────┘      └────────┬────────┘
         │                        │
         │ WebSocket              │ API (60s缓存)
         │                        │
    ┌────▼────────────────────────┴────┐
    │         Trading Bot (main.py)    │
    └────┬─────────────────────────────┘
         │
         │ SQLite (本地写入)
         │
    ┌────▼────┐
    │  data/  │
    │ trading │
    │_local.db│
    └─────────┘
```

- **SQLite**: 高频数据（交易、仓位、奖励快照）
- **Airtable**: 配置和汇总（市场列表、交易配置、每日汇总、告警）
