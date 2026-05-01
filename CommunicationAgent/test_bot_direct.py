#!/usr/bin/env python3
"""
Test Telegram Bot - Direct API calls (no polling conflict)
"""

import asyncio
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv
import time

# Load environment
env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


class TelegramTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    async def send_message(self, text: str) -> dict:
        """Send message via HTTP API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/sendMessage",
                json={"chat_id": CHAT_ID, "text": text}
            )
            return response.json()

    async def get_updates(self, offset=None) -> dict:
        """Get updates via HTTP API"""
        async with httpx.AsyncClient() as client:
            params = {"timeout": 1}
            if offset:
                params["offset"] = offset
            response = await client.get(f"{BASE_URL}/getUpdates", params=params)
            return response.json()

    async def send_and_check(self, message: str, wait_time: int = 6):
        """Send message and return latest bot response"""
        print(f"\n📤 Sending: {message}")

        # Send message
        await self.send_message(message)

        # Wait for bot to process
        await asyncio.sleep(wait_time)

        # Get recent messages
        updates_response = await self.get_updates()

        if not updates_response.get("ok"):
            print(f"❌ Failed to get updates: {updates_response}")
            return None

        # Find latest bot response
        results = updates_response.get("result", [])
        bot_messages = []

        for update in reversed(results[-20:]):  # Check last 20 updates
            if "message" in update:
                msg = update["message"]
                if msg.get("from", {}).get("is_bot") and str(msg["chat"]["id"]) == str(CHAT_ID):
                    bot_messages.append(msg["text"])

        if bot_messages:
            response = bot_messages[0]
            print(f"📥 Response ({len(response)} chars): {response[:200]}{'...' if len(response) > 200 else ''}")
            return response
        else:
            print("❌ No bot response found")
            return None

    def check(self, name: str, condition: bool, msg=""):
        """Check test result"""
        if condition:
            self.passed += 1
            print(f"✅ {name}")
            if msg:
                print(f"   {msg}")
        else:
            self.failed += 1
            print(f"❌ {name}")
            if msg:
                print(f"   {msg}")

    async def run_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("TELEGRAM BOT TESTS (Same as test_function2.py)")
        print("=" * 80)

        # Test 1: Start
        print("\n[TEST 1] /start")
        resp = await self.send_and_check("/start", wait_time=4)
        self.check("Start command", resp is not None and "welcome" in resp.lower())

        # Test 2: List strategies
        print("\n[TEST 2] List all strategies")
        resp = await self.send_and_check("list all strategies", wait_time=6)
        self.check("List strategies", resp is not None)
        if resp:
            self.check("Has strategy data", "strateg" in resp.lower() or "found" in resp.lower())

        # Test 3: Get strategy info
        print("\n[TEST 3] Get strategy info")
        resp = await self.send_and_check("tell me about MA_Dip_Buyer", wait_time=6)
        self.check("Get strategy info", resp is not None)

        # Test 4: Last backtest
        print("\n[TEST 4] Get last backtest")
        resp = await self.send_and_check("show me the last backtest", wait_time=6)
        self.check("Last backtest", resp is not None)

        # Test 5: Best backtest
        print("\n[TEST 5] Get best backtest")
        resp = await self.send_and_check("show me the best backtest", wait_time=6)
        self.check("Best backtest", resp is not None)

        # Test 6: Run backtest
        print("\n[TEST 6] Run backtest")
        resp = await self.send_and_check("run backtest for MA_Dip_Buyer on BTC for 30 days", wait_time=10)
        self.check("Run backtest", resp is not None)

        # Test 7: Deploy
        print("\n[TEST 7] Deploy for backtest")
        resp = await self.send_and_check("deploy MA_Dip_Buyer for backtest", wait_time=8)
        self.check("Deploy", resp is not None)

        # Summary
        print("\n" + "=" * 80)
        print(f"RESULTS: {self.passed} passed, {self.failed} failed")
        print("=" * 80)

        if self.failed == 0:
            print("✅ ALL TESTS PASSED!")
        else:
            print(f"❌ {self.failed} tests need fixing")


async def main():
    tester = TelegramTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
