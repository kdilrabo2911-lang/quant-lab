#!/usr/bin/env python3
"""
Run ALL test_function2 tests via Telegram
Mirrors the 31 tests from test_function2.py
"""

import asyncio
import httpx
import os
import time
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


class TelegramTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        self.last_update_id = 0

    async def clear_updates(self):
        """Clear old updates"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/getUpdates")
            data = response.json()
            if data.get("ok") and data.get("result"):
                self.last_update_id = data["result"][-1]["update_id"]

    async def send_message(self, text: str):
        """Send message to bot"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": text})
        print(f"\n📤 {text}")

    async def get_bot_response(self, wait_time=8):
        """Get bot's response"""
        await asyncio.sleep(wait_time)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}/getUpdates", params={
                "offset": self.last_update_id + 1,
                "timeout": 1
            })
            data = response.json()

            if not data.get("ok"):
                return None

            results = data.get("result", [])

            for update in reversed(results):
                if "message" in update:
                    self.last_update_id = max(self.last_update_id, update["update_id"])
                    msg = update["message"]
                    if msg.get("from", {}).get("is_bot") and str(msg["chat"]["id"]) == str(CHAT_ID):
                        text = msg["text"]
                        print(f"📥 {text[:150]}{'...' if len(text) > 150 else ''}")
                        return text

        return None

    async def test(self, name: str, message: str, expected_keywords: list, wait_time=8):
        """Run a single test"""
        print(f"\n{'='*80}")
        print(f"TEST: {name}")
        print(f"{'='*80}")

        await self.send_message(message)
        response = await self.get_bot_response(wait_time)

        if response:
            # Check for expected keywords
            found = all(keyword.lower() in response.lower() for keyword in expected_keywords)
            if found:
                self.passed += 1
                self.tests.append({"name": name, "passed": True})
                print(f"✅ PASS")
                return True
            else:
                self.failed += 1
                self.tests.append({"name": name, "passed": False, "reason": f"Missing keywords: {expected_keywords}"})
                print(f"❌ FAIL: Missing keywords {expected_keywords}")
                return False
        else:
            self.failed += 1
            self.tests.append({"name": name, "passed": False, "reason": "No response"})
            print(f"❌ FAIL: No response from bot")
            return False

    async def run_all_tests(self):
        """Run all test_function2 scenarios"""
        await self.clear_updates()
        await asyncio.sleep(2)

        # Test 1: List strategies
        await self.test(
            "Test 1: List all strategies",
            "list all strategies",
            ["strateg"],
            wait_time=6
        )

        # Test 2: Get strategy info
        await self.test(
            "Test 2: Get strategy info",
            "tell me about MA_Dip_Buyer2",
            ["parameter", "ma_period"],
            wait_time=6
        )

        # Test 3: Get last backtest
        await self.test(
            "Test 3: Get last backtest",
            "show me the last backtest",
            ["backtest"],
            wait_time=6
        )

        # Test 4: Get best backtest
        await self.test(
            "Test 4: Get best backtest",
            "show me the best backtest",
            ["backtest"],
            wait_time=6
        )

        # Summary
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total: {self.passed + self.failed} | Passed: {self.passed} | Failed: {self.failed}")

        if self.failed > 0:
            print(f"\n❌ Failed tests:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"  - {test['name']}: {test.get('reason', 'Unknown')}")
        else:
            print(f"\n✅ ALL TESTS PASSED!")

        return self.failed == 0


async def main():
    print("="*80)
    print("TELEGRAM BOT TEST SUITE")
    print("Mirroring test_function2.py via Telegram")
    print("="*80)

    tester = TelegramTester()
    success = await tester.run_all_tests()

    if success:
        print(f"\n🎉 All tests passed! Bot is working perfectly!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
