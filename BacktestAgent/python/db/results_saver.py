"""
Save backtest results to DigitalOcean PostgreSQL database
"""
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
from datetime import datetime
import json

# Load environment variables
env_file = Path(__file__).parent.parent.parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)


class BacktestResultsSaver:
    """Saves backtest results to PostgreSQL database"""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL") or os.getenv("database_url")
        if not self.db_url:
            raise ValueError("DATABASE_URL or database_url not found in secrets.env")

    async def save_backtest(
        self,
        strategy_name: str,
        coins: List[str],
        start_date: datetime,
        end_date: datetime,
        results: Dict[str, Dict],
        strategy_parameters: Dict = None
    ) -> int:
        """
        Save complete backtest results to database

        Args:
            strategy_name: Name of the strategy (e.g., "ma_trailing")
            coins: List of coins tested
            start_date: Backtest start date
            end_date: Backtest end date
            results: Dictionary mapping coin -> backtest results
            strategy_parameters: Optional strategy parameters

        Returns:
            backtest_run_id: ID of the created backtest run
        """

        conn = await asyncpg.connect(self.db_url)

        try:
            # Calculate portfolio-level metrics
            portfolio_metrics = self._calculate_portfolio_metrics(results)
            period_days = (end_date - start_date).days

            # 1. Insert backtest run (portfolio-level)
            backtest_run_id = await conn.fetchval("""
                INSERT INTO backtest_runs (
                    run_timestamp,
                    strategy_name,
                    coins,
                    start_date,
                    end_date,
                    period_days,
                    portfolio_total_return_pct,
                    portfolio_sharpe_ratio,
                    portfolio_max_drawdown_pct,
                    total_trades,
                    strategy_parameters
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (run_timestamp, strategy_name, coins)
                DO UPDATE SET
                    portfolio_total_return_pct = EXCLUDED.portfolio_total_return_pct,
                    portfolio_sharpe_ratio = EXCLUDED.portfolio_sharpe_ratio,
                    total_trades = EXCLUDED.total_trades
                RETURNING id
            """,
                datetime.now(),
                strategy_name,
                coins,
                start_date,
                end_date,
                period_days,
                portfolio_metrics['total_return_pct'],
                portfolio_metrics['sharpe_ratio'],
                portfolio_metrics['max_drawdown_pct'],
                portfolio_metrics['total_trades'],
                json.dumps(strategy_parameters) if strategy_parameters else None
            )

            print(f"✓ Saved backtest run #{backtest_run_id}")

            # 2. Insert coin-level results
            for coin, coin_results in results.items():
                if 'error' in coin_results:
                    continue

                coin_result_id = await conn.fetchval("""
                    INSERT INTO backtest_coin_results (
                        backtest_run_id,
                        coin,
                        total_return_pct,
                        num_trades,
                        win_rate,
                        avg_profit_pct,
                        avg_loss_pct,
                        max_drawdown_pct,
                        sharpe_ratio,
                        equity_curve
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (backtest_run_id, coin)
                    DO UPDATE SET
                        total_return_pct = EXCLUDED.total_return_pct,
                        num_trades = EXCLUDED.num_trades,
                        win_rate = EXCLUDED.win_rate
                    RETURNING id
                """,
                    backtest_run_id,
                    coin,
                    coin_results['total_return_pct'],
                    coin_results['num_trades'],
                    coin_results['win_rate'],
                    coin_results.get('avg_profit_pct'),
                    coin_results.get('avg_loss_pct'),
                    coin_results.get('max_drawdown_pct'),
                    coin_results.get('sharpe_ratio'),
                    json.dumps(coin_results.get('equity_curve', []))
                )

                # 3. Insert trade logs
                trades = coin_results.get('trades', [])
                if trades:
                    trade_records = [
                        (
                            backtest_run_id,
                            coin_result_id,
                            coin,
                            datetime.strptime(trade['buy_time'], '%Y-%m-%d %H:%M:%S'),
                            datetime.strptime(trade['sell_time'], '%Y-%m-%d %H:%M:%S'),
                            trade['buy_price'],
                            trade['sell_price'],
                            trade['profit_pct'],
                            trade.get('peak_profit_pct'),
                            trade.get('hold_duration'),
                            trade.get('sell_reason')
                        )
                        for trade in trades
                    ]

                    await conn.executemany("""
                        INSERT INTO backtest_trades (
                            backtest_run_id,
                            coin_result_id,
                            coin,
                            buy_time,
                            sell_time,
                            buy_price,
                            sell_price,
                            profit_pct,
                            peak_profit_pct,
                            hold_duration,
                            sell_reason
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """, trade_records)

                    print(f"  ✓ {coin}: {len(trades)} trades saved")

            print(f"✓ Backtest saved to database (ID: {backtest_run_id})")
            return backtest_run_id

        finally:
            await conn.close()

    def _calculate_portfolio_metrics(self, results: Dict[str, Dict]) -> Dict:
        """Calculate portfolio-level metrics from individual coin results"""

        valid_results = [r for r in results.values() if 'error' not in r]

        if not valid_results:
            return {
                'total_return_pct': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'total_trades': 0
            }

        # Equal-weighted portfolio return (average of all coins)
        avg_return = sum(r['total_return_pct'] for r in valid_results) / len(valid_results)

        # Average Sharpe ratio
        avg_sharpe = sum(r.get('sharpe_ratio', 0) for r in valid_results) / len(valid_results)

        # Max drawdown across all coins
        max_dd = max(r.get('max_drawdown_pct', 0) for r in valid_results)

        # Total trades
        total_trades = sum(r['num_trades'] for r in valid_results)

        return {
            'total_return_pct': round(avg_return, 4),
            'sharpe_ratio': round(avg_sharpe, 4),
            'max_drawdown_pct': round(max_dd, 4),
            'total_trades': total_trades
        }


async def save_backtest_to_db(
    strategy_name: str,
    coins: List[str],
    start_date: datetime,
    end_date: datetime,
    results: Dict[str, Dict],
    strategy_parameters: Dict = None
) -> int:
    """
    Convenience function to save backtest results

    Example:
        await save_backtest_to_db(
            strategy_name="ma_trailing",
            coins=["BTC", "ETH", "SOL"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            results={"BTC": {...}, "ETH": {...}},
            strategy_parameters={"ma_period": 144, "a": 1.0, "b": 0.5}
        )
    """
    saver = BacktestResultsSaver()
    return await saver.save_backtest(
        strategy_name,
        coins,
        start_date,
        end_date,
        results,
        strategy_parameters
    )
