"""
Single Source of Truth: Database-Backed Strategy Store

ALL strategies stored in PostgreSQL database.
Files are just cache/deployment artifacts.

This eliminates:
- Redundant definitions in multiple places
- Sync issues between locations
- Manual file management
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Strategy:
    """Single strategy definition - stored in database"""
    id: int
    name: str
    version: str
    type: str  # "custom" or "builtin"

    # Core definition
    description: str
    parameters: Dict[str, Any]
    buy_conditions: List[Dict]
    sell_conditions: List[Dict]

    # Optimization
    optimization_grid: Optional[Dict[str, List]] = None

    # Metadata
    created_at: str = None
    updated_at: str = None
    created_by: str = "user"

    # Deployment (generated on-demand, not stored)
    _cached_csharp: Optional[str] = None
    _cached_cpp: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if not k.startswith('_')}


class StrategyStore:
    """
    Database-backed strategy store - SINGLE SOURCE OF TRUTH

    Strategies are stored in PostgreSQL.
    Code is generated on-demand when needed.
    """

    def __init__(self):
        self._db_pool = None

    async def connect(self):
        """Connect to database"""
        from db_storage import db_storage
        if not db_storage.pool:
            await db_storage.connect()
        self._db_pool = db_storage.pool

        # Create strategies table if not exists
        await self._create_table()

    async def _create_table(self):
        """Create strategies table"""
        await self._db_pool.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                version VARCHAR(50) NOT NULL,
                type VARCHAR(50) NOT NULL,
                description TEXT,
                parameters JSONB NOT NULL,
                buy_conditions JSONB NOT NULL,
                sell_conditions JSONB NOT NULL,
                optimization_grid JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255) DEFAULT 'user'
            )
        """)

        # Create index for faster lookups
        await self._db_pool.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name)
        """)

    async def create(self, strategy: Strategy) -> int:
        """Create new strategy - returns ID"""
        strategy_id = await self._db_pool.fetchval("""
            INSERT INTO strategies (
                name, version, type, description,
                parameters, buy_conditions, sell_conditions,
                optimization_grid, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            strategy.name,
            strategy.version,
            strategy.type,
            strategy.description,
            json.dumps(strategy.parameters),
            json.dumps(strategy.buy_conditions),
            json.dumps(strategy.sell_conditions),
            json.dumps(strategy.optimization_grid) if strategy.optimization_grid else None,
            strategy.created_by
        )

        return strategy_id

    async def get(self, name: str) -> Optional[Strategy]:
        """Get strategy by name"""
        row = await self._db_pool.fetchrow("""
            SELECT * FROM strategies
            WHERE name = $1
            ORDER BY updated_at DESC
            LIMIT 1
        """, name)

        if not row:
            return None

        return Strategy(
            id=row['id'],
            name=row['name'],
            version=row['version'],
            type=row['type'],
            description=row['description'],
            parameters=json.loads(row['parameters']) if isinstance(row['parameters'], str) else row['parameters'],
            buy_conditions=json.loads(row['buy_conditions']) if isinstance(row['buy_conditions'], str) else row['buy_conditions'],
            sell_conditions=json.loads(row['sell_conditions']) if isinstance(row['sell_conditions'], str) else row['sell_conditions'],
            optimization_grid=json.loads(row['optimization_grid']) if row['optimization_grid'] and isinstance(row['optimization_grid'], str) else row['optimization_grid'],
            created_at=row['created_at'].isoformat() if row['created_at'] else None,
            updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
            created_by=row['created_by']
        )

    async def list_all(self) -> List[Strategy]:
        """List all strategies"""
        rows = await self._db_pool.fetch("""
            SELECT * FROM strategies
            ORDER BY name
        """)

        return [Strategy(
            id=row['id'],
            name=row['name'],
            version=row['version'],
            type=row['type'],
            description=row['description'],
            parameters=json.loads(row['parameters']) if isinstance(row['parameters'], str) else row['parameters'],
            buy_conditions=json.loads(row['buy_conditions']) if isinstance(row['buy_conditions'], str) else row['buy_conditions'],
            sell_conditions=json.loads(row['sell_conditions']) if isinstance(row['sell_conditions'], str) else row['sell_conditions'],
            optimization_grid=json.loads(row['optimization_grid']) if row['optimization_grid'] and isinstance(row['optimization_grid'], str) else row['optimization_grid'],
            created_at=row['created_at'].isoformat() if row['created_at'] else None,
            updated_at=row['updated_at'].isoformat() if row['updated_at'] else None,
            created_by=row['created_by']
        ) for row in rows]

    async def update(self, strategy: Strategy):
        """Update existing strategy"""
        await self._db_pool.execute("""
            UPDATE strategies
            SET version = $2,
                description = $3,
                parameters = $4,
                buy_conditions = $5,
                sell_conditions = $6,
                optimization_grid = $7,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = $1
        """,
            strategy.name,
            strategy.version,
            strategy.description,
            json.dumps(strategy.parameters),
            json.dumps(strategy.buy_conditions),
            json.dumps(strategy.sell_conditions),
            json.dumps(strategy.optimization_grid) if strategy.optimization_grid else None
        )

    async def delete(self, name: str):
        """Delete strategy"""
        await self._db_pool.execute("""
            DELETE FROM strategies WHERE name = $1
        """, name)

    async def get_or_generate_code(self, name: str, language: str = "csharp") -> Optional[str]:
        """
        Get strategy code (generate if not cached)

        This is where code generation happens on-demand.
        No need to store code files everywhere!
        """
        strategy = await self.get(name)
        if not strategy:
            return None

        if language == "csharp":
            if strategy._cached_csharp:
                return strategy._cached_csharp

            # Generate C# code on-demand
            from csharp_full_generator import FullCSharpGenerator
            generator = FullCSharpGenerator()

            # Convert to StrategyDefinition format (legacy)
            from strategy_definition import StrategyDefinition, StrategyParameter, Condition

            params = {
                name: StrategyParameter(
                    name=name,
                    value=param['value'],
                    type=param['type'],
                    description=param.get('description', ''),
                    min_value=param.get('min_value'),
                    max_value=param.get('max_value'),
                    optimizable=param.get('optimizable', True)
                )
                for name, param in strategy.parameters.items()
            }

            legacy_strategy = StrategyDefinition(
                name=strategy.name,
                description=strategy.description,
                parameters=params,
                buy_conditions=[Condition(**c) for c in strategy.buy_conditions],
                sell_conditions=[Condition(**c) for c in strategy.sell_conditions],
                version=strategy.version
            )

            files = generator.generate(legacy_strategy)
            strategy._cached_csharp = files  # Cache it
            return files

        elif language == "cpp":
            # TODO: Implement C++ generation
            pass

        return None


