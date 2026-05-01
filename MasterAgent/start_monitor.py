"""
Start the Live Market Monitor

This connects to DataAgent WebSocket and detects patterns in real-time
Press Ctrl+C to stop
"""

import asyncio
from market_monitor import LiveMarketMonitor

async def main():
    print("="*60)
    print("🤖 MASTER AGENT - LIVE MARKET MONITOR")
    print("="*60)
    print("\n📊 Monitoring: BTC, ETH, SOL")
    print("💡 Patterns will be detected and shown instantly")
    print("📝 All alerts saved to messages.txt")
    print("\nPress Ctrl+C to stop\n")
    print("="*60 + "\n")

    monitor = LiveMarketMonitor()

    # Monitor these coins live
    await monitor.connect_and_monitor(["BTC", "ETH", "SOL"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✓ Monitor stopped by user")
