"""
DataAgent Main Entry Point
"""
import uvicorn
import logging
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the DataAgent API server"""
    logger.info("=" * 60)
    logger.info("DataAgent - Historical OHLC Data Service")
    logger.info("=" * 60)

    if settings.tracked_coins_list is None:
        logger.info(f"Tracked coins: AUTO (will detect from database)")
    else:
        logger.info(f"Tracked coins: {', '.join(settings.tracked_coins_list)}")

    logger.info(f"Update interval: {settings.update_interval_seconds} seconds")
    logger.info(f"Candle interval: {settings.candle_interval_minutes} minutes")
    logger.info(f"API: http://{settings.api_host}:{settings.api_port}")
    logger.info("=" * 60)

    uvicorn.run(
        "app.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
