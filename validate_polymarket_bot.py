import logging
import os
import time
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY
from web3 import Web3  # For USDC balance check
from discord_webhook import DiscordWebhook  # Optional for alerts
import requests  # For timeout in order book calls

# Prevent running as a pytest test
if 'pytest' in sys.modules:
    print("This script is not meant to be run as a pytest test. Run directly with 'python validate_polymarket_bot.py'.")
    sys.exit(1)

# Setup logging with detailed levels
logging.basicConfig(
    filename='polymarket_validation.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

# Load environment variables
load_dotenv()
private_key = os.getenv('PK') or os.getenv('POLYMARKET_PRIVATE_KEY')
funder_address = os.getenv('BROWSER_ADDRESS') or os.getenv('POLYMARKET_FUNDER_ADDRESS')
discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
polygon_rpc_url = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')

# Constants
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"


def send_discord_alert(message):
    if discord_webhook_url:
        webhook = DiscordWebhook(url=discord_webhook_url, content=message)
        webhook.execute()


def init_client():
    for attempt in range(3):
        try:
            if not private_key or not funder_address:
                raise ValueError("Missing POLYMARKET_PRIVATE_KEY or POLYMARKET_FUNDER_ADDRESS in .env")
            logging.info(f"Initializing client with key: {private_key[:10]}... and funder: {funder_address[:10]}...")
            client = ClobClient(
                host=HOST,
                key=private_key,
                chain_id=CHAIN_ID,
                signature_type=2,
                funder=funder_address
            )
            api_creds = client.create_or_derive_api_creds()
            client.set_api_creds(api_creds)
            logging.info("API credentials set successfully")
            status = client.get_ok()
            logging.info(f"Client API status: {status}")
            return client
        except Exception as e:
            logging.error(f"Client initialization failed (attempt {attempt + 1}/3): {e}", exc_info=True)
            if attempt < 2:
                time.sleep(2 * (2 ** attempt))
            else:
                raise


def check_auth_and_balance(client):
    try:
        w3 = Web3(Web3.HTTPProvider(polygon_rpc_url))
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to Polygon RPC")
        logging.info(f"Connected to Polygon RPC at {polygon_rpc_url}")

        usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=[
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
             "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
             "type": "function"}
        ])
        balance_wei = usdc_contract.functions.balanceOf(funder_address).call()
        balance_usdc = balance_wei / 10 ** 6
        logging.info(f"USDC balance for {funder_address[:10]}...: {balance_usdc} USDC")
        if balance_usdc < 10:
            send_discord_alert(f"Low balance detected! Current: {balance_usdc} USDC. Fund with at least 10 USDC.")
            return False
        return True
    except Exception as e:
        logging.error(f"Authentication/balance check failed: {e}", exc_info=True)
        send_discord_alert(f"Authentication failed: {e}")
        return False


def place_small_trade(client, market_token_id, amount=5, side="buy", price=0.5):
    for attempt in range(3):
        try:
            logging.info(
                f"Attempting trade: {side.upper()} {amount} USDC at {price} for token {market_token_id[:10]}...")
            order_args = OrderArgs(token_id=market_token_id, price=price, size=amount, side=side.upper())
            logging.debug(f"Order args created: {order_args.__dict__}")
            signed_order = client.create_order(order_args)
            logging.debug(f"Signed order: {signed_order}")
            order_book = client.get_order_book(market_token_id)
            if not order_book or not (order_book.bids or order_book.asks):
                raise ValueError(f"Order book for token {market_token_id[:10]} is empty or does not exist")
            resp = client.post_order(signed_order, orderType=OrderType.GTC)
            logging.info(f"Trade response: {resp}")
            if isinstance(resp, dict) and resp.get('status') == 'success':
                send_discord_alert(f"Trade placed: {market_token_id}, {side}, {amount} USDC at {price}")
                return True
            else:
                logging.warning(f"Trade response indicates failure: {resp}")
                return False
        except Exception as e:
            logging.error(f"Trade failed (attempt {attempt + 1}/3): {e}", exc_info=True)
            send_discord_alert(f"Trade failed: {e}")
            if attempt < 2:
                time.sleep(2 * (2 ** attempt))
            else:
                return False


