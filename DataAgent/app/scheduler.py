"""
Scheduler - Run periodic updates every 5 minutes
"""
import asyncio
import logging
from datetime import datetime
from .updater import updater
from .config import settings

logger = logging.getLogger(__name__)


class UpdateScheduler:
    """Schedules periodic candle updates"""

    def __init__(self):
        self.is_running = False
        self.task = None

    async def start(self):
        """Start the periodic update loop"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        logger.info(f"Scheduler started - will update every {settings.update_interval_seconds} seconds")

        # Run initial update in background (don't block API startup)
        logger.info("[SCHEDULER] Starting initial update in background...")
        asyncio.create_task(self._run_initial_update())

        # Start periodic loop
        self.task = asyncio.create_task(self._update_loop())

    async def _run_initial_update(self):
        """Run initial update without blocking"""
        try:
            await updater.update_all_coins()
            logger.info("[SCHEDULER] Initial update complete")
        except Exception as e:
            logger.error(f"[SCHEDULER] Initial update failed: {e}")

    async def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _update_loop(self):
        """Internal loop that runs updates periodically"""
        while self.is_running:
            try:
                # Wait for the interval
                await asyncio.sleep(settings.update_interval_seconds)

                # Run update
                logger.info(f"[SCHEDULER] Running scheduled update at {datetime.now()}")
                await updater.update_all_coins()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SCHEDULER] Error during update: {e}")
                # Continue running even if update fails


# Global scheduler instance
scheduler = UpdateScheduler()
