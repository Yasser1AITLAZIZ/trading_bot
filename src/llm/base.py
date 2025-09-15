"""Base LLM client implementation."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog

from ..core.settings import get_settings
from ..core.types import LLMProvider, LLMResponse
from ..core.utils import retry_with_backoff

logger = structlog.get_logger(__name__)


class LLMError(Exception):
    """Exception raised during LLM operations."""
    pass


class RateLimitError(LLMError):
    """Exception raised when rate limit is exceeded."""
    pass


class BaseLLMClient(ABC):
    """Base class for LLM clients."""
    
    def __init__(self, provider: LLMProvider, model: str, api_key: str):
        """Initialize the LLM client.
        
        Args:
            provider: LLM provider
            model: Model name
            api_key: API key for the provider
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.settings = get_settings()
        self._request_count = 0
        self._token_count = 0
        self._last_reset = time.time()
    
    @abstractmethod
    def _make_request(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make a request to the LLM provider.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Raw response from the provider
        """
        pass
    
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
        start_time = time.time()
        
        # Check rate limits
        self._check_rate_limits()
        
        try:
            # Make request with retry logic
            response_data = retry_with_backoff(
                lambda: self._make_request(prompt, temperature, max_tokens, **kwargs),
                max_attempts=self.settings.llm.retry_attempts,
                base_delay=self.settings.llm.retry_delay,
            )
            
            # Extract content and usage
            content = self._extract_content(response_data)
            usage = self._extract_usage(response_data)
            
            # Update rate limit counters
            self._update_counters(usage)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=self.model,
                provider=self.provider,
                latency_ms=latency_ms,
            )
        
        except Exception as e:
            logger.error(
                "LLM request failed",
                provider=self.provider.value,
                model=self.model,
                error=str(e),
            )
            raise LLMError(f"LLM request failed: {e}")
    
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
        prompt = f"""
        Score the following text against the given criteria on a scale of 0 to 1.
        
        Text: {text}
        
        Criteria: {criteria}
        
        Provide only a numerical score between 0 and 1 (e.g., 0.85).
        """
        
        response = self.generate(prompt, temperature=0.0, max_tokens=10, **kwargs)
        
        try:
            # Extract numerical score from response
            score_text = response.content.strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))  # Clamp between 0 and 1
        except ValueError:
            logger.warning("Failed to parse score from LLM response", response=response.content)
            return 0.5  # Default neutral score
    
    def structured(
        self,
        prompt: str,
        schema: type,
        **kwargs: Any,
    ):
        """Generate structured output using the LLM.
        
        Args:
            prompt: Input prompt
            schema: Pydantic model schema
            **kwargs: Additional parameters
            
        Returns:
            Structured response matching the schema
        """
        # Add schema instruction to prompt
        structured_prompt = f"""
        {prompt}
        
        Please respond with valid JSON that matches this schema:
        {schema.model_json_schema()}
        
        Ensure the response is valid JSON and matches the required structure.
        """
        
        response = self.generate(structured_prompt, temperature=0.1, **kwargs)
        
        try:
            import json
            data = json.loads(response.content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse structured response", error=str(e), response=response.content)
            raise LLMError(f"Failed to generate structured response: {e}")
    
    def _check_rate_limits(self) -> None:
        """Check if rate limits are exceeded."""
        current_time = time.time()
        
        # Reset counters every minute
        if current_time - self._last_reset >= 60:
            self._request_count = 0
            self._token_count = 0
            self._last_reset = current_time
        
        # Check request rate limit
        if self._request_count >= self.settings.llm.max_requests_per_minute:
            raise RateLimitError("Request rate limit exceeded")
        
        # Check token rate limit
        if self._token_count >= self.settings.llm.max_tokens_per_minute:
            raise RateLimitError("Token rate limit exceeded")
    
    def _update_counters(self, usage: Dict[str, int]) -> None:
        """Update rate limit counters.
        
        Args:
            usage: Token usage information
        """
        self._request_count += 1
        self._token_count += usage.get("total_tokens", 0)
    
    @abstractmethod
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from provider response.
        
        Args:
            response_data: Raw response from provider
            
        Returns:
            Extracted content string
        """
        pass
    
    @abstractmethod
    def _extract_usage(self, response_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract usage information from provider response.
        
        Args:
            response_data: Raw response from provider
            
        Returns:
            Usage information dictionary
        """
        pass
