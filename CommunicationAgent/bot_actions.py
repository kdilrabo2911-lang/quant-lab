"""
BotActions - All working functions for the telegram bot
These are the same tested functions from test_function2.py
"""

import sys
from pathlib import Path

# Add MasterAgent to path to import its modules
sys.path.insert(0, str(Path(__file__).parent.parent / "MasterAgent"))

from strategy_store import get_store, Strategy
from action_executor import ActionExecutor
from db_storage import db_storage
from typing import Dict, List, Optional


class BotActions:
    """Contains all tested bot functions - same as test_function2.py"""

    def __init__(self):
        self.store = get_store()
        self.executor = ActionExecutor()

    async def _ensure_connected(self):
        """Ensure database connection"""
        if not self.store._db_pool:
            await self.store.connect()

    # ===================================================================
    # STRATEGY MANAGEMENT
    # ===================================================================

    async def list_all_strategies(self) -> str:
        """List all strategies from database - TESTED IN test_function2"""
        await self._ensure_connected()
        strategies = await self.store.list_all()

        if not strategies:
            return "📋 No strategies in database yet.\n\n💡 Create one: 'create strategy: buy dips, sell at profit'"

        result = f"📋 {len(strategies)} Strategies:\n\n"
        for s in strategies:
            result += f"• {s.name} v{s.version} ({s.type})\n"
            result += f"  Params: {len(s.parameters)} | Buy: {len(s.buy_conditions)} | Sell: {len(s.sell_conditions)}\n\n"

        return result

    async def get_strategy_info(self, name: str) -> str:
        """Get details about a strategy - TESTED IN test_function2"""
        await self._ensure_connected()
        strategy = await self.store.get(name)

        if not strategy:
            available = await self.store.list_all()
            names = [s.name for s in available]
            return f"❌ Strategy '{name}' not found.\n\nAvailable: {', '.join(names)}"

        result = f"{strategy.name} v{strategy.version}\n\n"
        result += f"📝 {strategy.description}\n\n"
        result += f"⚙️ Parameters ({len(strategy.parameters)}):\n"
        for k, v in strategy.parameters.items():
            result += f"  • {k}: {v}\n"

        result += f"\n✅ Buy conditions: {len(strategy.buy_conditions)}\n"
        result += f"❌ Sell conditions: {len(strategy.sell_conditions)}\n"

        return result

    async def create_strategy(self, name: str, description: str,
                            parameters: Dict, buy_conditions: List,
                            sell_conditions: List) -> str:
        """Create new strategy - TESTED IN test_function2"""
        await self._ensure_connected()

        strategy = Strategy(
            id=0,
            name=name,
            version="1.0",
            type="custom",
            description=description,
            parameters=parameters,
            buy_conditions=buy_conditions,
            sell_conditions=sell_conditions
        )

        strategy_id = await self.store.create(strategy)
        return f"✅ Created {name} (ID: {strategy_id})"

    async def delete_strategy(self, name: str) -> str:
        """Delete strategy - TESTED IN test_function2"""
        await self._ensure_connected()

        # Check if exists
        strategy = await self.store.get(name)
        if not strategy:
            return f"❌ Strategy '{name}' not found."

        await self.store.delete(name)
        return f"✅ Deleted {name}"

    # ===================================================================
    # BACKTESTING
    # ===================================================================

    async def run_backtest(self, strategy_name: str, coins: List[str],
                          days: int = 30) -> str:
        """Run backtest - TESTED IN test_function2

        Auto-deploys if needed (generates C++ code automatically)
        """
        result = await self.executor.run_backtest(
            strategy_name=strategy_name,
            coins=coins,
            days=days
        )

        if result.get("needs_deployment"):
            # AUTO-DEPLOY: Generate C++ code automatically
            deploy_msg = f"🔧 Strategy needs C++ code generation. Deploying automatically...\n\n"

            deploy_result = await self.executor.deploy_strategy_for_backtest(strategy_name)

            if not deploy_result.get("success"):
                return deploy_msg + f"❌ Deployment failed: {deploy_result.get('error')}\n\n" \
                       "Please fix the strategy definition and try again."

            # Check if it was compiled
            if deploy_result.get("compiled"):
                deploy_msg += f"✅ Generated and compiled C++ code!\n"
                deploy_msg += f"   Files: {', '.join(deploy_result.get('files_generated', []))}\n\n"

                if deploy_result.get("auto_fixed"):
                    deploy_msg += f"🔧 Auto-fixed compilation errors ({deploy_result.get('fix_attempts', 0)} attempts)\n\n"

                deploy_msg += f"🚀 Strategy is ready for backtesting!\n\n"
                deploy_msg += "Now running backtest..."

                # Try to run backtest now that it's compiled
                result = await self.executor.run_backtest(
                    strategy_name=strategy_name,
                    coins=coins,
                    days=days
                )

                if result.get("success"):
                    # Get metrics from result data
                    data = result.get("data", {})
                    metrics = data.get("metrics", {})
                    db_id = data.get("db_record_id")

                    return_pct = metrics.get("total_return_pct", "N/A")
                    trades = metrics.get("total_trades", "N/A")

                    deploy_msg += f"\n✅ Backtest complete!\n\n"
                    deploy_msg += f"📊 Results:\n"
                    deploy_msg += f"• Return: {return_pct}%\n"
                    deploy_msg += f"• Trades: {trades}\n"
                    if db_id:
                        deploy_msg += f"• Saved to database (Run #{db_id})"

                    return deploy_msg
                else:
                    return deploy_msg + f"\n\n❌ Backtest failed: {result.get('error', 'Unknown')}"
            else:
                # Compilation wasn't attempted or failed
                deploy_msg += f"✅ Generated C++ code: {', '.join(deploy_result.get('files_generated', []))}\n\n"
                deploy_msg += "⚠️ Note: C++ code generated but needs CMake compilation.\n"
                deploy_msg += "Run these commands:\n"
                deploy_msg += "```\ncd BacktestAgent/build\ncmake ..\nmake -j4\n```\n\n"
                deploy_msg += "Then try the backtest again!"
                return deploy_msg

        if not result.get("success"):
            return f"❌ {result.get('error', 'Unknown error')}"

        # Get metrics from result data
        data = result.get("data", {})
        metrics = data.get("metrics", {})
        db_id = data.get("db_record_id")

        return_pct = metrics.get("total_return_pct", "N/A")
        trades = metrics.get("total_trades", "N/A")

        response = f"✅ Backtest complete!\n\n📊 Results:\n• Return: {return_pct}%\n• Trades: {trades}"
        if db_id:
            response += f"\n• Saved to database (Run #{db_id})"

        return response

    async def deploy_strategy_for_backtest(self, strategy_name: str) -> str:
        """Deploy strategy (generate C++ code) - TESTED IN test_function2"""
        result = await self.executor.deploy_strategy_for_backtest(strategy_name)

        if not result.get("success"):
            return f"❌ {result.get('error', 'Deployment failed')}"

        files = result.get("files_generated", [])
        return f"✅ Deployed {strategy_name}\n\nGenerated: {', '.join(files)}\n\n⚠️ Note: Needs CMake compilation before backtesting"

    async def optimize_strategy(self, strategy_name: str, param_grid: Dict,
                               coins: List[str], days: int = 30) -> str:
        """Optimize strategy parameters - find best parameter combination"""
        await self._ensure_connected()

        # Get strategy from database
        strategy = await self.store.get(strategy_name)
        if not strategy:
            return f"❌ Strategy '{strategy_name}' not found."

        # Update optimization grid
        strategy.optimization_grid = param_grid
        await self.store.update(strategy)

        # Run optimization
        result = await self.executor.optimize_strategy(
            strategy_name=strategy_name,
            coins=coins,
            days=days
        )

        if not result.get("success"):
            return f"❌ Optimization failed: {result.get('error', 'Unknown error')}"

        best = result.get("best_params", {})
        best_return = result.get("best_return", 0.0)
        total_tested = result.get("tested_combinations", result.get("total_combinations", 0))

        result_str = f"✅ Optimization complete!\n\n"
        result_str += f"📊 Tested {total_tested} combinations\n"
        result_str += f"🏆 Best return: {best_return:.2f}%\n\n"
        result_str += f"Best parameters:\n"
        for k, v in best.items():
            result_str += f"  • {k}: {v}\n"

        return result_str

    async def create_and_backtest(self, name: str, description: str,
                                  parameters: Dict, buy_conditions: List,
                                  sell_conditions: List, coins: List[str],
                                  days: int = 30) -> str:
        """Create strategy, deploy it, and run backtest - complete workflow"""
        await self._ensure_connected()

        # Step 1: Create strategy in database
        strategy = Strategy(
            id=0,
            name=name,
            version="1.0",
            type="custom",
            description=description,
            parameters=parameters,
            buy_conditions=buy_conditions,
            sell_conditions=sell_conditions
        )

        try:
            strategy_id = await self.store.create(strategy)
            result = f"✅ Created {name} (ID: {strategy_id})\n\n"
        except Exception as e:
            return f"❌ Failed to create strategy: {e}"

        # Step 2: Deploy (generate C++ code)
        result += "🔨 Deploying (generating C++ code)...\n"
        deploy_result = await self.executor.deploy_strategy_for_backtest(name)

        if not deploy_result.get("success"):
            return f"{result}❌ Deployment failed: {deploy_result.get('error')}"

        result += f"✅ Deployed\n\n"

        # Step 3: Run backtest
        result += f"🧪 Running backtest on {coins} for {days} days...\n"
        backtest_result = await self.executor.run_backtest(
            strategy_name=name,
            coins=coins,
            days=days
        )

        if not backtest_result.get("success"):
            return f"{result}❌ Backtest failed: {backtest_result.get('error')}"

        summary = backtest_result.get("summary", {})
        return_pct = summary.get("portfolio_total_return_pct", "N/A")
        trades = summary.get("total_trades", "N/A")

        result += f"✅ Backtest complete!\n\n📊 Results:\n• Return: {return_pct}%\n• Trades: {trades}"

        return result

    # ===================================================================
    # DATABASE QUERIES
    # ===================================================================

    async def get_last_backtest(self) -> str:
        """Get last backtest result - TESTED IN test_function2"""
        await db_storage.connect()

        last_run = await db_storage.pool.fetchrow("""
            SELECT id, strategy_name, coins, portfolio_total_return_pct
            FROM backtest_runs
            ORDER BY id DESC
            LIMIT 1
        """)

        if not last_run:
            return "📊 No backtests found."

        return f"📊 Last Backtest:\n• Run #{last_run['id']}\n• Strategy: {last_run['strategy_name']}\n• Coins: {last_run['coins']}\n• Return: {last_run['portfolio_total_return_pct']}%"

    async def get_best_backtest(self, strategy_name: Optional[str] = None) -> str:
        """Get best backtest - TESTED IN test_function2"""
        await db_storage.connect()

        query = """
            SELECT id, strategy_name, coins, portfolio_total_return_pct
            FROM backtest_runs
        """
        params = []

        if strategy_name:
            query += " WHERE strategy_name = $1"
            params.append(strategy_name)

        query += " ORDER BY portfolio_total_return_pct DESC LIMIT 1"

        best_run = await db_storage.pool.fetchrow(query, *params)

        if not best_run:
            return f"📊 No backtests found{' for ' + strategy_name if strategy_name else ''}."

        return f"🏆 Best Backtest:\n• Run #{best_run['id']}\n• Strategy: {best_run['strategy_name']}\n• Coins: {best_run['coins']}\n• Return: {best_run['portfolio_total_return_pct']}%"

    async def get_backtest_by_id(self, backtest_id: int) -> str:
        """Get specific backtest by ID"""
        await db_storage.connect()

        backtest = await db_storage.pool.fetchrow("""
            SELECT id, strategy_name, coins, portfolio_total_return_pct, total_trades, created_at
            FROM backtest_runs
            WHERE id = $1
        """, backtest_id)

        if not backtest:
            return f"❌ Backtest #{backtest_id} not found."

        return f"📊 Backtest #{backtest['id']}:\n• Strategy: {backtest['strategy_name']}\n• Coins: {backtest['coins']}\n• Return: {backtest['portfolio_total_return_pct']}%\n• Trades: {backtest['total_trades']}\n• Date: {backtest['created_at']}"

    async def list_backtests_for_strategy(self, strategy_name: str, limit: int = 10) -> str:
        """List recent backtests for a strategy"""
        await db_storage.connect()

        backtests = await db_storage.pool.fetch("""
            SELECT id, coins, portfolio_total_return_pct, total_trades, created_at
            FROM backtest_runs
            WHERE strategy_name = $1
            ORDER BY id DESC
            LIMIT $2
        """, strategy_name, limit)

        if not backtests:
            return f"📊 No backtests found for {strategy_name}."

        result = f"📊 Backtests for {strategy_name} (last {len(backtests)}):\n\n"
        for bt in backtests:
            result += f"• Run #{bt['id']}: {bt['coins']} → {bt['portfolio_total_return_pct']}% ({bt['total_trades']} trades)\n"

        return result

    async def compare_strategies(self, strategy_names: List[str], coins: List[str], days: int) -> str:
        """Compare multiple strategies by running backtests"""
        results_data = []

        for strategy_name in strategy_names:
            # Run backtest for each strategy
            result_text = await self.run_backtest(strategy_name, coins, days)

            # Parse the result (simple keyword extraction)
            import re
            match = re.search(r'Return:\s*([-+]?\d+\.?\d*)%', result_text, re.IGNORECASE)
            return_pct = float(match.group(1)) if match else 0.0

            results_data.append({
                "strategy": strategy_name,
                "return": return_pct,
                "result": result_text
            })

        # Sort by return
        results_data.sort(key=lambda x: x["return"], reverse=True)

        # Format comparison
        result = f"📊 Strategy Comparison ({len(strategy_names)} strategies on {coins} for {days} days):\n\n"
        for i, data in enumerate(results_data, 1):
            result += f"{i}. {data['strategy']}: {data['return']}%\n"

        result += f"\n🏆 Winner: {results_data[0]['strategy']} ({results_data[0]['return']}%)"

        return result
