"""
Updater Service - Fetch latest candles from Kraken and store in PostgreSQL
"""
import logging
from typing import Dict
from datetime import datetime, timedelta, timezone
from .kraken_client import KrakenClient
from .data_manager import data_manager
from .models import UpdateStatusResponse
from .config import settings

logger = logging.getLogger(__name__)


class CandleUpdater:
    """Fetches latest candles from Kraken and updates database"""

    def __init__(self):
        self.kraken_client = KrakenClient()
        self.last_update: Dict[str, datetime] = {}

    async def update_coin(self, coin: str) -> UpdateStatusResponse:
        """
        Update candles for a single coin

        Args:
            coin: Coin symbol (e.g., 'BTC', 'ETH')

        Returns:
            UpdateStatusResponse with status info
        """
        try:
            logger.info(f"[UPDATE] {coin}: Starting update...")

            # Get latest timestamp from database
            latest_db_time = await data_manager.get_latest_timestamp(coin)

            # Fetch latest candles from Kraken (max 720 candles = ~2.5 days for 5min interval)
            candles = self.kraken_client.fetch_latest_candles(
                coin=coin,
                interval_minutes=settings.candle_interval_minutes,
                count=720  # Maximum allowed by Kraken API
            )

            if not candles:
                logger.warning(f"[UPDATE] {coin}: No candles received from Kraken")
                return UpdateStatusResponse(
                    coin=coin,
                    success=False,
                    candles_added=0,
                    latest_timestamp=latest_db_time,
                    error="No candles received from Kraken"
                )

            # Filter out candles we already have
            if latest_db_time:
                # Only keep candles newer than what we have (with small overlap for safety)
                overlap_time = latest_db_time - timedelta(minutes=settings.candle_interval_minutes)
                new_candles = [c for c in candles if c.time > overlap_time]
            else:
                # No data in DB yet, take all candles
                new_candles = candles

            if not new_candles:
                logger.info(f"[UPDATE] {coin}: No new candles to add (already up to date)")
                return UpdateStatusResponse(
                    coin=coin,
                    success=True,
                    candles_added=0,
                    latest_timestamp=latest_db_time
                )

            # Insert into database
            inserted_count = await data_manager.insert_candles(coin, new_candles)

            # Update last update time
            self.last_update[coin] = datetime.now(timezone.utc)

            latest_timestamp = new_candles[-1].time if new_candles else latest_db_time

            logger.info(f"[UPDATE] {coin}: Success - added {inserted_count} new candles (latest: {latest_timestamp})")

            return UpdateStatusResponse(
                coin=coin,
                success=True,
                candles_added=inserted_count,
                latest_timestamp=latest_timestamp
            )

        except Exception as e:
            logger.error(f"[UPDATE] {coin}: Failed - {e}")
            return UpdateStatusResponse(
                coin=coin,
                success=False,
                candles_added=0,
                latest_timestamp=None,
                error=str(e)
            )

    async def update_all_coins(self) -> Dict[str, UpdateStatusResponse]:
        """
        Update all tracked coins

        Returns:
            Dictionary mapping coin -> UpdateStatusResponse
        """
        # Auto-detect coins from database if TRACKED_COINS=AUTO
        if settings.tracked_coins_list is None:
            coins = await data_manager.get_available_coins()
            logger.info(f"[AUTO-DETECT] Found {len(coins)} coins in database: {coins}")
        else:
            coins = settings.tracked_coins_list

        logger.info(f"[UPDATE ALL] Starting update for {len(coins)} coins...")

        results = {}
        for coin in coins:
            result = await self.update_coin(coin)
            results[coin] = result

        successful = sum(1 for r in results.values() if r.success)
        total_candles = sum(r.candles_added for r in results.values())

        logger.info(f"[UPDATE ALL] Complete - {successful}/{len(results)} coins updated, {total_candles} total candles added")

        return results


# Global updater instance
updater = CandleUpdater()
