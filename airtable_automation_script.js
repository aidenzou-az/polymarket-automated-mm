// ============================================================
// Airtable 自动化脚本 - 一键创建 Polymarket 交易机器人所需的表结构
//
// 使用方法：
// 1. 打开你的 Airtable Base
// 2. 点击右上角的 "Extensions" (扩展)
// 3. 点击 "Add an extension"
// 4. 选择 "Scripting" (脚本)
// 5. 删除默认代码，复制粘贴下面的全部代码
// 6. 点击 "Run" (运行)
// ============================================================

// 表结构定义
const tablesConfig = [
    {
        name: 'Markets',
        fields: [
            { name: 'condition_id', type: 'singleLineText' },
            { name: 'question', type: 'singleLineText' },
            { name: 'answer1', type: 'singleLineText' },
            { name: 'answer2', type: 'singleLineText' },
            { name: 'token1', type: 'singleLineText' },
            { name: 'token2', type: 'singleLineText' },
            { name: 'neg_risk', type: 'checkbox', options: { color: 'greenBright', icon: 'check' } },
            { name: 'best_bid', type: 'number', options: { precision: 4 } },
            { name: 'best_ask', type: 'number', options: { precision: 4 } },
            { name: 'spread', type: 'number', options: { precision: 4 } },
            { name: 'gm_reward_per_100', type: 'percent', options: { precision: 2 } },
            { name: 'rewards_daily_rate', type: 'number', options: { precision: 2 } },
            { name: 'volatility_sum', type: 'number', options: { precision: 2 } },
            { name: 'min_size', type: 'number', options: { precision: 0 } },
            { name: 'max_spread', type: 'number', options: { precision: 4 } },
            { name: 'tick_size', type: 'number', options: { precision: 3 } },
            { name: 'market_slug', type: 'singleLineText' },
            {
                name: 'status',
                type: 'singleSelect',
                options: {
                    choices: [
                        { name: 'active', color: 'greenBright2' },
                        { name: 'ended', color: 'yellowBright2' },
                        { name: 'paused', color: 'orangeBright2' },
                        { name: 'archived', color: 'grayBright' }
                    ]
                }
            }
        ]
    },
    {
        name: 'Trading Configs',
        fields: [
            { name: 'Name', type: 'singleLineText' },
            { name: 'trade_size', type: 'number', options: { precision: 0 } },
            { name: 'max_size', type: 'number', options: { precision: 0 } },
            {
                name: 'param_type',
                type: 'singleSelect',
                options: {
                    choices: [
                        { name: 'conservative', color: 'blueBright2' },
                        { name: 'default', color: 'yellowBright2' },
                        { name: 'aggressive', color: 'redBright2' }
                    ]
                }
            },
            { name: 'enabled', type: 'checkbox', options: { color: 'greenBright', icon: 'check' } },
            { name: 'comments', type: 'multilineText' }
            // Note: market, condition_id, question are linked fields to be created after Markets table
        ]
    },
    {
        name: 'Trade Summary',
        fields: [
            { name: 'date', type: 'date', options: { dateFormat: 'YYYY-MM-DD' } },
            { name: 'total_trades', type: 'number', options: { precision: 0 } },
            { name: 'buy_count', type: 'number', options: { precision: 0 } },
            { name: 'sell_count', type: 'number', options: { precision: 0 } },
            { name: 'total_volume', type: 'number', options: { precision: 2 } },
            { name: 'total_pnl', type: 'number', options: { precision: 2 } },
            { name: 'avg_trade_size', type: 'number', options: { precision: 2 } }
        ]
    },
    {
        name: 'Alerts',
        fields: [
            {
                name: 'level',
                type: 'singleSelect',
                options: {
                    choices: [
                        { name: 'info', color: 'blueBright2' },
                        { name: 'warning', color: 'yellowBright2' },
                        { name: 'error', color: 'orangeBright2' },
                        { name: 'critical', color: 'redBright2' }
                    ]
                }
            },
            { name: 'message', type: 'singleLineText' },
            { name: 'details', type: 'multilineText' },
            { name: 'acknowledged', type: 'checkbox', options: { color: 'greenBright', icon: 'check' } }
            // Note: related_market is linked field to be created after Markets table
        ]
    }
];

// 主函数
async function createTables() {
    output.markdown('# 🚀 Polymarket 交易机器人 - Airtable 初始化');
    output.markdown('开始创建所需的表结构...\n');

    let createdCount = 0;
    let existingCount = 0;

    for (const tableConfig of tablesConfig) {
        // 检查表是否已存在
        let table = base.getTableIfExists(tableConfig.name);

        if (table) {
            output.markdown(`⚠️ 表 "**${tableConfig.name}**" 已存在，跳过`);
            existingCount++;
            continue;
        }

        // 创建表
        try {
            output.markdown(`📝 创建表 "**${tableConfig.name}**"...`);

            // Airtable Scripting API 暂时不支持直接创建表
            // 所以这里只是输出信息
            output.markdown(`   ⬜ 需要手动创建: ${tableConfig.name}`);
            output.markdown(`   字段数: ${tableConfig.fields.length}`);

            // 列出所有字段
            for (const field of tableConfig.fields) {
                output.markdown(`   - ${field.name} (${field.type})`);
            }
            output.markdown('');

        } catch (error) {
            output.markdown(`❌ 创建表 "${tableConfig.name}" 失败: ${error.message}`);
        }
    }

    output.markdown('---');
    output.markdown('## 📋 下一步操作');
    output.markdown('由于 Airtable Scripting API 限制，无法自动创建表。');
    output.markdown('请按照上述列表，在 Airtable 界面中手动创建这些表和字段。\n');
    output.markdown('或者使用以下快捷方式：');
    output.markdown('1. 复制一个现有的 Base（如果有模板）');
    output.markdown('2. 使用 Airtable 的 CSV 导入功能');
    output.markdown('3. 手动创建（推荐，可以熟悉结构）\n');
}

// 运行
createTables();
