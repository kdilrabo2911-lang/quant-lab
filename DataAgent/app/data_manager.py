"""
Data Manager - Handle OHLC candle operations in PostgreSQL
"""
import logging
from typing import List, Optional
from datetime import datetime, timezone
from .database import db
from .models import OHLCCandle

logger = logging.getLogger(__name__)


class DataManager:
    """Manages OHLC candle data in PostgreSQL"""

    async def get_latest_timestamp(self, coin: str) -> Optional[datetime]:
        """
        Get the timestamp of the latest candle for a coin

        Args:
            coin: Coin symbol (e.g., 'BTC', 'ETH')

        Returns:
            Latest timestamp or None if no data exists
        """
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT MAX(time) as latest_time
                FROM ohlc_candles
                WHERE coin = $1
            """, coin)

            if row and row['latest_time']:
                logger.info(f"{coin}: Latest timestamp is {row['latest_time']}")
                return row['latest_time']

            logger.info(f"{coin}: No existing data found")
            return None

    async def insert_candles(self, coin: str, candles: List[OHLCCandle]) -> int:
        """
        Insert new candles into database (ignore duplicates)

        Args:
            coin: Coin symbol (e.g., 'BTC', 'ETH')
            candles: List of OHLCCandle objects

        Returns:
            Number of candles inserted (duplicates ignored)
        """
        if not candles:
            return 0

        async with db.pool.acquire() as conn:
            inserted_count = 0

            for candle in candles:
                try:
                    await conn.execute("""
                        INSERT INTO ohlc_candles (coin, time, open, high, low, close, volume, close_btc)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (coin, time) DO NOTHING
                    """, coin, candle.time, candle.open, candle.high, candle.low,
                        candle.close, candle.volume, candle.close_btc)

                    inserted_count += 1

                except Exception as e:
                    logger.warning(f"Skipped duplicate candle for {coin} at {candle.time}")

            logger.info(f"{coin}: Inserted {inserted_count}/{len(candles)} new candles")
            return inserted_count

    async def get_candles(
        self,
        coin: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[OHLCCandle]:
        """
        Get OHLC candles for a coin

        Args:
            coin: Coin symbol
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            limit: Maximum number of candles to return

        Returns:
            List of OHLCCandle objects, sorted by time ascending
        """
        async with db.pool.acquire() as conn:
            query = """
                SELECT time, open, high, low, close, volume, close_btc
                FROM ohlc_candles
                WHERE coin = $1
            """
            params = [coin]
            param_index = 2

            if start_time:
                query += f" AND time >= ${param_index}"
                params.append(start_time)
                param_index += 1

            if end_time:
                query += f" AND time <= ${param_index}"
                params.append(end_time)
                param_index += 1

            query += " ORDER BY time ASC"

            if limit:
                query += f" LIMIT ${param_index}"
                params.append(limit)

            rows = await conn.fetch(query, *params)

            candles = [
                OHLCCandle(
                    time=row['time'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    close_btc=row['close_btc']
                )
                for row in rows
            ]

            logger.info(f"{coin}: Retrieved {len(candles)} candles")
            return candles

    async def get_latest_candles(self, coin: str, count: int = 100) -> List[OHLCCandle]:
        """
        Get the most recent N candles for a coin

        Args:
            coin: Coin symbol
            count: Number of candles to retrieve

        Returns:
            List of OHLCCandle objects, sorted by time ascending
        """
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, open, high, low, close, volume, close_btc
                FROM ohlc_candles
                WHERE coin = $1
                ORDER BY time DESC
                LIMIT $2
            """, coin, count)

            # Reverse to get ascending order
            candles = [
                OHLCCandle(
                    time=row['time'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    close_btc=row['close_btc']
                )
                for row in reversed(rows)
            ]

            logger.info(f"{coin}: Retrieved {len(candles)} latest candles")
            return candles

    async def get_total_candles(self, coin: str) -> int:
        """Get total number of candles for a coin"""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM ohlc_candles
                WHERE coin = $1
            """, coin)

            return row['count'] if row else 0

    async def get_available_coins(self) -> List[str]:
        """Get list of coins that have data in the database"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT coin
                FROM ohlc_candles
                ORDER BY coin
            """)

            return [row['coin'] for row in rows]


# Global data manager instance
data_manager = DataManager()
