"""Google Gemini LLM client implementation."""

from typing import Any, Dict

import google.generativeai as genai
import structlog

from .base import BaseLLMClient
from ..core.types import LLMProvider

logger = structlog.get_logger(__name__)


class GeminiClient(BaseLLMClient):
    """Google Gemini LLM client."""
    
    def __init__(self, model: str = "gemini-pro", api_key: str = None):
        """Initialize Gemini client.
        
        Args:
            model: Gemini model name
            api_key: Gemini API key
        """
        super().__init__(LLMProvider.GEMINI, model, api_key)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)
    
    def _make_request(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make a request to Gemini API.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Raw response from Gemini
        """
        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            response = self.model_instance.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Convert to dictionary format
            return {
                "text": response.text,
                "usage_metadata": getattr(response, "usage_metadata", {}),
            }
        
        except Exception as e:
            logger.error("Gemini API request failed", error=str(e))
            raise
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from Gemini response.
        
        Args:
            response_data: Raw response from Gemini
            
        Returns:
            Extracted content string
        """
        try:
            return response_data["text"]
        except KeyError as e:
            logger.error("Failed to extract content from Gemini response", error=str(e))
            raise
    
    def _extract_usage(self, response_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract usage information from Gemini response.
        
        Args:
            response_data: Raw response from Gemini
            
        Returns:
            Usage information dictionary
        """
        try:
            usage_metadata = response_data.get("usage_metadata", {})
            return {
                "prompt_tokens": usage_metadata.get("prompt_token_count", 0),
                "completion_tokens": usage_metadata.get("candidates_token_count", 0),
                "total_tokens": usage_metadata.get("total_token_count", 0),
            }
        except Exception as e:
            logger.error("Failed to extract usage from Gemini response", error=str(e))
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
