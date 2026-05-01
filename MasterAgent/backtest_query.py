"""
Backtest Query - Query backtest results from database
"""

import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional
import json

# Load environment
env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)


class BacktestQuery:
    """Query backtest results from PostgreSQL database"""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL") or os.getenv("database_url")

    async def get_run_summary(self, run_id: int) -> Optional[Dict]:
        """Get summary for a specific backtest run"""

        if not self.db_url:
            return None

        try:
            conn = await asyncpg.connect(self.db_url)

            try:
                # Get run summary
                row = await conn.fetchrow("""
                    SELECT * FROM backtest_summary WHERE id = $1
                """, run_id)

                if not row:
                    return None

                return dict(row)

            finally:
                await conn.close()

        except Exception as e:
            print(f"Error querying database: {e}")
            return None

    async def get_run_trades(self, run_id: int) -> List[Dict]:
        """Get all trades for a specific backtest run"""

        if not self.db_url:
            return []

        try:
            conn = await asyncpg.connect(self.db_url)

            try:
                # Get trades
                rows = await conn.fetch("""
                    SELECT
                        t.*
                    FROM backtest_trades t
                    WHERE t.backtest_run_id = $1
                    ORDER BY t.buy_time
                """, run_id)

                return [dict(row) for row in rows]

            finally:
                await conn.close()

        except Exception as e:
            print(f"Error querying trades: {e}")
            return []

    async def get_coin_results(self, run_id: int) -> List[Dict]:
        """Get per-coin results for a backtest run"""

        if not self.db_url:
            return []

        try:
            conn = await asyncpg.connect(self.db_url)

            try:
                rows = await conn.fetch("""
                    SELECT * FROM backtest_coin_results
                    WHERE backtest_run_id = $1
                    ORDER BY total_return_pct DESC
                """, run_id)

                return [dict(row) for row in rows]

            finally:
                await conn.close()

        except Exception as e:
            print(f"Error querying coin results: {e}")
            return []

    async def analyze_run(self, run_id: int) -> Dict:
        """Complete analysis of a backtest run"""

        summary = await self.get_run_summary(run_id)
        if not summary:
            return {
                "success": False,
                "error": f"Run ID {run_id} not found"
            }

        coin_results = await self.get_coin_results(run_id)
        trades = await self.get_run_trades(run_id)

        # Calculate additional metrics
        winning_trades = [t for t in trades if t.get('profit_pct', 0) > 0]
        losing_trades = [t for t in trades if t.get('profit_pct', 0) <= 0]

        analysis = {
            "success": True,
            "run_id": run_id,
            "summary": {
                "strategy": summary['strategy_name'],
                "coins": summary['coins'],
                "period_days": summary['period_days'],
                "total_return": f"{summary['portfolio_total_return_pct']:.2f}%",
                "sharpe_ratio": f"{summary['portfolio_sharpe_ratio']:.2f}",
                "total_trades": summary['total_trades']
            },
            "coin_performance": [
                {
                    "coin": cr['coin'],
                    "return": f"{cr['total_return_pct']:.2f}%",
                    "trades": cr['num_trades'],
                    "win_rate": f"{cr['win_rate']*100:.1f}%",
                    "sharpe": f"{cr['sharpe_ratio']:.2f}"
                }
                for cr in coin_results
            ],
            "trade_stats": {
                "total": len(trades),
                "winners": len(winning_trades),
                "losers": len(losing_trades),
                "win_rate": f"{len(winning_trades)/len(trades)*100:.1f}%" if trades else "0%",
                "avg_win": f"{sum(t['profit_pct'] for t in winning_trades)/len(winning_trades):.2f}%" if winning_trades else "0%",
                "avg_loss": f"{sum(t['profit_pct'] for t in losing_trades)/len(losing_trades):.2f}%" if losing_trades else "0%"
            },
            "trades": trades[:10]  # First 10 trades as sample
        }

        return analysis

    async def export_trades_csv(self, run_id: int, output_file: str) -> bool:
        """Export trades to CSV file"""

        trades = await self.get_run_trades(run_id)

        if not trades:
            return False

        try:
            import csv

            with open(output_file, 'w', newline='') as f:
                if trades:
                    writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                    writer.writeheader()
                    writer.writerows(trades)

            return True

        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False


if __name__ == "__main__":
    # Test
    query = BacktestQuery()
    result = asyncio.run(query.analyze_run(2))
    print(json.dumps(result, indent=2))
