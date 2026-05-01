#!/usr/bin/env python3
"""
Query backtest results from database
"""
import asyncpg
import asyncio
from pathlib import Path
import os
from dotenv import load_dotenv
import json

# Load environment variables
env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)


async def query_results():
    """Query and display backtest results"""

    db_url = os.getenv("DATABASE_URL") or os.getenv("database_url")
    conn = await asyncpg.connect(db_url)

    try:
        print("\n" + "="*80)
        print("BACKTEST SUMMARY")
        print("="*80)

        # Query summary view
        summary = await conn.fetch("SELECT * FROM backtest_summary ORDER BY run_timestamp DESC LIMIT 10")

        for row in summary:
            print(f"\nRun ID: {row['id']}")
            print(f"  Timestamp: {row['run_timestamp']}")
            print(f"  Strategy: {row['strategy_name']}")
            print(f"  Coins: {', '.join(row['coins'])}")
            print(f"  Period: {row['period_days']} days")
            print(f"  Portfolio Return: {row['portfolio_total_return_pct']:.2f}%")
            print(f"  Portfolio Sharpe: {row['portfolio_sharpe_ratio']:.2f}")
            print(f"  Total Trades: {row['total_trades']}")
            print(f"  Coins Tested: {row['num_coins']}")
            print(f"  Best Coin: {row['best_coin_return_pct']:.2f}%")
            print(f"  Worst Coin: {row['worst_coin_return_pct']:.2f}%")

        print("\n" + "="*80)
        print("COIN-LEVEL RESULTS")
        print("="*80)

        # Query coin results
        coin_results = await conn.fetch("""
            SELECT cr.*, br.strategy_name, br.run_timestamp
            FROM backtest_coin_results cr
            JOIN backtest_runs br ON cr.backtest_run_id = br.id
            ORDER BY br.run_timestamp DESC, cr.total_return_pct DESC
            LIMIT 20
        """)

        for row in coin_results:
            print(f"\n{row['coin']} - {row['strategy_name']} (Run #{row['backtest_run_id']})")
            print(f"  Return: {row['total_return_pct']:.2f}%")
            print(f"  Trades: {row['num_trades']}")
            print(f"  Win Rate: {row['win_rate']*100:.1f}%")
            print(f"  Avg Profit: {row['avg_profit_pct']:.2f}%")
            print(f"  Avg Loss: {row['avg_loss_pct']:.2f}%")
            print(f"  Sharpe: {row['sharpe_ratio']:.2f}")

        print("\n" + "="*80)
        print(f"Total backtest runs in database: {len(summary)}")
        print("="*80 + "\n")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(query_results())
