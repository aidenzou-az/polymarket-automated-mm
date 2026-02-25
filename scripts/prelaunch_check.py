#!/usr/bin/env python3
"""
启动前检查脚本 - 验证 Airtable + SQLite 系统是否准备就绪
"""
import os
import sys
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_status(category, item, status, message="", required=True):
    """打印检查状态"""
    if status == "OK":
        symbol = f"{Colors.GREEN}✓{Colors.RESET}"
    elif status == "WARN":
        symbol = f"{Colors.YELLOW}⚠{Colors.RESET}"
    elif status == "FAIL":
        symbol = f"{Colors.RED}✗{Colors.RESET}" if required else f"{Colors.YELLOW}○{Colors.RESET}"
    else:
        symbol = f"{Colors.BLUE}ℹ{Colors.RESET}"

    req_label = "[必需]" if required else "[可选]"
    print(f"  {symbol} [{category}] {item} {req_label}")
    if message:
        print(f"      → {message}")


def check_python_version():
    """检查 Python 版本"""
    print(f"\n{Colors.BLUE}▶ Python 环境{Colors.RESET}")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_status("Python", f"版本 {version.major}.{version.minor}.{version.micro}", "OK")
        return True
    else:
        print_status("Python", f"版本 {version.major}.{version.minor}.{version.micro}", "FAIL", "需要 Python 3.8+")
        return False


def check_dependencies():
    """检查依赖包"""
    print(f"\n{Colors.BLUE}▶ 依赖包检查{Colors.RESET}")
    required = {
        'pandas': '数据分析',
        'py_clob_client': 'Polymarket API',
        'dotenv': '环境变量',
        'pyairtable': 'Airtable 客户端',
    }

    all_ok = True

    for pkg, desc in required.items():
        try:
            __import__(pkg)
            print_status("依赖", f"{pkg} ({desc})", "OK")
        except ImportError:
            print_status("依赖", f"{pkg} ({desc})", "FAIL", f"请运行: pip install {pkg}")
            all_ok = False

    return all_ok


def check_environment_variables():
    """检查环境变量"""
    print(f"\n{Colors.BLUE}▶ 环境变量检查{Colors.RESET}")

    # 必需变量
    required_vars = {
        'PK': 'Polymarket 私钥',
        'AIRTABLE_API_KEY': 'Airtable API Key',
        'AIRTABLE_BASE_ID': 'Airtable Base ID',
    }

    # 可选变量
    optional_vars = {
        'SQLITE_DB_PATH': 'SQLite 路径，默认: data/trading_local.db',
        'DISCORD_WEBHOOK_URL': 'Discord 告警 webhook',
    }

    all_ok = True

    # 检查必需变量
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:6] + "..." if len(value) > 10 else "已设置"
            print_status("必需", f"{var} ({desc})", "OK", f"值: {masked}")
        else:
            print_status("必需", f"{var} ({desc})", "FAIL", "未设置！请在 .env 文件中添加")
            all_ok = False

    # 检查可选变量
    print(f"\n  {Colors.BLUE}可选配置:{Colors.RESET}")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print_status("可选", f"{var}", "OK", f"当前值: {value}", required=False)
        else:
            default = "data/trading_local.db"
            print_status("可选", f"{var}", "WARN", f"使用默认值: {default}", required=False)

    return all_ok


def check_file_structure():
    """检查文件结构"""
    print(f"\n{Colors.BLUE}▶ 文件结构检查{Colors.RESET}")

    required_dirs = {
        'data': '数据目录（SQLite 数据库）',
        'scripts': '脚本目录',
        'poly_data': '核心模块目录',
    }

    required_files = {
        'poly_data/local_storage.py': 'SQLite 存储模块',
        'poly_data/airtable_client.py': 'Airtable 客户端',
        'poly_data/hybrid_storage.py': '混合存储层',
        'scripts/init_new_system.py': '新系统初始化脚本',
        'scripts/daily_maintenance.py': '每日维护脚本',
    }

    all_ok = True

    # 检查目录
    for dirname, desc in required_dirs.items():
        if os.path.isdir(dirname):
            print_status("目录", f"{dirname}/ ({desc})", "OK")
        else:
            print_status("目录", f"{dirname}/ ({desc})", "FAIL", f"请创建目录: mkdir {dirname}")
            all_ok = False

    # 检查文件
    print(f"\n  {Colors.BLUE}必需文件:{Colors.RESET}")
    for filename, desc in required_files.items():
        if os.path.isfile(filename):
            print_status("文件", f"{filename} ({desc})", "OK")
        else:
            print_status("文件", f"{filename} ({desc})", "FAIL", "文件缺失！")
            all_ok = False

    return all_ok


