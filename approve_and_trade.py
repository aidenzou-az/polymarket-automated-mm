#!/usr/bin/env python3
"""
Approve USDC and Place Test Order

This script:
1. Approves USDC for trading (one-time requirement)
2. Places a small test order
"""

from dotenv import load_dotenv
from poly_data.polymarket_client import PolymarketClient
from poly_data.gspread import get_spreadsheet
import pandas as pd
import os
from eth_account import Account

load_dotenv()

EXCHANGE_CONTRACT = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
MAX_UINT256 = 2**256 - 1

def main():
    print("🚀 APPROVE USDC AND PLACE ORDER\n")

    client = PolymarketClient()

    # Step 1: Check and approve USDC
    print("Step 1: Checking USDC approval...")
    allowance = client.usdc_contract.functions.allowance(
        client.browser_wallet,
        EXCHANGE_CONTRACT
    ).call()

    if allowance == 0:
        print("❌ USDC not approved. Approving now...\n")

        account = Account.from_key(os.getenv("PK"))
        nonce = client.web3.eth.get_transaction_count(client.browser_wallet)

        approval_tx = client.usdc_contract.functions.approve(
            EXCHANGE_CONTRACT,
            MAX_UINT256
        ).build_transaction({
            'from': client.browser_wallet,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': client.web3.eth.gas_price,
            'chainId': 137
        })

        signed_tx = account.sign_transaction(approval_tx)
        tx_hash = client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"Approval TX: {tx_hash.hex()}")
        print("Waiting for confirmation...")

        receipt = client.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print("✅ USDC approved!\n")
        else:
            print("❌ Approval failed!")
            return
    else:
        print(f"✅ Already approved\n")

    # Step 2: Place order
    print("Step 2: Placing test order...")

    spreadsheet = get_spreadsheet()
    all_markets = pd.DataFrame(spreadsheet.worksheet('All Markets').get_all_records())
    market = all_markets[all_markets['question'] == 'Trump–Putin Meeting in Hungary by Dec 31?'].iloc[0]

    print(f"Market: {market['question']}")
    print(f"Price: ${float(market['best_ask']):.4f}")
    print(f"Size: $20\n")

    result = client.create_order(
        marketId=str(market['token1']),
        action='BUY',
        price=float(market['best_ask']),
        size=20.0,
        neg_risk=False
    )

    if result and 'orderID' in result:
        print(f"✅ ORDER PLACED!")
        print(f"Order ID: {result['orderID']}")
    else:
        print(f"❌ Order failed: {result}")

if __name__ == "__main__":
    main()
