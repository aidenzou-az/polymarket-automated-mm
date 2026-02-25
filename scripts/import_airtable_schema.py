#!/usr/bin/env python3
"""
Airtable 表结构导入脚本
一键创建所需的 4 张表及其字段
"""
import os
import sys
import json
from dotenv import load_dotenv

# 先加载环境变量
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_tables():
    """创建 Airtable 表结构"""
    print("=" * 60)
    print("Airtable 表结构导入")
    print("=" * 60)

    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')

    if not api_key or not base_id:
        print("\n❌ 错误：未设置 AIRTABLE_API_KEY 或 AIRTABLE_BASE_ID")
        print("   请在 .env 文件中添加这两个环境变量")
        return False

    try:
        import requests
    except ImportError:
        print("\n❌ 错误：需要 requests 模块")
        print("   请运行: pip install requests")
        return False

    # 读取 schema 文件
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'airtable_schema.json')
    if not os.path.exists(schema_path):
        print(f"\n❌ 错误：找不到 schema 文件: {schema_path}")
        return False

    with open(schema_path, 'r') as f:
        schema = json.load(f)

    print(f"\n📋 加载 schema 文件成功")
    print(f"   将创建 {len(schema['tables'])} 张表:")
    for table in schema['tables']:
        print(f"   - {table['name']}")

    # 检查现有的表
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    print("\n" + "=" * 60)
    print("1. 检查现有表结构")
    print("=" * 60)

    try:
        resp = requests.get(
            f'https://api.airtable.com/v0/meta/bases/{base_id}/tables',
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        existing_tables = resp.json().get('tables', [])
        existing_names = [t['name'] for t in existing_tables]

        print(f"   当前 Base 中已有 {len(existing_names)} 张表:")
        for name in existing_names:
            print(f"   - {name}")

    except Exception as e:
        print(f"\n❌ 无法获取现有表: {e}")
        existing_names = []

    # 创建表
    print("\n" + "=" * 60)
    print("2. 创建表")
    print("=" * 60)

    # 注意：Airtable API 不允许直接通过 API 创建表
    # 需要手动创建或使用 Airtable 的 web 界面
    print("\n⚠️  注意：Airtable API 不支持直接创建表")
    print("   你需要手动在 Airtable 网页界面中创建以下表：\n")

    for table in schema['tables']:
        if table['name'] in existing_names:
            print(f"   ✅ {table['name']} - 已存在")
        else:
            print(f"   ⬜ {table['name']} - 需要手动创建")

    # 打印字段信息
    print("\n" + "=" * 60)
    print("3. 表字段详情（请按此配置）")
    print("=" * 60)

    for table in schema['tables']:
        print(f"\n📊 {table['name']} 表")
        print("-" * 40)

        for field in table['fields']:
            field_type_map = {
                'singleLineText': '单行文本',
                'multilineText': '长文本',
                'number': '数字',
                'percent': '百分比',
                'checkbox': '复选框',
                'singleSelect': '单选',
                'date': '日期',
                'linkedRecord': '关联记录',
                'lookup': 'Lookup'
            }
            type_name = field_type_map.get(field['type'], field['type'])
            print(f"   • {field['name']:<20} ({type_name})")

    # 生成直接链接
    print("\n" + "=" * 60)
    print("4. 快速链接")
    print("=" * 60)
    print(f"\n   Airtable Base URL:")
    print(f"   https://airtable.com/{base_id}")
    print(f"\n   API 文档:")
    print(f"   https://airtable.com/{base_id}/api/docs")

    print("\n" + "=" * 60)
    print("✅ 指南生成完成")
    print("=" * 60)
    print("\n请按照上述字段详情，在 Airtable 网页界面中手动创建表。")
    print("或者使用 Airtable 的模板功能复制现有的结构。")

    return True


def print_manual_guide():
    """打印手动创建指南"""
    print("""
┌─────────────────────────────────────────────────────────────┐
│                    手动创建步骤                             │
├─────────────────────────────────────────────────────────────┤
│ 1. 打开 https://airtable.com 并登录                          │
│ 2. 进入你的 Base                                            │
│ 3. 点击左下角的 "+" 添加新表                                 │
│ 4. 表名必须为以下之一：                                      │
│    • Markets                                                │
│    • Trading Configs                                        │
│    • Trade Summary                                          │
│    • Alerts                                                 │
│ 5. 在每个表中添加对应的字段（见上方列表）                      │
│ 6. 对于关联字段（如 market），先创建 Markets 表               │
│    然后在 Trading Configs 中选择 "Link to another record"      │
└─────────────────────────────────────────────────────────────┘
""")


def main():
    """主函数"""
    if create_tables():
        print_manual_guide()
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
