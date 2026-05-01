# BotBuildAgent - Live Trading Bots

## Overview

BotBuildAgent generates and manages live trading bots based on strategies tested in BacktestAgent. Each strategy is an independent executable bot that connects to Kraken exchange and executes trades based on its specific signal logic.

## Architecture

```
BotBuildAgent/
├── Common/                          # Shared infrastructure (referenced by all strategies)
│   ├── Exchange/                    # Kraken REST + WebSocket clients
│   ├── Execution/                   # Unified order executor
│   ├── Portfolio/                   # Portfolio tracking
│   ├── Utilization/                 # Capital allocation
│   ├── Models/                      # Shared data models
│   └── DataAgent/                   # DataAgent client (stub)
│
└── Strategies/                      # Individual strategy bots
    ├── MovingAverages/              # Golden/Death cross strategy
    ├── VolatilityHarvesting/        # Bollinger Bands mean reversion
    └── SentimentMomentum/           # ROC + volume momentum
```

## Key Design Principles

1. **Single Responsibility**: Each strategy bot implements only its signal generation logic
2. **Unified Execution**: All strategies use the same `OrderExecutor` from Common module
3. **Strategy Attribution**: Every trade is tagged with `StrategyName` for performance tracking
4. **No Code Duplication**: Common infrastructure shared across all strategies
5. **Dry-Run by Default**: Requires explicit `--live` flag to enable real trading

## Implemented Strategies

### 1. MovingAverages

**Strategy**: Golden cross (buy) / Death cross (sell)

**Parameters**:
- `FastPeriod`: 12 candles
- `SlowPeriod`: 72 candles

**Buy Signal**: Fast MA crosses above slow MA
**Sell Signal**: Fast MA crosses below slow MA

**Position Limit**: 1 position per coin

**Build & Run**:
```bash
cd Strategies/MovingAverages
dotnet build
dotnet run                    # Dry-run mode
dotnet run -- --live          # Live trading (requires YES confirmation)
```

---

### 2. VolatilityHarvesting

**Strategy**: Bollinger Bands mean reversion

**Parameters**:
- `BollingerPeriod`: 20 candles
- `BollingerStdDev`: 2.0
- `ProfitTargetPct`: 2%

**Buy Signal**: Price touches/drops below lower Bollinger Band
**Sell Signal**: Price touches upper band OR profit target reached

**Position Limit**: 1 position per coin

**Build & Run**:
```bash
cd Strategies/VolatilityHarvesting
dotnet build
dotnet run                    # Dry-run mode
dotnet run -- --live          # Live trading
```

---

### 3. SentimentMomentum

**Strategy**: Rate of Change (ROC) + volume momentum

**Parameters**:
- `RocPeriod`: 14 candles
- `VolumeThreshold`: 1.5x average volume
- `VolumeAvgPeriod`: 50 candles
- `MaxHoldPeriod`: 288 candles (~5 hours at 1-min intervals)

**Buy Signal**: Positive ROC + volume spike
**Sell Signal**: Momentum reversal (ROC < 0) OR max hold period reached

**Position Limit**: 1 position per coin

**Build & Run**:
```bash
cd Strategies/SentimentMomentum
dotnet build
dotnet run                    # Dry-run mode
dotnet run -- --live          # Live trading
```

---

## Common Module

All strategies depend on the unified `Common` module:

```bash
cd Common
dotnet build
```

**Modules**:
- **Exchange**: Kraken API integration (REST + WebSocket)
- **Execution**: Unified `OrderExecutor` handles buy/sell for all strategies
- **Portfolio**: Balance tracking, P/L calculation
- **Utilization**: Capital allocation across coins
- **DataAgent**: Client for centralized data service (currently stub)
- **Models**: Shared data structures (Position, TradeLog, PortfolioState, etc.)

## Configuration

### API Keys

Create a `secrets.env` file in each strategy directory:

```bash
KRAKEN_API_KEY=your_api_key_here
KRAKEN_API_SECRET=your_api_secret_here
```

**Security**: `secrets.env` is in `.gitignore` - never commit API keys!

### Strategy Parameters

Currently hardcoded in `Program.cs` of each strategy. Future: Load from DataAgent.

Example (MovingAverages/Program.cs):
```csharp
var coinParameters = new Dictionary<string, MAParameters>
{
    { "ETH", new MAParameters { Coin = "ETH", FastPeriod = 12, SlowPeriod = 72 } },
    { "BTC", new MAParameters { Coin = "BTC", FastPeriod = 12, SlowPeriod = 72 } }
};
```

## Dry-Run vs Live Trading

**Dry-Run Mode** (default):
- Simulates orders without hitting exchange
- Logs all actions to console with `[DRY RUN]` prefix
- Uses separate data files (`trading_positions_dryrun.json`, etc.)
- Perfect for testing signal generation logic

**Live Trading** (`--live` flag):
- Places real orders on Kraken
- Requires typing `YES` at confirmation prompt
- Uses real money - **use with caution!**
- Logs show `[LIVE]` prefix

