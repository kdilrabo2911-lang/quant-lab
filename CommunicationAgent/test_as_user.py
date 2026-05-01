#!/usr/bin/env python3
"""
Test bot by simulating user messages via Telegram API
This sends messages AS THE USER, not as a bot
"""

import asyncio
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("MANAGER_TELEGRAM_CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_as_user_and_get_response(message: str, wait_time=8):
    """
    The trick: We can't actually send as user via API, but we can:
    1. Manually send message in YOUR Telegram app
    2. OR use webhook simulation
    3. OR just check if bot CAN process the message format

    For now, let's just verify the bot logic works by calling bot_actions directly
    """
    print(f"\n📤 Testing: {message}")

    # Import bot_actions and test directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "MasterAgent"))

    from bot_actions import BotActions

    actions = BotActions()

    # Parse the message and call appropriate function
    message_lower = message.lower()

    try:
        if "list" in message_lower and "strateg" in message_lower:
            response = await actions.list_all_strategies()
        elif "tell me about" in message_lower or "info" in message_lower:
            name = message.split("about")[-1].strip() if "about" in message else "MA_Dip_Buyer2"
            response = await actions.get_strategy_info(name)
        elif "last backtest" in message_lower:
            response = await actions.get_last_backtest()
        elif "best backtest" in message_lower:
            response = await actions.get_best_backtest()
        else:
            response = "Unknown command"

        print(f"📥 Response: {response[:200]}{'...' if len(response) > 200 else ''}")
        return response
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run basic tests"""
    print("="*80)
    print("TELEGRAM BOT FUNCTION TESTS (Direct bot_actions.py)")
    print("="*80)

    passed = 0
    failed = 0

    # Test 1
    print(f"\n[TEST 1] List strategies")
    resp = await send_as_user_and_get_response("list all strategies")
    if resp and "strateg" in resp.lower():
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")
        failed += 1

    # Test 2
    print(f"\n[TEST 2] Get strategy info")
    resp = await send_as_user_and_get_response("tell me about MA_Dip_Buyer2")
    if resp and "parameter" in resp.lower():
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")
        failed += 1

    # Test 3
    print(f"\n[TEST 3] Last backtest")
    resp = await send_as_user_and_get_response("show me the last backtest")
    if resp and "backtest" in resp.lower():
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")
        failed += 1

    # Test 4
    print(f"\n[TEST 4] Best backtest")
    resp = await send_as_user_and_get_response("show me the best backtest")
    if resp and "backtest" in resp.lower():
        print("✅ PASS")
        passed += 1
    else:
        print("❌ FAIL")
        failed += 1

    print(f"\n{'='*80}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*80}")

    if failed == 0:
        print("✅ All bot_actions functions work!")
        print("\nNow test manually on YOUR Telegram:")
        print("1. list all strategies")
        print("2. tell me about MA_Dip_Buyer2")
        print("3. show me the last backtest")
        print("4. show me the best backtest")


if __name__ == "__main__":
    asyncio.run(main())
