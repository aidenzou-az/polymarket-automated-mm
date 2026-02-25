#!/usr/bin/env python3
"""
Update Markets - Fetches market data from Polymarket and updates Airtable
This is a wrapper around data_updater/data_updater.py
"""

import sys
import os

# Use the main data_updater module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_updater.data_updater import fetch_and_process_data
import traceback
import time

if __name__ == "__main__":
    print("=" * 80)
    print("Market Data Updater")
    print("=" * 80)
    print("\nThis script fetches market data from Polymarket and updates Airtable.")
    print("Running once...\n")

    try:
        fetch_and_process_data()
        print("\n✓ Market data updated successfully!")
        print("  Check Airtable 'Markets' table for results.")
        print("  CSV backups saved to data/ directory.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\nTo run continuously (updating every hour), use:")
    print("  python data_updater/data_updater.py")
