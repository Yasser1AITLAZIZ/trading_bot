"""Strategy registry for managing available trading strategies."""

from typing import Dict, List, Optional, Type

import structlog

from .base import BaseStrategy
from .llm_strategy import LLMStrategy
from .technical_strategy import TechnicalStrategy
from ..llm.base import BaseLLMClient
from ..llm.factory import get_llm_client

logger = structlog.get_logger(__name__)


class StrategyRegistry:
    """Registry for managing available trading strategies."""
    
    def __init__(self):
        """Initialize the strategy registry."""
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._register_default_strategies()
    
    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """Register a new strategy.
        
        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        self._strategies[name] = strategy_class
        logger.info("Registered strategy", name=name, class_name=strategy_class.__name__)
    
    def get_strategy(self, name: str, **kwargs) -> Optional[BaseStrategy]:
        """Get a strategy instance by name.
        
        Args:
            name: Strategy name
            **kwargs: Additional parameters for strategy initialization
            
        Returns:
            Strategy instance or None if not found
        """
        if name not in self._strategies:
            logger.warning("Strategy not found", name=name, available=list(self._strategies.keys()))
            return None
        
        try:
            strategy_class = self._strategies[name]
            return strategy_class(**kwargs)
        except Exception as e:
            logger.error("Failed to create strategy", name=name, error=str(e))
            return None
    
    def list_strategies(self) -> List[str]:
        """List all available strategy names.
        
        Returns:
            List of strategy names
        """
        return list(self._strategies.keys())
    
    def get_strategy_info(self, name: str) -> Optional[Dict[str, str]]:
        """Get strategy information.
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy information dictionary or None if not found
        """
        strategy = self.get_strategy(name)
        if strategy:
            return strategy.get_strategy_info()
        return None
    
    def _register_default_strategies(self) -> None:
        """Register default strategies."""
        # Register technical strategy
        self.register_strategy("technical", TechnicalStrategy)
        
        # Register LLM strategy (requires LLM client)
        self.register_strategy("llm", LLMStrategy)
        
        logger.info("Registered default strategies", strategies=list(self._strategies.keys()))


class StrategyFactory:
    """Factory for creating strategy instances with proper configuration."""
    
    def __init__(self, registry: Optional[StrategyRegistry] = None):
        """Initialize the strategy factory.
        
        Args:
            registry: Strategy registry (defaults to global registry)
        """
        self.registry = registry or StrategyRegistry()
    
    def create_strategy(
        self,
        name: str,
        llm_provider: Optional[str] = None,
        **kwargs,
    ) -> Optional[BaseStrategy]:
        """Create a strategy instance with proper configuration.
        
        Args:
            name: Strategy name
            llm_provider: LLM provider for LLM-based strategies
            **kwargs: Additional parameters
            
        Returns:
            Strategy instance or None if creation failed
        """
        if name == "llm":
            # Create LLM client for LLM strategy
            try:
                if llm_provider:
                    llm_client = get_llm_client(provider=llm_provider)
                else:
                    llm_client = get_llm_client()
                
                return self.registry.get_strategy(name, llm_client=llm_client, **kwargs)
            except Exception as e:
                logger.error("Failed to create LLM strategy", error=str(e))
                return None
        else:
            # Create other strategies
            return self.registry.get_strategy(name, **kwargs)
    
    def create_strategy_with_fallback(
        self,
        primary_name: str,
        fallback_name: str = "technical",
        **kwargs,
    ) -> Optional[BaseStrategy]:
        """Create a strategy with fallback option.
        
        Args:
            primary_name: Primary strategy name
            fallback_name: Fallback strategy name
            **kwargs: Additional parameters
            
        Returns:
            Strategy instance or None if both fail
        """
        # Try primary strategy first
        strategy = self.create_strategy(primary_name, **kwargs)
        if strategy:
            logger.info("Created primary strategy", name=primary_name)
            return strategy
        
        # Try fallback strategy
        logger.warning("Primary strategy failed, trying fallback", primary=primary_name, fallback=fallback_name)
        strategy = self.create_strategy(fallback_name, **kwargs)
        if strategy:
            logger.info("Created fallback strategy", name=fallback_name)
            return strategy
        
        logger.error("Both primary and fallback strategies failed", primary=primary_name, fallback=fallback_name)
        return None


# Global registry and factory instances
strategy_registry = StrategyRegistry()
strategy_factory = StrategyFactory(strategy_registry)


def get_strategy(name: str, **kwargs) -> Optional[BaseStrategy]:
    """Get a strategy instance by name.
    
    Args:
        name: Strategy name
        **kwargs: Additional parameters
        
    Returns:
        Strategy instance or None if not found
    """
    return strategy_factory.create_strategy(name, **kwargs)


def get_strategy_with_fallback(primary_name: str, fallback_name: str = "technical", **kwargs) -> Optional[BaseStrategy]:
    """Get a strategy with fallback option.
    
    Args:
        primary_name: Primary strategy name
        fallback_name: Fallback strategy name
        **kwargs: Additional parameters
        
    Returns:
        Strategy instance or None if both fail
    """
    return strategy_factory.create_strategy_with_fallback(primary_name, fallback_name, **kwargs)


def list_available_strategies() -> List[str]:
    """List all available strategies.
    
    Returns:
        List of strategy names
    """
    return strategy_registry.list_strategies()
