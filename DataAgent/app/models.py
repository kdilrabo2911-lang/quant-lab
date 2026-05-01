"""
Data models for DataAgent
"""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class OHLCCandle(BaseModel):
    """Single OHLC candle"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_btc: float


class PresignedURLResponse(BaseModel):
    """Response containing S3 presigned URL"""
    coin: str
    url: str
    expires_in_seconds: int
    file_key: str


class UpdateStatusResponse(BaseModel):
    """Status of data update operation"""
    coin: str
    success: bool
    candles_added: int
    latest_timestamp: Optional[datetime]
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    uptime_seconds: float
    last_update: Optional[datetime]
    tracked_coins: List[str]


class StrategyRegistration(BaseModel):
    """Strategy registration request"""
    strategy_name: str
    coins: List[str]  # List of coins this strategy trades


class StrategyRegistrationResponse(BaseModel):
    """Strategy registration response"""
    strategy_name: str
    coins: List[str]
    success: bool
    message: str
