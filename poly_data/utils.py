import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
import time


def get_sheet_df():
    load_dotenv()
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)
    except Exception as e:
        print(f"Warning: Falling back to read-only mode for Google Sheets: {str(e)}")
        client = gspread.Client(auth=None)
    sheet = client.open_by_url(os.getenv("SPREADSHEET_URL"))

    # Selected Markets
    try:
        worksheet = sheet.worksheet("Selected Markets")
        current_headers = worksheet.row_values(1) or []
        required_cols = ['question', 'max_size', 'trade_size', 'param_type', 'comments']
        print(f"Selected Markets raw headers: {current_headers}")
        if current_headers != required_cols:
            print(f"Fixing 'Selected Markets' headers. Expected: {required_cols}")
            worksheet.batch_clear(['A1:E1'])
            worksheet.update('A1:E1', [required_cols])
            time.sleep(2)
            current_headers = worksheet.row_values(1) or []
            print(f"After update, Selected Markets headers: {current_headers}")
        df_selected = pd.DataFrame(worksheet.get_all_records())
        if not all(col in df_selected.columns for col in required_cols):
            print("Warning: 'Selected Markets' sheet is empty or missing required columns. Using empty DataFrame.")
            df_selected = pd.DataFrame(columns=required_cols)
    except Exception as e:
        print(f"Warning: 'Selected Markets' sheet is empty or missing required columns: {str(e)}")
        df_selected = pd.DataFrame(columns=required_cols)

    # All Markets
    try:
        worksheet = sheet.worksheet("All Markets")
        current_headers = worksheet.row_values(1) or []
        required_cols = [
            'question', 'answer1', 'answer2', 'spread', 'rewards_daily_rate', 'gm_reward_per_100',
            'sm_reward_per_100', 'bid_reward_per_100', 'ask_reward_per_100', 'volatility_sum',
            'volatility/reward', 'min_size', '1_hour', '3_hour', '6_hour', '12_hour', '24_hour',
            '7_day', '30_day', 'best_bid', 'best_ask', 'volatility_price', 'max_spread',
            'tick_size', 'neg_risk', 'market_slug', 'token1', 'token2', 'condition_id'
        ]
        print(f"All Markets raw headers: {current_headers}")
        if current_headers != required_cols:
            print(f"Fixing 'All Markets' headers. Expected: {required_cols}")
            worksheet.batch_clear(['A1:AD1'])
            worksheet.update('A1:AD1', [required_cols])
            time.sleep(2)
            current_headers = worksheet.row_values(1) or []
            print(f"After update, All Markets headers: {current_headers}")
        df_all = pd.DataFrame(worksheet.get_all_records())
        if not all(col in df_all.columns for col in required_cols):
            print("Warning: 'All Markets' sheet is empty or missing required columns. Using empty DataFrame.")
            df_all = pd.DataFrame(columns=required_cols)
    except Exception as e:
        print(f"Warning: 'All Markets' sheet is empty or missing required columns: {str(e)}")
        df_all = pd.DataFrame(columns=required_cols)

    # Hyperparameters
    try:
        worksheet = sheet.worksheet("Hyperparameters")
        current_headers = worksheet.row_values(1) or []
        required_cols = ['type', 'param', 'value']
        print(f"Hyperparameters raw headers: {current_headers}")
        if current_headers != required_cols:
            print(f"Fixing 'Hyperparameters' headers. Expected: {required_cols}")
            worksheet.batch_clear(['A1:C1'])
            worksheet.update('A1:C1', [required_cols])
            time.sleep(2)
        df_hyper = pd.DataFrame(worksheet.get_all_records())
        if not all(col in df_hyper.columns for col in required_cols):
            print("Warning: 'Hyperparameters' sheet is empty or missing required columns. Using empty DataFrame.")
            df_hyper = pd.DataFrame(columns=required_cols)
    except Exception as e:
        print(f"Warning: 'Hyperparameters' sheet is empty or missing required columns: {str(e)}")
        df_hyper = pd.DataFrame(columns=['type', 'param', 'value'])

    # Transform hyperparameters DataFrame into nested dictionary
    hyperparams = {}
    current_type = None

    for _, row in df_hyper.iterrows():
        # Update current_type only when we have a non-empty type value
        if row['type'] and str(row['type']).strip():
            current_type = str(row['type']).strip()

        # Skip rows where we don't have a current_type set
        if current_type:
            # Convert numeric values to appropriate types
            value = row['value']
            try:
                # Try to convert to float if it's numeric
                if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                    value = float(value)
                elif isinstance(value, (int, float)):
                    value = float(value)
            except (ValueError, TypeError):
                pass  # Keep as string if conversion fails

            if current_type not in hyperparams:
                hyperparams[current_type] = {}
            hyperparams[current_type][row['param']] = value

    print(f"Loaded hyperparameters: {list(hyperparams.keys())}")

    # Merge Selected Markets with All Markets to get full market details
    if len(df_selected) > 0 and len(df_all) > 0:
        # Merge on 'question' column to get full market data for selected markets
        df_merged = df_selected.merge(df_all, on='question', how='left')
        print(f"Merged {len(df_merged)} selected markets with All Markets data")
        return df_merged, hyperparams
    elif len(df_selected) > 0:
        # If All Markets is empty, just use Selected Markets
        print("Warning: All Markets sheet is empty, using Selected Markets only")
        return df_selected, hyperparams
    else:
        # No selected markets
        print("Warning: No markets selected in Selected Markets sheet")
        return pd.DataFrame(), hyperparams