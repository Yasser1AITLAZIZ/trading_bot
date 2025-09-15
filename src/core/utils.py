"""Utility functions and helpers."""

import hashlib
import secrets
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import structlog

logger = structlog.get_logger(__name__)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracking.
    
    Returns:
        Unique correlation ID string
    """
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(8)
    return f"{timestamp}_{random_part}"


def generate_client_order_id(symbol: str, side: str) -> str:
    """Generate a unique client order ID.
    
    Args:
        symbol: Trading symbol
        side: Order side (BUY/SELL)
        
    Returns:
        Unique client order ID
    """
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(4)
    return f"{symbol}_{side}_{timestamp}_{random_part}"


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Mask sensitive data in a dictionary.
    
    Args:
        data: Dictionary containing potentially sensitive data
        sensitive_keys: List of keys to mask (defaults to common sensitive keys)
        
    Returns:
        Dictionary with sensitive data masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "api_key", "secret_key", "password", "token", "key",
            "secret", "private_key", "access_token", "refresh_token"
        ]
    
    masked_data = data.copy()
    
    for key, value in masked_data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            if isinstance(value, str) and len(value) > 8:
                masked_data[key] = f"{value[:4]}...{value[-4:]}"
            else:
                masked_data[key] = "***MASKED***"
    
    return masked_data


def calculate_percentage_change(old_value: Union[float, Decimal], new_value: Union[float, Decimal]) -> float:
    """Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change as a float
    """
    if old_value == 0:
        return 0.0
    
    return float((new_value - old_value) / old_value * 100)


def calculate_risk_amount(account_balance: Decimal, risk_percentage: float) -> Decimal:
    """Calculate risk amount based on account balance and risk percentage.
    
    Args:
        account_balance: Current account balance
        risk_percentage: Risk percentage (0.01 = 1%)
        
    Returns:
        Risk amount in account currency
    """
    return account_balance * Decimal(str(risk_percentage))


def calculate_position_size(
    account_balance: Decimal,
    risk_percentage: float,
    entry_price: Decimal,
    stop_loss_price: Decimal,
) -> Decimal:
    """Calculate position size based on risk management parameters.
    
    Args:
        account_balance: Current account balance
        risk_percentage: Risk percentage (0.01 = 1%)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        
    Returns:
        Position size in base currency
    """
    risk_amount = calculate_risk_amount(account_balance, risk_percentage)
    price_difference = abs(entry_price - stop_loss_price)
    
    if price_difference == 0:
        return Decimal("0")
    
    return risk_amount / price_difference


def round_to_tick_size(price: Decimal, tick_size: Decimal) -> Decimal:
    """Round price to the nearest tick size.
    
    Args:
        price: Price to round
        tick_size: Minimum tick size
        
    Returns:
        Rounded price
    """
    if tick_size == 0:
        return price
    
    return (price / tick_size).quantize(Decimal("1")) * tick_size


def round_to_lot_size(quantity: Decimal, lot_size: Decimal) -> Decimal:
    """Round quantity to the nearest lot size.
    
    Args:
        quantity: Quantity to round
        lot_size: Minimum lot size
        
    Returns:
        Rounded quantity
    """
    if lot_size == 0:
        return quantity
    
    return (quantity / lot_size).quantize(Decimal("1")) * lot_size


def validate_symbol_format(symbol: str) -> bool:
    """Validate trading symbol format.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        True if symbol format is valid
    """
    if not symbol or len(symbol) < 3:
        return False
    
    # Basic validation - should be alphanumeric and contain trading pair
    return symbol.isalnum() and len(symbol) >= 3


def parse_timestamp(timestamp: Union[str, int, float, datetime]) -> datetime:
    """Parse various timestamp formats to datetime object.
    
    Args:
        timestamp: Timestamp in various formats
        
    Returns:
        Datetime object in UTC
    """
    if isinstance(timestamp, datetime):
        return timestamp.astimezone(timezone.utc)
    
    if isinstance(timestamp, str):
        # Try parsing ISO format
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            # Try parsing Unix timestamp
            try:
                return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
            except ValueError:
                raise ValueError(f"Unable to parse timestamp: {timestamp}")
    
    if isinstance(timestamp, (int, float)):
        # Handle Unix timestamp (seconds or milliseconds)
        if timestamp > 1e10:  # Milliseconds
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")


def create_data_hash(data: Any) -> str:
    """Create a hash of data for caching and deduplication.
    
    Args:
        data: Data to hash
        
    Returns:
        SHA-256 hash of the data
    """
    if isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = str(data).encode("utf-8")
    
    return hashlib.sha256(data_bytes).hexdigest()


def format_currency(amount: Decimal, currency: str = "USDT", precision: int = 2) -> str:
    """Format currency amount for display.
    
    Args:
        amount: Amount to format
        currency: Currency symbol
        precision: Decimal precision
        
    Returns:
        Formatted currency string
    """
    return f"{amount:.{precision}f} {currency}"


def format_percentage(value: float, precision: int = 2) -> str:
    """Format percentage value for display.
    
    Args:
        value: Percentage value (0.01 = 1%)
        precision: Decimal precision
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{precision}f}%"


def safe_divide(numerator: Union[float, Decimal], denominator: Union[float, Decimal], default: Union[float, Decimal] = 0) -> Union[float, Decimal]:
    """Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division by zero
        
    Returns:
        Division result or default value
    """
    if denominator == 0:
        return default
    
    return numerator / denominator


def clamp(value: Union[float, Decimal], min_value: Union[float, Decimal], max_value: Union[float, Decimal]) -> Union[float, Decimal]:
    """Clamp a value between min and max bounds.
    
    Args:
        value: Value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Clamped value
    """
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def retry_with_backoff(
    func,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter
        
    Returns:
        Function result
        
    Raises:
        Exception: Last exception if all attempts fail
    """
    import random
    
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt == max_attempts - 1:
                break
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            
            # Add jitter to prevent thundering herd
            if jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            logger.warning(
                "Retry attempt failed",
                attempt=attempt + 1,
                max_attempts=max_attempts,
                delay=delay,
                error=str(e)
            )
            
            time.sleep(delay)
    
    raise last_exception


class PerformanceTimer:
    """Context manager for measuring execution time."""
    
    def __init__(self, operation_name: str = "operation"):
        """Initialize timer.
        
        Args:
            operation_name: Name of the operation being timed
        """
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log result."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        logger.info(
            "Operation completed",
            operation=self.operation_name,
            duration_ms=duration * 1000
        )
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time
