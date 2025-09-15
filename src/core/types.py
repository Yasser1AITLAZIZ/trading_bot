"""Core type definitions for the trading bot."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

from pydantic import BaseModel, Field


class TradingMode(str, Enum):
    """Trading execution modes."""
    
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


class OrderSide(str, Enum):
    """Order side enumeration."""
    
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration."""
    
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class OHLCVData(BaseModel):
    """OHLCV (Open, High, Low, Close, Volume) data point."""
    
    timestamp: datetime = Field(..., description="Timestamp in UTC")
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Highest price")
    low: Decimal = Field(..., gt=0, description="Lowest price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(..., ge=0, description="Trading volume")
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")


class TechnicalIndicators(BaseModel):
    """Technical indicators calculated from OHLCV data."""
    
    rsi: Optional[float] = Field(None, ge=0, le=100, description="Relative Strength Index")
    sma_20: Optional[float] = Field(None, gt=0, description="Simple Moving Average (20 periods)")
    ema_20: Optional[float] = Field(None, gt=0, description="Exponential Moving Average (20 periods)")
    atr: Optional[float] = Field(None, gt=0, description="Average True Range")
    volatility: Optional[float] = Field(None, ge=0, description="Price volatility")
    log_returns: Optional[List[float]] = Field(None, description="Logarithmic returns")


class MarketSignals(BaseModel):
    """Market signals derived from technical analysis."""
    
    trend: str = Field(..., description="Market trend (bullish/bearish/sideways)")
    momentum: str = Field(..., description="Momentum signal (strong/weak/neutral)")
    volatility_regime: str = Field(..., description="Volatility regime (high/low/normal)")
    support_resistance: Dict[str, float] = Field(default_factory=dict, description="Support and resistance levels")


class TradingDecision(BaseModel):
    """Trading decision made by the strategy."""
    
    action: OrderSide = Field(..., description="Trading action to take")
    symbol: str = Field(..., description="Trading symbol")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    price: Optional[Decimal] = Field(None, gt=0, description="Order price (for limit orders)")
    stop_loss: Optional[Decimal] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price")
    confidence: float = Field(..., ge=0, le=1, description="Decision confidence (0-1)")
    reasoning: str = Field(..., description="Human-readable reasoning for the decision")
    risk_score: float = Field(..., ge=0, le=1, description="Risk assessment (0-1)")


class OrderRequest(BaseModel):
    """Order request to be sent to the exchange."""
    
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    price: Optional[Decimal] = Field(None, gt=0, description="Order price")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="Stop price")
    time_in_force: str = Field(default="GTC", description="Time in force")
    client_order_id: Optional[str] = Field(None, description="Client order ID")


class OrderResponse(BaseModel):
    """Response from order execution."""
    
    order_id: str = Field(..., description="Exchange order ID")
    client_order_id: Optional[str] = Field(None, description="Client order ID")
    symbol: str = Field(..., description="Trading symbol")
    status: OrderStatus = Field(..., description="Order status")
    side: OrderSide = Field(..., description="Order side")
    quantity: Decimal = Field(..., description="Order quantity")
    price: Optional[Decimal] = Field(None, description="Order price")
    executed_quantity: Decimal = Field(default=Decimal("0"), description="Executed quantity")
    executed_price: Optional[Decimal] = Field(None, description="Average executed price")
    timestamp: datetime = Field(..., description="Order timestamp")


class LLMResponse(BaseModel):
    """Response from LLM provider."""
    
    content: str = Field(..., description="Generated content")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")
    model: str = Field(..., description="Model used")
    provider: LLMProvider = Field(..., description="LLM provider")
    latency_ms: float = Field(..., description="Response latency in milliseconds")


class StrategyConfig(BaseModel):
    """Configuration for a trading strategy."""
    
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    max_risk_per_trade: float = Field(default=0.01, ge=0, le=0.1, description="Maximum risk per trade (1% default)")
    max_drawdown: float = Field(default=0.05, ge=0, le=0.5, description="Maximum drawdown (5% default)")
    stop_loss_pct: float = Field(default=0.02, ge=0, le=0.1, description="Stop loss percentage (2% default)")
    take_profit_pct: float = Field(default=0.04, ge=0, le=0.2, description="Take profit percentage (4% default)")
    min_confidence: float = Field(default=0.7, ge=0, le=1, description="Minimum confidence threshold")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")


class TradingSession(BaseModel):
    """Trading session information."""
    
    session_id: str = Field(..., description="Unique session identifier")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    mode: TradingMode = Field(..., description="Trading mode")
    strategy: str = Field(..., description="Active strategy name")
    initial_balance: Decimal = Field(..., description="Initial balance")
    current_balance: Decimal = Field(..., description="Current balance")
    total_trades: int = Field(default=0, description="Total number of trades")
    successful_trades: int = Field(default=0, description="Number of successful trades")
    pnl: Decimal = Field(default=Decimal("0"), description="Profit and loss")


class Strategy(Protocol):
    """Protocol for trading strategies."""
    
    def decide(
        self,
        data: List[OHLCVData],
        indicators: TechnicalIndicators,
        signals: MarketSignals,
        config: StrategyConfig,
    ) -> TradingDecision:
        """Make a trading decision based on market data and signals.
        
        Args:
            data: Historical OHLCV data
            indicators: Technical indicators
            signals: Market signals
            config: Strategy configuration
            
        Returns:
            Trading decision
        """
        ...


class LLMClient(Protocol):
    """Protocol for LLM clients."""
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text using the LLM.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLM response
        """
        ...
    
    def score(
        self,
        text: str,
        criteria: str,
        **kwargs: Any,
    ) -> float:
        """Score text against criteria.
        
        Args:
            text: Text to score
            criteria: Scoring criteria
            **kwargs: Additional parameters
            
        Returns:
            Score between 0 and 1
        """
        ...
    
    def structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """Generate structured output using the LLM.
        
        Args:
            prompt: Input prompt
            schema: Pydantic model schema
            **kwargs: Additional parameters
            
        Returns:
            Structured response matching the schema
        """
        ...
