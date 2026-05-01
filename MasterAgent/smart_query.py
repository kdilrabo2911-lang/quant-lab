"""
Smart Query Interface - Natural language and flexible indexing for database queries
"""

import asyncpg
import os
from typing import Dict, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv


class SmartQuery:
    """Flexible query interface - query by index, natural language, or filters"""

    def __init__(self):
        env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
        load_dotenv(env_file)
        self.db_url = os.getenv("DATABASE_URL")
        self.pool = None

    async def connect(self):
        """Connect to database"""
        if not self.pool and self.db_url:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=5)

    async def query_backtests(
        self,
        run_id: Optional[int] = None,
        index: Optional[int] = None,
        strategy: Optional[str] = None,
        coin: Optional[str] = None,
        limit: int = 1,
        order_by: str = "run_timestamp",
        order: str = "DESC"
    ) -> Union[Dict, List[Dict]]:
        """
        Flexible backtest query - supports ID, index-based and filter-based queries

        Examples:
            query_backtests(run_id=15)  # Specific backtest by run ID
            query_backtests(index=-1)  # Last backtest
            query_backtests(index=15)  # Backtest at index 15
            query_backtests(index=-2)  # Second to last
            query_backtests(coin="RNDR", limit=5)  # Last 5 RNDR backtests
            query_backtests(strategy="ma_trailing")  # Last ma_trailing backtest

        Args:
            run_id: Specific backtest run ID
            index: Row index (0-based, negative for from-end)
            strategy: Filter by strategy name
            coin: Filter by coin
            limit: Number of results
            order_by: Column to order by
            order: ASC or DESC

        Returns:
            Single dict if index specified, list of dicts otherwise
        """
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            # If querying by run_id, fetch directly
            if run_id is not None:
                query = """
                    SELECT
                        br.id,
                        br.strategy_name,
                        br.coins,
                        br.portfolio_total_return_pct,
                        br.portfolio_sharpe_ratio,
                        br.portfolio_max_drawdown_pct,
                        br.total_trades,
                        br.run_timestamp,
                        br.period_days,
                        br.strategy_parameters,
                        bs.num_coins,
                        bs.avg_coin_return_pct,
                        bs.best_coin_return_pct,
                        bs.worst_coin_return_pct
                    FROM backtest_runs br
                    LEFT JOIN backtest_summary bs ON br.id = bs.id
                    WHERE br.id = $1
                """
                row = await conn.fetchrow(query, run_id)
                return dict(row) if row else None

            # Build WHERE clause
            where_parts = []
            params = []
            param_idx = 1

            if strategy:
                where_parts.append(f"br.strategy_name = ${param_idx}")
                params.append(strategy)
                param_idx += 1

            if coin:
                where_parts.append(f"${param_idx} = ANY(br.coins)")
                params.append(coin)
                param_idx += 1

            where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

            # If index is specified, we need to:
            # 1. Get total count
            # 2. Convert index to actual row (handle negative indices)
            # 3. Query that specific row
            if index is not None:
                # Get total count
                count_query = f"""
                    SELECT COUNT(*) FROM backtest_runs br
                    {where_clause}
                """
                total = await conn.fetchval(count_query, *params)

                if total == 0:
                    return None

                # Handle negative indices (Python-style)
                if index < 0:
                    actual_index = total + index
                else:
                    actual_index = index

                # Validate index
                if actual_index < 0 or actual_index >= total:
                    return None

                # Query specific row using OFFSET
                query = f"""
                    SELECT
                        br.id,
                        br.strategy_name,
                        br.coins,
                        bs.portfolio_total_return_pct,
                        bs.total_trades,
                        br.run_timestamp,
                        br.period_days
                    FROM backtest_runs br
                    JOIN backtest_summary bs ON br.id = bs.id
                    {where_clause}
                    ORDER BY br.{order_by} {order}
                    LIMIT 1
                    OFFSET ${param_idx}
                """
                params.append(actual_index)

                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None

            else:
                # Regular query - return list
                query = f"""
                    SELECT
                        br.id,
                        br.strategy_name,
                        br.coins,
                        bs.portfolio_total_return_pct,
                        bs.total_trades,
                        br.run_timestamp,
                        br.period_days
                    FROM backtest_runs br
                    JOIN backtest_summary bs ON br.id = bs.id
                    {where_clause}
                    ORDER BY br.{order_by} {order}
                    LIMIT ${param_idx}
                """
                params.append(limit)

                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]

    async def query_best(
        self,
        metric: str = "portfolio_total_return_pct",
        strategy: Optional[str] = None,
        coin: Optional[str] = None,
        limit: int = 1
    ) -> Union[Dict, List[Dict]]:
        """
        Query best performing backtests

        Examples:
            query_best()  # Best overall
            query_best(coin="RNDR")  # Best for RNDR
            query_best(strategy="ma_trailing", limit=5)  # Top 5 MA backtests

        Args:
            metric: Metric to optimize (portfolio_total_return_pct, win_rate, etc.)
            strategy: Filter by strategy
            coin: Filter by coin
            limit: Number of results

        Returns:
            Single dict if limit=1, list otherwise
        """
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            where_parts = []
            params = []
            param_idx = 1

            if strategy:
                where_parts.append(f"br.strategy_name = ${param_idx}")
                params.append(strategy)
                param_idx += 1

            if coin:
                where_parts.append(f"${param_idx} = ANY(br.coins)")
                params.append(coin)
                param_idx += 1

            where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

            query = f"""
                SELECT
                    br.id,
                    br.strategy_name,
                    br.coins,
                    bs.portfolio_total_return_pct,
                    bs.total_trades,
                    br.run_timestamp,
                    br.period_days
                FROM backtest_runs br
                JOIN backtest_summary bs ON br.id = bs.id
                {where_clause}
                ORDER BY bs.{metric} DESC
                LIMIT ${param_idx}
            """
            params.append(limit)

            rows = await conn.fetch(query, *params)

            if limit == 1:
                return dict(rows[0]) if rows else None
            else:
                return [dict(row) for row in rows]

    async def query_trades(
        self,
        run_id: int,
        winning_only: bool = False,
        losing_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Query trades for a specific backtest run

        Examples:
            query_trades(run_id=15)  # All trades for run 15
            query_trades(run_id=15, losing_only=True)  # Only losing trades
            query_trades(run_id=15, winning_only=True, limit=5)  # Top 5 winners

        Args:
            run_id: Backtest run ID
            winning_only: Only trades with profit > 0
            losing_only: Only trades with profit < 0
            limit: Limit results

        Returns:
            List of trade dicts
        """
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            where_parts = [f"backtest_run_id = $1"]

            if winning_only:
                where_parts.append("profit_pct > 0")
            elif losing_only:
                where_parts.append("profit_pct < 0")

            where_clause = "WHERE " + " AND ".join(where_parts)

            limit_clause = f"LIMIT {limit}" if limit else ""

            query = f"""
                SELECT
                    coin,
                    buy_price,
                    sell_price,
                    profit_pct,
                    buy_time,
                    sell_time,
                    sell_reason
                FROM backtest_trades
                {where_clause}
                ORDER BY profit_pct DESC
                {limit_clause}
            """

            rows = await conn.fetch(query, run_id)
            return [dict(row) for row in rows]


# Global instance
smart_query = SmartQuery()
