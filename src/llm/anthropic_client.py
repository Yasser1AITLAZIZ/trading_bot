"""Anthropic LLM client implementation."""

from typing import Any, Dict

import anthropic
import structlog

from .base import BaseLLMClient
from ..core.types import LLMProvider

logger = structlog.get_logger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic LLM client."""
    
    def __init__(self, model: str = "claude-3-sonnet-20240229", api_key: str = None):
        """Initialize Anthropic client.
        
        Args:
            model: Anthropic model name
            api_key: Anthropic API key
        """
        super().__init__(LLMProvider.ANTHROPIC, model, api_key)
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def _make_request(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make a request to Anthropic API.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Raw response from Anthropic
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            )
            
            return response.model_dump()
        
        except Exception as e:
            logger.error("Anthropic API request failed", error=str(e))
            raise
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from Anthropic response.
        
        Args:
            response_data: Raw response from Anthropic
            
        Returns:
            Extracted content string
        """
        try:
            return response_data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error("Failed to extract content from Anthropic response", error=str(e))
            raise
    
    def _extract_usage(self, response_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract usage information from Anthropic response.
        
        Args:
            response_data: Raw response from Anthropic
            
        Returns:
            Usage information dictionary
        """
        try:
            usage = response_data.get("usage", {})
            return {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            }
        except Exception as e:
            logger.error("Failed to extract usage from Anthropic response", error=str(e))
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
