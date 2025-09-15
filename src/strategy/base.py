"""Base strategy implementation and interfaces."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import structlog

from ..core.types import OHLCVData, TechnicalIndicators, TradingDecision, StrategyConfig
from ..llm.base import BaseLLMClient

logger = structlog.get_logger(__name__)


class StrategyError(Exception):
    """Exception raised during strategy operations."""
    pass


class BaseStrategy(ABC):
    """Base class for trading strategies."""
    
    def __init__(self, name: str, description: str, llm_client: Optional[BaseLLMClient] = None):
        """Initialize the strategy.
        
        Args:
            name: Strategy name
            description: Strategy description
            llm_client: Optional LLM client for AI-powered decisions
        """
        self.name = name
        self.description = description
        self.llm_client = llm_client
    
    @abstractmethod
    def decide(
        self,
        data: List[OHLCVData],
        indicators: TechnicalIndicators,
        signals: Dict[str, str],
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
        pass
    
    def validate_config(self, config: StrategyConfig) -> bool:
        """Validate strategy configuration.
        
        Args:
            config: Strategy configuration
            
        Returns:
            True if configuration is valid
        """
        # Basic validation
        if config.max_risk_per_trade <= 0 or config.max_risk_per_trade > 0.1:
            return False
        
        if config.max_drawdown <= 0 or config.max_drawdown > 0.5:
            return False
        
        if config.min_confidence < 0 or config.min_confidence > 1:
            return False
        
        return True
    
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        risk_percentage: float,
    ) -> float:
        """Calculate position size based on risk management.
        
        Args:
            account_balance: Current account balance
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_percentage: Risk percentage per trade
            
        Returns:
            Position size
        """
        if stop_loss_price == entry_price:
            return 0.0
        
        risk_amount = account_balance * risk_percentage
        price_difference = abs(entry_price - stop_loss_price)
        
        return risk_amount / price_difference
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        stop_loss_pct: float,
    ) -> float:
        """Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            side: Order side (BUY/SELL)
            stop_loss_pct: Stop loss percentage
            
        Returns:
            Stop loss price
        """
        if side == "BUY":
            return entry_price * (1 - stop_loss_pct)
        else:  # SELL
            return entry_price * (1 + stop_loss_pct)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        side: str,
        take_profit_pct: float,
    ) -> float:
        """Calculate take profit price.
        
        Args:
            entry_price: Entry price
            side: Order side (BUY/SELL)
            take_profit_pct: Take profit percentage
            
        Returns:
            Take profit price
        """
        if side == "BUY":
            return entry_price * (1 + take_profit_pct)
        else:  # SELL
            return entry_price * (1 - take_profit_pct)
    
    def get_strategy_info(self) -> Dict[str, str]:
        """Get strategy information.
        
        Returns:
            Dictionary with strategy information
        """
        return {
            "name": self.name,
            "description": self.description,
            "has_llm": self.llm_client is not None,
        }
