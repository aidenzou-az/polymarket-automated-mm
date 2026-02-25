"""
Market data utilities - Loads configuration from Airtable
"""
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()


def get_sheet_df():
    """Get market data and configuration from Airtable.

    Returns:
        Tuple of (DataFrame, hyperparams_dict)
    """
    from poly_data.hybrid_storage import get_hybrid_storage

    storage = get_hybrid_storage()

    # Get trading configs
    configs = storage.get_trading_configs()

    if not configs:
        print("Warning: No trading configs found in Airtable")
        return pd.DataFrame(), {}

    # Get active markets
    markets = storage.get_active_markets()

    # Create DataFrame from configs
    df_selected = pd.DataFrame(configs)

    # Create DataFrame from markets
    if markets:
        df_all = pd.DataFrame(markets)

        # Ensure required columns exist
        required_cols = [
            'question', 'answer1', 'answer2', 'spread', 'rewards_daily_rate', 'gm_reward_per_100',
            'min_size', 'best_bid', 'best_ask', 'max_spread', 'tick_size', 'neg_risk',
            'market_slug', 'token1', 'token2', 'condition_id'
        ]
        for col in required_cols:
            if col not in df_all.columns:
                df_all[col] = None
    else:
        # Create minimal DataFrame
        df_all = pd.DataFrame(columns=[
            'question', 'answer1', 'answer2', 'spread', 'rewards_daily_rate', 'gm_reward_per_100',
            'min_size', 'best_bid', 'best_ask', 'max_spread', 'tick_size', 'neg_risk',
            'market_slug', 'token1', 'token2', 'condition_id'
        ])

    # Merge configs with market data
    if len(df_selected) > 0 and len(df_all) > 0:
        df_merged = df_selected.merge(
            df_all,
            left_on='condition_id',
            right_on='condition_id',
            how='left',
            suffixes=('', '_market')
        )
        # Fill missing question from market data
        if 'question_market' in df_merged.columns:
            df_merged['question'] = df_merged['question'].fillna(df_merged['question_market'])
        print(f"Loaded {len(df_merged)} markets from Airtable")
    elif len(df_selected) > 0:
        df_merged = df_selected
        print(f"Loaded {len(df_merged)} markets from Airtable (configs only)")
    else:
        df_merged = pd.DataFrame()
        print("Warning: No markets found in Airtable")

    # Build hyperparams from configs
    hyperparams = {}
    for _, row in df_merged.iterrows():
        param_type = row.get('param_type', 'default')
        if param_type and param_type not in hyperparams:
            hyperparams[param_type] = {}

    print(f"Loaded hyperparameters: {list(hyperparams.keys())}")

    return df_merged, hyperparams
