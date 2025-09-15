"""OpenAI LLM client implementation."""

from typing import Any, Dict

import openai
import structlog

from .base import BaseLLMClient
from ..core.types import LLMProvider

logger = structlog.get_logger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM client."""
    
    def __init__(self, model: str = "gpt-4", api_key: str = None):
        """Initialize OpenAI client.
        
        Args:
            model: OpenAI model name
            api_key: OpenAI API key
        """
        super().__init__(LLMProvider.OPENAI, model, api_key)
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=api_key)
    
    def _make_request(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make a request to OpenAI API.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Raw response from OpenAI
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful trading assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.model_dump()
        
        except Exception as e:
            logger.error("OpenAI API request failed", error=str(e))
            raise
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from OpenAI response.
        
        Args:
            response_data: Raw response from OpenAI
            
        Returns:
            Extracted content string
        """
        try:
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error("Failed to extract content from OpenAI response", error=str(e))
            raise
    
    def _extract_usage(self, response_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract usage information from OpenAI response.
        
        Args:
            response_data: Raw response from OpenAI
            
        Returns:
            Usage information dictionary
        """
        try:
            usage = response_data.get("usage", {})
            return {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        except Exception as e:
            logger.error("Failed to extract usage from OpenAI response", error=str(e))
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
