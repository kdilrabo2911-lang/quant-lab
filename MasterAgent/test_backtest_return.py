#!/usr/bin/env python3
"""Test what run_backtest actually returns"""

import asyncio
from action_executor import ActionExecutor

async def main():
    executor = ActionExecutor()

    result = await executor.run_backtest(
        strategy_name="MA_Dip_Buyer2",
        coins=["RNDR"],
        days=30
    )

    print("=" * 80)
    print("BACKTEST RESULT STRUCTURE:")
    print("=" * 80)
    print(f"\nKeys: {result.keys()}")
    print(f"\nSuccess: {result.get('success')}")
    print(f"\nFull result:")
    import json
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
