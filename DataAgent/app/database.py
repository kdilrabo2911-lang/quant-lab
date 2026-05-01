"""
Database setup and connection management
"""
import asyncpg
import logging
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database manager"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created")

            # Create tables if they don't exist
            await self.create_tables()

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def create_tables(self):
        """Create all tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Create candles table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlc_candles (
                    id BIGSERIAL PRIMARY KEY,
                    coin VARCHAR(10) NOT NULL,
                    time TIMESTAMP WITH TIME ZONE NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL,
                    close_btc DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(coin, time)
                );
            """)

            # Create backtest outputs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_outputs (
                    id BIGSERIAL PRIMARY KEY,
                    run_id INTEGER,
                    strategy VARCHAR(50) NOT NULL,
                    coins TEXT[] NOT NULL,
                    days INTEGER,
                    output_text TEXT NOT NULL,
                    metrics JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # Create chat history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id BIGSERIAL PRIMARY KEY,
                    role VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlc_coin_time
                ON ohlc_candles (coin, time DESC);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlc_time
                ON ohlc_candles (time DESC);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backtest_run_id
                ON backtest_outputs (run_id);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backtest_created
                ON backtest_outputs (created_at DESC);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_timestamp
                ON chat_history (timestamp DESC);
            """)

            logger.info("Database tables created/verified")


# Global database instance
db = Database()
