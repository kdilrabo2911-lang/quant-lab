"""
Strategy Parameter Optimizer
Grid search to find optimal parameters for strategies
"""

import asyncio
import itertools
from typing import Dict, List, Optional
from action_executor import ActionExecutor
from backtest_query import BacktestQuery


class StrategyOptimizer:
    """Optimizes strategy parameters via grid search"""

    def __init__(self):
        self.action_executor = ActionExecutor()
        self.backtest_query = BacktestQuery()

    async def optimize(
        self,
        strategy_name: str,
        coins: List[str],
        days: int,
        param_grid: Dict[str, List]
    ) -> Dict:
        """
        Run grid search optimization

        Args:
            strategy_name: e.g. "VolatilityHarvesting"
            coins: e.g. ["RNDR"]
            days: Backtest period
            param_grid: Dict of param_name -> [values to try]
                       e.g. {"bb_period": [10, 20, 30], "profit_target": [1.5, 2.0, 2.5]}

        Returns:
            Dict with best parameters and results
        """

        print(f"\n🔬 Starting parameter optimization for {strategy_name}")
        print(f"Testing {len(list(itertools.product(*param_grid.values())))} combinations...")

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        results = []
        best_return = -float('inf')
        best_params = None
        best_run_id = None

        for i, combo in enumerate(combinations, 1):
            params = dict(zip(param_names, combo))

            print(f"\n[{i}/{len(combinations)}] Testing: {params}")

            # Run backtest with these parameters
            result = await self.action_executor.run_backtest(
                strategy_name=strategy_name,
                coins=coins,
                days=days,
                parameters=params
            )

            if not result.get("success"):
                print(f"  ⚠️  Failed: {result.get('error')}")
                continue

            # Extract performance metric (total return)
            # Metrics are nested in result["data"]["metrics"]
            data = result.get("data", {})
            metrics = data.get("metrics", {})
            total_return = metrics.get("total_return_pct", -100)
            trades = metrics.get("total_trades", 0)
            run_id = metrics.get("run_id")  # Get run_id from metrics

            print(f"  Return: {total_return:.2f}% | Trades: {trades} | Run ID: {run_id}")

            results.append({
                "params": params,
                "return": total_return,
                "trades": trades,
                "run_id": run_id,
                "metrics": metrics
            })

            # Track best
            if total_return > best_return:
                best_return = total_return
                best_params = params
                best_run_id = result.get("run_id")
                print(f"  ✨ New best!")

        # Sort results by return
        results.sort(key=lambda x: x["return"], reverse=True)

        return {
            "success": True,
            "strategy": strategy_name,
            "coins": coins,
            "days": days,
            "tested_combinations": len(results),
            "best_params": best_params,
            "best_return": best_return,
            "best_run_id": best_run_id,
            "all_results": results[:10],  # Top 10
            "message": f"Found best parameters: {best_params} with {best_return:.2f}% return"
        }


# Default parameter grids for each strategy
DEFAULT_PARAM_GRIDS = {
    "VolatilityHarvesting": {
        "lookback_period": [12, 24, 48],  # Hours to look back for peak
        "volatility_threshold_pct": [1.5, 2.0, 3.0],  # % dip from peak to buy
        "position_size_pct": [10.0, 15.0, 20.0]  # % of capital per trade
    },
    "MovingAverages": {
        "fast_period": [10, 20, 30],
        "slow_period": [50, 100, 150],
        "trailing_stop_pct": [3.0, 5.0, 7.0]
    },
    "SentimentMomentum": {
        "lookback_period": [7, 14, 21],
        "momentum_threshold": [0.5, 1.0, 1.5]
    },
    "MA_Dip_Buyer": {
        "ma_period": [144, 288, 576, 1152],  # 12h, 1d, 2d, 4d (5-min candles)
        "profit_target_pct": [2.0, 2.5, 3.0],
        "dip_threshold_pct": [2.0, 2.5, 3.0]
    },
    "MADipBuyer": {  # Alias
        "ma_period": [144, 288, 576, 1152],
        "profit_target_pct": [2.0, 2.5, 3.0],
        "dip_threshold_pct": [2.0, 2.5, 3.0]
    }
}