## How Strategies Work

1. **Startup**:
   - Load API credentials from `secrets.env`
   - Initialize Kraken REST + WebSocket clients
   - Load portfolio state from DataAgent
   - Load historical candles for each coin
   - Subscribe to WebSocket ticker updates

2. **Runtime Loop**:
   - On each ticker update:
     - Append new candle to history
     - Check sell signals for open positions
     - Check buy signals for new entries
     - Execute orders via unified `OrderExecutor`
     - Save updated positions to DataAgent

3. **Shutdown**:
   - Graceful disconnect from WebSocket
   - Save final portfolio state
   - Ctrl+C to stop

## Strategy Attribution

Every trade is tagged with `StrategyName`:

```csharp
var position = await _orderExecutor.ExecuteBuyAsync(
    STRATEGY_NAME,      // e.g., "MovingAverages"
    coin,
    currentPriceUsd,
    currentPriceBtc,
    positionSize
);
```

This allows:
- Multi-strategy performance analysis
- Strategy-specific position management
- Attribution: "Which strategy made this trade?"

## Data Flow

```
Kraken WebSocket
    ↓
TradingBot (strategy-specific)
    ↓
BuySignalGenerator / SellSignalGenerator (strategy-specific)
    ↓
OrderExecutor (unified - in Common module)
    ↓
Kraken REST API (place order)
    ↓
DataAgentClient (log trade, save positions)
    ↓
DataAgent service (centralized storage)
```

## Building All Strategies

Build all strategies at once:

```bash
# From BotBuildAgent root
dotnet build Common/Common.csproj
dotnet build Strategies/MovingAverages/bot.csproj
dotnet build Strategies/VolatilityHarvesting/bot.csproj
dotnet build Strategies/SentimentMomentum/bot.csproj
```

Or use the convenience script (create this):

```bash
#!/bin/bash
# build_all.sh

dotnet build Common/Common.csproj || exit 1
dotnet build Strategies/MovingAverages/bot.csproj || exit 1
dotnet build Strategies/VolatilityHarvesting/bot.csproj || exit 1
dotnet build Strategies/SentimentMomentum/bot.csproj || exit 1

echo "All strategies built successfully!"
```

## Testing

### Unit Tests (TODO)

Create test projects for each strategy:
```bash
Strategies/MovingAverages.Tests/
Strategies/VolatilityHarvesting.Tests/
Strategies/SentimentMomentum.Tests/
```

### Integration Tests

Test against Kraken testnet (if available) or use dry-run mode with simulated data.

## Deployment

**Production Setup**:
1. Deploy each strategy as a separate service/container
2. Run on VPS with stable connection
3. Monitor logs for errors and trade execution
4. Set up alerting (email/SMS on errors)
5. Use systemd or Docker to auto-restart on crash

**Example systemd service** (MovingAverages):
```ini
[Unit]
Description=MovingAverages Trading Bot
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/opt/kadirovquantlab/BotBuildAgent/Strategies/MovingAverages
ExecStart=/usr/bin/dotnet run -- --live
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Performance Monitoring

All trades are logged to DataAgent with:
- Buy/sell timestamps
- Prices, quantities, fees
- P/L (gross, net, percentage)
- Strategy name
- Sell reason

Use DataAgent queries to analyze:
- Win rate per strategy
- Average holding period
- Return distribution
- Sharpe ratio
- Maximum drawdown

## Safety Features

1. **Dry-run by default**: Prevents accidental live trading
2. **Explicit confirmation**: Must type `YES` to enable live mode
3. **Strategy isolation**: Each strategy manages only its own positions
4. **Minimum position size**: Enforced in `CapitalAllocator`
5. **Capital limits**: Per-strategy allocation prevents overexposure
6. **Error handling**: Graceful degradation on API errors

## Future Improvements

- [ ] Load parameters from DataAgent instead of hardcoding
- [ ] Implement real-time performance dashboard
- [ ] Add risk limits (max loss per day, max position count)
- [ ] Implement position sizing based on Kelly Criterion
- [ ] Add backtesting integration (test strategy before deploy)
- [ ] Create web UI for starting/stopping bots
- [ ] Add Telegram/Discord notifications
- [ ] Implement circuit breaker (auto-stop on consecutive losses)

## Troubleshooting

**Build errors**:
```bash
# Clean and rebuild
dotnet clean
dotnet restore
dotnet build
```

**WebSocket connection issues**:
- Check firewall settings
- Verify Kraken API status
- Check API key permissions

**Order execution failures**:
- Verify API keys are correct
- Check Kraken account balance
- Ensure trading pair is available on Kraken
- Check order size meets minimum requirements

**Data not persisting**:
- DataAgent service must be running (currently stub)
- Check file permissions for data directory
- Verify DataAgent URL in configuration

## Support

For issues, check:
1. Console logs (detailed error messages)
2. Kraken API status page
3. DataAgent service health
4. Network connectivity

## License

Proprietary - Kadirov Quant Lab
