# Communication Agent

**Single responsibility**: Handle all user communication (Telegram, Web UI, CLI) and route to tested functions.

## Architecture

```
User Message
    ↓
telegram_bot.py (Claude routes to function)
    ↓
    ├─→ function exists? → bot_actions.py (call it)
    │
    └─→ function missing? → function_generator.py
                              ↓
                          1. Generate code
                          2. Generate test
                          3. Run test
                          4. If pass → save to bot_actions.py + test_bot_actions.py
                          5. Reload & call
```

## Files

### `bot_actions.py`
All tested bot functions. Same functions from MasterAgent/test_function2.py.

**Available functions:**
- `list_all_strategies()` - List all strategies from database
- `get_strategy_info(name)` - Get strategy details
- `create_strategy(...)` - Create new strategy in database
- `delete_strategy(name)` - Delete strategy
- `run_backtest(strategy, coins, days)` - Run backtest
- `deploy_strategy_for_backtest(name)` - Generate C++ code for backtest
- `get_last_backtest()` - Get last backtest result
- `get_best_backtest(strategy_name?)` - Get best backtest

### `telegram_bot.py`
Main bot. Uses Claude to understand user intent → route to function → execute.

**Self-testing**: If function doesn't exist, generates it dynamically using `function_generator.py`.

### `function_generator.py`
Generates new functions when needed:
1. Use Claude to generate function code
2. Generate test code for it
3. Run test in isolated environment
4. If passes → save to `bot_actions.py` and `test_bot_actions.py`
5. If fails → report error to user

### `test_bot_actions.py`
Test suite for all bot functions. Ensures reliability.

## Setup

1. Copy `.env.example` to `.env`
2. Fill in your tokens:
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token
   ANTHROPIC_API_KEY=your_anthropic_key
   DATABASE_URL=postgresql://...
   ```

3. Run tests:
   ```bash
   python3 test_bot_actions.py
   ```

4. Start bot:
   ```bash
   python3 telegram_bot.py
   ```

## Design Principles

1. **Single Source of Truth**: Database (PostgreSQL) is the ONLY place strategies are stored
2. **Test Everything**: All functions have tests in `test_bot_actions.py`
3. **Self-Testing**: New functions are tested before being saved
4. **Separation of Concerns**: Communication logic separate from MasterAgent

## Workflow Examples

### User: "list all strategies"
```
1. telegram_bot.py receives message
2. Claude: "This needs list_all_strategies()"
3. bot_actions.py: list_all_strategies() exists → call it
4. Returns: "📋 5 Strategies: MA_Dip_Buyer, VolatilityHarvesting, ..."
```

### User: "optimize RNDR_DipBuyer"
```
1. telegram_bot.py receives message
2. Claude: "This needs optimize_strategy(name, param_grid)"
3. bot_actions.py: optimize_strategy() doesn't exist!
4. function_generator.py:
   - Generate optimize_strategy() function
   - Generate test_optimize_strategy() test
   - Run test → PASS ✅
   - Save to bot_actions.py
   - Add test to test_bot_actions.py
5. Reload bot_actions.py
6. Call optimize_strategy("RNDR_DipBuyer", {...})
7. Return result to user
```

## Testing

Run all tests:
```bash
cd /Users/dilrabokodirova/Desktop/KadirovQuantLab/CommunicationAgent
python3 test_bot_actions.py
```

Expected output:
```
✅ list_all_strategies: Got 123 chars
✅ get_strategy_info: Got info: 234 chars
✅ get_last_backtest: 156 chars
✅ get_best_backtest: 178 chars

Tests: 4/4 passed
```

## Dependencies

- **MasterAgent**: Uses `strategy_store.py`, `action_executor.py`, `db_storage.py`
- **BacktestAgent**: Runs backtests (C++ backtester)
- **BotBuildAgent**: Deploys bots (C# code generation)
- **DataAgent**: Provides market data

All communication flows through CommunicationAgent → routes to appropriate agent.

## Future Enhancements

- [ ] Web UI (same architecture as Telegram bot)
- [ ] CLI interface
- [ ] Slack integration
- [ ] Discord bot
- [ ] Voice commands

All use same `bot_actions.py` functions → guaranteed consistency.

## Directory Structure

```
CommunicationAgent/
├── README.md                  # This file
├── .env                       # Environment variables (TELEGRAM_BOT_TOKEN, etc)
├── .env.example               # Template
├── telegram_bot.py            # Main Telegram bot
├── bot_actions.py             # All tested functions
├── function_generator.py      # Dynamic function creation with testing
└── test_bot_actions.py        # Test suite
```
