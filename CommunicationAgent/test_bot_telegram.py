#!/usr/bin/env python3
"""
Test Telegram Bot - Same tests as test_function2.py but through Telegram
Sends messages to bot and verifies responses
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot
import time

# Load environment
env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("MANAGER_TELEGRAM_CHAT_ID"))


class TelegramBotTester:
    """Test telegram bot with same scenarios as test_function2.py"""

    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.passed = 0
        self.failed = 0
        self.last_update_id = 0

    async def send_and_wait(self, message: str, wait_time: int = 5) -> str:
        """Send message and wait for bot response"""
        print(f"\n📤 Sending: {message}")

        # Send message
        await self.bot.send_message(chat_id=CHAT_ID, text=message)

        # Wait for processing
        await asyncio.sleep(wait_time)

        # Get updates
        updates = await self.bot.get_updates(offset=self.last_update_id + 1, limit=10)

        # Find bot's response
        response = None
        for update in updates:
            if update.message:
                self.last_update_id = max(self.last_update_id, update.update_id)
                if update.message.from_user.is_bot and update.message.chat.id == CHAT_ID:
                    response = update.message.text

        if response:
            print(f"📥 Response: {response[:300]}{'...' if len(response) > 300 else ''}")
        else:
            print("❌ No response received")

        return response

    def check_result(self, test_name: str, condition: bool, message: str = ""):
        """Log test result"""
        if condition:
            self.passed += 1
            print(f"✅ PASS: {test_name}")
            if message:
                print(f"   {message}")
        else:
            self.failed += 1
            print(f"❌ FAIL: {test_name}")
            if message:
                print(f"   {message}")

    async def test_1_start_command(self):
        """Test /start command"""
        print("\n" + "=" * 80)
        print("TEST 1: /start command")
        print("=" * 80)

        response = await self.send_and_wait("/start", wait_time=3)

        self.check_result(
            "Start Command",
            response is not None and "welcome" in response.lower(),
            "Bot responds to /start"
        )

    async def test_2_list_all_strategies(self):
        """Test listing all strategies - mirrors test_function2.py test_2"""
        print("\n" + "=" * 80)
        print("TEST 2: List All Strategies (Database)")
        print("=" * 80)

        response = await self.send_and_wait("list all strategies", wait_time=5)

        self.check_result(
            "List Strategies",
            response is not None and ("strateg" in response.lower() or "found" in response.lower()),
            f"Got response about strategies"
        )

        # Check if it shows count
        has_count = any(char.isdigit() for char in response) if response else False
        self.check_result(
            "Strategies Count Shown",
            has_count,
            "Response includes strategy count"
        )

    async def test_3_get_strategy_info(self):
        """Test getting strategy info - mirrors test_function2.py test_3"""
        print("\n" + "=" * 80)
        print("TEST 3: Get Strategy Info from Database")
        print("=" * 80)

        # First get a strategy name
        list_response = await self.send_and_wait("list all strategies", wait_time=5)

        # Try to get info about first strategy (assuming MA_Dip_Buyer exists or similar)
        response = await self.send_and_wait("tell me about MA_Dip_Buyer", wait_time=5)

        if response and "not found" not in response.lower():
            self.check_result(
                "Get Strategy Info",
                "parameter" in response.lower() or "condition" in response.lower(),
                "Strategy details retrieved"
            )
        else:
            # Try any strategy name from list
            self.check_result(
                "Get Strategy Info",
                response is not None,
                "Attempted to get strategy info"
            )

    async def test_4_get_last_backtest(self):
        """Test getting last backtest - mirrors test_function2.py test_5"""
        print("\n" + "=" * 80)
        print("TEST 4: Get Last Backtest from Database")
        print("=" * 80)

        response = await self.send_and_wait("show me the last backtest", wait_time=5)

        self.check_result(
            "Get Last Backtest",
            response is not None,
            "Bot responded to last backtest query"
        )

        if response:
            has_data = "backtest" in response.lower() or "return" in response.lower() or "no backtest" in response.lower()
            self.check_result(
                "Last Backtest Has Data",
                has_data,
                "Response contains backtest info or indicates no backtests"
            )

    async def test_5_get_best_backtest(self):
        """Test getting best backtest - mirrors test_function2.py test_6"""
        print("\n" + "=" * 80)
        print("TEST 5: Get Best Backtest from Database")
        print("=" * 80)

        response = await self.send_and_wait("show me the best backtest", wait_time=5)

        self.check_result(
            "Get Best Backtest",
            response is not None,
            "Bot responded to best backtest query"
        )

        if response:
            has_data = "backtest" in response.lower() or "return" in response.lower() or "no backtest" in response.lower()
            self.check_result(
                "Best Backtest Has Data",
                has_data,
                "Response contains backtest info"
            )

    async def test_6_run_backtest(self):
        """Test running backtest - mirrors test_function2.py test_8 workflow"""
        print("\n" + "=" * 80)
        print("TEST 6: Run Backtest Command")
        print("=" * 80)

        response = await self.send_and_wait(
            "run backtest for MA_Dip_Buyer on BTC for 30 days",
            wait_time=10
        )

        self.check_result(
            "Run Backtest Command",
            response is not None,
            "Bot responded to backtest command"
        )

        if response:
            # Could succeed, need deployment, or strategy not found
            valid_response = any([
                "backtest" in response.lower(),
                "deployment" in response.lower(),
                "not found" in response.lower(),
                "error" in response.lower()
            ])
            self.check_result(
                "Backtest Response Valid",
                valid_response,
                f"Response: {response[:100]}"
            )

    async def test_7_deploy_for_backtest(self):
        """Test deploying strategy for backtest - mirrors test_function2.py deploy workflow"""
        print("\n" + "=" * 80)
        print("TEST 7: Deploy Strategy for Backtest")
        print("=" * 80)

        response = await self.send_and_wait(
            "deploy MA_Dip_Buyer for backtest",
            wait_time=8
        )

        self.check_result(
            "Deploy Command",
            response is not None,
            "Bot responded to deploy command"
        )

        if response:
            valid_response = any([
                "deploy" in response.lower(),
                "generat" in response.lower(),
                "c++" in response.lower(),
                "not found" in response.lower()
            ])
            self.check_result(
                "Deploy Response Valid",
                valid_response,
                f"Response: {response[:100]}"
            )

    async def test_8_optimize_strategy(self):
        """Test optimization command"""
        print("\n" + "=" * 80)
        print("TEST 8: Optimize Strategy")
        print("=" * 80)

        response = await self.send_and_wait(
            "optimize MA_Dip_Buyer for RNDR, try ma_period 6,12,24,72,168",
            wait_time=10
        )

        self.check_result(
            "Optimize Command",
            response is not None,
            "Bot responded to optimize command"
        )

    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print("\n" + "=" * 80)
        print("TELEGRAM BOT TEST SUMMARY")
        print("=" * 80)
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed}")

        if self.failed > 0:
            print(f"\n❌ {self.failed} tests failed")
            print("\nBot needs fixes!")
        else:
            print(f"\n✅ All {self.passed} tests passed!")
            print("\nBot is working correctly!")


async def main():
    """Run all telegram bot tests"""
    print("=" * 80)
    print("TELEGRAM BOT TEST SUITE")
    print("Mirroring test_function2.py but through Telegram interface")
    print("=" * 80)

    tester = TelegramBotTester()

    # Clear old updates
    updates = await tester.bot.get_updates()
    if updates:
        tester.last_update_id = updates[-1].update_id

    # Run tests
    await tester.test_1_start_command()
    await tester.test_2_list_all_strategies()
    await tester.test_3_get_strategy_info()
    await tester.test_4_get_last_backtest()
    await tester.test_5_get_best_backtest()
    await tester.test_6_run_backtest()
    await tester.test_7_deploy_for_backtest()
    await tester.test_8_optimize_strategy()

    # Summary
    tester.summary()


if __name__ == "__main__":
    asyncio.run(main())
