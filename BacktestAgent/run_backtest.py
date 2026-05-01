#!/usr/bin/env python3
"""
Main entry point for running backtests.

Usage:
    python run_backtest.py --strategy ma_trailing --coins BTC ETH --last-days 90
    python run_backtest.py --strategy ma_trailing --coins UNI RENDER TRX --last-days 90
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import pandas as pd
import asyncio

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from common.data_agent_client import DataAgentClient
from orchestrator.backtester_runner import BacktesterRunner
from db.results_saver import save_backtest_to_db


def fetch_data(coins, last_days):
    """Fetch data from DataAgent"""
    print(f"\n[STEP 1] Fetching data for {', '.join(coins)} (last {last_days} days)")
    print("=" * 60)

    client = DataAgentClient()
    data = client.get_data(coins=coins, last_days=last_days)

    for coin, df in data.items():
        print(f"✓ {coin}: {len(df)} candles ({df.index[0]} to {df.index[-1]})")

    return data


def prepare_csv_files(data):
    """Save data to temp CSV files for C++ backtester"""
    print(f"\n[STEP 2] Preparing CSV files for C++ backtester")
    print("=" * 60)

    csv_files = {}

    for coin, df in data.items():
        # Create temp file
        csv_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'_{coin}.csv', delete=False)
        csv_path = csv_file.name

        # Prepare data in format C++ expects
        # Columns: timestamp,open,high,low,close,volume,close_btc
        df_export = df.copy()

        # Rename 'time' to 'timestamp' if needed
        if 'time' in df_export.columns:
            df_export['timestamp'] = df_export['time']
        elif df_export.index.name == 'time' or isinstance(df_export.index, pd.DatetimeIndex):
            df_export['timestamp'] = df_export.index.strftime('%Y-%m-%d %H:%M:%S')

        df_export = df_export[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_btc']]

        # Save to CSV
        df_export.to_csv(csv_path, index=False)
        csv_files[coin] = csv_path

        print(f"✓ {coin}: {csv_path}")

    return csv_files


def run_backtests(strategy, csv_files, parameters=None):
    """Run C++ backtests for all coins"""
    print(f"\n[STEP 3] Running {strategy} backtest")
    if parameters:
        print(f"Parameters: {parameters}")
    print("=" * 60)

    runner = BacktesterRunner()

    if not runner.use_cpp:
        print("[ERROR] C++ backtester not found. Please build it first:")
        print("  cd BacktestAgent && mkdir -p build && cd build && cmake .. && make -j4")
        sys.exit(1)

    results = {}

    for coin, csv_path in csv_files.items():
        print(f"\n--- Running backtest for {coin} ---")
        try:
            result = runner.run(
                strategy=strategy,
                data_file=csv_path,
                coin=coin,
                parameters=parameters
            )
            results[coin] = result

            # Print summary
            print(f"\n{coin} Results:")
            print(f"  Total Return: {result['total_return_pct']:.2f}%")
            print(f"  Trades: {result['num_trades']}")
            print(f"  Win Rate: {result['win_rate']*100:.2f}%")
            print(f"  Sharpe: {result['sharpe_ratio']:.2f}")

        except Exception as e:
            print(f"[ERROR] Failed to run backtest for {coin}: {e}")
            results[coin] = {"error": str(e)}

    return results


def save_results(strategy, results, output_dir):
    """Results are saved to PostgreSQL database - no local files needed"""
    print(f"\n[STEP 4] Results saved to database")
    print("=" * 60)
    print("✓ All backtest results are stored in PostgreSQL database")
    print("✓ Query them using MasterAgent or DataAgent API")
    return None  # No local file created


def print_summary(results):
    """Print final summary"""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for coin, result in results.items():
        if "error" in result:
            print(f"{coin:10s} ERROR: {result['error']}")
        else:
            print(f"{coin:10s} Return: {result['total_return_pct']:8.2f}%  |  "
                  f"Trades: {result['num_trades']:3d}  |  "
                  f"Win Rate: {result['win_rate']*100:5.1f}%  |  "
                  f"Sharpe: {result['sharpe_ratio']:5.2f}")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Run backtests using DataAgent + C++ backtester")

    parser.add_argument("--strategy", required=True,
                        help="Strategy to backtest (any strategy name - auto-detected)")

    parser.add_argument("--coins", nargs="+", required=True,
                        help="Coins to backtest (e.g., BTC ETH UNI)")

    parser.add_argument("--last-days", type=int,
                        help="Backtest last N days")

    parser.add_argument("--start", type=str,
                        help="Start date (YYYY-MM-DD)")

    parser.add_argument("--end", type=str,
                        help="End date (YYYY-MM-DD)")

    parser.add_argument("--output-dir", default="./results",
                        help="Output directory for results")

    parser.add_argument("--param", action="append", dest="params",
                        help="Strategy parameters (key=value format, can be used multiple times)")

    args = parser.parse_args()

    # Parse parameters
    parameters = {}
    if args.params:
        for param in args.params:
            if '=' in param:
                key, value = param.split('=', 1)
                # Try to convert to int or float
                try:
                    if '.' in value:
                        parameters[key] = float(value)
                    else:
                        parameters[key] = int(value)
                except ValueError:
                    parameters[key] = value

    # Validate date arguments
    if not args.last_days and not (args.start and args.end):
        parser.error("Either --last-days or both --start and --end are required")

    try:
        # Step 1: Fetch data
        if args.last_days:
            data = fetch_data(args.coins, args.last_days)
            start_date = datetime.now() - timedelta(days=args.last_days)
            end_date = datetime.now()
        else:
            # TODO: Implement date range fetching
            print("[ERROR] Date range fetching not implemented yet. Use --last-days")
            sys.exit(1)

        # Step 2: Prepare CSV files
        csv_files = prepare_csv_files(data)

        # Step 3: Run backtests
        results = run_backtests(args.strategy, csv_files, parameters=parameters if parameters else None)

        # Step 4: Save to local JSON file
        save_results(args.strategy, results, args.output_dir)

        # Step 5: Save to database
        print(f"\n[STEP 5] Saving to database")
        print("=" * 60)
        try:
            backtest_run_id = asyncio.run(save_backtest_to_db(
                strategy_name=args.strategy,
                coins=args.coins,
                start_date=start_date,
                end_date=end_date,
                results=results,
                strategy_parameters=parameters if parameters else None
            ))
            print(f"✓ Saved to database (Run ID: {backtest_run_id})")
        except Exception as e:
            print(f"[WARNING] Failed to save to database: {e}")
            print("(Results still saved locally)")

        # Print summary
        print_summary(results)

        # Clean up temp files
        import os
        for csv_path in csv_files.values():
            if os.path.exists(csv_path):
                os.remove(csv_path)

        print("✓ Done!\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
