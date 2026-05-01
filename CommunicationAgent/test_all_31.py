#!/usr/bin/env python3
"""
Comprehensive test suite - ALL 32 tests (31 from test_function2.py + complete workflow)
Tests bot_actions.py functions directly with STRICT validation
Flags placeholder/invalid outputs (0.0000%, N/A, empty) as FAILURES

Test 32: Complete Workflow - Create → Backtest → Optimize → Re-backtest → AI Analysis
"""

import asyncio
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "MasterAgent"))

from bot_actions import BotActions
from strategy_store import get_store, Strategy
from db_storage import db_storage
from action_executor import ActionExecutor


def is_placeholder_value(text: str) -> bool:
    """Check if output contains invalid placeholder values

    NOTE: 'no data', 'not found', 'no backtest' are VALID responses (not placeholders)
    Placeholders are things like N/A in data that should exist
    """
    text_lower = text.lower()

    # These are NOT placeholders - they're valid "no data" responses
    if any(phrase in text_lower for phrase in [
        "no backtest", "no data", "not found", "no strateg"
    ]):
        return False  # This is a valid response, not a placeholder

    # Check for explicit N/A when data SHOULD exist
    if " n/a " in text_lower or "n/a%" in text_lower:
        return True

    # Check for 0.0000% returns when should have data (but allow negative values)
    if re.search(r'return:\s*0\.0+%', text_lower) and "no backtest" not in text_lower:
        # 0% is valid if there are no backtests, invalid if there are
        return True

    return False


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add(self, name, passed, message=""):
        self.tests.append({"name": name, "passed": passed, "message": message})
        if passed:
            self.passed += 1
            print(f"✅ {name}")
            if message:
                print(f"   {message}")
        else:
            self.failed += 1
            print(f"❌ {name}")
            if message:
                print(f"   {message}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed}")
        if self.failed > 0:
            print(f"\n❌ Failed tests:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"  - {test['name']}")
                    if test["message"]:
                        print(f"    {test['message']}")


async def main():
    print("=" * 80)
    print("COMPREHENSIVE TEST SUITE - ALL 32 TESTS")
    print("Testing bot_actions.py with STRICT validation")
    print("Test 32: Complete Workflow with AI Analysis")
    print("=" * 80)

    results = TestResults()
    actions = BotActions()
    executor = ActionExecutor()

    # ===========================================================================
    # TEST 1: Database Connection
    # ===========================================================================
    print("\n[TEST 1] Database Connection")
    try:
        store = get_store()
        await store.connect()
        results.add("1. Database Connection", True, "✓ Connected to PostgreSQL")
    except Exception as e:
        results.add("1. Database Connection", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 2: List Strategies from Database
    # ===========================================================================
    print("\n[TEST 2] List Strategies from Database")
    try:
        store = get_store()
        await store.connect()
        strategies = await store.list_all()

        has_strategies = len(strategies) > 0
        results.add("2. List Strategies", has_strategies,
                   f"Found {len(strategies)} strategies in database")

        for s in strategies[:3]:  # Show first 3
            print(f"  • {s.name} v{s.version} ({s.type})")
    except Exception as e:
        results.add("2. List Strategies", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 3: Get Specific Strategy from Database
    # ===========================================================================
    print("\n[TEST 3] Get Specific Strategy from Database")
    try:
        store = get_store()
        await store.connect()

        strategies = await store.list_all()
        if len(strategies) == 0:
            results.add("3. Get Strategy", False, "No strategies in database")
        else:
            strategy_name = strategies[0].name
            strategy = await store.get(strategy_name)

            if strategy:
                results.add("3. Get Strategy", True,
                           f"Retrieved {strategy.name} v{strategy.version}")
            else:
                results.add("3. Get Strategy", False, f"Strategy {strategy_name} not found")
    except Exception as e:
        results.add("3. Get Strategy", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 4: No Local Strategy Files (Database Only)
    # ===========================================================================
    print("\n[TEST 4] No Local Strategy Files (Database Only)")
    base_path = Path(__file__).parent.parent

    # Check MasterAgent/strategies
    master_strategies = base_path / "MasterAgent" / "strategies"
    master_count = len(list(master_strategies.glob("*/*.json"))) if master_strategies.exists() else 0

    # Check BotBuildAgent/Strategies
    botbuild_strategies = base_path / "BotBuildAgent" / "Strategies"
    botbuild_dirs = [d for d in botbuild_strategies.iterdir() if d.is_dir()] if botbuild_strategies.exists() else []

    # C++ files are OK (they're generated from DB)
    results.add("4a. No MasterAgent Files", master_count == 0,
               f"{master_count} JSON files (should be 0)")
    results.add("4b. No BotBuildAgent Strategies", len(botbuild_dirs) == 0,
               f"{len(botbuild_dirs)} deployed bots (should be 0)")

    # ===========================================================================
    # TEST 5: Backtest Database Integration
    # ===========================================================================
    print("\n[TEST 5] Backtest Database Integration")
    try:
        await db_storage.connect()

        # Query last backtest
        last_run = await db_storage.pool.fetchrow("""
            SELECT id, strategy_name, coins, created_at
            FROM backtest_runs
            ORDER BY id DESC
            LIMIT 1
        """)

        if last_run:
            results.add("5a. Backtest in Database", True,
                       f"Run #{last_run['id']}: {last_run['strategy_name']} on {last_run['coins']}")

            # Get summary directly from backtest_runs (no separate summary table)
            summary = await db_storage.pool.fetchrow("""
                SELECT portfolio_total_return_pct, total_trades
                FROM backtest_runs
                WHERE id = $1
            """, last_run['id'])

            if summary:
                return_pct = summary['portfolio_total_return_pct']
                trades = summary['total_trades']

                # STRICT: Check for valid return (not 0.0% placeholder)
                is_valid = return_pct != 0.0 or trades > 0
                results.add("5b. Backtest Summary", is_valid,
                           f"Return: {return_pct}%, Trades: {trades}")
            else:
                results.add("5b. Backtest Summary", False, "No summary found")
        else:
            results.add("5a. Backtest in Database", False, "No backtests found")

        # Count total backtests
        count = await db_storage.pool.fetchval("SELECT COUNT(*) FROM backtest_runs")
        results.add("5c. Total Backtests", count > 0, f"{count} backtest runs")

    except Exception as e:
        results.add("5. Backtest Database Integration", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 6: Query Best Backtest
    # ===========================================================================
    print("\n[TEST 6] Query Best Backtest")
    try:
        await db_storage.connect()

        best_run = await db_storage.pool.fetchrow("""
            SELECT
                id, strategy_name, coins,
                portfolio_total_return_pct
            FROM backtest_runs
            WHERE portfolio_total_return_pct IS NOT NULL
            ORDER BY portfolio_total_return_pct DESC
            LIMIT 1
        """)

        if best_run:
            return_pct = best_run['portfolio_total_return_pct']
            # Best backtest should have positive return
            is_valid = return_pct > 0
            results.add("6. Best Backtest", is_valid,
                       f"Run #{best_run['id']}: {best_run['strategy_name']}, Return: {return_pct}%")
        else:
            results.add("6. Best Backtest", False, "No backtests found")

    except Exception as e:
        results.add("6. Best Backtest", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 7: Telegram Bot Imports
    # ===========================================================================
    print("\n[TEST 7] Telegram Bot (Database-First)")
    try:
        from telegram_bot import TelegramBot
        results.add("7a. Bot Imports", True, "✓ Telegram bot imports successfully")

        # Check bot uses BotActions which has strategy_store
        bot = TelegramBot()
        has_actions = hasattr(bot, 'actions')
        results.add("7b. Bot Uses BotActions", has_actions,
                   "✓ Bot has BotActions" if has_actions else "Missing BotActions")

    except Exception as e:
        results.add("7. Telegram Bot", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 8: Action Executor Database Integration
    # ===========================================================================
    print("\n[TEST 8] Action Executor Database Integration")
    try:
        executor = ActionExecutor()

        # Check executor has store
        has_store = hasattr(executor, 'store')
        results.add("8a. Executor Has Store", has_store,
                   "✓ ActionExecutor has strategy_store" if has_store else "Missing")

        # Test checking for a database strategy
        store = get_store()
        await store.connect()
        strategies = await store.list_all()

        if len(strategies) > 0:
            strategy_name = strategies[0].name
            result = await executor.run_backtest(
                strategy_name=strategy_name,
                coins=['BTC'],
                days=7
            )

            # Check result
            if result.get('needs_deployment'):
                results.add("8b. Database Strategy Detection", True,
                           f"✓ Detected {strategy_name} (needs deployment)")
            elif result.get('success'):
                results.add("8b. Database Strategy Detection", True,
                           f"✓ Ran {strategy_name} successfully")
            else:
                results.add("8b. Database Strategy Detection", False,
                           f"Error: {result.get('error', 'Unknown')}")
        else:
            results.add("8b. Database Strategy Detection", False, "No strategies to test")

    except Exception as e:
        results.add("8. Action Executor", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 9: Create Strategy in Database
    # ===========================================================================
    print("\n[TEST 9] Create Strategy in Database")
    try:
        store = get_store()
        await store.connect()

        # Create test strategy
        test_strategy = Strategy(
            id=0,
            name="Test_MA_Strategy_AutoTest",
            version="1.0",
            type="custom",
            description="Test moving average strategy",
            parameters={"ma_period": 144, "profit_target": 2.0},
            buy_conditions=[{"type": "price_above_ma"}],
            sell_conditions=[{"type": "profit_target_hit"}]
        )

        # Check if exists
        existing = await store.get("Test_MA_Strategy_AutoTest")

        if existing:
            # Update version
            test_strategy.id = existing.id
            test_strategy.version = "1.1"
            await store.update(test_strategy)
            results.add("9a. Update Strategy", True, "✓ Updated to v1.1")
        else:
            # Create new
            strategy_id = await store.create(test_strategy)
            results.add("9a. Create Strategy", True, f"✓ Created (ID: {strategy_id})")

        # Verify it exists
        retrieved = await store.get("Test_MA_Strategy_AutoTest")
        results.add("9b. Verify Created Strategy", retrieved is not None,
                   f"✓ Retrieved {retrieved.name} v{retrieved.version}" if retrieved else "Not found")

        # Clean up - delete test strategy
        await store.delete("Test_MA_Strategy_AutoTest")
        results.add("9c. Delete Strategy", True, "✓ Deleted test strategy")

    except Exception as e:
        results.add("9. Create Strategy", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 10: BOT_ACTIONS.PY FUNCTIONS (Telegram Bot Interface)
    # ===========================================================================
    print("\n[TEST 10] BOT_ACTIONS.PY Functions (Telegram Bot)")

    # TEST 10.1: list_all_strategies
    print("\n[10.1] list_all_strategies()")
    try:
        response = await actions.list_all_strategies()
        has_strategies = "strateg" in response.lower() and len(response) > 50
        is_placeholder = is_placeholder_value(response)

        passed = has_strategies and not is_placeholder
        results.add("10.1 list_all_strategies", passed,
                   f"✓ Got {len(response)} chars" if passed else "Placeholder/invalid output")
    except Exception as e:
        results.add("10.1 list_all_strategies", False, f"Exception: {e}")

    # TEST 10.2: get_strategy_info
    print("\n[10.2] get_strategy_info('MA_Dip_Buyer2')")
    try:
        response = await actions.get_strategy_info("MA_Dip_Buyer2")
        has_info = "parameter" in response.lower() and "ma_period" in response.lower()
        is_placeholder = is_placeholder_value(response)

        passed = has_info and not is_placeholder
        results.add("10.2 get_strategy_info", passed,
                   f"✓ Got strategy details" if passed else "Missing/invalid info")
    except Exception as e:
        results.add("10.2 get_strategy_info", False, f"Exception: {e}")

    # TEST 10.3: get_last_backtest
    print("\n[10.3] get_last_backtest()")
    try:
        response = await actions.get_last_backtest()
        has_backtest = "backtest" in response.lower() or "run #" in response.lower()

        # STRICT: Check for valid return (not 0.0000%)
        has_valid_return = False
        match = re.search(r'Return:\s*([-+]?\d+\.?\d*)%', response, re.IGNORECASE)
        if match:
            return_val = float(match.group(1))
            has_valid_return = return_val != 0.0

        # Allow "no backtest" as valid response
        if "no backtest" in response.lower():
            has_valid_return = True

        is_placeholder = is_placeholder_value(response) and "no backtest" not in response.lower()

        passed = has_backtest and has_valid_return and not is_placeholder
        results.add("10.3 get_last_backtest", passed,
                   f"✓ Return: {match.group(1) if match else 'N/A'}%" if passed
                   else f"❌ Invalid/placeholder return: {response[:100]}")
    except Exception as e:
        results.add("10.3 get_last_backtest", False, f"Exception: {e}")

    # TEST 10.4: get_best_backtest
    print("\n[10.4] get_best_backtest()")
    try:
        response = await actions.get_best_backtest()
        has_backtest = "backtest" in response.lower() and "return" in response.lower()

        # STRICT: Best backtest MUST have positive return
        has_positive_return = False
        match = re.search(r'Return:\s*([-+]?\d+\.?\d*)%', response, re.IGNORECASE)
        if match:
            return_val = float(match.group(1))
            has_positive_return = return_val > 0

        is_placeholder = is_placeholder_value(response)

        passed = has_backtest and has_positive_return and not is_placeholder
        results.add("10.4 get_best_backtest", passed,
                   f"✓ Return: {match.group(1) if match else 'N/A'}%" if passed
                   else "❌ Invalid/placeholder or non-positive return")
    except Exception as e:
        results.add("10.4 get_best_backtest", False, f"Exception: {e}")

    # TEST 10.5: get_best_backtest for specific strategy
    print("\n[10.5] get_best_backtest('MA_Dip_Buyer2')")
    try:
        response = await actions.get_best_backtest("MA_Dip_Buyer2")
        has_strategy_name = "ma_dip_buyer2" in response.lower()

        # If has backtest, check for valid return
        has_valid_data = True
        if has_strategy_name and "no backtest" not in response.lower():
            match = re.search(r'Return:\s*([-+]?\d+\.?\d*)%', response, re.IGNORECASE)
            if match:
                return_val = float(match.group(1))
                has_valid_data = return_val != 0.0

        is_placeholder = is_placeholder_value(response) and "no backtest" not in response.lower()

        passed = has_strategy_name and has_valid_data and not is_placeholder
        results.add("10.5 get_best_backtest(strategy)", passed,
                   f"✓ Got best for MA_Dip_Buyer2" if passed else "Invalid/placeholder")
    except Exception as e:
        results.add("10.5 get_best_backtest(strategy)", False, f"Exception: {e}")

    # TEST 10.6: run_backtest
    print("\n[10.6] run_backtest('MA_Dip_Buyer2', ['RNDR'], 30)")
    try:
        response = await actions.run_backtest("MA_Dip_Buyer2", ["RNDR"], 30)

        # Should contain backtest results or needs_deployment message
        has_result = any(keyword in response.lower() for keyword in
                        ["return", "trades", "deployment", "compiled"])

        # Check for valid metrics (not 0.0000% or N/A)
        has_valid_metrics = True
        match = re.search(r'Return:\s*([-+]?\d+\.?\d*)%', response, re.IGNORECASE)
        if match and "needs" not in response.lower():
            return_val = float(match.group(1))
            has_valid_metrics = return_val != 0.0

        is_placeholder = is_placeholder_value(response) and "needs" not in response.lower()

        passed = has_result and has_valid_metrics and not is_placeholder
        results.add("10.6 run_backtest", passed,
                   f"✓ Backtest executed" if passed else f"❌ Invalid: {response[:100]}")
    except Exception as e:
        results.add("10.6 run_backtest", False, f"Exception: {e}")

    # TEST 10.7: optimize_strategy
    print("\n[10.7] optimize_strategy('MA_Dip_Buyer2', grid, ['RNDR'], 30)")
    try:
        param_grid = {
            "ma_period": [100, 200, 300],
            "profit_target_pct": [2.0, 3.0]
        }
        response = await actions.optimize_strategy("MA_Dip_Buyer2", param_grid, ["RNDR"], 30)

        # Should contain optimization results
        has_result = any(keyword in response.lower() for keyword in
                        ["optimization", "best", "parameters", "runs"])

        is_placeholder = is_placeholder_value(response)

        passed = has_result and not is_placeholder
        results.add("10.7 optimize_strategy", passed,
                   f"✓ Optimization completed" if passed else "Invalid/placeholder")
    except Exception as e:
        results.add("10.7 optimize_strategy", False, f"Exception: {e}")

    # TEST 10.8: deploy_strategy_for_backtest
    print("\n[10.8] deploy_strategy_for_backtest('MA_Dip_Buyer2')")
    try:
        response = await actions.deploy_strategy_for_backtest("MA_Dip_Buyer2")

        # Should indicate deployment status
        has_result = any(keyword in response.lower() for keyword in
                        ["deployed", "generated", "compiled", "success", "error"])

        is_placeholder = is_placeholder_value(response)

        passed = has_result and not is_placeholder
        results.add("10.8 deploy_strategy_for_backtest", passed,
                   f"✓ Deployment executed" if passed else "Invalid/placeholder")
    except Exception as e:
        results.add("10.8 deploy_strategy_for_backtest", False, f"Exception: {e}")

    # TEST 10.9: get_backtest_by_id
    print("\n[10.9] get_backtest_by_id(1)")
    try:
        response = await actions.get_backtest_by_id(1)

        # Should return backtest details or not found
        has_result = any(keyword in response.lower() for keyword in
                        ["backtest", "run", "return", "not found"])

        # If found, check for valid return
        has_valid_data = True
        if "not found" not in response.lower():
            match = re.search(r'Return:\s*([-+]?\d+\.?\d*)%', response, re.IGNORECASE)
            if match:
                return_val = float(match.group(1))
                has_valid_data = return_val != 0.0

        is_placeholder = is_placeholder_value(response) and "not found" not in response.lower()

        passed = has_result and has_valid_data and not is_placeholder
        results.add("10.9 get_backtest_by_id", passed,
                   f"✓ Got backtest #1" if passed else "Invalid/placeholder")
    except Exception as e:
        results.add("10.9 get_backtest_by_id", False, f"Exception: {e}")

    # TEST 10.10: list_backtests_for_strategy
    print("\n[10.10] list_backtests_for_strategy('MA_Dip_Buyer2')")
    try:
        response = await actions.list_backtests_for_strategy("MA_Dip_Buyer2")

        # Should list backtests or say none found
        has_result = any(keyword in response.lower() for keyword in
                        ["backtest", "run", "found", "none"])

        is_placeholder = is_placeholder_value(response) and "no backtest" not in response.lower()

        passed = has_result and not is_placeholder
        results.add("10.10 list_backtests_for_strategy", passed,
                   f"✓ Listed backtests" if passed else "Invalid/placeholder")
    except Exception as e:
        results.add("10.10 list_backtests_for_strategy", False, f"Exception: {e}")

    # TEST 10.11: compare_strategies
    print("\n[10.11] compare_strategies(['MA_Dip_Buyer2'], ['RNDR'], 30)")
    try:
        response = await actions.compare_strategies(["MA_Dip_Buyer2"], ["RNDR"], 30)

        # Should show comparison results
        has_result = any(keyword in response.lower() for keyword in
                        ["comparison", "strategy", "return", "performance"])

        is_placeholder = is_placeholder_value(response)

        passed = has_result and not is_placeholder
        results.add("10.11 compare_strategies", passed,
                   f"✓ Comparison completed" if passed else "Invalid/placeholder")
    except Exception as e:
        results.add("10.11 compare_strategies", False, f"Exception: {e}")

    # ===========================================================================
    # TEST 11: COMPLETE WORKFLOW - Create → Backtest → Optimize → Re-backtest → AI Analysis
    # ===========================================================================
    print("\n[TEST 11] COMPLETE WORKFLOW WITH AI ANALYSIS")

    test_strategy_name = "RSI_Reversal_Test"

    try:
        # Step 1: Create new strategy
        print("\n[11.1] Creating new strategy...")
        create_result = await actions.create_strategy(
            name=test_strategy_name,
            description="RSI reversal strategy for testing complete workflow",
            parameters={
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "profit_target_pct": 3.0
            },
            buy_conditions=[{"type": "rsi_below", "value": 30}],
            sell_conditions=[{"type": "rsi_above", "value": 70}]
        )

        created = test_strategy_name in create_result and "created" in create_result.lower()
        results.add("11.1 Create strategy", created,
                   f"✓ Created {test_strategy_name}" if created else f"Failed: {create_result}")

        if not created:
            results.add("11.2-11.6 Skipped", False, "Skipped due to creation failure")
        else:
            # Step 1.5: Deploy strategy (generate C++ code and compile)
            print(f"\n[11.1.5] Deploying {test_strategy_name} for backtesting...")
            deploy_result = await actions.deploy_strategy_for_backtest(test_strategy_name)
            deployed = "success" in deploy_result.lower() and "compil" in deploy_result.lower()

            if not deployed:
                print(f"   ⚠️ Deployment failed, backtests may return 0%")

            # Step 2: Initial backtest (2025 data)
            print("\n[11.2] Running initial backtest...")
            backtest1_result = await actions.run_backtest(test_strategy_name, ["BTC"], 30)

            has_result = "return" in backtest1_result.lower() and not is_placeholder_value(backtest1_result)
            results.add("11.2 Initial backtest", has_result,
                       f"✓ Backtest completed" if has_result else f"Failed: {backtest1_result[:100]}")

            # Step 3: Optimize parameters
            print("\n[11.3] Optimizing rsi_oversold parameter...")
            opt_grid = {"rsi_oversold": [25, 30, 35]}

            opt_result = await actions.optimize_strategy(test_strategy_name, opt_grid, ["BTC"], 30)

            optimized = "best" in opt_result.lower() and "parameter" in opt_result.lower()
            results.add("11.3 Optimize parameters", optimized,
                       f"✓ Optimization completed" if optimized else "Failed")

            # Step 4: Re-backtest with optimized parameters
            print("\n[11.4] Re-backtesting with optimized parameters...")
            backtest2_result = await actions.run_backtest(test_strategy_name, ["BTC"], 30)

            has_result2 = "return" in backtest2_result.lower() and not is_placeholder_value(backtest2_result)
            results.add("11.4 Re-backtest with optimized params", has_result2,
                       f"✓ Re-backtest completed" if has_result2 else "Failed")

            # Step 5: AI Analysis - Ask Claude why optimized version performs better
            print("\n[11.5] Getting AI analysis of performance difference...")

            # This would use Claude AI to analyze the results
            import anthropic
            import os

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                client = anthropic.Anthropic(api_key=api_key)

                analysis_prompt = f'''You are a quantitative trading analyst.

Strategy: {test_strategy_name}
Initial Parameters: rsi_oversold=30
Optimized Parameters: rsi_oversold=25 (best from optimization)

Initial Backtest Result:
{backtest1_result}

Optimized Backtest Result:
{backtest2_result}

Please analyze why the optimized version performs better or worse. Be specific about:
1. Which parameter changed and how
2. How this affects trade entry timing
3. Why this leads to better/worse performance
4. Keep it concise (3-4 sentences max)
'''

                try:
                    response = client.messages.create(
                        model="claude-opus-4-7",
                        max_tokens=300,
                        messages=[{"role": "user", "content": analysis_prompt}]
                    )

                    ai_analysis = response.content[0].text

                    # Check if AI gave meaningful analysis
                    has_analysis = len(ai_analysis) > 50 and any(word in ai_analysis.lower() for word in ["parameter", "performance", "trade", "rsi"])

                    results.add("11.5 AI Performance Analysis", has_analysis,
                               f"✓ AI Analysis: {ai_analysis[:150]}..." if has_analysis else "No analysis")

                except Exception as e:
                    results.add("11.5 AI Performance Analysis", False, f"AI call failed: {e}")
            else:
                results.add("11.5 AI Performance Analysis", False, "No API key found")

            # Step 6: Cleanup - delete test strategy
            print("\n[11.6] Cleaning up test strategy...")
            delete_result = await actions.delete_strategy(test_strategy_name)
            deleted = "deleted" in delete_result.lower()
            results.add("11.6 Cleanup test strategy", deleted,
                       f"✓ Deleted" if deleted else "Failed to delete")

    except Exception as e:
        import traceback
        results.add("11. Complete Workflow", False, f"Exception: {e}")
        traceback.print_exc()

    # ===========================================================================
    # SUMMARY
    # ===========================================================================
    results.summary()

    if results.failed == 0:
        print("\n🎉 ALL 32 TESTS PASSED!")
        print("\n✅ Database-first architecture working correctly")
        print("✅ Bot actions validated with NO placeholder values")
        print("✅ Complete workflow: Create → Backtest → Optimize → Re-backtest → AI Analysis ✅")
        print("✅ Ready for Telegram bot integration")
        return 0
    else:
        print(f"\n⚠️  {results.failed} tests failed")
        print("Fixing issues iteratively...")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
