"""
Market Data Updater - Fetches market data from Polymarket and stores in Airtable + SQLite
"""
# === HTTP Timeout Patch (MUST be before importing py_clob_client) ===
import os
import requests
from functools import wraps

# Configuration from environment variables
CONNECT_TIMEOUT = float(os.getenv('REQUEST_CONNECT_TIMEOUT', '5'))
READ_TIMEOUT = float(os.getenv('REQUEST_READ_TIMEOUT', '15'))
REQUEST_TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

_original_request = requests.request

@wraps(_original_request)
def _patched_request(method, url, **kwargs):
    """Add default timeout to all HTTP requests"""
    if 'timeout' not in kwargs:
        kwargs['timeout'] = REQUEST_TIMEOUT
    return _original_request(method, url, **kwargs)

requests.request = _patched_request

# Also patch Session.request (used internally by third-party libraries)
_original_session_request = requests.Session.request

@wraps(_original_session_request)
def _patched_session_request(self, method, url, **kwargs):
    """Add default timeout to all session requests"""
    if 'timeout' not in kwargs:
        kwargs['timeout'] = REQUEST_TIMEOUT
    return _original_session_request(self, method, url, **kwargs)

requests.Session.request = _patched_session_request
# ===================================================================

import time
import pandas as pd
import sys
import warnings
import json
import traceback
from dotenv import load_dotenv
import concurrent.futures
import numpy as np
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_updater.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
warnings.filterwarnings("ignore")

# Import Airtable client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from poly_data.airtable_client import AirtableClient


def get_clob_client():
    """Create and return Polymarket ClobClient"""
    logger.info("Creating ClobClient")
    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    chain_id = 137

    if key is None:
        logger.error("Environment variable 'PK' not found")
        raise ValueError("PK environment variable is required")

    try:
        from py_clob_client.client import ClobClient
        client = ClobClient(host, key=key, chain_id=chain_id)
        api_creds = client.create_or_derive_api_creds()
        client.set_api_creds(api_creds)
        logger.info(f"ClobClient created successfully")
        return client
    except Exception as ex:
        logger.error(f"Error creating ClobClient: {ex}", exc_info=True)
        raise


def get_all_markets(client):
    """Fetch all markets from Polymarket"""
    logger.info("Fetching all markets from Polymarket")
    cursor = ""
    all_markets = []

    while True:
        try:
            markets = client.get_sampling_markets(next_cursor=cursor)
            markets_df = pd.DataFrame(markets['data'])
            cursor = markets['next_cursor']
            all_markets.append(markets_df)
            logger.info(f"Fetched {len(markets_df)} markets, cursor: {cursor}")

            if cursor is None or cursor == "LTE=":
                break
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            break

    if not all_markets:
        raise ValueError("No markets fetched")

    all_df = pd.concat(all_markets, ignore_index=True)
    logger.info(f"Total markets fetched: {len(all_df)}")
    return all_df


def process_single_row(row, client):
    """Process a single market row"""
    try:
        ret = {
            'question': row['question'],
            'neg_risk': row.get('neg_risk', False),
            'answer1': row['tokens'][0]['outcome'],
            'answer2': row['tokens'][1]['outcome'],
            'min_size': row['rewards']['min_size'],
            'max_spread': row['rewards']['max_spread'],
            'token1': row['tokens'][0]['token_id'],
            'token2': row['tokens'][1]['token_id'],
        }

        # Get reward rate
        rate = 0
        for rate_info in row['rewards']['rates']:
            if rate_info['asset_address'].lower() == '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'.lower():
                rate = rate_info['rewards_daily_rate']
                break
        ret['rewards_daily_rate'] = rate

        # Get order book
        try:
            book = client.get_order_book(ret['token1'])
        except:
            book = type('obj', (object,), {'bids': [], 'asks': []})()

        bids = pd.DataFrame()
        asks = pd.DataFrame()

        try:
            bids = pd.DataFrame(book.bids).astype(float)
        except:
            pass
        try:
            asks = pd.DataFrame(book.asks).astype(float)
        except:
            pass

        # Get best prices
        try:
            ret['best_bid'] = bids.iloc[-1]['price'] if not bids.empty else 0
        except:
            ret['best_bid'] = 0
        try:
            ret['best_ask'] = asks.iloc[0]['price'] if not asks.empty else 0
        except:
            ret['best_ask'] = 0

        ret['midpoint'] = (ret['best_bid'] + ret['best_ask']) / 2
        if ret['midpoint'] == 0 or pd.isna(ret['midpoint']):
            ret['midpoint'] = 0.5
            ret['best_bid'] = 0.49
            ret['best_ask'] = 0.51

        TICK_SIZE = row.get('minimum_tick_size', 0.01)
        ret['tick_size'] = TICK_SIZE

        # Calculate spread
        ret['spread'] = abs(ret['best_ask'] - ret['best_bid'])

        # Calculate rewards
        v = round((ret['max_spread'] / 100), 2)
        mid = ret['midpoint']

        # Simple reward calculation (fixed to handle large distances)
        bid_reward = 0
        ask_reward = 0

        if ret['best_bid'] > 0 and ret['best_ask'] > 0 and v > 0:
            bid_distance = abs(ret['best_bid'] - mid)
            ask_distance = abs(ret['best_ask'] - mid)

            # Use the formula from find_markets.py: ((v - s) / v) ** 2
            # This works even when s > v (result is > 1)
            bid_s = ((v - bid_distance) / v) ** 2
            ask_s = ((v - ask_distance) / v) ** 2

            # Scale by rate (divided by 24 for hourly approximation)
            bid_reward = max(0, bid_s * rate / 24)
            ask_reward = max(0, ask_s * rate / 24)

        ret['bid_reward_per_100'] = round(bid_reward, 2)
        ret['ask_reward_per_100'] = round(ask_reward, 2)
        ret['gm_reward_per_100'] = round((bid_reward * ask_reward) ** 0.5, 2) if bid_reward > 0 and ask_reward > 0 else 0

        ret['end_date_iso'] = row.get('end_date_iso', '')
        ret['market_slug'] = row.get('market_slug', '')
        ret['condition_id'] = row['condition_id']

        return ret

    except Exception as e:
        logger.error(f"Error processing row: {e}")
        return None


