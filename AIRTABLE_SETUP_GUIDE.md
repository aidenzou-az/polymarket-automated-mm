# Airtable 详细设置指南

## 一、创建 Base

1. 访问 https://airtable.com 并登录
2. 点击 "Create a base" → "Build a new base from scratch"
3. 命名为 **"Polymarket Trading"**

---

## 二、创建表及字段（详细配置）

### 表 1: Markets

**用途**: 存储市场信息

**主字段配置**:
- 字段名: `condition_id`
- 类型: Single line text
- 说明: 设置为 Primary field（主字段），需要手动填写市场的 condition_id

#### 完整字段列表

| 序号 | 字段名 | 类型 | 配置详情 | 说明 |
|------|--------|------|----------|------|
| 1 | **condition_id** | Single line text | 设为 Primary field | 市场的唯一标识，如 "0x123abc..." |
| 2 | **question** | Single line text | 默认 | 市场问题，如 "Will BTC reach $100k?" |
| 3 | **answer1** | Single line text | 默认 | 答案1，如 "Yes" |
| 4 | **answer2** | Single line text | 默认 | 答案2，如 "No" |
| 5 | **token1** | Single line text | 默认 | Token ID 1，如 "217426331434639062905690501558262415330672728883"
| 6 | **token2** | Single line text | 默认 | Token ID 2 |
| 7 | **neg_risk** | Checkbox | Color: greenBright<br>Icon: check | 是否为负风险市场 |
| 8 | **best_bid** | Number | Decimal: 4位<br>格式: Decimal | 最佳买入价，如 0.5500 |
| 9 | **best_ask** | Number | Decimal: 4位<br>格式: Decimal | 最佳卖出价，如 0.5600 |
| 10 | **spread** | Number | Decimal: 4位<br>格式: Decimal | 买卖价差，如 0.0100 |
| 11 | **gm_reward_per_100** | Percent | Decimal: 2位<br>格式: Percent | 每100美元的奖励率，如 1.25% |
| 12 | **rewards_daily_rate** | Number | Decimal: 2位<br>格式: Decimal | 每日奖励金额，如 12.50 |
| 13 | **volatility_sum** | Number | Decimal: 2位<br>格式: Decimal | 波动率总和，如 15.30 |
| 14 | **min_size** | Number | Decimal: 0位<br>格式: Integer | 最小交易金额，如 50 |
| 15 | **max_spread** | Number | Decimal: 4位<br>格式: Decimal | 最大价差，如 0.0100 |
| 16 | **tick_size** | Number | Decimal: 3位<br>格式: Decimal | 价格精度，如 0.001 |
| 17 | **market_slug** | Single line text | 默认 | 市场URL标识，如 "btc-100k-2024" |
| 18 | **status** | Single select | Options: <br>- active (greenBright2)<br>- ended (yellowBright2)<br>- paused (orangeBright2)<br>- archived (grayBright) | 市场状态 |

#### 创建步骤

1. 点击表名 "Table 1" 重命名为 "Markets"
2. 点击主字段 "Name" 重命名为 "condition_id"
3. 添加字段（点击 "+" 按钮）：
   - 选择字段类型
   - 输入字段名
   - 根据上表配置具体参数

---

### 表 2: Trading Configs

**用途**: 存储每个市场的交易配置

**主字段配置**:
- 字段名: `Name`
- 类型: Single line text
- 说明: 可以留空或使用公式自动生成，建议用 "market" 关联字段的值

#### 完整字段列表

| 序号 | 字段名 | 类型 | 配置详情 | 说明 |
|------|--------|------|----------|------|
| 1 | **Name** | Single line text | 设为 Primary field | 可以手动填写或使用公式 |
| 2 | **market** | Link to another record | **关键配置**:<br>- 关联到: **Markets** 表<br>- Allow linking to multiple records: **❌ 不勾选** (单项关联)<br>- 双向关联: 可勾选，会自动在 Markets 表创建关联字段 | 关联到 Markets 表的主字段 (condition_id) |
| 3 | **condition_id** | Lookup | **关键配置**:<br>- 源字段: **market**<br>- 查找字段: **condition_id**<br>- Show multiple values as: **list** | 从 Markets 表自动获取 |
| 4 | **question** | Lookup | **关键配置**:<br>- 源字段: **market**<br>- 查找字段: **question**<br>- Show multiple values as: **list** | 从 Markets 表自动获取市场问题 |
| 5 | **trade_size** | Number | Decimal: 0位<br>格式: Integer | 每次交易金额，如 50 |
| 6 | **max_size** | Number | Decimal: 0位<br>格式: Integer | 最大持仓金额，如 100 |
| 7 | **param_type** | Single select | Options: <br>- conservative (blueBright2)<br>- default (yellowBright2)<br>- aggressive (redBright2) | 交易策略类型 |
| 8 | **enabled** | Checkbox | Color: greenBright<br>Icon: check | 是否启用该市场的交易 |
| 9 | **comments** | Long text | 默认 | 备注信息 |

