#!/usr/bin/env python3
"""
Tests for bot_actions.py - Same tests from test_function2.py
Ensures all bot functions work correctly
"""

import asyncio
import sys
from pathlib import Path

# Add MasterAgent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "MasterAgent"))

from bot_actions import BotActions
from strategy_store import Strategy


class TestResult:
    """Simple test result tracker"""

    def __init__(self):
        self.passed = []
        self.failed = []

    def add(self, test_name: str, success: bool, message: str = ""):
        if success:
            self.passed.append(test_name)
            print(f"✅ {test_name}: {message}")
        else:
            self.failed.append(test_name)
            print(f"❌ {test_name}: {message}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"Tests: {len(self.passed)}/{total} passed")
        if self.failed:
            print(f"\nFailed tests:")
            for test in self.failed:
                print(f"  • {test}")
        print(f"{'='*60}\n")
        return len(self.failed) == 0


async def test_1_list_strategies(results: TestResult):
    """Test list_all_strategies()"""
    actions = BotActions()
    response = await actions.list_all_strategies()

    if isinstance(response, str) and len(response) > 0:
        results.add("list_all_strategies", True, f"Got {len(response)} chars")
    else:
        results.add("list_all_strategies", False, "Invalid response")


async def test_2_get_strategy_info(results: TestResult):
    """Test get_strategy_info()"""
    actions = BotActions()

    # Get first strategy
    all_strats = await actions.list_all_strategies()
    if "No strategies" in all_strats:
        results.add("get_strategy_info", True, "Skipped - no strategies")
        return

    # Try to get info (use known strategy name)
    response = await actions.get_strategy_info("MA_Dip_Buyer")

    if isinstance(response, str):
        results.add("get_strategy_info", True, f"Got info: {len(response)} chars")
    else:
        results.add("get_strategy_info", False, "Invalid response")


async def test_3_get_last_backtest(results: TestResult):
    """Test get_last_backtest()"""
    actions = BotActions()
    response = await actions.get_last_backtest()

    if isinstance(response, str):
        results.add("get_last_backtest", True, f"{len(response)} chars")
    else:
        results.add("get_last_backtest", False, "Invalid response")


async def test_4_get_best_backtest(results: TestResult):
    """Test get_best_backtest()"""
    actions = BotActions()
    response = await actions.get_best_backtest()

    if isinstance(response, str):
        results.add("get_best_backtest", True, f"{len(response)} chars")
    else:
        results.add("get_best_backtest", False, "Invalid response")


async def main():
    print("\n" + "="*60)
    print("Testing BotActions (Same as test_function2.py)")
    print("="*60 + "\n")

    results = TestResult()

    # Run tests
    await test_1_list_strategies(results)
    await test_2_get_strategy_info(results)
    await test_3_get_last_backtest(results)
    await test_4_get_best_backtest(results)

    # Summary
    all_passed = results.summary()

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
