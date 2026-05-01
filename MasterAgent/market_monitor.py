"""
Market Monitor - LIVE Event-Driven

Connects to DataAgent WebSocket and detects patterns in real-time
No polling - reacts instantly to price updates
"""

import asyncio
import websockets
import json
from datetime import datetime
from collections import deque
from typing import Dict, List
from communication import comm


class LiveMarketMonitor:
    def __init__(self, dataagent_url="ws://localhost:8000"):
        self.dataagent_url = dataagent_url
        self.price_history = {}  # coin -> deque of recent prices
        self.history_size = 100  # Keep last 100 prices per coin

        # Track state
        self.previous_patterns = set()

    async def connect_and_monitor(self, coins: List[str]):
        """
        Connect to DataAgent WebSocket and monitor coins in real-time

        Args:
            coins: List of coins to monitor (e.g., ["BTC", "ETH"])
        """
        print(f"🔗 Connecting to DataAgent WebSocket...")
        print(f"📊 Monitoring: {', '.join(coins)}")
        print(f"{'='*60}\n")

        # Initialize price history for each coin
        for coin in coins:
            self.price_history[coin] = deque(maxlen=self.history_size)

        # Connect to each coin's WebSocket
        tasks = [self.monitor_coin(coin) for coin in coins]
        await asyncio.gather(*tasks)

    async def monitor_coin(self, coin: str):
        """Monitor a single coin via WebSocket"""
        ws_url = f"{self.dataagent_url}/ws/prices/{coin}"

        while True:
            try:
                async with websockets.connect(ws_url) as websocket:
                    print(f"✅ Connected to {coin} WebSocket")

                    async for message in websocket:
                        # Parse price update
                        data = json.loads(message)
                        await self.on_price_update(coin, data)

            except Exception as e:
                print(f"❌ WebSocket error for {coin}: {e}")
                print(f"⏳ Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def on_price_update(self, coin: str, price_data: dict):
        """
        Called INSTANTLY when new price comes in

        This is where pattern detection happens LIVE
        """
        price = float(price_data.get('last', 0))
        timestamp = datetime.now()

        # Add to history
        self.price_history[coin].append({
            'price': price,
            'timestamp': timestamp
        })

        # Only analyze if we have enough data
        if len(self.price_history[coin]) < 20:
            return

        # DETECT PATTERNS INSTANTLY
        patterns = self.detect_patterns_live(coin)

        # Alert manager if new pattern detected
        for pattern in patterns:
            pattern_id = f"{coin}:{pattern['type']}"

            # Only alert once per pattern (don't spam)
            if pattern_id not in self.previous_patterns:
                self.previous_patterns.add(pattern_id)
                await self.alert_pattern(coin, pattern)

    def detect_patterns_live(self, coin: str) -> List[dict]:
        """
        Detect patterns in real-time as prices come in

        Returns list of detected patterns
        """
        patterns = []
        prices = [p['price'] for p in self.price_history[coin]]

        if len(prices) < 20:
            return patterns

        current_price = prices[-1]

        # Pattern 1: Sharp Drop (>5% in last 10 candles)
        recent_high = max(prices[-10:])
        drop_pct = ((recent_high - current_price) / recent_high) * 100

        if drop_pct > 5:
            patterns.append({
                'type': 'SHARP_DROP',
                'severity': 'HIGH' if drop_pct > 10 else 'MEDIUM',
                'drop_pct': drop_pct,
                'from_price': recent_high,
                'to_price': current_price,
                'message': f"{coin} dropped {drop_pct:.1f}% from ${recent_high:.2f} to ${current_price:.2f}"
            })

        # Pattern 2: Sharp Pump (>5% in last 10 candles)
        recent_low = min(prices[-10:])
        pump_pct = ((current_price - recent_low) / recent_low) * 100

        if pump_pct > 5:
            patterns.append({
                'type': 'SHARP_PUMP',
                'severity': 'HIGH' if pump_pct > 10 else 'MEDIUM',
                'pump_pct': pump_pct,
                'from_price': recent_low,
                'to_price': current_price,
                'message': f"{coin} pumped {pump_pct:.1f}% from ${recent_low:.2f} to ${current_price:.2f}"
            })

        # Pattern 3: Volatility Spike (price swinging a lot)
        if len(prices) >= 20:
            recent_std = self.calculate_volatility(prices[-20:])
            older_std = self.calculate_volatility(prices[-40:-20])

            if recent_std > older_std * 2:
                patterns.append({
                    'type': 'VOLATILITY_SPIKE',
                    'severity': 'MEDIUM',
                    'volatility_increase': (recent_std / older_std) * 100,
                    'message': f"{coin} volatility increased {(recent_std/older_std)*100:.0f}%"
                })

        # Pattern 4: Breakout (price breaking above recent resistance)
        if len(prices) >= 50:
            resistance = max(prices[-50:-5])  # Recent high (excluding last 5)
            if current_price > resistance * 1.02:  # 2% above resistance
                patterns.append({
                    'type': 'BREAKOUT',
                    'severity': 'MEDIUM',
                    'resistance': resistance,
                    'current': current_price,
                    'message': f"{coin} broke above resistance ${resistance:.2f} → ${current_price:.2f}"
                })

        return patterns

    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate standard deviation (simple volatility measure)"""
        if len(prices) < 2:
            return 0

        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return variance ** 0.5

    async def alert_pattern(self, coin: str, pattern: dict):
        """Alert manager when pattern detected"""
        urgency_map = {
            'HIGH': 'CRITICAL',
            'MEDIUM': 'MAJOR',
            'LOW': 'MINOR'
        }

        urgency = urgency_map.get(pattern['severity'], 'MINOR')

        message = f"""
🎯 PATTERN DETECTED: {pattern['type']}

{pattern['message']}

Coin: {coin}
Severity: {pattern['severity']}
Time: {datetime.now().strftime('%H:%M:%S')}
"""

        comm.notify_manager(message, urgency=urgency)

        # If critical, might need to take action
        if pattern['severity'] == 'HIGH':
            await self.handle_critical_pattern(coin, pattern)

    async def handle_critical_pattern(self, coin: str, pattern: dict):
        """Handle critical patterns that might need immediate action"""

        if pattern['type'] == 'SHARP_DROP' and pattern['drop_pct'] > 10:
            # Major drop - might need emergency action
            comm.notify_manager(
                f"⚠️ CRITICAL: {coin} dropped {pattern['drop_pct']:.1f}%\n"
                f"This might impact portfolio. Check active bots!",
                urgency='CRITICAL'
            )

        elif pattern['type'] == 'SHARP_PUMP' and pattern['pump_pct'] > 15:
            # Major pump - might be opportunity
            comm.notify_manager(
                f"🚀 OPPORTUNITY: {coin} pumped {pattern['pump_pct']:.1f}%\n"
                f"Other coins might follow. Consider quick positions?",
                urgency='MAJOR'
            )


async def main():
    """Test the live market monitor"""
    monitor = LiveMarketMonitor()

    # Monitor BTC, ETH, SOL live
    await monitor.connect_and_monitor(["BTC", "ETH", "SOL"])


if __name__ == "__main__":
    print("="*60)
    print("LIVE MARKET MONITOR - Event-Driven")
    print("="*60)
    print("\nListening to WebSocket... patterns will appear as detected\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✓ Monitor stopped")
