"""
Script to update Hyperparameters sheet with safe trading parameters.

Usage:
    python update_hyperparameters.py --mode conservative  # Safest settings
    python update_hyperparameters.py --mode default       # Balanced settings
    python update_hyperparameters.py --mode aggressive    # Higher risk/reward
    python update_hyperparameters.py --preview            # Just show what would be updated
"""

import pandas as pd
from data_updater.google_utils import get_spreadsheet
from gspread_dataframe import set_with_dataframe
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Recommended parameter sets
PARAMETER_SETS = {
    'conservative': {
        'stop_loss_threshold': -3,
        'take_profit_threshold': 3,
        'spread_threshold': 0.06,
        'vol_window': 30,
        'sleep_period': 2,
        'volatility_threshold': 10,
        'description': 'SAFEST - Wide stops, low volatility threshold, long cooldown'
    },
    'default': {
        'stop_loss_threshold': -2,
        'take_profit_threshold': 2,
        'spread_threshold': 0.05,
        'vol_window': 30,
        'sleep_period': 1,
        'volatility_threshold': 15,
        'description': 'BALANCED - Good starting point for most traders'
    },
    'moderate': {
        'stop_loss_threshold': -1.5,
        'take_profit_threshold': 2,
        'spread_threshold': 0.04,
        'vol_window': 20,
        'sleep_period': 1,
        'volatility_threshold': 20,
        'description': 'MODERATE - Tighter stops, medium risk'
    },
    'aggressive': {
        'stop_loss_threshold': -1.5,
        'take_profit_threshold': 1.5,
        'spread_threshold': 0.04,
        'vol_window': 20,
        'sleep_period': 1,
        'volatility_threshold': 25,
        'description': 'AGGRESSIVE - Tight stops, higher volatility tolerance'
    },
    'very_aggressive': {
        'stop_loss_threshold': -1,
        'take_profit_threshold': 1,
        'spread_threshold': 0.03,
        'vol_window': 15,
        'sleep_period': 0.5,
        'volatility_threshold': 40,
        'description': 'VERY AGGRESSIVE - Maximum risk, tight stops, high volatility'
    }
}


def create_hyperparameter_dataframe(param_sets_to_include):
    """Create a DataFrame with hyperparameters for specified parameter sets."""
    rows = []

    for param_type in param_sets_to_include:
        if param_type not in PARAMETER_SETS:
            print(f"Warning: Unknown parameter type '{param_type}', skipping...")
            continue

        params = PARAMETER_SETS[param_type]

        for param_name, value in params.items():
            if param_name != 'description':
                rows.append({
                    'type': param_type,
                    'param': param_name,
                    'value': value
                })

    return pd.DataFrame(rows)


