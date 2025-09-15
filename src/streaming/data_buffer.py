"""Data buffer for managing real-time market data with circular buffer."""

import threading
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Callable, Dict, Any
import structlog

from ..core.types import OHLCVData
from ..core.utils import parse_timestamp

logger = structlog.get_logger(__name__)


class DataBufferError(Exception):
    """Exception raised during data buffer operations."""
    pass


class DataBuffer:
    """Circular buffer for managing real-time market data."""
    
    def __init__(
        self,
        initial_data: Optional[List[OHLCVData]] = None,
        max_size: int = 480,  # 8 hours of 1-minute data
        on_buffer_updated: Optional[Callable[[List[OHLCVData]], None]] = None,
    ):
        """Initialize the data buffer.
        
        Args:
            initial_data: Initial historical data to populate buffer
            max_size: Maximum number of data points to keep
            on_buffer_updated: Callback function when buffer is updated
        """
        self.max_size = max_size
        self.on_buffer_updated = on_buffer_updated
        
        # Thread-safe circular buffer
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.RLock()
        
        # Statistics
        self.total_received = 0
        self.total_dropped = 0
        self.last_update = None
        
        # Initialize with historical data if provided
        if initial_data:
            self._initialize_with_historical_data(initial_data)
        
        logger.info(
            "Initialized data buffer",
            max_size=max_size,
            initial_count=len(self.buffer),
        )
    
    def _initialize_with_historical_data(self, data: List[OHLCVData]) -> None:
        """Initialize buffer with historical data.
        
        Args:
            data: Historical OHLCV data
        """
        with self.lock:
            # Sort data by timestamp to ensure chronological order
            sorted_data = sorted(data, key=lambda x: x.timestamp)
            
            # Add data to buffer
            for item in sorted_data:
                self.buffer.append(item)
            
            self.last_update = sorted_data[-1].timestamp if sorted_data else None
            
            logger.info(
                "Initialized buffer with historical data",
                data_points=len(sorted_data),
                start_time=sorted_data[0].timestamp if sorted_data else None,
                end_time=self.last_update,
            )
    
    def add_new_candle(self, candle: OHLCVData) -> None:
        """Add a new candle to the buffer.
        
        Args:
            candle: New OHLCV data point
        """
        with self.lock:
            # Validate candle data
            self._validate_candle(candle)
            
            # Check if this is a duplicate or out-of-order candle
            if self._should_skip_candle(candle):
                logger.debug("Skipping duplicate or out-of-order candle", timestamp=candle.timestamp)
                return
            
            # Add to buffer (automatically removes oldest if at max capacity)
            old_size = len(self.buffer)
            self.buffer.append(candle)
            self.total_received += 1
            
            # Update statistics
            self.last_update = candle.timestamp
            
            # Log if we dropped data
            if old_size == self.max_size:
                self.total_dropped += 1
                logger.debug("Buffer at capacity, dropped oldest data point")
            
            # Notify callback
            if self.on_buffer_updated:
                try:
                    self.on_buffer_updated(self.get_full_history())
                except Exception as e:
                    logger.error("Error in buffer update callback", error=str(e))
            
            logger.debug(
                "Added new candle to buffer",
                timestamp=candle.timestamp,
                close=candle.close,
                buffer_size=len(self.buffer),
            )
    
    def _validate_candle(self, candle: OHLCVData) -> None:
        """Validate candle data before adding to buffer.
        
        Args:
            candle: OHLCV data to validate
            
        Raises:
            DataBufferError: If candle data is invalid
        """
        if not candle.symbol:
            raise DataBufferError("Candle symbol cannot be empty")
        
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            raise DataBufferError("Candle prices must be positive")
        
        if candle.volume < 0:
            raise DataBufferError("Candle volume cannot be negative")
        
        if candle.high < candle.low:
            raise DataBufferError("High price cannot be less than low price")
        
        if candle.high < candle.open or candle.high < candle.close:
            raise DataBufferError("High price must be >= open and close prices")
        
        if candle.low > candle.open or candle.low > candle.close:
            raise DataBufferError("Low price must be <= open and close prices")
    
    def _should_skip_candle(self, candle: OHLCVData) -> bool:
        """Check if candle should be skipped (duplicate or out-of-order).
        
        Args:
            candle: OHLCV data to check
            
        Returns:
            True if candle should be skipped
        """
        if not self.buffer:
            return False
        
        # Check for duplicate timestamp
        last_candle = self.buffer[-1]
        if candle.timestamp == last_candle.timestamp:
            return True
        
        # Check for out-of-order data (allow small tolerance for network delays)
        time_diff = (candle.timestamp - last_candle.timestamp).total_seconds()
        if time_diff < -60:  # More than 1 minute in the past
            logger.warning(
                "Received out-of-order candle data",
                candle_time=candle.timestamp,
                last_time=last_candle.timestamp,
                time_diff=time_diff,
            )
            return True
        
        return False
    
    def get_full_history(self) -> List[OHLCVData]:
        """Get complete history from buffer.
        
        Returns:
            List of all OHLCV data points in chronological order
        """
        with self.lock:
            return list(self.buffer)
    
    def get_recent_data(self, count: int) -> List[OHLCVData]:
        """Get recent data points from buffer.
        
        Args:
            count: Number of recent data points to return
            
        Returns:
            List of recent OHLCV data points
        """
        with self.lock:
            if count >= len(self.buffer):
                return list(self.buffer)
            
            return list(self.buffer)[-count:]
    
    def get_data_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> List[OHLCVData]:
        """Get data within a specific time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of OHLCV data points within the time range
        """
        with self.lock:
            result = []
            for candle in self.buffer:
                if start_time <= candle.timestamp <= end_time:
                    result.append(candle)
            return result
    
    def get_latest_candle(self) -> Optional[OHLCVData]:
        """Get the most recent candle.
        
        Returns:
            Latest OHLCV data point or None if buffer is empty
        """
        with self.lock:
            return self.buffer[-1] if self.buffer else None
    
    def get_buffer_info(self) -> Dict[str, Any]:
        """Get buffer information and statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        with self.lock:
            return {
                "current_size": len(self.buffer),
                "max_size": self.max_size,
                "total_received": self.total_received,
                "total_dropped": self.total_dropped,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "start_time": self.buffer[0].timestamp.isoformat() if self.buffer else None,
                "end_time": self.buffer[-1].timestamp.isoformat() if self.buffer else None,
                "is_full": len(self.buffer) == self.max_size,
                "utilization": len(self.buffer) / self.max_size,
            }
    
    def clear(self) -> None:
        """Clear all data from buffer."""
        with self.lock:
            self.buffer.clear()
            self.total_received = 0
            self.total_dropped = 0
            self.last_update = None
            logger.info("Cleared data buffer")
    
    def resize(self, new_size: int) -> None:
        """Resize the buffer.
        
        Args:
            new_size: New maximum size for the buffer
        """
        if new_size <= 0:
            raise DataBufferError("Buffer size must be positive")
        
        with self.lock:
            old_size = self.max_size
            self.max_size = new_size
            
            # Create new deque with new size
            new_buffer = deque(self.buffer, maxlen=new_size)
            self.buffer = new_buffer
            
            logger.info(
                "Resized data buffer",
                old_size=old_size,
                new_size=new_size,
                current_count=len(self.buffer),
            )


class MultiSymbolDataBuffer:
    """Data buffer manager for multiple trading symbols."""
    
    def __init__(self, max_size: int = 480):
        """Initialize multi-symbol data buffer.
        
        Args:
            max_size: Maximum number of data points per symbol
        """
        self.max_size = max_size
        self.buffers: Dict[str, DataBuffer] = {}
        self.lock = threading.RLock()
    
    def add_symbol(
        self,
        symbol: str,
        initial_data: Optional[List[OHLCVData]] = None,
        on_buffer_updated: Optional[Callable[[str, List[OHLCVData]], None]] = None,
    ) -> DataBuffer:
        """Add a new symbol to the buffer manager.
        
        Args:
            symbol: Trading symbol
            initial_data: Initial historical data
            on_buffer_updated: Callback for buffer updates
            
        Returns:
            DataBuffer instance for the symbol
        """
        with self.lock:
            if symbol in self.buffers:
                logger.warning("Symbol already exists in buffer manager", symbol=symbol)
                return self.buffers[symbol]
            
            # Create callback wrapper
            def wrapped_callback(data):
                if on_buffer_updated:
                    on_buffer_updated(symbol, data)
            
            buffer = DataBuffer(
                initial_data=initial_data,
                max_size=self.max_size,
                on_buffer_updated=wrapped_callback,
            )
            
            self.buffers[symbol] = buffer
            logger.info("Added symbol to buffer manager", symbol=symbol)
            
            return buffer
    
    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from the buffer manager.
        
        Args:
            symbol: Trading symbol to remove
        """
        with self.lock:
            if symbol in self.buffers:
                del self.buffers[symbol]
                logger.info("Removed symbol from buffer manager", symbol=symbol)
    
    def add_candle(self, symbol: str, candle: OHLCVData) -> None:
        """Add a candle for a specific symbol.
        
        Args:
            symbol: Trading symbol
            candle: OHLCV data point
        """
        with self.lock:
            if symbol not in self.buffers:
                raise DataBufferError(f"Symbol {symbol} not found in buffer manager")
            
            self.buffers[symbol].add_new_candle(candle)
    
    def get_symbol_data(self, symbol: str) -> Optional[List[OHLCVData]]:
        """Get data for a specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of OHLCV data points or None if symbol not found
        """
        with self.lock:
            if symbol not in self.buffers:
                return None
            
            return self.buffers[symbol].get_full_history()
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols in the buffer manager.
        
        Returns:
            List of trading symbols
        """
        with self.lock:
            return list(self.buffers.keys())
    
    def get_manager_info(self) -> Dict[str, Any]:
        """Get information about all buffers.
        
        Returns:
            Dictionary with information about all symbol buffers
        """
        with self.lock:
            return {
                symbol: buffer.get_buffer_info()
                for symbol, buffer in self.buffers.items()
            }