# Global singleton
_store = None

def get_store() -> StrategyStore:
    """Get global strategy store"""
    global _store
    if _store is None:
        _store = StrategyStore()
    return _store


# Migration utilities
async def migrate_from_files():
    """
    One-time migration: Import all existing strategies into database

    This consolidates:
    - MasterAgent/strategies/*.json → database
    - Removes redundancy
    """
    store = get_store()
    await store.connect()

    migrated = []

    # Migrate from MasterAgent/strategies
    strategies_dir = Path(__file__).parent / "strategies"

    if strategies_dir.exists():
        for strategy_dir in strategies_dir.iterdir():
            if not strategy_dir.is_dir():
                continue

            # Find latest JSON
            json_files = [f for f in strategy_dir.glob("*.json")
                         if "optimization_grid" not in f.name]

            if not json_files:
                continue

            latest = None
            for f in json_files:
                if "_latest.json" in f.name:
                    latest = f
                    break

            if not latest:
                latest = sorted(json_files)[-1]

            try:
                with open(latest) as f:
                    data = json.load(f)

                # Check if already in database
                existing = await store.get(strategy_dir.name)
                if existing:
                    print(f"  ⏭️  {strategy_dir.name} already in database")
                    continue

                # Create strategy object
                strategy = Strategy(
                    id=0,  # Will be assigned by database
                    name=strategy_dir.name,
                    version=data.get("version", "1.0"),
                    type="custom",
                    description=data.get("description", ""),
                    parameters=data.get("parameters", {}),
                    buy_conditions=data.get("buy_conditions", []),
                    sell_conditions=data.get("sell_conditions", []),
                    optimization_grid=None,  # Load separately
                    created_by="migration"
                )

                # Load optimization grid if exists
                grid_file = strategy_dir / "optimization_grid.json"
                if grid_file.exists():
                    with open(grid_file) as f:
                        strategy.optimization_grid = json.load(f)

                # Insert into database
                strategy_id = await store.create(strategy)
                migrated.append(strategy_dir.name)
                print(f"  ✅ Migrated {strategy_dir.name} (ID={strategy_id})")

            except Exception as e:
                print(f"  ❌ Failed to migrate {strategy_dir.name}: {e}")

    print(f"\n📊 Migrated {len(migrated)} strategies to database")
    return migrated


async def cleanup_redundant_files():
    """
    AFTER migration: Remove redundant file copies

    WARNING: Only run after verifying database has everything!
    """
    print("\n⚠️  This will DELETE redundant strategy files!")
    print("Make sure database migration succeeded first.")

    # TODO: Implement cleanup after confirming migration worked
    pass