def update_hyperparameters(mode='default', preview=False, keep_existing=False, auto_confirm=False):
    """
    Update the Hyperparameters sheet with safe trading parameters.

    Args:
        mode: Which parameter set to use ('conservative', 'default', 'aggressive', etc.)
        preview: If True, only show what would be updated without applying
        keep_existing: If True, keep existing custom parameter types and only add missing ones
    """
    print("Connecting to Google Sheets...")
    spreadsheet = get_spreadsheet()

    # Determine which parameter sets to include
    if mode == 'all':
        param_sets = list(PARAMETER_SETS.keys())
        print("\nCreating ALL parameter sets (conservative, default, moderate, aggressive, very_aggressive)")
    else:
        param_sets = [mode]
        print(f"\nCreating '{mode}' parameter set")

    # Show parameter details
    print("\n" + "=" * 100)
    print("PARAMETER SETS TO BE CREATED:")
    print("=" * 100)
    for param_type in param_sets:
        if param_type in PARAMETER_SETS:
            params = PARAMETER_SETS[param_type]
            print(f"\n{param_type.upper()}: {params['description']}")
            print("-" * 100)
            for param_name, value in params.items():
                if param_name != 'description':
                    print(f"  {param_name:25s} = {value}")
    print("=" * 100)

    if preview:
        print("\n[PREVIEW MODE] - Not applying changes. Remove --preview to update the sheet.")
        return

    # Get current hyperparameters
    print("\nLoading current Hyperparameters sheet...")
    hyper_sheet = spreadsheet.worksheet("Hyperparameters")

    try:
        current_df = pd.DataFrame(hyper_sheet.get_all_records())
        print(f"Found {len(current_df)} existing parameter rows")

        if keep_existing and len(current_df) > 0:
            print("Keeping existing custom parameters...")
            # Get existing types
            existing_types = set(current_df['type'].unique())
            # Only create new parameter sets that don't exist
            param_sets = [p for p in param_sets if p not in existing_types]

            if len(param_sets) == 0:
                print("All requested parameter types already exist. Nothing to add.")
                return

            print(f"Adding new parameter types: {param_sets}")
            new_df = create_hyperparameter_dataframe(param_sets)
            combined_df = pd.concat([current_df, new_df], ignore_index=True)
        else:
            print("Replacing all hyperparameters...")
            combined_df = create_hyperparameter_dataframe(param_sets)
    except Exception as e:
        print(f"No existing parameters found or error reading: {e}")
        print("Creating new hyperparameters from scratch...")
        combined_df = create_hyperparameter_dataframe(param_sets)

    # Confirm update
    print(f"\nAbout to update Hyperparameters sheet with {len(combined_df)} parameter rows")
    print("This will affect how your bot trades!")

    if not auto_confirm:
        response = input("\nContinue? [Y/n]: ").strip().upper()
        if response and response != 'Y':
            print("Aborted.")
            return
    else:
        print("\n[Auto-confirmed with --yes flag]")

    # Update the sheet
    print("\nUpdating Hyperparameters sheet...")
    set_with_dataframe(hyper_sheet, combined_df, include_index=False, include_column_header=True, resize=True)

    print(f"\n✓ Successfully updated Hyperparameters sheet!")
    print(f"  Total parameter rows: {len(combined_df)}")
    print(f"  Parameter types: {combined_df['type'].unique().tolist()}")
    print("\nYour bot will use these parameters on the next market refresh (within 60 seconds).")
    print("\nIMPORTANT: Make sure your Selected Markets use param_type that matches one of:")
    for param_type in combined_df['type'].unique():
        print(f"  - {param_type}")


def show_current_parameters():
    """Display current hyperparameters from the sheet."""
    print("Loading current hyperparameters...")
    spreadsheet = get_spreadsheet()
    hyper_sheet = spreadsheet.worksheet("Hyperparameters")

    try:
        current_df = pd.DataFrame(hyper_sheet.get_all_records())

        if len(current_df) == 0:
            print("No hyperparameters found in sheet.")
            return

        print("\n" + "=" * 100)
        print("CURRENT HYPERPARAMETERS:")
        print("=" * 100)

        for param_type in current_df['type'].unique():
            print(f"\n{param_type.upper()}:")
            print("-" * 100)
            type_df = current_df[current_df['type'] == param_type]
            for _, row in type_df.iterrows():
                print(f"  {row['param']:25s} = {row['value']}")
        print("=" * 100)

    except Exception as e:
        print(f"Error reading hyperparameters: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update Hyperparameters sheet with safe trading parameters')
    parser.add_argument('--mode', type=str, default='default',
                       choices=['conservative', 'default', 'moderate', 'aggressive', 'very_aggressive', 'all'],
                       help='Which parameter set to create (default: default)')
    parser.add_argument('--preview', action='store_true',
                       help='Show what would be updated without applying changes')
    parser.add_argument('--keep-existing', action='store_true',
                       help='Keep existing custom parameter types and only add new ones')
    parser.add_argument('--show-current', action='store_true',
                       help='Display current hyperparameters and exit')
    parser.add_argument('--yes', action='store_true',
                       help='Auto-confirm all prompts (for non-interactive use)')

    args = parser.parse_args()

    if args.show_current:
        show_current_parameters()
    else:
        update_hyperparameters(
            mode=args.mode,
            preview=args.preview,
            keep_existing=args.keep_existing,
            auto_confirm=args.yes
        )
