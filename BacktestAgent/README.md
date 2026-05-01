# BacktestAgent

High-performance backtesting system for quantitative trading strategies.

## Overview

BacktestAgent provides a hybrid Python + C++ architecture for fast, reliable strategy backtesting:
- **Python**: Handles data fetching, orchestration, and database storage
- **C++**: Executes backtests at 100x speed with SIMD optimizations
- **PostgreSQL**: Stores all results in cloud database for analysis

## Architecture

```
BacktestAgent/
├── run_backtest.py          # Main entry point
├── query_results.py         # Query backtest results from database
├── python/
│   ├── common/
│   │   └── data_agent_client.py    # Fetch data from DataAgent
│   ├── orchestrator/
│   │   └── backtester_runner.py    # Python-C++ bridge
│   └── db/
│       ├── schema.sql              # Database schema
│       └── results_saver.py        # Save results to PostgreSQL
└── cpp/
    ├── main.cpp             # C++ CLI entry point
    ├── include/             # Header files (backtester, strategies, types)
    ├── src/                 # Core backtester implementation
    └── strategies/          # Strategy implementations
        ├── moving_averages.cpp
        ├── moving_averages_trailing.cpp
        ├── volatility_harvesting.cpp
        └── sentiment_momentum.cpp
```

## Features

✅ **4 Built-in Strategies**
- Moving Averages (MA crossover)
- Moving Averages Trailing (MA with trailing stop)
- Volatility Harvesting (Bollinger Bands)
- Sentiment Momentum (ROC + volume)

✅ **Fast C++ Engine**
- SIMD optimized indicator calculations
- ~100x faster than pure Python
- Parallel compilation support

✅ **Automatic Database Storage**
- Portfolio-level metrics
- Coin-level performance
- Individual trade logs
- Historical comparison

✅ **Flexible Data Fetching**
- Last N days
- Specific date ranges
- Multiple coins in parallel

## Quick Start

### 1. Build C++ Backtester

```bash
cd BacktestAgent
mkdir -p build && cd build
cmake ..
make -j4
```

This creates `build/backtester_cli` binary.

### 2. Run Your First Backtest

```bash
# Backtest MovingAveragesTrailing for BTC, ETH, SOL (last 90 days)
python3 run_backtest.py --strategy ma_trailing --coins BTC ETH SOL --last-days 90
```

**Output:**
- Console summary with metrics
- Local JSON file: `results/ma_trailing_TIMESTAMP.json`
- Cloud database record (automatic)

### 3. View Results from Database

```bash
python3 query_results.py
```

Shows all backtest runs with performance metrics.

## Usage Examples

```bash
# Test single coin for 30 days
python3 run_backtest.py --strategy ma_trailing --coins RENDER --last-days 30

# Multiple coins, 6 months
python3 run_backtest.py --strategy volatility --coins LINK AAVE UNI --last-days 180

# Different strategy
python3 run_backtest.py --strategy ma --coins BTC ETH --last-days 60
```

## Available Strategies

| Strategy | Code | Description |
|----------|------|-------------|
| **Moving Averages** | `ma` | Fast/slow MA crossover strategy |
| **MA Trailing** | `ma_trailing` | MA entry + trailing stop exit |
| **Volatility Harvesting** | `volatility` | Mean reversion using Bollinger Bands |
| **Sentiment Momentum** | `sentiment` | ROC + volume momentum strategy |

## Database Schema

### Tables

**backtest_runs** - Portfolio-level runs
- Strategy name, coins, date range
- Portfolio return, Sharpe ratio
- Total trades

**backtest_coin_results** - Coin-level performance
- Individual coin metrics
- Win rate, avg profit/loss
- Equity curve (JSON)

**backtest_trades** - Trade logs
- Buy/sell timestamps and prices
- Profit percentage
- Hold duration, sell reason

### Views

**backtest_summary** - Quick overview of all backtests
- Portfolio metrics
- Best/worst coin performance
- Number of coins tested

## Performance Metrics

Each backtest calculates:
- **Total Return %** - Overall profit/loss
- **Number of Trades** - Trade count
- **Win Rate** - Percentage of profitable trades
- **Sharpe Ratio** - Risk-adjusted returns
- **Max Drawdown** - Largest peak-to-trough decline
- **Avg Profit/Loss** - Average winning and losing trades

## Configuration

BacktestAgent uses DataAgent's database configuration from `../DataAgent/.env`:

```env
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
```

No additional configuration needed - it automatically:
- Fetches data from DataAgent API
- Saves results to PostgreSQL
- Keeps local JSON backups

## Development

### Adding a New Strategy

1. Create `cpp/strategies/your_strategy.cpp`
2. Implement `StrategyInterface` methods:
   - `ShouldBuy()` - Entry logic
   - `ShouldSell()` - Exit logic
   - `ComputeIndicators()` - Calculate indicators once
3. Add factory function
4. Update `CMakeLists.txt` and `cpp/main.cpp`
5. Rebuild: `cd build && make -j4`

### Running C++ Backtester Directly

```bash
./build/backtester_cli ma_trailing /path/to/data.csv BTC --json results.json
```

## Requirements

**Python:**
- pandas
- httpx
- asyncpg
- python-dotenv

Install: `pip install -r python/requirements.txt`

**System:**
- CMake 3.15+
- C++17 compiler
- PostgreSQL database (via DataAgent)

## Troubleshooting

**"C++ backtester not found"**
```bash
cd BacktestAgent/build
cmake .. && make -j4
```

**"Failed to save to database"**
- Check DataAgent is running
- Verify `DATABASE_URL` in `../DataAgent/.env`
- Run schema: `python3 create_tables.py` (one-time)

**"No data available for coin X"**
- Coin not in DataAgent database
- Check available coins: `curl http://localhost:8000/coins`

## Best Practices

1. **Start Small** - Test 1-2 coins for 30 days first
2. **Review Trades** - Check individual trades in database
3. **Compare Strategies** - Run multiple strategies on same coins/period
4. **Monitor Metrics** - Focus on Sharpe ratio and win rate, not just returns
5. **Keep Local Backups** - JSON files saved automatically

## Example Workflow

```bash
# 1. Run backtest
python3 run_backtest.py --strategy ma_trailing --coins UNI RENDER TRX --last-days 90

# 2. Review results
python3 query_results.py

# 3. Compare with different strategy
python3 run_backtest.py --strategy volatility --coins UNI RENDER TRX --last-days 90

# 4. Query database for comparison
python3 query_results.py
```

## Notes

- All backtests assume 0.26% trading fees (Kraken maker/taker)
- Prices are BTC-denominated for consistency
- Results saved to both local JSON and cloud database
- Equity curve stored in database for detailed analysis

## Support

For issues or questions:
1. Check DataAgent is running: `http://localhost:8000/health`
2. Verify C++ binary exists: `ls -lh build/backtester_cli`
3. Review database connection in `../DataAgent/.env`
