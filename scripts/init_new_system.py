#!/usr/bin/env python3
"""
初始化脚本 - 从零开始设置 Airtable + SQLite 系统
（不需要从 Google Sheets 迁移历史数据）
"""
import os
import sys
from datetime import datetime

# 先加载环境变量
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_environment():
    """检查环境变量"""
    print("=" * 60)
    print("1. 检查环境变量")
    print("=" * 60)

    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    pk = os.getenv('PK')

    if not pk:
        print("❌ 未设置 PK (Polymarket 私钥)")
        print("   请在 .env 文件中添加: PK=your_private_key")
        return False
    else:
        print(f"✓ PK 已设置: {pk[:6]}...")

    if not api_key:
        print("❌ 未设置 AIRTABLE_API_KEY")
        print("   请在 .env 文件中添加: AIRTABLE_API_KEY=keyXXXXXX")
        print("   获取地址: https://airtable.com/create/tokens")
        return False
    else:
        print(f"✓ AIRTABLE_API_KEY 已设置: {api_key[:10]}...")

    if not base_id:
        print("❌ 未设置 AIRTABLE_BASE_ID")
        print("   请在 .env 文件中添加: AIRTABLE_BASE_ID=appXXXXXX")
        print("   从你的 Airtable Base URL 中获取")
        return False
    else:
        print(f"✓ AIRTABLE_BASE_ID 已设置: {base_id}")

    return True


def test_connections():
    """测试连接"""
    print("\n" + "=" * 60)
    print("2. 测试连接")
    print("=" * 60)

    # 测试 SQLite
    try:
        from poly_data.local_storage import LocalStorage
        storage = LocalStorage()
        stats = storage.get_db_stats()
        print(f"✓ SQLite 连接成功")
        print(f"   数据库大小: {stats.get('db_size_mb', 0)} MB")
        storage.close()
    except Exception as e:
        print(f"❌ SQLite 连接失败: {e}")
        return False

    # 测试 Airtable
    try:
        from poly_data.airtable_client import AirtableClient
        client = AirtableClient()
        stats = client.check_record_count()
        print(f"✓ Airtable 连接成功")
        print(f"   记录数: {stats['total']['count']}/{stats['total']['limit']}")
        print(f"   使用率: {stats['usage_percent']}%")
    except Exception as e:
        print(f"❌ Airtable 连接失败: {e}")
        return False

    return True


def setup_airtable_tables():
    """设置 Airtable 表结构"""
    print("\n" + "=" * 60)
    print("3. 检查 Airtable 表结构")
    print("=" * 60)

    try:
        from pyairtable import Api

        api_key = os.getenv('AIRTABLE_API_KEY')
        base_id = os.getenv('AIRTABLE_BASE_ID')

        api = Api(api_key)
        base = api.base(base_id)

        # 获取所有表
        tables = base.tables()
        table_names = [t.name for t in tables]

        print(f"当前 Base 中的表: {table_names}")

        required_tables = ['Markets', 'Trading Configs', 'Trade Summary', 'Alerts']
        missing_tables = [t for t in required_tables if t not in table_names]

        if missing_tables:
            print(f"\n⚠️  缺少以下表: {missing_tables}")
            print("\n请手动在 Airtable 中创建这些表：")
            print("\n1. Markets 表（字段）:")
            print("   - condition_id (Single line text, Primary)")
            print("   - question (Single line text)")
            print("   - answer1, answer2 (Single line text)")
            print("   - token1, token2 (Single line text)")
            print("   - neg_risk (Checkbox)")
            print("   - best_bid, best_ask (Number)")
            print("   - spread (Number)")
            print("   - gm_reward_per_100 (Percent)")
            print("   - rewards_daily_rate (Number)")
            print("   - volatility_sum (Number)")
            print("   - min_size, max_spread, tick_size (Number)")
            print("   - market_slug (Single line text)")
            print("   - status (Single select: active/ended/paused/archived)")

            print("\n2. Trading Configs 表（字段）:")
            print("   - market (Link to Markets)")
            print("   - condition_id (Lookup from Markets)")
            print("   - question (Lookup from Markets)")
            print("   - trade_size, max_size (Number)")
            print("   - param_type (Single select: conservative/default/aggressive)")
            print("   - enabled (Checkbox)")
            print("   - comments (Long text)")

            print("\n3. Trade Summary 表（字段）:")
            print("   - date (Date)")
            print("   - total_trades, buy_count, sell_count (Number)")
            print("   - total_volume, total_pnl, avg_trade_size (Number)")

            print("\n4. Alerts 表（字段）:")
            print("   - level (Single select: info/warning/error/critical)")
            print("   - message (Single line text)")
            print("   - details (Long text)")
            print("   - related_market (Link to Markets)")
            print("   - acknowledged (Checkbox)")

            return False
        else:
            print(f"✓ 所有必需的表都存在")
            return True

    except Exception as e:
        print(f"❌ 检查表结构失败: {e}")
        return False