def get_all_results(all_df, client, max_workers=5):
    """Process all markets in parallel"""
    logger.info(f"Processing {len(all_df)} markets")
    all_results = []

    def process_with_progress(args):
        idx, row = args
        try:
            result = process_single_row(row, client)
            if result:
                return result
        except Exception as e:
            logger.error(f"Error processing row {idx}: {e}")
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_with_progress, (idx, row)) for idx, row in all_df.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                all_results.append(result)
            if len(all_results) % 100 == 0:
                logger.info(f'Processed {len(all_results)} markets')

    logger.info(f"Successfully processed {len(all_results)} markets")
    return all_results


def calculate_annualized_volatility(df, hours):
    """Calculate annualized volatility"""
    if df.empty:
        return 0
    end_time = df['t'].max()
    start_time = end_time - pd.Timedelta(hours=hours)
    window_df = df[df['t'] >= start_time]
    if window_df.empty:
        return 0
    volatility = window_df['log_return'].std()
    annualized = volatility * np.sqrt(60 * 24 * 252)
    return round(annualized, 2)


def add_volatility(row):
    """Add volatility data to a market row"""
    try:
        res = requests.get(
            f'https://clob.polymarket.com/prices-history?interval=1m&market={row["token1"]}&fidelity=10',
            timeout=10
        )
        price_df = pd.DataFrame(res.json()['history'])
        price_df['t'] = pd.to_datetime(price_df['t'], unit='s')
        price_df['p'] = price_df['p'].round(2)

        # Save to CSV for reference
        price_df.to_csv(f'data/{row["token1"]}.csv', index=False)

        price_df['log_return'] = np.log(price_df['p'] / price_df['p'].shift(1))

        row_dict = row.copy()
        row_dict.update({
            '1_hour': calculate_annualized_volatility(price_df, 1),
            '3_hour': calculate_annualized_volatility(price_df, 3),
            '6_hour': calculate_annualized_volatility(price_df, 6),
            '12_hour': calculate_annualized_volatility(price_df, 12),
            '24_hour': calculate_annualized_volatility(price_df, 24),
            '7_day': calculate_annualized_volatility(price_df, 24 * 7),
            '30_day': calculate_annualized_volatility(price_df, 24 * 30),
            'volatility_price': price_df['p'].iloc[-1] if not price_df.empty else 0
        })

        return row_dict
    except Exception as e:
        logger.error(f"Error adding volatility: {e}")
        return row


def add_volatility_to_df(df, max_workers=3):
    """Add volatility data to all markets"""
    if df.empty:
        return df

    logger.info(f"Adding volatility to {len(df)} markets")
    results = []

    def process_volatility(args):
        idx, row = args
        try:
            return add_volatility(row.to_dict())
        except:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_volatility, (idx, row)) for idx, row in df.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
            if len(results) % 50 == 0:
                logger.info(f'Processed volatility for {len(results)} markets')

    return pd.DataFrame(results)


