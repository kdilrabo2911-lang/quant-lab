"""
REST API for DataAgent
"""
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime
import pandas as pd
import io
import logging

from .models import OHLCCandle, HealthResponse, UpdateStatusResponse, StrategyRegistration, StrategyRegistrationResponse
from .data_manager import data_manager
from .updater import updater
from .scheduler import scheduler
from .database import db
from .config import settings
from .websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Coin aliases - map alternative names to canonical names
COIN_ALIASES = {
    "RNDR": "RENDER",  # RNDR is stored as RENDER in database
}

def normalize_coin_symbol(coin: str) -> str:
    """Normalize coin symbol using aliases"""
    coin_upper = coin.upper()
    normalized = COIN_ALIASES.get(coin_upper, coin_upper)
    if coin_upper != normalized:
        logger.info(f"Normalizing {coin_upper} -> {normalized}")
    return normalized

app = FastAPI(
    title="DataAgent API",
    description="Historical OHLC data service for Kadirov Quant Lab",
    version="1.0.0"
)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "service": "DataAgent",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        uptime_seconds=0.0,  # TODO: Track actual uptime
        last_update=None,     # TODO: Track last successful update
        tracked_coins=settings.tracked_coins_list
    )


@app.get("/coins", tags=["Data"])
async def get_available_coins() -> List[str]:
    """Get list of coins that have data available"""
    coins = await data_manager.get_available_coins()
    return coins


@app.get("/candles/{coin}", response_model=List[OHLCCandle], tags=["Data"])
async def get_candles(
    coin: str,
    start: Optional[datetime] = Query(None, description="Start timestamp (ISO format)"),
    end: Optional[datetime] = Query(None, description="End timestamp (ISO format)"),
    limit: Optional[int] = Query(None, description="Maximum number of candles")
):
    """
    Get OHLC candles for a coin

    - **coin**: Coin symbol (e.g., BTC, ETH)
    - **start**: Optional start timestamp
    - **end**: Optional end timestamp
    - **limit**: Optional limit on number of candles
    """
    normalized_coin = normalize_coin_symbol(coin)
    logger.info(f"API: get_candles called for {coin} -> normalized to {normalized_coin}")
    candles = await data_manager.get_candles(
        coin=normalized_coin,
        start_time=start,
        end_time=end,
        limit=limit
    )

    if not candles:
        raise HTTPException(status_code=404, detail=f"No data found for {coin}")

    return candles


@app.get("/candles/{coin}/latest", response_model=List[OHLCCandle], tags=["Data"])
async def get_latest_candles(
    coin: str,
    count: int = Query(100, description="Number of candles to retrieve", ge=1, le=10000)
):
    """
    Get the most recent N candles for a coin

    - **coin**: Coin symbol (e.g., BTC, ETH)
    - **count**: Number of candles (default: 100, max: 10000)
    """
    normalized_coin = normalize_coin_symbol(coin)
    candles = await data_manager.get_latest_candles(normalized_coin, count=count)

    if not candles:
        raise HTTPException(status_code=404, detail=f"No data found for {coin}")

    return candles


@app.get("/candles/{coin}/csv", tags=["Data"])
async def get_candles_csv(
    coin: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None)
):
    """
    Download OHLC candles as CSV file

    - **coin**: Coin symbol
    - **start**: Optional start timestamp
    - **end**: Optional end timestamp
    """
    normalized_coin = normalize_coin_symbol(coin)
    candles = await data_manager.get_candles(
        coin=normalized_coin,
        start_time=start,
        end_time=end
    )

    if not candles:
        raise HTTPException(status_code=404, detail=f"No data found for {coin}")

    # Convert to DataFrame
    df = pd.DataFrame([
        {
            'time': c.time.strftime('%Y-%m-%d %H:%M:%S'),
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume,
            'close_btc': c.close_btc
        }
        for c in candles
    ])

    # Convert to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    # Return as streaming response
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={coin}_ohlc.csv"
        }
    )


@app.post("/update/{coin}", response_model=UpdateStatusResponse, tags=["Admin"])
async def trigger_update(coin: str):
    """
    Manually trigger an update for a specific coin

    - **coin**: Coin symbol to update
    """
    result = await updater.update_coin(coin.upper())
    return result


@app.post("/update/all", tags=["Admin"])
async def trigger_update_all():
    """Manually trigger an update for all tracked coins"""
    results = await updater.update_all_coins()
    return results


@app.post("/register", response_model=StrategyRegistrationResponse, tags=["Strategy Management"])
async def register_strategy(registration: StrategyRegistration):
    """
    Register a trading strategy with the coins it trades

    When a bot starts, it should register itself with DataAgent.
    DataAgent will then subscribe to live price feeds for those coins.

    Example:
    POST /register
    {
        "strategy_name": "MovingAverages",
        "coins": ["BTC", "ETH", "SOL"]
    }
    """
    try:
        success = await ws_manager.register_strategy(
            registration.strategy_name,
            registration.coins
        )

        return StrategyRegistrationResponse(
            strategy_name=registration.strategy_name,
            coins=registration.coins,
            success=success,
            message=f"Strategy '{registration.strategy_name}' registered with {len(registration.coins)} coins"
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unregister/{strategy_name}", response_model=StrategyRegistrationResponse, tags=["Strategy Management"])
async def unregister_strategy(strategy_name: str):
    """
    Unregister a trading strategy

    When a bot stops, it should unregister itself.
    DataAgent will then unsubscribe from price feeds that are no longer needed.

    Example:
    POST /unregister/MovingAverages
    """
    try:
        success = await ws_manager.unregister_strategy(strategy_name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

        return StrategyRegistrationResponse(
            strategy_name=strategy_name,
            coins=[],
            success=success,
            message=f"Strategy '{strategy_name}' unregistered"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unregistration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/strategies", tags=["Strategy Management"])
async def get_registered_strategies():
    """Get all registered strategies and their coins"""
    strategies = ws_manager.get_registered_strategies()

    return {
        "strategies": {
            name: list(coins) for name, coins in strategies.items()
        },
        "active_coins": list(ws_manager.get_active_coins()),
        "total_strategies": len(strategies)
    }


@app.websocket("/ws/prices/{coin}")
async def websocket_endpoint(websocket: WebSocket, coin: str):
    """
    WebSocket endpoint for live price streaming

    Connect to receive real-time ticker updates for a specific coin:
    ws://localhost:8000/ws/prices/BTC

    Message format:
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
    """
    await websocket.accept()
    coin = coin.upper()

    logger.info(f"WebSocket client connected for {coin}")

    try:
        # Add client to WebSocket manager
        await ws_manager.add_client(coin, websocket)

        # Keep connection alive (client will receive broadcasts from ws_manager)
        while True:
            try:
                # Just keep connection alive, ignore any client messages
                await websocket.receive_text()
            except:
                # Connection closed
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from {coin}")
    except Exception as e:
        logger.error(f"WebSocket error for {coin}: {e}")
    finally:
        await ws_manager.remove_client(coin, websocket)


@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    logger.info("Starting DataAgent API...")

    # Connect to database
    await db.connect()

    # Start WebSocket manager (Kraken live prices)
    await ws_manager.start()

    # Start scheduler
    await scheduler.start()

    logger.info("DataAgent API ready")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down DataAgent API...")

    # Stop scheduler
    await scheduler.stop()

    # Stop WebSocket manager
    await ws_manager.stop()

    # Disconnect from database
    await db.disconnect()

    logger.info("DataAgent API stopped")
