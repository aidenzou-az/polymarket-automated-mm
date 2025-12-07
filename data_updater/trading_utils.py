from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY
from web3 import Web3
import json
from dotenv import load_dotenv
import time
import os

MAX_INT = 2 ** 256 - 1


def get_clob_client():
    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    chain_id = POLYGON

    if key is None:
        print("Environment variable 'PK' cannot be found")
        return None

    try:
        client = ClobClient(host, key=key, chain_id=chain_id)
        api_creds = client.create_or_derive_api_creds()
        client.set_api_creds(api_creds)
        return client
    except Exception as ex:
        print(f"Error creating clob client: {ex}")
        return None


def market_action(marketId, action, price, size):
    if os.getenv("DRY_RUN") == "true":
        print(f"DRY_RUN: Skipping market_action for marketId={marketId}, action={action}, price={price}, size={size}")
        return
    order_args = OrderArgs(
        price=price,
        size=size,
        side=action,
        token_id=marketId,
    )
    signed_order = get_clob_client().create_order(order_args)

    try:
        resp = get_clob_client().post_order(signed_order)
        print(resp)
    except Exception as ex:
        print(f"Error posting order: {ex}")


def get_position(marketId):
    client = get_clob_client()
    if not client:
        return 0
    try:
        position_res = client.get_balance_allowance(
            BalanceAllowanceParams(
                asset_type=AssetType.CONDITIONAL,
                token_id=marketId
            )
        )
        orderBook = client.get_order_book(marketId)
        price = float(orderBook.bids[-1].price) if orderBook.bids else 0
        shares = int(position_res['balance']) / 1e6
        return shares * price
    except Exception as ex:
        print(f"Error getting position: {ex}")
        return 0


# Disabled to prevent transactions with $0 balance
def approveContracts():
    print("approveContracts disabled in DRY_RUN mode")
    return