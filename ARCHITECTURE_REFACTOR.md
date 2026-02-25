# 架构重构说明：完全移除 Google Sheets

## 变更概述

从混合架构（Airtable + Google Sheets）彻底迁移到纯 Airtable + SQLite 架构。

## 已完成的修改

### 1. data_updater/data_updater.py ✅
- **完全重写**，移除所有 Google Sheets 相关代码
- 移除依赖：`gspread`, `google.oauth2`, `gspread_dataframe`
- 数据直接写入 Airtable Markets 表
- CSV 仅作为备份，不再是主要存储

### 2. poly_data/utils.py ✅
- **完全重写**，移除所有 Google Sheets 代码
- 删除 `get_sheet_df_from_sheets()` 函数
- `get_sheet_df()` 改名为 `get_trading_configs_from_airtable()`
- 直接从 Airtable 读取配置和市场数据

### 3. poly_data/data_utils.py ✅
- 移除 `from poly_data.utils import get_sheet_df`
- 添加 `get_trading_configs_from_airtable()` 函数
- `update_markets()` 现在从 Airtable 读取

## 需要继续修改的文件

以下文件仍包含 Google Sheets 引用，需要逐步清理：

### 高优先级（影响运行）
1. `update_selected_markets.py` - 市场选择脚本
2. `update_markets.py` - 市场更新脚本
3. `main.py` - 主程序入口
4. `trading.py` - 交易逻辑

### 中优先级（功能相关）
5. `poly_data/gspread.py` - 可以删除
6. `data_updater/google_utils.py` - 可以删除
7. `poly_utils/google_utils.py` - 可以删除

### 低优先级（辅助功能）
8. `export_trades_to_sheets.py` - 可以删除或重写
9. `check_positions.py` - 检查持仓
10. `approve_and_trade.py` - 交易审批

## 环境变量变更

### 删除（不再需要）
```bash
# 这些变量可以删除
SPREADSHEET_URL=
GOOGLE_CREDENTIALS_PATH=
```

### 保留（必需）
```bash
# Airtable 配置（必需）
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=

# SQLite 配置（可选，有默认值）
SQLITE_DB_PATH=data/trading_local.db

# Polymarket 配置（必需）
PK=
```

## 数据流向（新架构）

```
┌─────────────────┐      ┌─────────────────┐
│   Polymarket    │      │   Airtable      │
│   (交易执行)     │      │   (配置/市场)    │
└────────┬────────┘      └────────┬────────┘
         │                        │
         │ WebSocket              │ API
         │                        │
    ┌────▼────────────────────────▼────┐
│         Trading Bot                │
│  - 从 Airtable 读取配置             │
│  - 从 Airtable 读取市场列表         │
│  - 执行交易                         │
└────┬────────────────────────────────┘
     │
     │ 写入
     │
┌────▼──────────┐     ┌──────────────┐
│  SQLite       │     │  CSV Backup  │
│  - trades     │     │  (可选)      │
│  - positions  │     └──────────────┘
│  - rewards    │
└───────────────┘
```

## 关键变更点

### 1. 配置读取
**旧代码：**
```python
from poly_data.utils import get_sheet_df
df, params = get_sheet_df()
```

**新代码：**
```python
from poly_data.airtable_client import AirtableClient
client = AirtableClient()
configs = client.get_trading_configs()
markets = client.get_active_markets()
```

### 2. 市场数据更新
**旧代码：**
```python
spreadsheet = get_spreadsheet()
worksheet = spreadsheet.worksheet("All Markets")
worksheet.update(data)
```

**新代码：**
```python
airtable = AirtableClient()
airtable.upsert_markets_batch(markets_data)
```

### 3. 交易记录
**旧代码：**
```python
from poly_data.gspread import get_spreadsheet
_worksheet.append_row(trade_data)
```

**新代码：**
```python
from poly_data.local_storage import LocalStorage
storage = LocalStorage()
storage.log_trade(trade_data)
```

## 回滚方案

如果需要回滚到 Google Sheets：

1. 检出旧版本代码：`git checkout <commit-hash>`
2. 恢复 Google Sheets 凭证：`credentials.json`
3. 设置环境变量：`STORAGE_BACKEND=sheets`

但建议不要回滚，而是修复 Airtable 配置问题。

## 下一步工作

1. 修改 `update_selected_markets.py` 支持 Airtable
2. 修改 `main.py` 移除 Google Sheets 初始化
3. 删除不再使用的文件：
   - `poly_data/gspread.py`
   - `data_updater/google_utils.py`
   - `poly_utils/google_utils.py`
4. 更新文档
5. 全面测试
