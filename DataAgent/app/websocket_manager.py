"""
WebSocket Manager - Stream live prices from Kraken to connected clients
"""
import asyncio
import json
import logging
from typing import Dict, Set
import websockets
from websockets.exceptions import ConnectionClosed
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class KrakenWebSocketManager:
    """
    Manages WebSocket connection to Kraken and broadcasts to connected clients
    """

    KRAKEN_WS_URL = "wss://ws.kraken.com/"

    def __init__(self):
        self.kraken_ws = None
        self.clients: Dict[str, Set[WebSocket]] = {}  # coin -> set of client websockets
        self.is_running = False
        self.subscribed_coins: Set[str] = set()
        self.registered_strategies: Dict[str, Set[str]] = {}  # strategy_name -> set of coins

    async def start(self):
        """Start WebSocket connection to Kraken"""
        if self.is_running:
            logger.warning("WebSocket manager already running")
            return

        self.is_running = True
        logger.info("Starting Kraken WebSocket manager...")

        # Start background task to maintain Kraken connection
        asyncio.create_task(self._maintain_kraken_connection())

    async def stop(self):
        """Stop WebSocket connection"""
        self.is_running = False

        if self.kraken_ws:
            await self.kraken_ws.close()

        logger.info("Kraken WebSocket manager stopped")

    async def _maintain_kraken_connection(self):
        """Maintain connection to Kraken WebSocket (auto-reconnect)"""
        while self.is_running:
            try:
                logger.info(f"Connecting to Kraken WebSocket: {self.KRAKEN_WS_URL}")

                async with websockets.connect(self.KRAKEN_WS_URL) as ws:
                    self.kraken_ws = ws
                    logger.info("✓ Connected to Kraken WebSocket")

                    # Resubscribe to all coins after reconnection
                    if self.subscribed_coins:
                        await self._resubscribe_all()

                    # Listen for messages from Kraken
                    async for message in ws:
                        await self._handle_kraken_message(message)

            except ConnectionClosed:
                logger.warning("Kraken WebSocket connection closed, reconnecting in 5s...")
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Kraken WebSocket error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _handle_kraken_message(self, message: str):
        """
        Handle incoming message from Kraken

        Kraken ticker format (v1):
        [
            channelID,
            {
                "a": ["ask_price", "ask_whole_lot_volume", "ask_lot_volume"],
                "b": ["bid_price", "bid_whole_lot_volume", "bid_lot_volume"],
                "c": ["close_price", "close_lot_volume"],
                "v": ["volume_today", "volume_24h"],
                "p": ["vwap_today", "vwap_24h"],
                "t": [trade_count_today, trade_count_24h],
                "l": ["low_today", "low_24h"],
                "h": ["high_today", "high_24h"],
                "o": ["open_today", "open_24h"]
            },
            "ticker",
            "PAIR"
        ]
        """
        try:
            data = json.loads(message)

            # Skip heartbeat and system messages
            if isinstance(data, dict):
                event = data.get("event")
                if event == "heartbeat":
                    return
                elif event == "systemStatus":
                    logger.info(f"Kraken system status: {data.get('status')}")
                    return
                elif event == "subscriptionStatus":
                    logger.info(f"Subscription status: {data.get('status')} - {data.get('pair')}")
                    return

            # Handle ticker data
            if isinstance(data, list) and len(data) >= 4:
                ticker_data = data[1]
                channel_name = data[2]
                pair = data[3]

                if channel_name == "ticker":
                    # Extract coin symbol from pair (e.g., "XBT/USD" -> "BTC")
                    coin = self._normalize_coin_symbol(pair)

                    # Parse ticker data
                    ticker_info = {
                        "coin": coin,
                        "pair": pair,
                        "ask": float(ticker_data["a"][0]) if "a" in ticker_data else None,
                        "bid": float(ticker_data["b"][0]) if "b" in ticker_data else None,
                        "last": float(ticker_data["c"][0]) if "c" in ticker_data else None,
                        "volume_24h": float(ticker_data["v"][1]) if "v" in ticker_data else None,
                        "vwap_24h": float(ticker_data["p"][1]) if "p" in ticker_data else None,
                        "low_24h": float(ticker_data["l"][1]) if "l" in ticker_data else None,
                        "high_24h": float(ticker_data["h"][1]) if "h" in ticker_data else None,
                        "open_24h": float(ticker_data["o"][1]) if "o" in ticker_data else None,
                    }

                    # Broadcast to all clients subscribed to this coin
                    await self._broadcast_to_clients(coin, ticker_info)

        except Exception as e:
            logger.error(f"Error handling Kraken message: {e}")

    def _normalize_coin_symbol(self, pair: str) -> str:
        """
        Normalize Kraken pair to coin symbol
        XBT/USD -> BTC
        ETH/USD -> ETH
        """
        # Remove /USD suffix
        coin = pair.replace("/USD", "").replace("USD", "")

        # Convert XBT to BTC
        if coin == "XBT":
            coin = "BTC"
        if coin == "XXBT":
            coin = "BTC"
        if coin == "XETH":
            coin = "ETH"

        return coin.upper()

    async def _broadcast_to_clients(self, coin: str, ticker_info: dict):
        """Broadcast ticker data to all connected clients for this coin"""
        if coin not in self.clients or not self.clients[coin]:
            return

        # Create message
        message = json.dumps(ticker_info)

        # Send to all clients (remove disconnected ones)
        disconnected = set()
        for client in self.clients[coin]:
            try:
                await client.send_text(message)
            except Exception:
                disconnected.add(client)

        # Clean up disconnected clients
        if disconnected:
            self.clients[coin] -= disconnected
            logger.info(f"Removed {len(disconnected)} disconnected clients for {coin}")

    async def subscribe_coin(self, coin: str):
        """Subscribe to ticker updates for a coin"""
        if coin in self.subscribed_coins:
            return

        pair = self._get_kraken_pair(coin)

        subscribe_msg = {
            "event": "subscribe",
            "pair": [pair],
            "subscription": {"name": "ticker"}
        }

        if self.kraken_ws:
            await self.kraken_ws.send(json.dumps(subscribe_msg))
            self.subscribed_coins.add(coin)
            logger.info(f"Subscribed to {coin} ({pair}) ticker")

    async def _resubscribe_all(self):
        """Resubscribe to all coins after reconnection"""
        logger.info(f"Resubscribing to {len(self.subscribed_coins)} coins...")

        for coin in list(self.subscribed_coins):
            pair = self._get_kraken_pair(coin)
            subscribe_msg = {
                "event": "subscribe",
                "pair": [pair],
                "subscription": {"name": "ticker"}
            }
            await self.kraken_ws.send(json.dumps(subscribe_msg))

    def _get_kraken_pair(self, coin: str) -> str:
        """Convert coin symbol to Kraken pair"""
        # Map common symbols
        mapping = {
            "BTC": "XBT/USD",
            "ETH": "ETH/USD",
            "SOL": "SOL/USD",
            "LINK": "LINK/USD",
            "UNI": "UNI/USD",
            "AAVE": "AAVE/USD",
            "ADA": "ADA/USD",
            "DOT": "DOT/USD",
            "MATIC": "MATIC/USD",
        }

        return mapping.get(coin.upper(), f"{coin.upper()}/USD")

    async def add_client(self, coin: str, websocket: WebSocket):
        """Add a client WebSocket connection for a coin"""
        coin = coin.upper()

        if coin not in self.clients:
            self.clients[coin] = set()

        self.clients[coin].add(websocket)

        # Subscribe to Kraken if this is the first client for this coin
        if coin not in self.subscribed_coins:
            await self.subscribe_coin(coin)

        logger.info(f"Client connected to {coin} feed ({len(self.clients[coin])} total clients)")

    async def remove_client(self, coin: str, websocket: WebSocket):
        """Remove a client WebSocket connection"""
        coin = coin.upper()

        if coin in self.clients:
            self.clients[coin].discard(websocket)

            # If no more clients for this coin, we could unsubscribe from Kraken
            # (but keeping subscription is fine for simplicity)

            logger.info(f"Client disconnected from {coin} feed ({len(self.clients[coin])} remaining)")

    async def register_strategy(self, strategy_name: str, coins: list[str]) -> bool:
        """
        Register a trading strategy and its coins

        Args:
            strategy_name: Name of the strategy (e.g., "MovingAverages")
            coins: List of coins the strategy trades

        Returns:
            True if successful
        """
        coins_upper = {coin.upper() for coin in coins}

        # Store strategy registration
        self.registered_strategies[strategy_name] = coins_upper

        logger.info(f"Strategy '{strategy_name}' registered with coins: {coins_upper}")

        # Subscribe to new coins that weren't already subscribed
        for coin in coins_upper:
            if coin not in self.subscribed_coins:
                await self.subscribe_coin(coin)

        # Unsubscribe from coins that are no longer needed by any strategy
        await self._cleanup_subscriptions()

        return True

    async def unregister_strategy(self, strategy_name: str) -> bool:
        """
        Unregister a trading strategy

        Args:
            strategy_name: Name of the strategy to unregister

        Returns:
            True if successful
        """
        if strategy_name in self.registered_strategies:
            coins = self.registered_strategies[strategy_name]
            del self.registered_strategies[strategy_name]

            logger.info(f"Strategy '{strategy_name}' unregistered (was trading: {coins})")

            # Unsubscribe from coins that are no longer needed
            await self._cleanup_subscriptions()

            return True

        logger.warning(f"Strategy '{strategy_name}' not found for unregistration")
        return False

    async def _cleanup_subscriptions(self):
        """Unsubscribe from coins that are no longer needed by any strategy"""
        # Get all coins needed by all strategies
        needed_coins = set()
        for strategy_coins in self.registered_strategies.values():
            needed_coins.update(strategy_coins)

        # Unsubscribe from coins that are no longer needed
        for coin in list(self.subscribed_coins):
            if coin not in needed_coins:
                await self._unsubscribe_coin(coin)

    async def _unsubscribe_coin(self, coin: str):
        """Unsubscribe from ticker updates for a coin"""
        if coin not in self.subscribed_coins:
            return

        pair = self._get_kraken_pair(coin)

        unsubscribe_msg = {
            "event": "unsubscribe",
            "pair": [pair],
            "subscription": {"name": "ticker"}
        }

        if self.kraken_ws:
            await self.kraken_ws.send(json.dumps(unsubscribe_msg))
            self.subscribed_coins.discard(coin)
            logger.info(f"Unsubscribed from {coin} ({pair}) ticker")

    def get_active_coins(self) -> Set[str]:
        """Get list of coins currently being traded by registered strategies"""
        active_coins = set()
        for strategy_coins in self.registered_strategies.values():
            active_coins.update(strategy_coins)
        return active_coins

    def get_registered_strategies(self) -> Dict[str, Set[str]]:
        """Get all registered strategies and their coins"""
        return self.registered_strategies.copy()


# Global WebSocket manager instance
ws_manager = KrakenWebSocketManager()
