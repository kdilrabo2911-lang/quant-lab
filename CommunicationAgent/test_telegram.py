#!/usr/bin/env python3
"""Test telegram bot by sending messages directly"""

import asyncio
from telegram import Bot
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID")


async def send_message(text: str):
    """Send message to bot and wait for response"""
    bot = Bot(token=BOT_TOKEN)

    print(f"\n📤 Sending: {text}")
    await bot.send_message(chat_id=CHAT_ID, text=text)

    # Wait a bit for response
    await asyncio.sleep(3)

    # Get updates
    updates = await bot.get_updates(limit=5)

    # Find bot's response
    for update in reversed(updates):
        if update.message and update.message.chat.id == int(CHAT_ID):
            if update.message.from_user.is_bot:
                print(f"📥 Response: {update.message.text[:200]}")
                return update.message.text

    return None


async def main():
    """Run test suite"""
    print("=" * 80)
    print("TELEGRAM BOT TEST SUITE")
    print("=" * 80)

    # Test 1: List strategies
    print("\n[TEST 1] List all strategies")
    await send_message("list all strategies")

    await asyncio.sleep(5)

    # Test 2: Get strategy info
    print("\n[TEST 2] Get strategy info")
    await send_message("tell me about MA_Dip_Buyer")

    await asyncio.sleep(5)

    # Test 3: Show last backtest
    print("\n[TEST 3] Show last backtest")
    await send_message("show me the last backtest")

    await asyncio.sleep(5)

    # Test 4: Show best backtest
    print("\n[TEST 4] Show best backtest")
    await send_message("show me the best backtest")

    print("\n" + "=" * 80)
    print("Tests complete! Check your Telegram app for responses.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
