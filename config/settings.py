"""
Configuration management for the Trading System.
Uses Pydantic Settings for type-safe configuration.
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI
    openai_api_key: str = "your_openai_key_here"
    openai_model: str = "gpt-4o-mini"
    
    # Polygon API
    polygon_api_key: str = ""
    
    # Brave Search API
    brave_api_key: str = ""
    
    # Pushover
    pushover_user_key: str = ""
    pushover_api_token: str = ""
    
    # Trading Configuration
    initial_capital: float = 100000.0
    max_position_size: float = 0.1  # 10% of portfolio
    risk_per_trade: float = 0.02    # 2% risk per trade
    paper_trading: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trading_floor.log"
    
    # Default tickers to monitor
    default_tickers: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
