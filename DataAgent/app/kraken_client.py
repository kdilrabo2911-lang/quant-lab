"""
Kraken Client - Fetch latest OHLC candles from Kraken REST API
Based on existing C# KrakenClient implementation
"""
import httpx
import logging
import time
from typing import List, Optional
from datetime import datetime, timezone
from .models import OHLCCandle

logger = logging.getLogger(__name__)


class KrakenClient:
    """Client for Kraken public REST API"""

    BASE_URL = "https://api.kraken.com/0/public"
    RATE_LIMIT_DELAY = 0.5  # 500ms between requests

    # Kraken pair mappings (from C# code)
    PAIR_MAPPING = {
        "BTC": "XXBTZUSD",
        "ETH": "XETHZUSD",
        "SOL": "SOLUSD",
        "LINK": "LINKUSD",
        "UNI": "UNIUSD",
        "AAVE": "AAVEUSD",
        "ADA": "ADAUSD",
        "DOT": "DOTUSD",
        "MATIC": "MATICUSD",
        "RNDR": "RENDERUSD",  # Render token
        "RENDER": "RENDERUSD",  # Alternative name
    }

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.last_request_time = 0
        logger.info("KrakenClient initialized")

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _get_kraken_pair(self, coin: str) -> str:
        """Convert coin symbol to Kraken pair name"""
        return self.PAIR_MAPPING.get(coin.upper(), f"{coin.upper()}USD")

    def get_btc_price(self) -> float:
        """Get current BTC price in USD"""
        try:
            self._rate_limit()

            url = f"{self.BASE_URL}/Ticker"
            params = {"pair": "XXBTZUSD"}

            response = self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("error"):
                logger.error(f"Error fetching BTC price: {data['error']}")
                return 1.0

            result = data.get("result", {})

            # Find the BTC key (usually XXBTZUSD)
            btc_key = next((k for k in result.keys() if "XBT" in k), None)

            if not btc_key:
                logger.error("BTC price not found in response")
                return 1.0

            ticker_data = result[btc_key]
            last_price = float(ticker_data["c"][0])  # c = close price [price, lot volume]

            return last_price if last_price > 0 else 1.0

        except Exception as e:
            logger.error(f"Error fetching BTC price: {e}")
            return 1.0

    def fetch_latest_candles(
        self,
        coin: str,
        interval_minutes: int = 5,
        count: int = 10
    ) -> List[OHLCCandle]:
        """
        Fetch latest OHLC candles from Kraken
        Matches the C# FetchOhlcDataAsync implementation

        Args:
            coin: Coin symbol (e.g., 'BTC', 'ETH')
            interval_minutes: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            count: Number of recent candles to return

        Returns:
            List of OHLCCandle objects, sorted by time (oldest first)
        """
        pair = self._get_kraken_pair(coin)

        try:
            self._rate_limit()

            logger.info(f"Fetching OHLC data for {coin} (pair: {pair}, interval: {interval_minutes}min)")

            # Kraken OHLC endpoint
            url = f"{self.BASE_URL}/OHLC"
            params = {
                "pair": pair,
                "interval": str(interval_minutes),
            }

            response = self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get("error") and len(data["error"]) > 0:
                logger.error(f"Kraken API error for {coin}: {data['error']}")
                return []

            result = data.get("result", {})

            # Find the data key (not 'last')
            data_key = next((k for k in result.keys() if k != "last"), None)

            if not data_key:
                logger.error(f"No OHLC data found for {coin}")
                return []

            ohlc_data = result[data_key]

            # Get BTC price for close_btc calculation
            btc_price = self.get_btc_price()

            candles = []

            # Kraken OHLC format: [time, open, high, low, close, vwap, volume, count]
            for row in ohlc_data[-count:]:  # Take last N candles
                timestamp = datetime.fromtimestamp(int(row[0]), tz=timezone.utc)
                open_price = float(row[1])
                high_price = float(row[2])
                low_price = float(row[3])
                close_price = float(row[4])
                # vwap = float(row[5])  # Not used
                volume = float(row[6])
                # trade_count = int(row[7])  # Not used

                # Calculate close_btc
                close_btc = close_price / btc_price if btc_price > 0 else 0.0

                candle = OHLCCandle(
                    time=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    close_btc=close_btc
                )
                candles.append(candle)

            logger.info(f"Fetched {len(candles)} candles for {coin} (latest: {candles[-1].time if candles else 'N/A'})")
            return candles

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {coin}: {e.response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Error fetching {coin} from Kraken: {e}")
            return []

    def close(self):
        """Close HTTP client"""
        self.client.close()
