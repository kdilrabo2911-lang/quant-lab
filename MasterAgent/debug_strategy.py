#!/usr/bin/env python3
"""Debug MA_Dip_Buyer2 strategy to see what's wrong"""

import asyncio
from strategy_store import get_store

async def main():
    store = get_store()
    await store.connect()

    strategy = await store.get("MA_Dip_Buyer2")

    if not strategy:
        print("Strategy not found!")
        return

    print(f"Strategy: {strategy.name}")
    print(f"Parameters: {strategy.parameters}")
    print(f"Parameters type: {type(strategy.parameters)}")

    print(f"\nBuy Conditions ({len(strategy.buy_conditions)}):")
    for i, c in enumerate(strategy.buy_conditions):
        print(f"  [{i}] {c}")
        print(f"      Type: {type(c)}")

    print(f"\nSell Conditions ({len(strategy.sell_conditions)}):")
    for i, c in enumerate(strategy.sell_conditions):
        print(f"  [{i}] {c}")
        print(f"      Type: {type(c)}")

if __name__ == "__main__":
    asyncio.run(main())
