"""Binance WebSocket client for real-time data streaming."""

import asyncio
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Dict, Optional, Any
import structlog
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..core.types import OHLCVData
from ..core.settings import get_settings

logger = structlog.get_logger(__name__)


class BinanceWebSocketError(Exception):
    """Exception raised during WebSocket operations."""
    pass


class BinanceWebSocket:
    """Binance WebSocket client for streaming real-time market data."""
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1m",
        on_new_candle: Optional[Callable[[OHLCVData], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Initialize the Binance WebSocket client.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for kline data (e.g., '1m', '5m', '1h')
            on_new_candle: Callback function for new candle data
            on_error: Callback function for error handling
        """
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        self.on_new_candle = on_new_candle
        self.on_error = on_error
        
        self.settings = get_settings()
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.running = False
        self.retry_count = 0
        self.max_retries = self.settings.websocket_retry_attempts
        self.retry_delay = self.settings.websocket_retry_delay
        
        # WebSocket URL for Binance
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@kline_{self.timeframe}"
        
        # Connection state
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # seconds
        
        logger.info(
            "Initialized Binance WebSocket",
            symbol=self.symbol,
            timeframe=self.timeframe,
            ws_url=self.ws_url,
        )
    
    async def connect(self) -> None:
        """Connect to Binance WebSocket."""
        try:
            logger.info("Connecting to Binance WebSocket", url=self.ws_url)
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
            
            self.running = True
            self.retry_count = 0
            self.last_heartbeat = time.time()
            
            logger.info("Successfully connected to Binance WebSocket")
            
        except Exception as e:
            logger.error("Failed to connect to Binance WebSocket", error=str(e))
            raise BinanceWebSocketError(f"Connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Binance WebSocket."""
        self.running = False
        
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Disconnected from Binance WebSocket")
            except Exception as e:
                logger.warning("Error during WebSocket disconnect", error=str(e))
            finally:
                self.websocket = None
    
    async def start_streaming(self) -> None:
        """Start streaming data from Binance WebSocket."""
        while self.running:
            try:
                if not self.websocket or self.websocket.closed:
                    await self.connect()
                
                # Listen for messages
                async for message in self.websocket:
                    if not self.running:
                        break
                    
                    try:
                        await self._handle_message(message)
                        self.last_heartbeat = time.time()
                    except Exception as e:
                        logger.error("Error handling WebSocket message", error=str(e))
                        if self.on_error:
                            self.on_error(e)
                
            except (ConnectionClosed, WebSocketException) as e:
                logger.warning("WebSocket connection lost", error=str(e))
                await self._handle_connection_error(e)
            
            except Exception as e:
                logger.error("Unexpected WebSocket error", error=str(e))
                await self._handle_connection_error(e)
    
    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message.
        
        Args:
            message: Raw WebSocket message
        """
        try:
            data = json.loads(message)
            
            # Check if it's kline data
            if "k" in data:
                kline_data = data["k"]
                
                # Only process closed candles
                if kline_data["x"]:  # x indicates if kline is closed
                    ohlcv = self._parse_kline_data(kline_data)
                    
                    if self.on_new_candle:
                        self.on_new_candle(ohlcv)
                    
                    logger.debug(
                        "Received new candle",
                        symbol=ohlcv.symbol,
                        timestamp=ohlcv.timestamp,
                        close=ohlcv.close,
                    )
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse WebSocket message", error=str(e))
        except Exception as e:
            logger.error("Error processing WebSocket message", error=str(e))
    
    def _parse_kline_data(self, kline_data: Dict[str, Any]) -> OHLCVData:
        """Parse Binance kline data to OHLCVData.
        
        Args:
            kline_data: Raw kline data from Binance
            
        Returns:
            Parsed OHLCV data
        """
        return OHLCVData(
            timestamp=datetime.fromtimestamp(
                kline_data["t"] / 1000, tz=timezone.utc
            ),
            open=Decimal(str(kline_data["o"])),
            high=Decimal(str(kline_data["h"])),
            low=Decimal(str(kline_data["l"])),
            close=Decimal(str(kline_data["c"])),
            volume=Decimal(str(kline_data["v"])),
            symbol=self.symbol,
        )
    
    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle WebSocket connection errors with retry logic.
        
        Args:
            error: Connection error
        """
        if self.retry_count >= self.max_retries:
            logger.error(
                "Max retry attempts reached, stopping WebSocket",
                retry_count=self.retry_count,
                max_retries=self.max_retries,
            )
            self.running = False
            
            if self.on_error:
                self.on_error(
                    BinanceWebSocketError(
                        f"Max retry attempts reached: {self.max_retries}"
                    )
                )
            return
        
        self.retry_count += 1
        retry_delay = self.retry_delay * (2 ** (self.retry_count - 1))  # Exponential backoff
        
        logger.warning(
            "WebSocket connection error, retrying",
            error=str(error),
            retry_count=self.retry_count,
            retry_delay=retry_delay,
        )
        
        # Notify error callback
        if self.on_error:
            self.on_error(error)
        
        # Wait before retry
        await asyncio.sleep(retry_delay)
    
    async def send_ping(self) -> None:
        """Send ping to keep connection alive."""
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.ping()
                self.last_heartbeat = time.time()
            except Exception as e:
                logger.warning("Failed to send ping", error=str(e))
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected.
        
        Returns:
            True if connected and running
        """
        return (
            self.running and
            self.websocket is not None and
            not self.websocket.closed
        )
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information.
        
        Returns:
            Dictionary with connection status and metrics
        """
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "connected": self.is_connected(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_heartbeat": self.last_heartbeat,
            "ws_url": self.ws_url,
        }


class WebSocketManager:
    """Manager for multiple WebSocket connections."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.connections: Dict[str, BinanceWebSocket] = {}
        self.running = False
    
    async def add_connection(
        self,
        symbol: str,
        timeframe: str = "1m",
        on_new_candle: Optional[Callable[[OHLCVData], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> BinanceWebSocket:
        """Add a new WebSocket connection.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for data
            on_new_candle: Callback for new candle data
            on_error: Callback for error handling
            
        Returns:
            WebSocket connection instance
        """
        connection_id = f"{symbol}_{timeframe}"
        
        if connection_id in self.connections:
            logger.warning("Connection already exists", connection_id=connection_id)
            return self.connections[connection_id]
        
        ws = BinanceWebSocket(
            symbol=symbol,
            timeframe=timeframe,
            on_new_candle=on_new_candle,
            on_error=on_error,
        )
        
        self.connections[connection_id] = ws
        
        if self.running:
            await ws.connect()
            asyncio.create_task(ws.start_streaming())
        
        logger.info("Added WebSocket connection", connection_id=connection_id)
        return ws
    
    async def remove_connection(self, symbol: str, timeframe: str = "1m") -> None:
        """Remove a WebSocket connection.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for data
        """
        connection_id = f"{symbol}_{timeframe}"
        
        if connection_id in self.connections:
            ws = self.connections[connection_id]
            await ws.disconnect()
            del self.connections[connection_id]
            logger.info("Removed WebSocket connection", connection_id=connection_id)
    
    async def start_all(self) -> None:
        """Start all WebSocket connections."""
        self.running = True
        
        for ws in self.connections.values():
            await ws.connect()
            asyncio.create_task(ws.start_streaming())
        
        logger.info("Started all WebSocket connections", count=len(self.connections))
    
    async def stop_all(self) -> None:
        """Stop all WebSocket connections."""
        self.running = False
        
        for ws in self.connections.values():
            await ws.disconnect()
        
        logger.info("Stopped all WebSocket connections")
    
    def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connections.
        
        Returns:
            Dictionary with connection status information
        """
        return {
            connection_id: ws.get_connection_info()
            for connection_id, ws in self.connections.items()
        }
