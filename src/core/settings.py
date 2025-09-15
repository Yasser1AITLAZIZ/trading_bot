"""Application settings and configuration management."""

import os
from typing import Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    url: str = Field(default="sqlite:///trading_bot.db", description="Database URL")
    echo: bool = Field(default=False, description="Enable SQL echo for debugging")


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    # Provider selection
    primary_provider: str = Field(default="openai", description="Primary LLM provider")
    fallback_providers: List[str] = Field(default=["anthropic", "gemini"], description="Fallback providers")
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=1000, description="Maximum tokens for OpenAI")
    openai_temperature: float = Field(default=0.1, description="OpenAI temperature")
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model to use")
    anthropic_max_tokens: int = Field(default=1000, description="Maximum tokens for Anthropic")
    anthropic_temperature: float = Field(default=0.1, description="Anthropic temperature")
    
    # Gemini settings
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    gemini_model: str = Field(default="gemini-pro", description="Gemini model to use")
    gemini_max_tokens: int = Field(default=1000, description="Maximum tokens for Gemini")
    gemini_temperature: float = Field(default=0.1, description="Gemini temperature")
    
    # Rate limiting
    max_requests_per_minute: int = Field(default=60, description="Maximum requests per minute")
    max_tokens_per_minute: int = Field(default=100000, description="Maximum tokens per minute")
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    
    # Telegram integration
    telegram_bot_token: Optional[str] = Field(default=None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID for notifications")
    telegram_allowed_users: List[int] = Field(default=[], description="List of allowed Telegram user IDs")
    
    @validator("primary_provider")
    def validate_primary_provider(cls, v: str) -> str:
        """Validate primary provider is supported."""
        valid_providers = ["openai", "anthropic", "gemini"]
        if v not in valid_providers:
            raise ValueError(f"Primary provider must be one of {valid_providers}")
        return v


class BinanceSettings(BaseSettings):
    """Binance API configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="BINANCE_")
    
    # API credentials
    api_key: Optional[str] = Field(default=None, description="Binance API key")
    secret_key: Optional[str] = Field(default=None, description="Binance secret key")
    
    # Trading mode
    mode: str = Field(default="paper", description="Trading mode (paper/testnet/live)")
    testnet_url: str = Field(
        default="https://testnet.binance.vision",
        description="Binance testnet URL"
    )
    live_url: str = Field(
        default="https://api.binance.com",
        description="Binance live API URL"
    )
    
    # Risk management
    max_risk_per_trade: float = Field(default=0.01, description="Maximum risk per trade (1%)")
    max_position_size: float = Field(default=0.1, description="Maximum position size (10%)")
    max_daily_trades: int = Field(default=50, description="Maximum daily trades")
    max_daily_loss: float = Field(default=0.05, description="Maximum daily loss (5%)")
    
    # Order settings
    default_time_in_force: str = Field(default="GTC", description="Default time in force")
    min_order_size: float = Field(default=10.0, description="Minimum order size in USDT")
    max_order_size: float = Field(default=10000.0, description="Maximum order size in USDT")
    
    # Rate limiting
    requests_per_minute: int = Field(default=1200, description="API requests per minute limit")
    orders_per_second: int = Field(default=10, description="Orders per second limit")
    
    @validator("mode")
    def validate_mode(cls, v: str) -> str:
        """Validate trading mode."""
        valid_modes = ["paper", "testnet", "live"]
        if v not in valid_modes:
            raise ValueError(f"Mode must be one of {valid_modes}")
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="LOG_")
    
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="json",
        description="Log format (json/text)"
    )
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max log file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup log files")
    
    # Structured logging
    include_timestamps: bool = Field(default=True, description="Include timestamps in logs")
    include_correlation_ids: bool = Field(default=True, description="Include correlation IDs")
    mask_sensitive_data: bool = Field(default=True, description="Mask sensitive data in logs")
    
    @validator("level")
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class DataSettings(BaseSettings):
    """Data processing configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="DATA_")
    
    # Data sources
    data_directory: str = Field(default="./data", description="Data directory path")
    cache_directory: str = Field(default="./cache", description="Cache directory path")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    
    # Data validation
    max_data_age_hours: int = Field(default=24, description="Maximum data age in hours")
    min_data_points: int = Field(default=100, description="Minimum data points required")
    max_missing_data_pct: float = Field(default=0.05, description="Maximum missing data percentage")
    
    # Technical indicators
    rsi_period: int = Field(default=14, description="RSI calculation period")
    sma_period: int = Field(default=20, description="SMA calculation period")
    ema_period: int = Field(default=20, description="EMA calculation period")
    atr_period: int = Field(default=14, description="ATR calculation period")
    
    # Data formats
    supported_formats: List[str] = Field(
        default=["csv", "json", "parquet"],
        description="Supported data formats"
    )
    default_format: str = Field(default="csv", description="Default data format")


class StreamingSettings(BaseSettings):
    """Streaming configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="STREAMING_")
    
    # WebSocket settings
    websocket_retry_attempts: int = Field(default=5, description="Maximum WebSocket retry attempts")
    websocket_retry_delay: int = Field(default=30, description="WebSocket retry delay in seconds")
    websocket_ping_interval: int = Field(default=20, description="WebSocket ping interval in seconds")
    websocket_ping_timeout: int = Field(default=10, description="WebSocket ping timeout in seconds")
    
    # Data buffer settings
    buffer_max_size: int = Field(default=480, description="Maximum buffer size (8 hours of 1m data)")
    buffer_validation: bool = Field(default=True, description="Enable data validation")
    buffer_duplicate_check: bool = Field(default=True, description="Check for duplicate data")
    
    # Analysis scheduler settings
    analysis_interval: int = Field(default=60, description="Analysis interval in seconds")
    analysis_alignment: bool = Field(default=True, description="Align analysis to minute boundaries")
    max_consecutive_errors: int = Field(default=5, description="Maximum consecutive analysis errors")


class TradingSettings(BaseSettings):
    """Trading configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="TRADING_")
    
    # Order management
    max_concurrent_orders: int = Field(default=2, description="Maximum concurrent orders")
    order_timeout: int = Field(default=30, description="Order execution timeout in seconds")
    
    # Risk management
    max_daily_trades: int = Field(default=50, description="Maximum daily trades")
    max_daily_loss: float = Field(default=0.05, description="Maximum daily loss (5%)")
    emergency_stop_loss: float = Field(default=0.10, description="Emergency stop loss (10%)")
    
    # Trading windows
    trading_enabled: bool = Field(default=True, description="Enable trading")
    trading_windows: List[str] = Field(default=["24/7"], description="Trading time windows")


class AppSettings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application metadata
    app_name: str = Field(default="GenAI Trading Bot", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (dev/test/prod)")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    binance: BinanceSettings = Field(default_factory=BinanceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    streaming: StreamingSettings = Field(default_factory=StreamingSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    
    # Performance settings
    max_workers: int = Field(default=4, description="Maximum worker threads")
    request_timeout: int = Field(default=30, description="Default request timeout")
    retry_attempts: int = Field(default=3, description="Default retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    
    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        valid_envs = ["development", "testing", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """Get the global settings instance.
    
    Returns:
        Application settings instance
    """
    return settings


def reload_settings() -> AppSettings:
    """Reload settings from environment variables.
    
    Returns:
        Reloaded application settings instance
    """
    global settings
    settings = AppSettings()
    return settings