#### 创建步骤

1. 点击左下角 "+" 添加新表，命名为 "Trading Configs"
2. 添加字段：

**步骤 2.1: 添加 market 关联字段**
1. 点击 "+" 添加字段
2. 选择 "Link to another record"
3. 字段名填写: `market`
4. 选择要关联的表: **Markets**
5. **重要**: 取消勾选 "Allow linking to multiple records"（确保单项关联）
6. 可以勾选双向关联，会在 Markets 表自动创建反向关联字段
7. 点击 "Save"

**步骤 2.2: 添加 Lookup 字段 (condition_id)**
1. 点击 "+" 添加字段
2. 选择 "Lookup"
3. 字段名填写: `condition_id`
4. 配置:
   - Linked record field: 选择 **market**
   - Lookup field: 选择 **condition_id**
   - Formatting: 保持默认
5. 点击 "Save"

**步骤 2.3: 添加 Lookup 字段 (question)**
1. 同上步骤，字段名填写: `question`
2. Linked record field: **market**
3. Lookup field: **question**

**步骤 2.4: 添加其他字段**
按照字段列表添加 trade_size, max_size, param_type, enabled, comments

---

### 表 3: Trade Summary

**用途**: 每日交易汇总统计

**主字段配置**:
- 字段名: `date`
- 类型: Date
- 说明: 设置为 Primary field，使用日期作为主键

#### 完整字段列表

| 序号 | 字段名 | 类型 | 配置详情 | 说明 |
|------|--------|------|----------|------|
| 1 | **date** | Date | 设为 Primary field<br>Format: ISO (YYYY-MM-DD)<br>Include time: ❌ 不勾选 | 日期，如 2024-01-15 |
| 2 | **total_trades** | Number | Decimal: 0位<br>格式: Integer | 总交易次数 |
| 3 | **buy_count** | Number | Decimal: 0位<br>格式: Integer | 买入次数 |
| 4 | **sell_count** | Number | Decimal: 0位<br>格式: Integer | 卖出次数 |
| 5 | **total_volume** | Number | Decimal: 2位<br>格式: Decimal<br>Currency: 可选 USD | 总交易量 |
| 6 | **total_pnl** | Number | Decimal: 2位<br>格式: Decimal<br>Currency: 可选 USD | 总盈亏 |
| 7 | **avg_trade_size** | Number | Decimal: 2位<br>格式: Decimal<br>Currency: 可选 USD | 平均交易金额 |

#### 创建步骤

1. 添加新表，命名为 "Trade Summary"
2. 点击主字段 "Name" 重命名为 "date"
3. 更改主字段类型为 "Date"
4. 配置:
   - Date format: ISO (YYYY-MM-DD)
   - Include time: 取消勾选
5. 添加其他字段

---

### 表 4: Alerts

**用途**: 系统告警通知

**主字段配置**:
- 字段名: `message`
- 类型: Single line text
- 说明: 设置为 Primary field，存储告警标题

#### 完整字段列表

| 序号 | 字段名 | 类型 | 配置详情 | 说明 |
|------|--------|------|----------|------|
| 1 | **message** | Single line text | 设为 Primary field | 告警标题，如 "Order filled" |
| 2 | **level** | Single select | Options: <br>- info (blueBright2)<br>- warning (yellowBright2)<br>- error (orangeBright2)<br>- critical (redBright2) | 告警级别 |
| 3 | **details** | Long text | 默认 | 告警详细信息 |
| 4 | **related_market** | Link to another record | **关键配置**:<br>- 关联到: **Markets** 表<br>- Allow linking to multiple records: **❌ 不勾选** (单项关联)<br>- 双向关联: 可选 | 关联到 Markets 表 |
| 5 | **acknowledged** | Checkbox | Color: greenBright<br>Icon: check | 是否已确认告警 |
| 6 | **created_at** | Created time | Date format: ISO<br>Include time: ✅ 勾选<br>Use same time zone: GMT | 自动记录创建时间 |

#### 创建步骤

1. 添加新表，命名为 "Alerts"
2. 点击主字段 "Name" 重命名为 "message"
3. 添加字段:

**步骤 4.1: 添加 related_market 关联字段**
1. 点击 "+" 添加字段
2. 选择 "Link to another record"
3. 字段名填写: `related_market`
4. 选择要关联的表: **Markets**
5. **重要**: 取消勾选 "Allow linking to multiple records"
6. 点击 "Save"

**步骤 4.2: 添加 created_at 字段**
1. 点击 "+" 添加字段
2. 选择 "Created time"
3. 字段名填写: `created_at`
4. 配置:
   - Date format: ISO
   - Include time: 勾选
   - Use same time zone: GMT (推荐)
