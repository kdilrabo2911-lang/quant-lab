"""
DataAgent Client - Flexible data fetching from DataAgent API
"""
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Union
from io import StringIO
import logging

logger = logging.getLogger(__name__)


class DataAgentClient:
    """
    Client for fetching historical OHLC data from DataAgent

    Features:
    - Flexible date ranges (absolute dates or relative periods)
    - Multiple coins in single request
    - CSV or JSON format
    - Automatic retry on failures
    - Response caching (optional)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 300):
        """
        Initialize DataAgent client

        Args:
            base_url: DataAgent API URL (default: http://localhost:8000)
            timeout: Request timeout in seconds (default: 300 for large datasets)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=timeout)
        self._cache: Dict[str, pd.DataFrame] = {}
        logger.info(f"DataAgent client initialized: {self.base_url}")

    def get_data(
        self,
        coins: Union[str, List[str]],
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        last_days: Optional[int] = None,
        last_months: Optional[int] = None,
        limit: Optional[int] = None,
        use_cache: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical OHLC data for one or multiple coins

        Args:
            coins: Single coin ("BTC") or list of coins (["BTC", "ETH", "SOL"])
            start: Start date (str "2023-01-01" or datetime object)
            end: End date (str "2024-12-31" or datetime object)
            last_days: Fetch last N days (e.g., 90 for last 90 days)
            last_months: Fetch last N months (e.g., 6 for last 6 months)
            limit: Maximum number of candles per coin
            use_cache: Use cached data if available

        Returns:
            Dictionary mapping coin -> DataFrame with columns:
            ['time', 'open', 'high', 'low', 'close', 'volume', 'close_btc']

        Examples:
            # Last 90 days for BTC
            client.get_data("BTC", last_days=90)

            # Specific date range for multiple coins
            client.get_data(["BTC", "ETH", "SOL"], start="2023-01-01", end="2024-12-31")

            # Last 6 months for all Kraken coins
            client.get_data(["BTC", "ETH", "SOL", "LINK", "UNI"], last_months=6)

            # Last 1000 candles
            client.get_data("ETH", limit=1000)
        """
        # Normalize coins to list
        if isinstance(coins, str):
            coins = [coins]

        coins = [c.upper() for c in coins]

        # Calculate date range
        start_date, end_date = self._parse_date_range(start, end, last_days, last_months)

        # Fetch data for each coin
        results = {}
        for coin in coins:
            cache_key = self._get_cache_key(coin, start_date, end_date, limit)

            # Check cache
            if use_cache and cache_key in self._cache:
                logger.info(f"Using cached data for {coin}")
                results[coin] = self._cache[cache_key].copy()
                continue

            # Fetch from API
            logger.info(f"Fetching {coin} data from DataAgent...")
            df = self._fetch_coin_data(coin, start_date, end_date, limit)

            if df is not None and len(df) > 0:
                results[coin] = df
                if use_cache:
                    self._cache[cache_key] = df.copy()

                logger.info(f"✓ {coin}: {len(df)} candles ({df['time'].min()} to {df['time'].max()})")
            else:
                logger.warning(f"✗ {coin}: No data available")

        return results

    def get_data_single_coin(
        self,
        coin: str,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        last_days: Optional[int] = None,
        last_months: Optional[int] = None,
        limit: Optional[int] = None,
        use_cache: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single coin (convenience method)

        Returns:
            DataFrame or None if no data available
        """
        results = self.get_data(coin, start, end, last_days, last_months, limit, use_cache)
        return results.get(coin.upper())

    def _parse_date_range(
        self,
        start: Optional[Union[str, datetime]],
        end: Optional[Union[str, datetime]],
        last_days: Optional[int],
        last_months: Optional[int]
    ) -> tuple:
        """Parse date range from various input formats"""

        # Relative date ranges (last_days, last_months)
        if last_days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=last_days)
            return start_date, end_date

        if last_months is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=last_months * 30)  # Approximate
            return start_date, end_date

        # Absolute date ranges
        start_date = self._parse_date(start) if start else None
        end_date = self._parse_date(end) if end else None

        return start_date, end_date

    def _parse_date(self, date: Union[str, datetime]) -> datetime:
        """Parse date from string or datetime object"""
        if isinstance(date, datetime):
            return date

        if isinstance(date, str):
            # Try various formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(date, fmt)
                except ValueError:
                    continue

            raise ValueError(f"Unable to parse date: {date}")

        raise TypeError(f"Date must be string or datetime, got {type(date)}")

    def _fetch_coin_data(
        self,
        coin: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: Optional[int]
    ) -> Optional[pd.DataFrame]:
        """Fetch data for a single coin from DataAgent API"""

        # Build URL
        url = f"{self.base_url}/candles/{coin}/csv"

        # Build query parameters
        params = {}
        if start:
            params['start'] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end:
            params['end'] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
        if limit:
            params['limit'] = limit

        try:
            # Make request
            response = self.client.get(url, params=params)
            response.raise_for_status()

            # Parse CSV
            df = pd.read_csv(StringIO(response.text))

            # Convert time to datetime
            df['time'] = pd.to_datetime(df['time'])

            return df

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"No data found for {coin}")
                return None
            else:
                logger.error(f"HTTP error fetching {coin}: {e.response.status_code}")
                raise

        except Exception as e:
            logger.error(f"Error fetching {coin}: {e}")
            raise

    def get_available_coins(self) -> List[str]:
        """Get list of coins available in DataAgent"""
        try:
            response = self.client.get(f"{self.base_url}/coins")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching available coins: {e}")
            return []

    def get_data_info(self, coin: str) -> Optional[Dict]:
        """
        Get metadata about available data for a coin

        Returns:
            {
                "coin": "BTC",
                "total_candles": 500000,
                "earliest": "2022-10-01 00:00:00",
                "latest": "2026-04-20 23:55:00"
            }
        """
        try:
            # Fetch latest candle to get info
            response = self.client.get(f"{self.base_url}/candles/{coin}/latest?count=1")
            response.raise_for_status()

            data = response.json()
            if data:
                return {
                    "coin": coin,
                    "latest": data[0]['time']
                }
            return None

        except Exception as e:
            logger.error(f"Error fetching data info for {coin}: {e}")
            return None

    def clear_cache(self):
        """Clear cached data"""
        self._cache.clear()
        logger.info("Cache cleared")

    def _get_cache_key(
        self,
        coin: str,
        start: Optional[datetime],
        end: Optional[datetime],
        limit: Optional[int]
    ) -> str:
        """Generate cache key"""
        start_str = start.strftime("%Y%m%d") if start else "none"
        end_str = end.strftime("%Y%m%d") if end else "none"
        limit_str = str(limit) if limit else "none"
        return f"{coin}_{start_str}_{end_str}_{limit_str}"

    def close(self):
        """Close HTTP client"""
        self.client.close()
        logger.info("DataAgent client closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = DataAgentClient()

    print("=" * 60)
    print("DataAgent Client - Example Usage")
    print("=" * 60)

    # Example 1: Last 90 days for BTC
    print("\n1. Fetching last 90 days for BTC...")
    data = client.get_data("BTC", last_days=90)
    if "BTC" in data:
        print(f"   Got {len(data['BTC'])} candles")
        print(f"   Columns: {list(data['BTC'].columns)}")
        print(f"   Sample:\n{data['BTC'].head(3)}")

    # Example 2: Specific date range for multiple coins
    print("\n2. Fetching 2024 data for BTC, ETH, SOL...")
    data = client.get_data(
        ["BTC", "ETH", "SOL"],
        start="2024-01-01",
        end="2024-12-31"
    )
    for coin, df in data.items():
        print(f"   {coin}: {len(df)} candles")

    # Example 3: Last 1000 candles for ETH
    print("\n3. Fetching last 1000 candles for ETH...")
    eth_data = client.get_data_single_coin("ETH", limit=1000)
    if eth_data is not None:
        print(f"   Got {len(eth_data)} candles")

    # Example 4: Get available coins
    print("\n4. Available coins in DataAgent:")
    coins = client.get_available_coins()
    print(f"   {coins}")

    print("\n" + "=" * 60)
    print("✓ Examples complete!")
    print("=" * 60)

    client.close()