def create_sample_data():
    """创建示例数据"""
    print("\n" + "=" * 60)
    print("4. 创建示例数据（可选）")
    print("=" * 60)

    try:
        from poly_data.airtable_client import AirtableClient

        client = AirtableClient()

        # 检查是否已有数据
        markets = client.get_all_markets()
        configs = client.get_trading_configs()

        if len(markets) > 0 or len(configs) > 0:
            print(f"ℹ️  已有数据: {len(markets)} 个市场, {len(configs)} 个配置")
            print("   跳过示例数据创建")
            return True

        print("没有现有数据，你需要：")
        print("1. 运行 data_updater/data_updater.py 获取市场数据")
        print("2. 或使用 update_selected_markets.py 选择交易的市场")

        return True

    except Exception as e:
        print(f"⚠️  检查数据失败: {e}")
        return False


def test_sqlite_operations():
    """测试 SQLite 操作"""
    print("\n" + "=" * 60)
    print("5. 测试 SQLite 写入")
    print("=" * 60)

    try:
        from poly_data.local_storage import LocalStorage

        storage = LocalStorage()

        # 测试写入交易
        test_trade = {
            'condition_id': 'test-init',
            'token_id': 'test-token',
            'side': 'BUY',
            'price': 0.5,
            'size': 100,
            'status': 'PLACED',  # 必须是允许的枚举值之一
            'order_id': 'test-order',
            'market': 'Test Market',
            'notes': 'Initialization test'
        }

        trade_id = storage.log_trade(test_trade)
        print(f"✓ 测试交易写入成功 (ID: {trade_id})")

        # 清理测试数据
        storage.close()

        return True

    except Exception as e:
        print(f"❌ SQLite 写入测试失败: {e}")
        return False


def print_next_steps():
    """打印下一步操作"""
    print("\n" + "=" * 60)
    print("✓ 初始化完成！下一步操作")
    print("=" * 60)
    print("""
1. 获取市场数据：
   python data_updater/data_updater.py

2. 选择要交易的市场（在 Airtable 的 Trading Configs 表中配置）：
   - 打开 Airtable
   - 在 Trading Configs 表中添加记录
   - 关联到 Markets 表中的市场
   - 设置 trade_size, max_size, param_type

3. 或者使用命令行工具选择市场（需要修改以支持 Airtable）

4. 启动交易机器人：
   python main.py

5. 设置每日维护定时任务：
   0 1 * * * python scripts/daily_maintenance.py
""")


def main():
    """主函数"""
    print("=" * 60)
    print("   Airtable + SQLite 系统初始化")
    print("   （从零开始，无需迁移）")
    print("=" * 60)

    steps = [
        ("环境变量检查", check_environment),
        ("连接测试", test_connections),
        ("表结构检查", setup_airtable_tables),
        ("示例数据", create_sample_data),
        ("SQLite 写入测试", test_sqlite_operations),
    ]

    all_passed = True
    for name, func in steps:
        try:
            if not func():
                all_passed = False
                print(f"\n❌ {name} 失败，请修复后重试")
                break
        except Exception as e:
            all_passed = False
            print(f"\n❌ {name} 出错: {e}")
            import traceback
            traceback.print_exc()
            break

    if all_passed:
        print_next_steps()
        print("\n✓ 所有检查通过！系统已准备就绪。")
        return 0
    else:
        print("\n✗ 初始化未完成，请修复上述问题后重试。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
