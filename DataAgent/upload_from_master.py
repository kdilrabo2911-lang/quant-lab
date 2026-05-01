"""
Upload historical data from master_data.csv to PostgreSQL
Uses UsdPrice for candle values and BtcPrice for close_btc field
"""
import asyncio
import asyncpg
import pandas as pd
import json
import sys
from pathlib import Path
from app.config import settings

MASTER_DATA_FILE = Path("/Users/dilrabokodirova/Desktop/KadirovQuantLab/master_data.csv")


async def main():
    print("=" * 70)
    print("UPLOADING FROM MASTER_DATA.CSV TO POSTGRESQL")
    print("=" * 70)
    print(f"Source: {MASTER_DATA_FILE}")
    print(f"Database: {settings.database_url[:50]}...")
    print("=" * 70)

    # Connect to database
    print("\nConnecting to database...")
    try:
        conn = await asyncpg.connect(settings.database_url)
        print("✓ Connected to database\n")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)

    # Drop existing data and recreate table
    print("Clearing existing data...")
    await conn.execute("DROP TABLE IF EXISTS ohlc_candles CASCADE")

    await conn.execute("""
        CREATE TABLE ohlc_candles (
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

    await conn.execute("""
        CREATE INDEX idx_ohlc_coin_time ON ohlc_candles (coin, time DESC);
    """)

    print("✓ Database schema ready\n")

    # Read master_data.csv
    print("Reading master_data.csv...")
    df_master = pd.read_csv(MASTER_DATA_FILE)
    print(f"✓ Loaded {len(df_master):,} rows\n")

    # Process data
    print("Processing and uploading data...")

    # Dictionary to accumulate candles for each coin
    coin_candles = {}

    processed_count = 0
    error_count = 0

    for idx, row in df_master.iterrows():
        if idx % 50000 == 0 and idx > 0:
            print(f"  Processed {idx:,}/{len(df_master):,} rows...")

        try:
            # Parse timestamp
            timestamp_str = row['Time']
            timestamp = pd.to_datetime(timestamp_str)

            # Parse PriceData JSON
            price_data = json.loads(row['PriceData'])

            # Extract data for each coin
            for coin, prices in price_data.items():
                coin_upper = coin.upper()

                if 'UsdPrice' not in prices or 'BtcPrice' not in prices:
                    continue

                usd_price = float(prices['UsdPrice'])
                btc_price = float(prices['BtcPrice'])

                # Initialize coin list if needed
                if coin_upper not in coin_candles:
                    coin_candles[coin_upper] = []

                # Add candle (using UsdPrice for OHLC, BtcPrice for close_btc)
                coin_candles[coin_upper].append((
                    coin_upper,
                    timestamp,
                    usd_price,  # open
                    usd_price,  # high
                    usd_price,  # low
                    usd_price,  # close
                    0.0,        # volume (not available)
                    btc_price   # close_btc
                ))

            processed_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  Error on row {idx}: {str(e)[:100]}")
            continue

    print(f"\n✓ Processing complete!")
    print(f"  Successful: {processed_count:,}")
    print(f"  Errors: {error_count:,}")
    print(f"  Coins found: {len(coin_candles)}\n")

    # Upload to database in batches
    print("Uploading to database...")

    batch_size = 10000
    total_inserted = 0

    for coin in sorted(coin_candles.keys()):
        candles = coin_candles[coin]
        print(f"[{coin}] Uploading {len(candles):,} candles...")

        # Upload in batches
        for i in range(0, len(candles), batch_size):
            batch = candles[i:i+batch_size]

            await conn.executemany("""
                INSERT INTO ohlc_candles (coin, time, open, high, low, close, volume, close_btc)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (coin, time) DO NOTHING
            """, batch)

            total_inserted += len(batch)

        print(f"[{coin}] ✓ Complete")

    # Get final statistics
    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)

    coin_counts = await conn.fetch("""
        SELECT coin, COUNT(*) as count, MIN(time) as earliest, MAX(time) as latest
        FROM ohlc_candles
        GROUP BY coin
        ORDER BY coin
    """)

    for row in coin_counts:
        print(f"  {row['coin']:10s} {row['count']:>8,} candles  ({row['earliest'].date()} to {row['latest'].date()})")

    total_db_count = await conn.fetchval("SELECT COUNT(*) FROM ohlc_candles")

    print("=" * 70)
    print(f"✓ Upload complete!")
    print(f"Total coins: {len(coin_counts)}")
    print(f"Total candles: {total_db_count:,}")
    print("=" * 70)

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
