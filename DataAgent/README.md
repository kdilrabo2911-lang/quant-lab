# DataAgent

**Simple OHLC data service for Kadirov Quant Lab**

## What it does

1. **Stores historical price data** - 11M+ candles in PostgreSQL (DigitalOcean)
2. **Appends live prices** - Fetches from Kraken every 5 minutes
3. **Serves data via REST API** - Other agents fetch historical data over HTTP
4. **Streams live prices via WebSocket** - Real-time ticker updates for live trading bots

## Quick Start

```bash
# Start the service
cd DataAgent
python3 -m app.main
```

Service runs on `http://localhost:8000`

## API Endpoints

### REST API (Historical Data)

```bash
# Get latest 100 candles
GET /candles/BTC/latest?count=100

# Get candles for date range
GET /candles/ETH?start=2024-01-01T00:00:00Z&end=2024-12-31T23:59:59Z

# Download as CSV
GET /candles/SOL/csv

# Health check
GET /health

# API docs
GET /docs
```

### WebSocket API (Live Prices)

**First, register your strategy:**
```bash
# Register your strategy with the coins it trades
POST /register
{
  "strategy_name": "MovingAverages",
  "coins": ["BTC", "ETH", "SOL"]
}

# DataAgent will subscribe to Kraken WebSocket for these coins
```

**Then, connect to live prices:**
```bash
# Connect to live price stream for BTC
ws://localhost:8000/ws/prices/BTC

# Message format received:
{
  "coin": "BTC",
  "pair": "XBT/USD",
  "ask": 76500.0,
  "bid": 76499.5,
  "last": 76500.0,
  "volume_24h": 1234.56,
  "vwap_24h": 76400.0,
  "low_24h": 75000.0,
  "high_24h": 77000.0,
  "open_24h": 76000.0
}
```

**When your bot stops:**
```bash
# Unregister your strategy
POST /unregister/MovingAverages

# DataAgent will unsubscribe from coins that are no longer needed
```

**Check active strategies:**
```bash
# Get all registered strategies and their coins
GET /strategies

# Response:
{
  "strategies": {
    "MovingAverages": ["BTC", "ETH", "SOL"],
    "SentimentMomentum": ["LINK", "UNI"]
  },
  "active_coins": ["BTC", "ETH", "SOL", "LINK", "UNI"],
  "total_strategies": 2
}
```

## Configuration

Edit [.env](.env):

```bash
# Database (DigitalOcean PostgreSQL)
DATABASE_URL=postgresql://...

# Kraken API credentials (optional, uses public endpoints)
KRAKEN_API_KEY=...
KRAKEN_API_SECRET=...

# Update settings
UPDATE_INTERVAL_SECONDS=300    # Update every 5 minutes
CANDLE_INTERVAL_MINUTES=5      # 5-minute candles
TRACKED_COINS=AUTO             # Auto-detect from database
```

## Data

- **40 coins tracked**: BTC, ETH, SOL, LINK, AAVE, etc.
- **11M+ candles**: Historical data from 2022-10-01
- **5-minute intervals**: Real-time updates every 5 minutes
- **Automatic de-duplication**: No duplicate candles

## Database Schema

```sql
CREATE TABLE ohlc_candles (
    id BIGSERIAL PRIMARY KEY,
    coin VARCHAR(10) NOT NULL,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    close_btc DOUBLE PRECISION NOT NULL,
    UNIQUE(coin, time)
);
```

## Utility Scripts

```bash
# Test database and Kraken connection
python3 test_connection.py

# Upload historical data from master_data.csv (one-time)
python3 upload_from_master.py
```

## How It Works

```
┌─────────────────────────────────────┐
│          DataAgent                  │
├─────────────────────────────────────┤
│                                     │
│  Scheduler (every 5 min)            │
│    ├─ Auto-detect coins from DB     │
│    ├─ Fetch latest from Kraken      │
│    └─ Insert new candles            │
│                                     │
│  REST API (FastAPI)                 │
│    └─ Serve data to other agents    │
│                                     │
└─────────────────────────────────────┘
         │                    │
         ▼                    ▼
    Kraken API        PostgreSQL DB
```

## File Structure

```
DataAgent/
├── .env                    # Configuration
├── requirements.txt        # Python dependencies
├── test_connection.py      # Test DB and Kraken
├── upload_from_master.py   # Backfill historical data
└── app/
    ├── main.py            # Entry point
    ├── config.py          # Load settings
    ├── api.py             # REST endpoints
    ├── database.py        # PostgreSQL connection
    ├── data_manager.py    # CRUD operations
    ├── kraken_client.py   # Fetch from Kraken
    ├── updater.py         # Update logic
    ├── scheduler.py       # Run updates every 5min
    └── models.py          # Data models
```

## Monitoring

Check logs to see updates:

```
2026-04-20 16:20:07 - [AUTO-DETECT] Found 40 coins in database
2026-04-20 16:20:07 - [UPDATE ALL] Starting update for 40 coins...
2026-04-20 16:20:07 - [UPDATE] BTC: Success - added 1 new candles
2026-04-20 16:20:07 - [UPDATE ALL] Complete - 40/40 coins updated, 40 total candles added
```

## Integration Examples

### Historical Data (BacktestAgent)

**Python:**
```python
import httpx

# Fetch historical candles
response = httpx.get("http://localhost:8000/candles/BTC/latest?count=1000")
candles = response.json()
```

### Live Prices (BotBuildAgent)

**Python:**
```python
import asyncio
import httpx
import websockets
import json

async def trading_bot():
    # Step 1: Register strategy
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:8000/register", json={
            "strategy_name": "MyBot",
            "coins": ["BTC", "ETH"]
        })

    # Step 2: Subscribe to live prices
    async with websockets.connect("ws://localhost:8000/ws/prices/BTC") as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"BTC Price: ${data['last']}")

            # Your trading logic here...

asyncio.run(trading_bot())
```

**C#:**
```csharp
using System.Net.Http;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;

// Step 1: Register strategy
var httpClient = new HttpClient();
await httpClient.PostAsJsonAsync("http://localhost:8000/register", new {
    strategy_name = "MyBot",
    coins = new[] { "BTC", "ETH" }
});

// Step 2: Subscribe to live prices
var ws = new ClientWebSocket();
await ws.ConnectAsync(new Uri("ws://localhost:8000/ws/prices/BTC"), CancellationToken.None);

var buffer = new byte[1024];
while (ws.State == WebSocketState.Open)
{
    var result = await ws.ReceiveAsync(buffer, CancellationToken.None);
    var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
    var data = JsonSerializer.Deserialize<TickerData>(message);
    Console.WriteLine($"BTC Price: ${data.Last}");

    // Your trading logic here...
}

// Step 3: Unregister when done
await httpClient.PostAsync("http://localhost:8000/unregister/MyBot", null);
```

## That's it!

Keep it running 24/7 and it will maintain your historical + live price data.
