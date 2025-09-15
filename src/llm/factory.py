"""LLM client factory for creating provider-specific clients."""

from typing import Optional

import structlog

from .anthropic_client import AnthropicClient
from .base import BaseLLMClient
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient
from ..core.settings import get_settings
from ..core.types import LLMProvider

logger = structlog.get_logger(__name__)


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    def __init__(self):
        """Initialize the factory."""
        self.settings = get_settings()
    
    def create_client(
        self,
        provider: Optional[LLMProvider] = None,
        **kwargs,
    ) -> BaseLLMClient:
        """Create an LLM client for the specified provider.
        
        Args:
            provider: LLM provider (defaults to primary provider from settings)
            **kwargs: Additional parameters for client initialization
            
        Returns:
            LLM client instance
            
        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        if provider is None:
            provider = LLMProvider(self.settings.llm.primary_provider)
        
        logger.info("Creating LLM client", provider=provider.value)
        
        if provider == LLMProvider.OPENAI:
            return self._create_openai_client(**kwargs)
        elif provider == LLMProvider.ANTHROPIC:
            return self._create_anthropic_client(**kwargs)
        elif provider == LLMProvider.GEMINI:
            return self._create_gemini_client(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def _create_openai_client(self, **kwargs) -> OpenAIClient:
        """Create OpenAI client.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            OpenAI client instance
        """
        api_key = kwargs.get("api_key") or self.settings.llm.openai_api_key
        model = kwargs.get("model") or self.settings.llm.openai_model
        
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        return OpenAIClient(model=model, api_key=api_key)
    
    def _create_anthropic_client(self, **kwargs) -> AnthropicClient:
        """Create Anthropic client.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Anthropic client instance
        """
        api_key = kwargs.get("api_key") or self.settings.llm.anthropic_api_key
        model = kwargs.get("model") or self.settings.llm.anthropic_model
        
        if not api_key:
            raise ValueError("Anthropic API key is required")
        
        return AnthropicClient(model=model, api_key=api_key)
    
    def _create_gemini_client(self, **kwargs) -> GeminiClient:
        """Create Gemini client.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Gemini client instance
        """
        api_key = kwargs.get("api_key") or self.settings.llm.gemini_api_key
        model = kwargs.get("model") or self.settings.llm.gemini_model
        
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        return GeminiClient(model=model, api_key=api_key)
    
    def create_fallback_client(self, **kwargs) -> BaseLLMClient:
        """Create a fallback client using the first available provider.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            LLM client instance
            
        Raises:
            ValueError: If no providers are available
        """
        # Try primary provider first
        try:
            return self.create_client(**kwargs)
        except ValueError as e:
            logger.warning("Primary provider failed", error=str(e))
        
        # Try fallback providers
        for provider_name in self.settings.llm.fallback_providers:
            try:
                provider = LLMProvider(provider_name)
                return self.create_client(provider=provider, **kwargs)
            except ValueError as e:
                logger.warning("Fallback provider failed", provider=provider_name, error=str(e))
                continue
        
        raise ValueError("No LLM providers are available")


# Global factory instance
llm_factory = LLMClientFactory()


def get_llm_client(provider: Optional[LLMProvider] = None, **kwargs) -> BaseLLMClient:
    """Get an LLM client instance.
    
    Args:
        provider: LLM provider (defaults to primary provider from settings)
        **kwargs: Additional parameters for client initialization
        
    Returns:
        LLM client instance
    """
    return llm_factory.create_client(provider, **kwargs)


def get_fallback_llm_client(**kwargs) -> BaseLLMClient:
    """Get a fallback LLM client instance.
    
    Args:
        **kwargs: Additional parameters for client initialization
        
    Returns:
        LLM client instance
    """
    return llm_factory.create_fallback_client(**kwargs)
