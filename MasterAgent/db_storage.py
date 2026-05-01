"""Database Storage Module - Store files in PostgreSQL instead of local/cloud"""

import os
import asyncpg
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from dotenv import load_dotenv

# Load environment
env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)


class DatabaseStorage:
    """Store backtest outputs and chat history in PostgreSQL"""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.pool: Optional[asyncpg.Pool] = None
        self.enabled = bool(self.database_url)

    async def connect(self):
        """Create database connection pool"""
        if not self.enabled:
            print("⚠️ Database storage disabled - missing DATABASE_URL")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=60
            )
            print("✅ Database storage connected")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.enabled = False

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    async def save_backtest_output(
        self,
        strategy: str,
        coins: List[str],
        output_text: str,
        days: Optional[int] = None,
        run_id: Optional[int] = None,
        metrics: Optional[Dict] = None
    ) -> Optional[int]:
        """Save backtest output to database

        Args:
            strategy: Strategy name
            coins: List of coin symbols
            output_text: Full backtest output text
            days: Number of days backtested
            run_id: Backtest run ID (from backtest_results table)
            metrics: Parsed metrics dictionary

        Returns:
            Database record ID if successful, None otherwise
        """
        if not self.enabled or not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                record_id = await conn.fetchval("""
                    INSERT INTO backtest_outputs (run_id, strategy, coins, days, output_text, metrics, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    RETURNING id
                """, run_id, strategy, coins, days, output_text, json.dumps(metrics) if metrics else None)

                print(f"✅ Backtest output saved to database (ID: {record_id})")
                return record_id

        except Exception as e:
            # Silently handle - table may not exist after consolidation
            # Output is already in backtest_runs table
            return None

    async def get_backtest_output(self, record_id: int) -> Optional[Dict]:
        """Get backtest output from database

        Args:
            record_id: Database record ID

        Returns:
            Dict with backtest data if found, None otherwise
        """
        if not self.enabled or not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, run_id, strategy, coins, days, output_text, metrics, created_at
                    FROM backtest_outputs
                    WHERE id = $1
                """, record_id)

                if row:
                    return {
                        "id": row["id"],
                        "run_id": row["run_id"],
                        "strategy": row["strategy"],
                        "coins": row["coins"],
                        "days": row["days"],
                        "output_text": row["output_text"],
                        "metrics": json.loads(row["metrics"]) if row["metrics"] else None,
                        "created_at": row["created_at"].isoformat()
                    }

        except Exception as e:
            print(f"❌ Failed to get backtest output: {e}")
            return None

    async def get_backtest_by_run_id(self, run_id: int) -> Optional[Dict]:
        """Get most recent backtest output by run_id

        Args:
            run_id: Backtest run ID

        Returns:
            Dict with backtest data if found, None otherwise
        """
        if not self.enabled or not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, run_id, strategy, coins, days, output_text, metrics, created_at
                    FROM backtest_outputs
                    WHERE run_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, run_id)

                if row:
                    return {
                        "id": row["id"],
                        "run_id": row["run_id"],
                        "strategy": row["strategy"],
                        "coins": row["coins"],
                        "days": row["days"],
                        "output_text": row["output_text"],
                        "metrics": json.loads(row["metrics"]) if row["metrics"] else None,
                        "created_at": row["created_at"].isoformat()
                    }

        except Exception as e:
            print(f"❌ Failed to get backtest by run_id: {e}")
            return None

    async def list_backtest_outputs(self, limit: int = 20) -> List[Dict]:
        """List recent backtest outputs

        Args:
            limit: Maximum number of records to return

        Returns:
            List of backtest output dicts
        """
        if not self.enabled or not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, run_id, strategy, coins, days, created_at
                    FROM backtest_outputs
                    ORDER BY created_at DESC
                    LIMIT $1
                """, limit)

                return [{
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "strategy": row["strategy"],
                    "coins": row["coins"],
                    "days": row["days"],
                    "created_at": row["created_at"].isoformat()
                } for row in rows]

        except Exception as e:
            print(f"❌ Failed to list backtest outputs: {e}")
            return []

    async def save_chat_message(self, role: str, message: str, timestamp: Optional[datetime] = None) -> Optional[int]:
        """Save chat message to database

        Args:
            role: "user" or "assistant"
            message: Message text
            timestamp: Message timestamp (default: now)

        Returns:
            Database record ID if successful, None otherwise
        """
        if not self.enabled or not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                record_id = await conn.fetchval("""
                    INSERT INTO chat_history (role, message, timestamp)
                    VALUES ($1, $2, $3)
                    RETURNING id
                """, role, message, timestamp or datetime.now())

                return record_id

        except Exception as e:
            print(f"❌ Failed to save chat message: {e}")
            return None

    async def get_chat_history(self, limit: int = 100) -> List[Dict]:
        """Get recent chat history

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of chat message dicts
        """
        if not self.enabled or not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, role, message, timestamp
                    FROM chat_history
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)

                # Reverse to get chronological order
                return [{
                    "id": row["id"],
                    "role": row["role"],
                    "message": row["message"],
                    "timestamp": row["timestamp"].isoformat()
                } for row in reversed(rows)]

        except Exception as e:
            print(f"❌ Failed to get chat history: {e}")
            return []

    async def save_chat_history_bulk(self, messages: List[Dict]) -> int:
        """Save multiple chat messages at once

        Args:
            messages: List of message dicts with role, message, timestamp

        Returns:
            Number of messages saved
        """
        if not self.enabled or not self.pool:
            return 0

        try:
            async with self.pool.acquire() as conn:
                count = 0
                for msg in messages:
                    await conn.execute("""
                        INSERT INTO chat_history (role, message, timestamp)
                        VALUES ($1, $2, $3)
                    """, msg["role"], msg["message"],
                    datetime.fromisoformat(msg["timestamp"]) if isinstance(msg["timestamp"], str) else msg["timestamp"])
                    count += 1

                return count

        except Exception as e:
            print(f"❌ Failed to save chat history bulk: {e}")
            return 0


# Global instance
db_storage = DatabaseStorage()


if __name__ == "__main__":
    # Test database storage
    import asyncio

    async def test():
        print("Testing Database Storage...")
        print(f"Enabled: {db_storage.enabled}")

        if db_storage.enabled:
            await db_storage.connect()

            # Test backtest output
            record_id = await db_storage.save_backtest_output(
                strategy="VolatilityHarvesting",
                coins=["BTC", "ETH"],
                output_text="Test output " + datetime.now().isoformat(),
                days=30,
                run_id=999,
                metrics={"return": 15.5, "trades": 42}
            )
            print(f"✅ Saved backtest output: ID {record_id}")

            # Retrieve it
            output = await db_storage.get_backtest_output(record_id)
            print(f"✅ Retrieved: {output['strategy']} - {output['coins']}")

            # List recent
            recent = await db_storage.list_backtest_outputs(limit=5)
            print(f"✅ Recent backtests: {len(recent)}")

            # Test chat history
            msg_id = await db_storage.save_chat_message("user", "Test message")
            print(f"✅ Saved chat message: ID {msg_id}")

            history = await db_storage.get_chat_history(limit=10)
            print(f"✅ Chat history: {len(history)} messages")

            await db_storage.disconnect()
        else:
            print("⚠️ Add DATABASE_URL to .env to test")

    asyncio.run(test())