def check_sqlite_setup():
    """检查 SQLite 设置"""
    print(f"\n{Colors.BLUE}▶ SQLite 检查{Colors.RESET}")

    try:
        import sqlite3
        print_status("SQLite", "sqlite3 模块", "OK", f"版本: {sqlite3.sqlite_version}")

        # 测试数据库目录
        db_path = os.getenv('SQLITE_DB_PATH', 'data/trading_local.db')
        db_dir = os.path.dirname(db_path)

        if not os.path.exists(db_dir):
            print_status("SQLite", f"目录 {db_dir}", "FAIL", f"请创建: mkdir {db_dir}")
            return False

        # 测试写入权限
        test_file = os.path.join(db_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print_status("SQLite", f"目录写入权限 ({db_dir})", "OK")
        except Exception as e:
            print_status("SQLite", f"目录写入权限 ({db_dir})", "FAIL", str(e))
            return False

        # 测试数据库连接
        try:
            from poly_data.local_storage import LocalStorage
            storage = LocalStorage()
            stats = storage.get_db_stats()
            print_status("SQLite", "数据库连接", "OK", f"当前大小: {stats.get('db_size_mb', 0)} MB")
            storage.close()
            return True
        except Exception as e:
            print_status("SQLite", "数据库初始化", "FAIL", str(e))
            return False

    except ImportError:
        print_status("SQLite", "sqlite3 模块", "FAIL", "Python 标准库缺失？")
        return False


def check_airtable_setup():
    """检查 Airtable 设置"""
    print(f"\n{Colors.BLUE}▶ Airtable 检查{Colors.RESET}")

    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')

    if not api_key or not base_id:
        print_status("Airtable", "连接", "FAIL", "未配置 API Key 或 Base ID")
        return False

    try:
        from poly_data.airtable_client import AirtableClient
        client = AirtableClient()
        stats = client.check_record_count()

        print_status("Airtable", "API 连接", "OK", f"已用 {stats['usage_percent']}% ({stats['total']['count']}/{stats['total']['limit']} 记录)")

        # 检查表是否存在
        tables_to_check = ['Markets', 'Trading Configs', 'Trade Summary', 'Alerts']
        table_counts = {
            'Markets': stats['markets']['count'],
            'Trading Configs': stats['configs']['count'],
            'Trade Summary': stats['trade_summary']['count'],
            'Alerts': stats['alerts']['count'],
        }

        print(f"\n  {Colors.BLUE}表状态:{Colors.RESET}")
        for table in tables_to_check:
            count = table_counts.get(table, 0)
            print_status("表", f"{table}", "OK", f"{count} 条记录", required=False)

        return True

    except Exception as e:
        print_status("Airtable", "API 连接", "FAIL", str(e))
        return False


def check_network():
    """检查网络连接"""
    print(f"\n{Colors.BLUE}▶ 网络连接检查{Colors.RESET}")

    import socket

    services = {
        'Polymarket API': ('clob.polymarket.com', 443),
        'Airtable API': ('api.airtable.com', 443),
    }

    all_ok = True
    for name, (host, port) in services.items():
        try:
            socket.create_connection((host, port), timeout=5)
            print_status("网络", name, "OK")
        except Exception as e:
            print_status("网络", name, "WARN", f"无法连接: {e}")
            all_ok = False

    return all_ok


def print_summary(results):
    """打印总结"""
    print(f"\n{'=' * 60}")
    print(f"{Colors.BLUE}检查总结{Colors.RESET}")
    print('=' * 60)

    all_passed = all(results.values())

    for check, passed in results.items():
        if passed:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {check}")
        else:
            print(f"  {Colors.RED}✗{Colors.RESET} {check}")

    print()
    if all_passed:
        print(f"{Colors.GREEN}✓ 所有检查通过！系统已准备就绪。{Colors.RESET}")
        print(f"\n下一步:")
        print(f"  1. 运行: python data_updater/data_updater.py")
        print(f"  2. 配置 Trading Configs 表")
        print(f"  3. 启动机器人: python main.py")
    else:
        print(f"{Colors.RED}✗ 部分检查未通过，请修复以上问题后再启动。{Colors.RESET}")

    return all_passed


def main():
    """主函数"""
    print(f"{Colors.BLUE}")
    print("=" * 60)
    print("   Polymarket 交易机器人 - 启动前检查")
    print("   Airtable + SQLite 架构")
    print("=" * 60)
    print(f"{Colors.RESET}")

    results = {
        'Python 版本': check_python_version(),
        '依赖包': check_dependencies(),
        '环境变量': check_environment_variables(),
        '文件结构': check_file_structure(),
        'SQLite': check_sqlite_setup(),
        'Airtable': check_airtable_setup(),
        '网络连接': check_network(),
    }

    passed = print_summary(results)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
