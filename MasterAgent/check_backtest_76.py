#!/usr/bin/env python3
"""Check backtest run 76"""

import asyncio
from db_storage import db_storage

async def main():
    await db_storage.connect()

    # Get run 76
    run = await db_storage.pool.fetchrow("""
        SELECT br.*, bs.portfolio_total_return_pct, bs.total_trades
        FROM backtest_runs br
        LEFT JOIN backtest_summary bs ON br.id = bs.id
        WHERE br.id = 76
    """)

    if run:
        print("Backtest Run 76:")
        print(f"  Strategy: {run['strategy_name']}")
        print(f"  Coins: {run['coins']}")
        print(f"  Return: {run['portfolio_total_return_pct']}%")
        print(f"  Trades: {run['total_trades']}")
    else:
        print("Run 76 not found")

if __name__ == "__main__":
    asyncio.run(main())