5. 点击 "Save"

**步骤 4.3: 添加其他字段**
按照字段列表添加 level, details, acknowledged

---

## 三、字段类型详细说明

### 1. Single line text（单行文本）
- 默认配置即可
- 不需要特殊格式

### 2. Number（数字）
配置步骤:
1. 添加字段时选择 "Number"
2. 点击字段下拉菜单 → "Customize field type"
3. 配置:
   - **Decimal places**: 按字段列表要求设置 (0-4位)
   - **Format**:
     - 普通数字选 "Decimal"
     - 金额可选 "Currency" → USD

### 3. Percent（百分比）
配置步骤:
1. 添加字段时选择 "Percent"
2. 配置 Decimal places: 2
3. 存储时会自动转换为小数 (如 1.25% 存储为 0.0125)

### 4. Checkbox（复选框）
配置步骤:
1. 添加字段时选择 "Checkbox"
2. 点击字段下拉菜单 → "Customize field type"
3. 配置:
   - **Color**: greenBright (或其他颜色)
   - **Icon**: check

### 5. Single select（单选）
配置步骤:
1. 添加字段时选择 "Single select"
2. 添加选项:
   - 输入选项名称
   - 选择颜色 (推荐颜色见字段列表)
3. 按字段列表添加所有选项

### 6. Date（日期）
配置步骤:
1. 添加字段时选择 "Date"
2. 配置:
   - **Date format**: ISO (YYYY-MM-DD)
   - **Include time**: 根据需要勾选
   - **Time format**: 24小时制
   - **Use same time zone**: GMT (推荐)

### 7. Link to another record（关联记录）
配置步骤:
1. 添加字段时选择 "Link to another record"
2. 选择要关联的表
3. **重要选项**:
   - **Allow linking to multiple records**:
     - 勾选 = 可以关联多个记录 (多对多)
     - 不勾选 = 只能关联一个记录 (多对一)
   - 本系统所有关联都使用 **单项关联** (不勾选)
4. **双向关联**:
   - 勾选后会自动在关联表创建反向关联字段
   - 推荐勾选，方便查看关联关系

### 8. Lookup（查找）
配置步骤:
1. **必须先创建 Link 字段**（如 market）
2. 添加字段时选择 "Lookup"
3. 配置:
   - **Linked record field**: 选择 Link 字段名（如 market）
   - **Lookup field**: 选择要从关联表获取的字段（如 condition_id）
4. 数据会自动从关联表同步

### 9. Created time（创建时间）
- 自动记录行创建时间
- 配置:
  - Date format: ISO
  - Include time: 勾选

---

## 四、主字段自动生成配置

### Trading Configs 表的 Name 字段（可选）

如果你想让 Name 字段自动显示关联市场的名称，可以使用公式：

1. 将 Name 字段类型改为 "Formula"
2. 输入公式:
```
IF({market}, {market})
```
或更详细的:
```
IF(AND({market}, {question}), {market} & " - " & LEFT({question}, 30))
```

这样 Name 字段会自动显示 "condition_id - 市场问题前30字"

---

## 五、验证表结构

创建完成后，运行检查脚本:

```bash
python scripts/import_airtable_schema.py
```

或:

```bash
python scripts/init_new_system.py
```

如果看到以下输出，说明配置正确:
```
✓ Airtable 连接成功
   记录数: 0/1200
   使用率: 0%
✓ 所有必需的表都存在
```

---

## 六、常见问题

### Q: 创建 Lookup 字段时提示 "No linked record field"
**原因**: 没有先创建 Link to another record 字段
**解决**: 先创建 market 字段（Link 类型），再创建 condition_id 和 question（Lookup 类型）

### Q: 关联字段显示 "Multiple cells"
**原因**: 允许多项关联了
**解决**: 编辑关联字段，取消勾选 "Allow linking to multiple records"

### Q: Lookup 字段不显示数据
**原因**: 关联字段为空，或 Lookup 配置错误
**解决**:
1. 确保 market 字段已关联到 Markets 表的记录
2. 检查 Lookup 配置中的 "Linked record field" 和 "Lookup field" 是否正确

### Q: 主字段 condition_id 不能是 Lookup
**原因**: Airtable 限制，Primary field 不能是 Lookup 或 Formula（除非先用文本创建再转换）
**解决**: Markets 表的 condition_id 使用 Single line text，手动填写或使用自动化填充

---

## 七、下一步

表结构创建完成后，继续:

1. **获取 API 凭证**: 查看本文件第一部分的 "获取 API Key" 和 "获取 Base ID"
2. **配置环境变量**: 将凭证填入 `.env` 文件
3. **初始化系统**: `python scripts/init_new_system.py`
4. **获取市场数据**: `python data_updater/data_updater.py`
5. **配置交易**: 在 Trading Configs 表中添加要交易的市场
6. **启动机器人**: `python main.py`
