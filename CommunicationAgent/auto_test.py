#!/usr/bin/env python3
"""Auto-test bot via Telegram API"""

import asyncio
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv
import time

env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(text: str):
    """Send message to bot"""
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": text})
    print(f"📤 Sent: {text}")


async def get_latest_bot_response(wait_time=10):
    """Get latest response from bot"""
    print(f"⏳ Waiting {wait_time}s for bot response...")
    await asyncio.sleep(wait_time)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/getUpdates", params={"timeout": 1})
        data = response.json()

        if not data.get("ok"):
            return None

        results = data.get("result", [])

        # Find latest bot message
        for update in reversed(results[-10:]):
            if "message" in update:
                msg = update["message"]
                if msg.get("from", {}).get("is_bot") and str(msg["chat"]["id"]) == str(CHAT_ID):
                    text = msg["text"]
                    print(f"📥 Bot response ({len(text)} chars):")
                    print(text)
                    print("-" * 80)
                    return text

    return None


async def main():
    print("=" * 80)
    print("AUTO-TESTING TELEGRAM BOT")
    print("=" * 80)

    # Test 1: Full backtest workflow
    print("\n[TEST 1] Full backtest workflow (auto-generate, compile, run)")
    await send_message("run backtest for MA_Dip_Buyer2 on RNDR for last 30 days")
    response = await get_latest_bot_response(wait_time=30)  # Longer wait for compilation

    if response:
        if "✅ Backtest complete" in response or "Return:" in response:
            print("✅ PASS: Full workflow completed successfully!")
        elif "Auto-compiling" in response or "Generated" in response:
            print("⚠️  PARTIAL: Code generated but check if backtest ran")
        else:
            print("❌ FAIL: Unexpected response")
    else:
        print("❌ FAIL: No response from bot")

    await asyncio.sleep(3)

    # Test 2: List strategies
    print("\n[TEST 2] List all strategies")
    await send_message("list all strategies")
    response = await get_latest_bot_response(wait_time=5)

    if response and "strateg" in response.lower():
        print("✅ PASS: List strategies works")
    else:
        print("❌ FAIL: List strategies failed")

    await asyncio.sleep(3)

    # Test 3: Get last backtest
    print("\n[TEST 3] Get last backtest")
    await send_message("show me the last backtest")
    response = await get_latest_bot_response(wait_time=5)

    if response and ("backtest" in response.lower() or "return" in response.lower()):
        print("✅ PASS: Get last backtest works")
    else:
        print("❌ FAIL: Get last backtest failed")

    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
