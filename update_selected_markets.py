#!/usr/bin/env python3
"""
Update Selected Markets: Remove outdated markets and replace with better options.
Supports filtering by minimum daily reward (--min-reward) or profitability-based selection.
"""

import pandas as pd
from data_updater.data_updater import get_spreadsheet
from gspread_dataframe import set_with_dataframe
from dotenv import load_dotenv
from datetime import datetime
import argparse

load_dotenv()

def update_selected_markets(min_daily_reward=None, max_markets=None, replace_existing=False):
    """
    Remove outdated markets and replace with better options.
    
    Args:
        min_daily_reward: If set, filter markets by minimum daily reward (in dollars)
        max_markets: Maximum number of markets to select (default: 5-6 for profitability, 10 for high reward)
        replace_existing: If True, replace all existing markets. If False, append.
    """
    
    print("=" * 100)
    print("UPDATING SELECTED MARKETS")
    print("=" * 100)
    print()
    
    # Connect to Google Sheets
    spreadsheet = get_spreadsheet(read_only=False)
    
    # Load current Selected Markets
    selected_sheet = spreadsheet.worksheet("Selected Markets")
    current_df = pd.DataFrame(selected_sheet.get_all_records())
    
    # Handle empty sheet
    if len(current_df) == 0 or 'question' not in current_df.columns:
        print("Selected Markets sheet is empty or missing columns. Starting fresh.")
        current_df = pd.DataFrame(columns=['question', 'max_size', 'trade_size', 'param_type', 'comments', 'rationale'])
    
    # Ensure rationale column exists for existing markets
    if 'rationale' not in current_df.columns:
        current_df['rationale'] = ''
    
    print(f"Current markets: {len(current_df)}")
    if len(current_df) > 0:
        print("\nCurrent list:")
        for i, row in current_df.iterrows():
            print(f"  {i+1}. {row.get('question', 'N/A')[:70]}")
    print()
    
    # Remove outdated markets (November 11 has passed) - only if we have data
    if len(current_df) > 0 and 'question' in current_df.columns:
        outdated_keywords = ['November 11', 'Nov 11', '2024-11-11']
        before_count = len(current_df)
        
        # Filter out outdated markets
        current_df = current_df[
            ~current_df['question'].str.contains('|'.join(outdated_keywords), case=False, na=False)
        ].copy()
        
        removed_count = before_count - len(current_df)
        if removed_count > 0:
            print(f"✓ Removed {removed_count} outdated market(s)")
        
        # Remove Microsoft markets (wide spreads, not ideal for market making)
        msft_markets = current_df[
            current_df['question'].str.contains('Microsoft|MSFT', case=False, na=False)
        ]
        if len(msft_markets) > 0:
            print(f"✓ Removing {len(msft_markets)} Microsoft market(s) (wide spreads)")
            current_df = current_df[
                ~current_df['question'].str.contains('Microsoft|MSFT', case=False, na=False)
            ].copy()
    
    print(f"\nMarkets after cleanup: {len(current_df)}")
    
    # Determine selection mode
    if min_daily_reward is not None:
        # HIGH REWARD MODE: Filter by minimum daily reward
        print(f"\n{'=' * 100}")
        print(f"HIGH REWARD MODE: Filtering by rewards_daily_rate >= ${min_daily_reward}")
        print("=" * 100)
        
        # Load All Markets (has rewards_daily_rate)
        print("\nLoading markets from 'All Markets' sheet...")
        all_markets_sheet = spreadsheet.worksheet("All Markets")
        source_df = pd.DataFrame(all_markets_sheet.get_all_records())
        
        if source_df.empty:
            print("❌ All Markets sheet is empty!")
            return
        
        print(f"✓ Loaded {len(source_df)} markets from All Markets\n")
        
        # Convert numeric columns
        numeric_cols = ['rewards_daily_rate', 'gm_reward_per_100', 'volatility_sum', 'spread', 
                       'best_bid', 'best_ask', 'min_size', '3_hour']
        for col in numeric_cols:
            if col in source_df.columns:
                source_df[col] = pd.to_numeric(source_df[col], errors='coerce')
        
        # Filter for high reward markets
        print(f"Filtering markets with rewards_daily_rate >= ${min_daily_reward}...")
        filtered = source_df[
            (source_df['rewards_daily_rate'] >= min_daily_reward) &
            (source_df['rewards_daily_rate'].notna())
        ].copy()
        
        if len(filtered) == 0:
            print(f"❌ No markets found with rewards_daily_rate >= ${min_daily_reward}")
            print(f"   Highest reward: ${source_df['rewards_daily_rate'].max():.2f}")
            return
        
        print(f"✓ Found {len(filtered)} markets with rewards >= ${min_daily_reward}/day\n")
        
        # Additional quality filters
        print("Applying quality filters...")
        before_filter = len(filtered)
        
        quality_filters = (
            (filtered['best_bid'] >= 0.1) &
            (filtered['best_bid'] <= 0.9) &
            (filtered['spread'] < 0.15)
        )
        
        if 'volatility_sum' in filtered.columns:
            quality_filters = quality_filters & (filtered['volatility_sum'] < 50)
        
        filtered = filtered[quality_filters].copy()
        
        after_filter = len(filtered)
        if before_filter > after_filter:
            print(f"✓ Filtered to {after_filter} markets after quality checks (removed {before_filter - after_filter})\n")
        
        # Sort by rewards_daily_rate (descending)
        filtered = filtered.sort_values('rewards_daily_rate', ascending=False)
        
        # Get currently selected question names (only filter if not replacing)
        if not replace_existing:
            current_questions = set(current_df['question'].tolist()) if len(current_df) > 0 else set()
            filtered = filtered[~filtered['question'].isin(current_questions)].copy()
        
        # Select top markets
        target_count = max_markets if max_markets else 10
        if replace_existing:
            needed = min(target_count, len(filtered))  # Take up to target_count
        else:
            needed = max(0, min(target_count - len(current_df), len(filtered)))
        
    else:
        # PROFITABILITY MODE: Original logic
        print(f"\n{'=' * 100}")
        print("PROFITABILITY MODE: Selecting markets by reward/volatility ratio")
        print("=" * 100)
        
        # Load Volatility Markets to find better replacements
        vol_sheet = spreadsheet.worksheet("Volatility Markets")
        source_df = pd.DataFrame(vol_sheet.get_all_records())
        
        # Convert numeric columns
        numeric_cols = ['gm_reward_per_100', 'volatility_sum', 'spread', 'rewards_daily_rate',
                       'best_bid', 'best_ask', '3_hour']
        for col in numeric_cols:
            if col in source_df.columns:
                source_df[col] = pd.to_numeric(source_df[col], errors='coerce')
        
        # Calculate profitability score
        source_df['profitability_score'] = source_df['gm_reward_per_100'] / (source_df['volatility_sum'] + 1)
        
        # Get currently selected question names
        current_questions = set(current_df['question'].tolist()) if len(current_df) > 0 else set()
        
        # Filter for good replacement markets:
        # - Reward >= 1.0%
        # - Volatility < 20
        # - Spread < 0.1 (tighter spreads)
        # - Price in reasonable range (0.1-0.9) - easier to manage
        # - Not already selected
        filtered = source_df[
            (source_df['gm_reward_per_100'] >= 1.0) &
            (source_df['volatility_sum'] < 20) &
            (source_df['spread'] < 0.1) &
            (source_df['best_bid'] >= 0.1) &
            (source_df['best_bid'] <= 0.9) &
            (~source_df['question'].isin(current_questions))
        ].copy()
        
        # Sort by profitability score
        filtered = filtered.sort_values('profitability_score', ascending=False)
        
        # Select top markets to replace (aim for 5-6 total markets)
        target_total = max_markets if max_markets else 5
        needed = max(0, target_total - len(current_df))
    
    if needed > 0:
        replacements = filtered.head(needed)
        
        print(f"\n{'=' * 100}")
        print(f"ADDING {len(replacements)} NEW MARKETS:")
        print("=" * 100)
        
        # Prepare new market data
        new_markets = []
        for _, row in replacements.iterrows():
            reward = row.get('gm_reward_per_100', 0)
            volatility = row.get('volatility_sum', 0)
            daily_reward = row.get('rewards_daily_rate', 0)
            min_size = row.get('min_size', 50)
            
            # Determine trade parameters based on market characteristics
            # For high reward markets, use larger sizes
            if min_daily_reward and daily_reward >= 200:
                trade_size = 100
                max_size = 200
                param_type = 'aggressive'
            elif min_daily_reward and daily_reward >= 150:
                trade_size = 80
                max_size = 160
                param_type = 'aggressive'
            elif volatility > 15:
                trade_size = 30
                max_size = 60
                param_type = 'aggressive'
            elif volatility > 10:
                trade_size = 40
                max_size = 80
                param_type = 'default'
            else:
                trade_size = 50
                max_size = 100
                param_type = 'conservative'
            
            # Adjust for very high reward markets (percentage-based)
            if reward > 2.0:
                trade_size = min(trade_size + 10, 60)
                max_size = min(max_size + 20, 120)
            
            # Ensure trade_size >= min_size
            if trade_size < min_size:
                trade_size = min_size
                max_size = max(trade_size * 2, max_size)
            
            # Generate detailed rationale
            rationale_parts = []
            
            # Daily reward (priority for high reward mode)
            if daily_reward >= 200:
                rationale_parts.append(f"Very high daily reward (${daily_reward:.0f}/day)")
            elif daily_reward >= 100:
                rationale_parts.append(f"High daily reward (${daily_reward:.0f}/day)")
            elif daily_reward >= 50:
                rationale_parts.append(f"Good daily reward (${daily_reward:.0f}/day)")
            elif daily_reward >= 10:
                rationale_parts.append(f"Daily reward (${daily_reward:.0f}/day)")
            
            # Percentage reward
            if reward >= 2.0:
                rationale_parts.append(f"High reward ({reward:.2f}% daily)")
            elif reward >= 1.0:
                rationale_parts.append(f"Good reward ({reward:.2f}% daily)")
            
            # Volatility
            if volatility < 10:
                rationale_parts.append(f"Low volatility ({volatility:.1f}) - safer")
            elif volatility < 15:
                rationale_parts.append(f"Moderate volatility ({volatility:.1f})")
            elif volatility < 25:
                rationale_parts.append(f"Higher volatility ({volatility:.1f}) - aggressive")
            
            # Spread
            spread_val = row.get('spread', 0)
            if spread_val < 0.02:
                rationale_parts.append("Tight spread - competitive pricing")
            elif spread_val < 0.05:
                rationale_parts.append("Reasonable spread")
            
            # Price range
            if 0.15 <= row.get('best_bid', 0) <= 0.85:
                rationale_parts.append("Price in optimal range (0.15-0.85)")
            
            # Profitability score (if available)
            if 'profitability_score' in row and pd.notna(row['profitability_score']):
                profitability_score = row['profitability_score']
                if profitability_score > 0.15:
                    rationale_parts.append("Excellent risk/reward ratio")
                elif profitability_score > 0.10:
                    rationale_parts.append("Good risk/reward ratio")
            
            rationale = " | ".join(rationale_parts) if rationale_parts else f"Reward: {reward:.2f}%, Vol: {volatility:.1f}"
            
            # Build comments
            if 'profitability_score' in row and pd.notna(row['profitability_score']):
                comments = f"Reward: {reward:.2f}%, Vol: {volatility:.1f}, Score: {row['profitability_score']:.3f}"
            else:
                comments = f"Reward: ${daily_reward:.0f}/day, Vol: {volatility:.1f}, Spread: {spread_val:.3f}"
            
            new_markets.append({
                'question': row['question'],
                'max_size': max_size,
                'trade_size': trade_size,
                'param_type': param_type,
                'comments': comments,
                'rationale': rationale
            })
            
            print(f"\n{len(new_markets)}. {row['question'][:75]}")
            if min_daily_reward:
                print(f"   Daily Reward: ${daily_reward:.2f} | Volatility: {volatility:.1f} | Spread: {spread_val:.4f}")
            else:
                print(f"   Reward: {reward:.2f}% | Volatility: {volatility:.1f} | "
                      f"Score: {row.get('profitability_score', 0):.3f}")
            print(f"   Price: ${row.get('best_bid', 0):.3f}-${row.get('best_ask', 0):.3f} | "
                  f"Daily Rate: ${daily_reward:.0f}")
            print(f"   Trade Size: ${trade_size} | Max Size: ${max_size} | Param: {param_type}")
        
        # Combine with existing or replace
        new_markets_df = pd.DataFrame(new_markets)
        if replace_existing:
            updated_df = new_markets_df
            print(f"\n✓ Replacing all markets with {len(new_markets)} high-reward markets")
        else:
            updated_df = pd.concat([current_df, new_markets_df], ignore_index=True)
            print(f"\n✓ Added {len(new_markets)} new markets (total: {len(updated_df)})")
    else:
        if replace_existing:
            updated_df = pd.DataFrame(columns=['question', 'max_size', 'trade_size', 'param_type', 'comments', 'rationale'])
            print("\nNo markets found matching criteria")
        else:
            updated_df = current_df
            print("\nNo replacements needed - already have enough good markets")
    
    # Update existing markets with rationale if missing
    # Merge with vol_df to get current metrics for existing markets
    if len(updated_df) > 0:
        # Get questions that need rationale
        questions_needing_rationale = updated_df[
            (updated_df['rationale'].isna()) | (updated_df['rationale'] == '')
        ]['question'].tolist()
        
        if len(questions_needing_rationale) > 0:
            # Match with vol_df to get metrics
            for idx, row in updated_df.iterrows():
                if pd.isna(row.get('rationale', '')) or row.get('rationale', '') == '':
                    # Find matching market in vol_df
                    match = vol_df[vol_df['question'] == row['question']]
                    if len(match) > 0:
                        m = match.iloc[0]
                        reward = m['gm_reward_per_100']
                        volatility = m['volatility_sum']
                        spread = m['spread']
                        
                        rationale_parts = []
                        if reward >= 2.0:
                            rationale_parts.append(f"High reward ({reward:.2f}% daily)")
                        elif reward >= 1.0:
                            rationale_parts.append(f"Good reward ({reward:.2f}% daily)")
                        
                        if volatility < 10:
                            rationale_parts.append(f"Low volatility ({volatility:.1f}) - safer")
                        elif volatility < 15:
                            rationale_parts.append(f"Moderate volatility ({volatility:.1f})")
                        
                        if spread < 0.02:
                            rationale_parts.append("Tight spread - competitive pricing")
                        elif spread < 0.05:
                            rationale_parts.append("Reasonable spread")
                        
                        if 0.15 <= m['best_bid'] <= 0.85:
                            rationale_parts.append("Price in optimal range (0.15-0.85)")
                        
                        if m['rewards_daily_rate'] >= 10:
                            rationale_parts.append(f"High daily rate (${m['rewards_daily_rate']:.0f}/day)")
                        
                        profitability_score = reward / (volatility + 1) if pd.notna(volatility) else 0
                        if profitability_score > 0.15:
                            rationale_parts.append("Excellent risk/reward ratio")
                        elif profitability_score > 0.10:
                            rationale_parts.append("Good risk/reward ratio")
                        
                        updated_df.at[idx, 'rationale'] = " | ".join(rationale_parts) if rationale_parts else f"Reward: {reward:.2f}%, Vol: {volatility:.1f}"
    
    # Ensure all required columns are present
    required_cols = ['question', 'max_size', 'trade_size', 'param_type', 'comments', 'rationale']
    for col in required_cols:
        if col not in updated_df.columns:
            updated_df[col] = ''
    
    # Reorder columns
    updated_df = updated_df[required_cols]
    
    # Update sheet using the same method as data_updater.py
    print(f"\n{'=' * 100}")
    print("UPDATING SELECTED MARKETS SHEET...")
    print("=" * 100)
    
    # Use the same update method as data_updater.py to avoid permission issues
    try:
        # Get existing sheet dimensions
        all_values = selected_sheet.get_all_values()
        existing_num_rows = len(all_values)
        existing_num_cols = len(all_values[0]) if all_values else 0
        
        num_rows, num_cols = updated_df.shape
        max_rows = max(num_rows + 1, existing_num_rows)  # +1 for header
        max_cols = max(num_cols, existing_num_cols)
        
        # Prepare data with padding
        padded_data = pd.DataFrame('', index=range(max_rows), columns=range(max_cols))
        # Add headers
        for j, col in enumerate(updated_df.columns):
            padded_data.iloc[0, j] = col
        # Add data
        padded_data.iloc[1:num_rows+1, :num_cols] = updated_df.values
        
        # Convert to list of lists for gspread
        values = padded_data.values.tolist()
        
        # Update the sheet
        selected_sheet.update('A1', values)
        print(f"✓ Successfully updated sheet with {num_rows} rows and {num_cols} columns")
    except Exception as e:
        print(f"Error updating sheet: {e}")
        # Fallback: try set_with_dataframe without resize
        try:
            from gspread_dataframe import set_with_dataframe
            # Manually set values to avoid resize
            selected_sheet.clear()
            selected_sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())
            print("✓ Updated using fallback method")
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            raise
    
    print(f"\n✓ SUCCESS! Updated Selected Markets")
    print(f"\nFinal market list ({len(updated_df)} markets):")
    for i, row in updated_df.iterrows():
        print(f"  {i+1}. {row['question'][:70]}")
        print(f"     Trade: ${row['trade_size']}, Max: ${row['max_size']}, Param: {row['param_type']}")
        if 'rationale' in row and pd.notna(row['rationale']) and row['rationale'] != '':
            print(f"     Rationale: {row['rationale']}")
        elif 'comments' in row and pd.notna(row['comments']):
            print(f"     {row['comments']}")
        print()
    
    print("\nThe bot will start trading these markets within 60 seconds.")
    print("Monitor with: tail -f main.log")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Update Selected Markets with profitable markets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: Profitability-based selection (5-6 markets)
  python update_selected_markets.py
  
  # High reward mode: Select markets with >= $100/day
  python update_selected_markets.py --min-reward 100
  
  # High reward mode: Select top 15 markets with >= $150/day, replace existing
  python update_selected_markets.py --min-reward 150 --max-markets 15 --replace
        """
    )
    parser.add_argument('--min-reward', type=float, default=None,
                       help='Minimum daily reward in dollars (enables high reward mode)')
    parser.add_argument('--max-markets', type=int, default=None,
                       help='Maximum number of markets to select')
    parser.add_argument('--replace', action='store_true',
                       help='Replace all existing markets instead of appending')
    
    args = parser.parse_args()
    
    update_selected_markets(
        min_daily_reward=args.min_reward,
        max_markets=args.max_markets,
        replace_existing=args.replace
    )


