"""
DataAgent Configuration
Loads settings from environment variables
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # PostgreSQL Database
    database_url: str

    # Kraken API (optional)
    kraken_api_key: str = ""
    kraken_api_secret: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Data Update
    update_interval_seconds: int = 300  # 5 minutes
    candle_interval_minutes: int = 5     # 5-minute candles

    # Coins to track (AUTO = fetch from database, or comma-separated list)
    tracked_coins: str = "AUTO"

    # Logging
    log_level: str = "INFO"

    # Telegram Bot (optional - used by MasterAgent)
    telegram_bot_token: str = ""
    manager_telegram_chat_id: str = ""

    # AI API Keys (optional - used by MasterAgent)
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    @property
    def tracked_coins_list(self) -> List[str]:
        """
        Parse tracked coins from comma-separated string
        Returns None if AUTO (will be fetched from database at runtime)
        """
        if self.tracked_coins.upper() == "AUTO":
            return None  # Will be populated from database
        return [coin.strip().upper() for coin in self.tracked_coins.split(',')]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
