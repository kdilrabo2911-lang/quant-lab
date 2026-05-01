"""
Clean Telegram Bot - Uses BotActions (tested functions)
Claude routes user requests to the right function

If function doesn't exist → generates it → tests it → saves it
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from pathlib import Path
from dotenv import load_dotenv
import json
import anthropic
from bot_actions import BotActions
from function_generator import FunctionGenerator

# Load environment
env_file = Path(__file__).parent / ".env"
if not env_file.exists():
    # Try parent directory
    env_file = Path(__file__).parent.parent / "DataAgent" / ".env"
load_dotenv(env_file)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


class TelegramBot:
    """Clean bot that uses tested BotActions + generates new functions when needed"""

    def __init__(self):
        self.actions = BotActions()
        self.function_generator = FunctionGenerator()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route user message to the right action"""
        user_message = update.message.text

        await update.message.reply_text("🔄 Working on it...")

        try:
            # Use Claude to understand and execute request
            prompt = f"""User request: "{user_message}"

You are a fully autonomous trading assistant with access to the complete system.

You can EITHER:
1. Use tested functions from bot_actions.py (preferred when available)
2. Write and execute Python code directly (for anything else)

Tested functions in bot_actions.py:
- list_all_strategies()
- get_strategy_info(name: str) - name is strategy name WITHOUT version
- run_backtest(strategy_name: str, coins: List[str], days: int)
- deploy_strategy_for_backtest(strategy_name: str) - generates C++ code
- optimize_strategy(strategy_name: str, param_grid: Dict, coins: List[str], days: int)
- get_last_backtest()
- get_best_backtest(strategy_name: Optional[str])

Return JSON in ONE of these formats:

1. Call tested function (preferred):
{{
  "function": "function_name",
  "args": {{...}}
}}

2. Execute Python code directly:
{{
  "code": "import asyncio\\nresult = await executor.run_backtest(...)"
}}

3. Ask for clarification:
{{
  "ask_user": "question..."
}}

4. Simple response:
{{
  "response": "answer"
}}

Available in code execution:
- bot_actions - BotActions instance with tested functions (PREFERRED)
- store = get_store() - strategy database
- executor = ActionExecutor() - runs backtests, optimizations, deployments
- Strategy, Parameter classes
- await store.create/get/update/delete/list_all()
- await bot_actions.optimize_strategy/run_backtest/etc. (PREFERRED)
- await executor.run_backtest/optimize_strategy/deploy_strategy_for_backtest()
- Use await for all async calls
- Set result = "your message to user"

IMPORTANT RULES:
- Strategy names do NOT include version numbers (use "MA_Dip_Buyer", not "MA_Dip_Buyer v1.24")
- For optimize_strategy: param_grid must be dict with parameter names as keys and list of values to test
  Example: {{"ma_period": [6, 12, 24, 72, 168]}}
- Time conversions: 6 hours=6, 12 hours=12, 1 day=24, 3 days=72, 7 days=168 (in hours)
- coins must be a list: ["RNDR"], not "RNDR"
- If user's request is ambiguous or missing info, use "ask_user" to clarify

Examples:
User: "list all strategies"
Return: {{"function": "list_all_strategies", "args": {{}}}}

User: "tell me about MA_Dip_Buyer v1.24"
Return: {{"function": "get_strategy_info", "args": {{"name": "MA_Dip_Buyer"}}}}

User: "backtest MA_Dip_Buyer2 for RNDR for last 30 days"
Return: {{"function": "run_backtest", "args": {{"strategy_name": "MA_Dip_Buyer2", "coins": ["RNDR"], "days": 30}}}}

User: "run backtest for MA_Dip_Buyer on BTC for 90 days"
Return: {{"function": "run_backtest", "args": {{"strategy_name": "MA_Dip_Buyer", "coins": ["BTC"], "days": 90}}}}

User: "optimize MA_Dip_Buyer2 for RNDR for last 30 days with default optimization grid"
Return: {{"function": "optimize_strategy", "args": {{"strategy_name": "MA_Dip_Buyer2", "param_grid": {{}}, "coins": ["RNDR"], "days": 30}}}}

User: "optimize strategy for MA_Dip_Buyer2 for RNDR coin where ma_periods are 6hrs,12hrs,1 day, 3 days, 7 days"
Return: {{"function": "optimize_strategy", "args": {{"strategy_name": "MA_Dip_Buyer2", "param_grid": {{"ma_period": [6, 12, 24, 72, 168]}}, "coins": ["RNDR"], "days": 365}}}}

User: "show me the last backtest"
Return: {{"function": "get_last_backtest", "args": {{}}}}

User: "show me the best backtest"
Return: {{"function": "get_best_backtest", "args": {{"strategy_name": null}}}}

User: "deploy MA_Dip_Buyer2 for backtest"
Return: {{"function": "deploy_strategy_for_backtest", "args": {{"strategy_name": "MA_Dip_Buyer2"}}}}

User: "create new strategy called VolatilityHarvesting that harvests 2% off volatility"
Return: {{"function": "create_strategy", "args": {{"name": "VolatilityHarvesting", "description": "Harvests 2% off coin volatility by capturing dips and peaks", "parameters": {{"volatility_threshold_pct": 2.0, "profit_target_pct": 2.0}}, "buy_conditions": [{{"type": "price_dip", "value": 2.0}}], "sell_conditions": [{{"type": "profit_target", "value": 2.0}}]}}}}
"""

            ai_response = anthropic_client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,  # Shorter response to ensure JSON fits
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = ai_response.content[0].text.strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]  # Remove ```json
            elif result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text[3:]

            if result_text.endswith("```"):
                result_text = result_text.rsplit("```", 1)[0]

            result_text = result_text.strip()

            # Debug: print what Claude returned
            print(f"Claude response: {result_text[:200]}...")

            try:
                plan = json.loads(result_text)
            except json.JSONDecodeError as e:
                # Claude didn't return JSON - send error with what it actually returned
                error_msg = f"❌ Failed to parse response as JSON.\n\nClaude returned:\n{result_text[:300]}"
                print(f"JSON Parse Error: {e}")
                print(f"Response was: {result_text}")
                await update.message.reply_text(error_msg)
                return

            # Execute based on plan
            response = None

            if "code" in plan:
                # Execute Python code directly
                code = plan["code"]
                print(f"Executing code:\n{code}\n")

                try:
                    # Set up execution environment
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent / "MasterAgent"))

                    from strategy_store import get_store, Strategy
                    from strategy_definition import Parameter, Condition
                    from action_executor import ActionExecutor

                    exec_globals = {
                        "get_store": get_store,
                        "Strategy": Strategy,
                        "Parameter": Parameter,
                        "Condition": Condition,
                        "ActionExecutor": ActionExecutor,
                        "bot_actions": self.actions,  # Add BotActions instance
                        "__builtins__": __builtins__,
                    }

                    # Wrap in async function
                    wrapped_code = f"""
import asyncio

async def _exec_async():
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    return locals().get('result', 'Done!')

_result = asyncio.create_task(_exec_async())
"""

                    exec_locals = {}
                    exec(wrapped_code, exec_globals, exec_locals)

                    # Await the result
                    if "_result" in exec_locals:
                        response = await exec_locals["_result"]
                    else:
                        response = "✅ Code executed"

                except Exception as e:
                    print(f"❌ Code execution error: {e}")
                    print(f"Original code:\n{code}")

                    # AUTO-FIX: Keep debugging until success or 5 min timeout
                    import time
                    start_time = time.time()
                    max_duration = 300  # 5 minutes in seconds
                    retry = 0
                    original_error = str(e)

                    # Notify user we're auto-fixing
                    await update.message.reply_text("🔧 Auto-fixing... (will keep trying for up to 5 min)")

                    while time.time() - start_time < max_duration:
                        retry += 1
                        elapsed = int(time.time() - start_time)
                        print(f"\n🔧 Auto-fix attempt #{retry} ({elapsed}s elapsed)...")

                        # Update user every 10 attempts
                        if retry % 10 == 0:
                            await update.message.reply_text(f"🔧 Still working... (attempt #{retry}, {elapsed}s)")

                        fix_prompt = f"""You are debugging Python code that failed.

User's original request: {user_message}

Code that failed:
```python
{code}
```

Error: {str(e)}

Available in execution environment:
- bot_actions - BotActions instance with tested functions like optimize_strategy, run_backtest, etc. (USE THIS)
- get_store() - returns StrategyStore for database operations
- Strategy class with fields: id, name, version, type, description, parameters, buy_conditions, sell_conditions
- ActionExecutor class (for creating new instances)

CRITICAL: For functions like optimize_strategy, use bot_actions:
result = await bot_actions.optimize_strategy(strategy_name, param_grid, coins, days)

CRITICAL: Database operations require connection first!
store = get_store()
await store.connect()  # MUST call this before any database operations!
await store.create(strategy)  # Creates strategy in database

IMPORTANT: Strategy.__init__ signature is:
Strategy(id: int, name: str, version: str, type: str, description: str, parameters: Dict, buy_conditions: List[Dict], sell_conditions: List[Dict])

Common errors and fixes:
- "'NoneType' object has no attribute 'fetchval'" → You forgot "await store.connect()" before database operations
- "missing 1 required positional argument: 'type'" → You must provide ALL required fields to Strategy()
- "unexpected keyword argument 'entry_logic'" → Use buy_conditions and sell_conditions, NOT entry_logic/exit_logic

Fix the code and return ONLY the corrected Python code in this JSON format:
{{"code": "corrected code here"}}

Rules:
- ALWAYS call "await store.connect()" before any store.create/get/update/delete operations
- Use buy_conditions and sell_conditions (NOT entry_logic/exit_logic)
- All required fields must be provided (id, name, version, type, description, parameters, buy_conditions, sell_conditions)
- Use type="custom" for user-created strategies
- Use id=0 for new strategies
- conditions should be list of dicts like [{{"type": "price_dip", "value": 2.0}}]
- Set result="success message" at the end so user sees confirmation
"""

                        try:
                            fix_response = anthropic_client.messages.create(
                                model="claude-opus-4-7",
                                max_tokens=1024,
                                messages=[{"role": "user", "content": fix_prompt}]
                            )

                            fix_text = fix_response.content[0].text.strip()
                            if fix_text.startswith("```json"):
                                fix_text = fix_text[7:]
                            if fix_text.endswith("```"):
                                fix_text = fix_text[:-3]
                            fix_text = fix_text.strip()

                            fix_plan = json.loads(fix_text)
                            fixed_code = fix_plan.get("code", "")

                            print(f"Fixed code:\n{fixed_code}")

                            # Try executing the fixed code
                            wrapped_fixed = f"""
import asyncio

async def _exec_async():
{chr(10).join('    ' + line for line in fixed_code.split(chr(10)))}
    return locals().get('result', 'Done!')

_result = asyncio.create_task(_exec_async())
"""

                            exec_locals_retry = {}
                            exec(wrapped_fixed, exec_globals, exec_locals_retry)

                            if "_result" in exec_locals_retry:
                                response = await exec_locals_retry["_result"]
                                print(f"✅ Auto-fix successful on attempt {retry + 1}")
                                break

                        except Exception as retry_error:
                            print(f"   Attempt #{retry} failed: {retry_error}")
                            # Update error and code for next iteration
                            e = retry_error
                            code = fixed_code
                            continue

                    # If we exit the loop without success
                    if response is None:
                        elapsed = int(time.time() - start_time)
                        response = f"❌ Auto-fix timeout after {elapsed}s ({retry} attempts)\n\nOriginal error: {original_error}\n\nLast error: {str(e)}\n\nPlease contact support."

            elif "ask_user" in plan:
                # Bot needs clarification
                response = f"❓ {plan['ask_user']}"

            elif "needs_new_function" in plan and plan["needs_new_function"]:
                # Generate new function for this capability
                await update.message.reply_text(
                    f"🔧 {plan.get('explanation', 'Creating new function')}..."
                )

                gen_result = await self.function_generator.generate_and_test_function(user_message)

                if gen_result["success"]:
                    # Reload bot_actions
                    import importlib
                    import bot_actions
                    importlib.reload(bot_actions)
                    self.actions = bot_actions.BotActions()

                    response = f"✅ Created and tested new function: {gen_result['function_name']}\n\nPlease try your request again!"
                else:
                    response = f"❌ Failed: {gen_result.get('error')}"

            elif "function" in plan:
                func_name = plan["function"]
                args = plan.get("args", {})

                # Call the function if it exists
                if hasattr(self.actions, func_name):
                    func = getattr(self.actions, func_name)
                    response = await func(**args)

                    # Add prefix if provided
                    if "response_prefix" in plan:
                        response = f"{plan['response_prefix']}\n\n{response}"
                else:
                    # Function doesn't exist → generate it!
                    await update.message.reply_text(
                        f"🔧 Function '{func_name}' not found. Generating and testing it..."
                    )

                    gen_result = await self.function_generator.generate_and_test_function(user_message)

                    if gen_result["success"]:
                        # Reload BotActions to get new function
                        import importlib
                        import bot_actions
                        importlib.reload(bot_actions)
                        self.actions = bot_actions.BotActions()

                        # Try calling the new function
                        if hasattr(self.actions, gen_result["function_name"]):
                            func = getattr(self.actions, gen_result["function_name"])
                            response = await func(**args)
                            response = f"✨ Created new function!\n\n{response}"
                        else:
                            response = f"✅ Created function '{gen_result['function_name']}', but name mismatch. Please try again."
                    else:
                        response = f"❌ Failed to generate function: {gen_result.get('error')}"

            elif "response" in plan:
                response = plan["response"]
            else:
                response = "❌ Invalid response from AI"

            # Don't use Markdown parsing to avoid parsing errors
            await update.message.reply_text(response)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Welcome! I use tested functions from test_function2.py\n\n"
            "Try:\n"
            "• list all strategies\n"
            "• tell me about RNDR_DipBuyer\n"
            "• run backtest for MA_Dip_Buyer on BTC\n"
            "• show me the best backtest\n"
        )

    def run(self):
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        print("🤖 Telegram Bot v2 running (uses BotActions)...")
        application.run_polling()


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