def sort_df(df):
    """Sort markets by composite score"""
    if df.empty or 'gm_reward_per_100' not in df.columns:
        return df

    logger.info("Sorting by composite score")

    mean_gm = df['gm_reward_per_100'].mean()
    std_gm = df['gm_reward_per_100'].std()
    mean_vol = df['volatility_sum'].mean() if 'volatility_sum' in df.columns else 0
    std_vol = df['volatility_sum'].std() if 'volatility_sum' in df.columns else 1

    df = df.copy()
    df['std_gm'] = (df['gm_reward_per_100'] - mean_gm) / std_gm if std_gm > 0 else 0
    df['std_vol'] = (df['volatility_sum'] - mean_vol) / std_vol if std_vol > 0 else 0

    def proximity_score(value):
        if pd.isna(value):
            return 0
        if 0.1 <= value <= 0.25:
            return (0.25 - value) / 0.15
        elif 0.75 <= value <= 0.9:
            return (value - 0.75) / 0.15
        return 0

    df['bid_score'] = df['best_bid'].apply(proximity_score)
    df['ask_score'] = df['best_ask'].apply(proximity_score)
    df['composite_score'] = df['std_gm'] - df['std_vol'] + df['bid_score'] + df['ask_score']

    sorted_df = df.sort_values(by='composite_score', ascending=False)
    sorted_df = sorted_df.drop(columns=['std_gm', 'std_vol', 'bid_score', 'ask_score', 'composite_score'], errors='ignore')

    return sorted_df


def fetch_and_process_data():
    """Main function to fetch and process market data"""
    try:
        logger.info("=" * 60)
        logger.info("Starting market data update")
        logger.info("=" * 60)

        # Initialize Airtable client
        airtable = AirtableClient()
        logger.info("Airtable client initialized")

        # Get Polymarket client
        client = get_clob_client()

        # Fetch all markets
        all_df = get_all_markets(client)

        # Process markets
        all_results = get_all_results(all_df, client)

        if not all_results:
            raise ValueError("No market results to process")

        # Convert to DataFrame
        new_df = pd.DataFrame(all_results)

        # Add volatility data
        new_df = add_volatility_to_df(new_df)

        # Calculate volatility sum (必须在 add_volatility_to_df 之后)
        if '24_hour' in new_df.columns:
            new_df['volatility_sum'] = new_df.get('24_hour', 0) + new_df.get('7_day', 0) + new_df.get('30_day', 0)
        else:
            new_df['volatility_sum'] = 0

        # Sort
        new_df = sort_df(new_df)

        # Select columns
        cols = ['question', 'answer1', 'answer2', 'spread', 'rewards_daily_rate', 'gm_reward_per_100',
                'min_size', '3_hour', '6_hour', '12_hour', '24_hour', '7_day', '30_day',
                'best_bid', 'best_ask', 'max_spread', 'tick_size',
                'neg_risk', 'market_slug', 'token1', 'token2', 'condition_id']
        new_df = new_df[[col for col in cols if col in new_df.columns]]

        logger.info(f"Final dataset: {len(new_df)} markets")

        # Upsert to Airtable
        logger.info("Updating Airtable Markets...")
        markets_to_upsert = []

        for _, row in new_df.iterrows():
            market = {
                'condition_id': str(row.get('condition_id', '')),
                'question': str(row.get('question', ''))[:200],
                'answer1': str(row.get('answer1', '')),
                'answer2': str(row.get('answer2', '')),
                'token1': str(row.get('token1', '')),
                'token2': str(row.get('token2', '')),
                'neg_risk': bool(row.get('neg_risk', False)),
                'best_bid': float(row.get('best_bid', 0)),
                'best_ask': float(row.get('best_ask', 0)),
                'spread': float(row.get('spread', 0)),
                'gm_reward_per_100': float(row.get('gm_reward_per_100', 0)),
                'rewards_daily_rate': float(row.get('rewards_daily_rate', 0)),
                'volatility_sum': float(row.get('volatility_sum', 0)),
                '1_hour': float(row.get('1_hour', 0)),
                '3_hour': float(row.get('3_hour', 0)),
                '6_hour': float(row.get('6_hour', 0)),
                '12_hour': float(row.get('12_hour', 0)),
                '24_hour': float(row.get('24_hour', 0)),
                '7_day': float(row.get('7_day', 0)),
                '30_day': float(row.get('30_day', 0)),
                'min_size': float(row.get('min_size', 50)),
                'max_spread': float(row.get('max_spread', 1.0)),
                'tick_size': float(row.get('tick_size', 0.01)),
                'market_slug': str(row.get('market_slug', '')),
                'status': 'active'
            }
            markets_to_upsert.append(market)

        if markets_to_upsert:
            result = airtable.upsert_markets_batch(markets_to_upsert)
            logger.info(f"Airtable update: {result.get('success', 0)} success, {result.get('errors', 0)} errors")

        # Save to CSV as backup
        new_df.to_csv('data/all_markets.csv', index=False)
        logger.info("Saved backup to data/all_markets.csv")

        # Log top markets
        logger.info("\nTop 10 Markets:")
        logger.info("\n" + new_df.head(10).to_string(index=False))

        logger.info("=" * 60)
        logger.info("Market data update complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error in fetch_and_process_data: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    while True:
        try:
            fetch_and_process_data()
            logger.info("Sleeping for 1 hour...")
            time.sleep(60 * 60)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            logger.info("Retrying in 5 minutes...")
            time.sleep(5 * 60)