def on_market_update_example(client, market_token_id):
    try:
        logging.info(f"Fetching trades for token {market_token_id[:10]}...")
        trades = client.get_trades(token_id=market_token_id)
        logging.debug(f"Raw trades response: {trades}")
        if trades and len(trades) > 0:
            latest_trade = trades[0]
            logging.info(f"Market update for {market_token_id}: Latest trade price {latest_trade['price']}")
            if float(latest_trade['price']) < 0.6:
                logging.info(f"Triggering trade due to price {latest_trade['price']} < 0.6")
                place_small_trade(client, market_token_id, amount=5, price=float(latest_trade['price']))
        else:
            logging.warning(f"No trades found for {market_token_id}")
    except Exception as e:
        logging.error(f"Error processing market update: {e}", exc_info=True)
        send_discord_alert(f"Market update error: {e}")


def validate_bot():
    logging.info("Starting bot validation process...")
    start_time = time.time()

    # Step 1: Initialize client and check auth/balance
    try:
        client = init_client()
    except Exception as e:
        logging.error(f"Client initialization failed: {e}", exc_info=True)
        return False

    if not check_auth_and_balance(client):
        logging.error("Validation failed: Authentication or balance issue")
        return False

    # Step 2: Load markets with sampling and pagination
    try:
        logging.info("Fetching markets from API with sampling and pagination...")
        all_markets = []
        cursor = ""
        max_pages = 10
        page = 1
        while page <= max_pages:
            logging.info(f"Fetching page {page} with cursor: {cursor or 'None'}")
            try:
                markets_response = client.get_sampling_markets(next_cursor=cursor)
                logging.debug(
                    f"Raw markets response page {page}: {json.dumps(markets_response, indent=2) if isinstance(markets_response, (dict, list)) else str(markets_response)}")
                if markets_response is None:
                    logging.warning(f"No response on page {page}")
                    break
                if isinstance(markets_response, str):
                    try:
                        markets = json.loads(markets_response)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse markets JSON on page {page}: {e}", exc_info=True)
                        break
                else:
                    markets = markets_response.get('data', [])
                all_markets.extend(markets)
                cursor = markets_response.get('next_cursor')
                logging.info(f"Page {page} loaded {len(markets)} markets, total so far: {len(all_markets)}")
                if cursor is None or cursor == "":
                    logging.info("Pagination complete—no more pages or cursor is empty")
                    break
                page += 1
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error fetching page {page} with cursor {cursor}: {e}", exc_info=True)
                break

        if not all_markets:
            logging.error("No markets fetched. Check client/API.")
            return False
        logging.info(f"All markets loaded, total count: {len(all_markets)}")

        for i, market in enumerate(all_markets):
            rate = float(
                str(market.get('rewards', {}).get('rates', [{}])[0].get('rewards_daily_rate', '0')).replace('N/A', '0'))
            question = market.get('question', 'N/A')
            is_old = any(year in question for year in ['2023', '2022', '2021'])
            end_date = market.get('end_date_iso')
            is_expired = end_date and datetime.fromisoformat(end_date[:-1]) < datetime.utcnow()
            logging.info(
                f"Market {i}: active={market.get('active', False)}, closed={market.get('closed', False)}, rewards_daily_rate={rate}, question={question[:50]}, is_old={is_old}, is_expired={is_expired}")
            logging.debug(f"Full market data {i}: {json.dumps(market, indent=2)}")

        # Filter for markets with rewards and valid status
        reward_markets = [m for m in all_markets if m.get('active', False) and not m.get('closed',
                                                                                         False) and not is_old and not is_expired and float(
            str(m.get('rewards', {}).get('rates', [{}])[0].get('rewards_daily_rate', '0')).replace('N/A', '0')) > 0]
        if not reward_markets:
            logging.warning("No markets with rewards_daily_rate > 0 found, using any active market")
            reward_markets = [m for m in all_markets if
                              m.get('active', False) and not m.get('closed', False) and not is_old and not is_expired]
        if not reward_markets:
            logging.error("No active markets available")
            return False

        # Limit to top 5 markets by rewards_daily_rate and verify order books with retries
        valid_markets = []
        reward_markets.sort(key=lambda x: float(
            str(x.get('rewards', {}).get('rates', [{}])[0].get('rewards_daily_rate', '0')).replace('N/A', '0')),
                            reverse=True)
        for market in reward_markets[:5]:  # Check top 5 only
            token_id = market['tokens'][0]['token_id']
            for attempt in range(3):  # Retry up to 3 times
                try:
                    response = requests.get(f"{HOST}/order_book?token_id={token_id}", timeout=10)
                    response.raise_for_status()
                    order_book = json.loads(response.text)
                    if order_book and (order_book.get('bids') or order_book.get('asks')):
                        rate = float(
                            str(market.get('rewards', {}).get('rates', [{}])[0].get('rewards_daily_rate', '0')).replace(
                                'N/A', '0'))
                        valid_markets.append((market, rate))
                        break  # Success, move to next market
                except Exception as e:
                    logging.warning(f"Order book check attempt {attempt + 1}/3 failed for token {token_id[:10]}: {e}")
                    if attempt < 2:
                        time.sleep(2 * (2 ** attempt))  # Exponential backoff: 2s, 4s
                    else:
                        logging.error(f"Order book check failed after 3 attempts for token {token_id[:10]}")
        if not valid_markets:
            logging.warning("No markets with valid order books found, falling back to hardcoded market")
            market_token_id = "114304586861386186441621124384163963092522056897081085884483958561365015034812"  # Example from data_updater.py
            logging.info(f"Using hardcoded live market token ID: {market_token_id}")
        else:
            valid_markets.sort(key=lambda x: x[1], reverse=True)
            liquid_market = valid_markets[0][0]
            market_token_id = liquid_market['tokens'][0]['token_id']
            logging.info(
                f"Selected market with highest rewards_daily_rate: {liquid_market.get('question', 'N/A')}, Token ID: {market_token_id}, active={liquid_market.get('active', False)}, closed={liquid_market.get('closed', False)}, rewards_daily_rate={valid_markets[0][1]}, end_date={liquid_market.get('end_date_iso')}")
    except Exception as e:
        logging.error(f"Failed to load markets: {e}", exc_info=True)
        return False

    # Step 3: Place small trade
    logging.info(f"Preparing to place small trade with token ID: {market_token_id}")
    if not place_small_trade(client, market_token_id):
        logging.error("Validation failed: Trade unsuccessful")
        if valid_markets:
            valid_markets = valid_markets[1:2]  # Try next highest reward market
            for market, rate in valid_markets:
                token_id = market['tokens'][0]['token_id']
                for attempt in range(3):
                    try:
                        response = requests.get(f"{HOST}/order_book?token_id={token_id}", timeout=10)
                        response.raise_for_status()
                        order_book = json.loads(response.text)
                        if order_book and (order_book.get('bids') or order_book.get('asks')):
                            market_token_id = token_id
                            logging.info(
                                f"Switching to market: {market.get('question', 'N/A')}, Token ID: {market_token_id}, rewards_daily_rate={rate}")
                            if place_small_trade(client, market_token_id):
                                break
                    except Exception as e:
                        logging.warning(
                            f"Order book check attempt {attempt + 1}/3 failed for token {token_id[:10]}: {e}")
                        if attempt < 2:
                            time.sleep(2 * (2 ** attempt))
                if place_small_trade(client, market_token_id):
                    break
        else:
            logging.error("Validation failed: Trade unsuccessful with fallback")
            return False

    # Step 4: Simulate subscription (poll for 5 minutes)
    try:
        logging.info("Starting market update simulation (5 minutes)")
        for i in range(30):  # Poll every 10 seconds
            elapsed_time = time.time() - start_time
            logging.info(f"Polling update {i + 1}/30, Elapsed time: {elapsed_time:.1f}s")
            on_market_update_example(client, market_token_id)
            if elapsed_time > 300:  # 5-minute cap
                break
            time.sleep(10)
    except Exception as e:
        logging.error(f"Polling failed: {e}", exc_info=True)
        return False

    logging.info(f"Validation completed successfully in {time.time() - start_time:.1f} seconds!")
    send_discord_alert("Polymarket bot validation passed!")
    return True


if __name__ == "__main__":
    if not validate_bot():
        logging.error("Validation process failed")
        sys.exit(1)