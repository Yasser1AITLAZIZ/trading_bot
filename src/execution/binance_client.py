"""Binance API client for trade execution."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import structlog
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

from ..core.settings import get_settings
from ..core.types import OrderRequest, OrderResponse, OrderStatus, OrderSide, OrderType, TradingMode
from ..core.utils import generate_client_order_id, mask_sensitive_data

logger = structlog.get_logger(__name__)


class BinanceClientError(Exception):
    """Exception raised during Binance operations."""
    pass


class BinanceClient:
    """Binance API client for trade execution."""
    
    def __init__(self, mode: TradingMode = TradingMode.PAPER):
        """Initialize the Binance client.
        
        Args:
            mode: Trading mode (paper/testnet/live)
        """
        self.settings = get_settings()
        self.mode = mode
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Binance client based on mode."""
        if self.mode == TradingMode.PAPER:
            # Paper trading - no real API calls
            logger.info("Initialized paper trading mode")
            return
        
        # Get API credentials
        api_key = self.settings.binance.api_key
        secret_key = self.settings.binance.secret_key
        
        if not api_key or not secret_key:
            raise BinanceClientError("Binance API credentials are required for non-paper trading")
        
        try:
            if self.mode == TradingMode.TESTNET:
                # Testnet mode
                self.client = Client(
                    api_key=api_key,
                    api_secret=secret_key,
                    testnet=True
                )
                logger.info("Initialized Binance testnet client")
            elif self.mode == TradingMode.LIVE:
                # Live trading mode
                self.client = Client(
                    api_key=api_key,
                    api_secret=secret_key
                )
                logger.info("Initialized Binance live client")
        except Exception as e:
            logger.error("Failed to initialize Binance client", error=str(e))
            raise BinanceClientError(f"Failed to initialize Binance client: {e}")
    
    def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order on Binance.
        
        Args:
            order_request: Order request details
            
        Returns:
            Order response from Binance
        """
        if self.mode == TradingMode.PAPER:
            return self._simulate_order(order_request)
        
        if not self.client:
            raise BinanceClientError("Binance client not initialized")
        
        try:
            # Generate client order ID if not provided
            if not order_request.client_order_id:
                order_request.client_order_id = generate_client_order_id(
                    order_request.symbol,
                    order_request.side.value
                )
            
            # Prepare order parameters
            order_params = {
                "symbol": order_request.symbol,
                "side": order_request.side.value,
                "type": order_request.order_type.value,
                "quantity": str(order_request.quantity),
                "timeInForce": order_request.time_in_force,
            }
            
            # Add price for limit orders
            if order_request.price:
                order_params["price"] = str(order_request.price)
            
            # Add stop price for stop orders
            if order_request.stop_price:
                order_params["stopPrice"] = str(order_request.stop_price)
            
            # Add client order ID
            order_params["newClientOrderId"] = order_request.client_order_id
            
            # Place order
            logger.info(
                "Placing order",
                symbol=order_request.symbol,
                side=order_request.side.value,
                type=order_request.order_type.value,
                quantity=str(order_request.quantity),
                client_order_id=order_request.client_order_id,
            )
            
            response = self.client.create_order(**order_params)
            
            # Convert response to our format
            return self._convert_order_response(response)
        
        except BinanceAPIException as e:
            logger.error("Binance API error", error=str(e), code=e.code)
            raise BinanceClientError(f"Binance API error: {e}")
        except BinanceOrderException as e:
            logger.error("Binance order error", error=str(e), code=e.code)
            raise BinanceClientError(f"Binance order error: {e}")
        except Exception as e:
            logger.error("Unexpected error placing order", error=str(e))
            raise BinanceClientError(f"Unexpected error: {e}")
    
    def get_order_status(self, symbol: str, order_id: str) -> OrderResponse:
        """Get order status from Binance.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            Order response with current status
        """
        if self.mode == TradingMode.PAPER:
            # For paper trading, return a mock response
            return OrderResponse(
                order_id=order_id,
                symbol=symbol,
                status=OrderStatus.FILLED,
                side=OrderSide.BUY,
                quantity=Decimal("0"),
                executed_quantity=Decimal("0"),
                timestamp=datetime.now(timezone.utc),
            )
        
        if not self.client:
            raise BinanceClientError("Binance client not initialized")
        
        try:
            response = self.client.get_order(symbol=symbol, orderId=order_id)
            return self._convert_order_response(response)
        except Exception as e:
            logger.error("Failed to get order status", error=str(e))
            raise BinanceClientError(f"Failed to get order status: {e}")
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order on Binance.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            True if order was cancelled successfully
        """
        if self.mode == TradingMode.PAPER:
            logger.info("Simulated order cancellation", symbol=symbol, order_id=order_id)
            return True
        
        if not self.client:
            raise BinanceClientError("Binance client not initialized")
        
        try:
            response = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info("Order cancelled", symbol=symbol, order_id=order_id)
            return True
        except Exception as e:
            logger.error("Failed to cancel order", error=str(e))
            raise BinanceClientError(f"Failed to cancel order: {e}")
    
    def get_account_info(self) -> Dict:
        """Get account information from Binance.
        
        Returns:
            Account information dictionary
        """
        if self.mode == TradingMode.PAPER:
            # Return mock account info for paper trading
            return {
                "accountType": "SPOT",
                "canTrade": True,
                "canWithdraw": False,
                "canDeposit": False,
                "balances": [
                    {"asset": "USDT", "free": "10000.00000000", "locked": "0.00000000"},
                    {"asset": "BTC", "free": "0.00000000", "locked": "0.00000000"},
                ],
            }
        
        if not self.client:
            raise BinanceClientError("Binance client not initialized")
        
        try:
            return self.client.get_account()
        except Exception as e:
            logger.error("Failed to get account info", error=str(e))
            raise BinanceClientError(f"Failed to get account info: {e}")
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol information from Binance.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Symbol information dictionary
        """
        if self.mode == TradingMode.PAPER:
            # Return mock symbol info for paper trading
            return {
                "symbol": symbol,
                "status": "TRADING",
                "baseAsset": "BTC",
                "baseAssetPrecision": 8,
                "quoteAsset": "USDT",
                "quotePrecision": 8,
                "filters": [
                    {"filterType": "LOT_SIZE", "minQty": "0.00001000", "maxQty": "9000.00000000", "stepSize": "0.00001000"},
                    {"filterType": "PRICE_FILTER", "minPrice": "0.01000000", "maxPrice": "1000000.00000000", "tickSize": "0.01000000"},
                ],
            }
        
        if not self.client:
            raise BinanceClientError("Binance client not initialized")
        
        try:
            exchange_info = self.client.get_exchange_info()
            for symbol_info in exchange_info["symbols"]:
                if symbol_info["symbol"] == symbol:
                    return symbol_info
            raise BinanceClientError(f"Symbol {symbol} not found")
        except Exception as e:
            logger.error("Failed to get symbol info", error=str(e))
            raise BinanceClientError(f"Failed to get symbol info: {e}")
    
    def _simulate_order(self, order_request: OrderRequest) -> OrderResponse:
        """Simulate order execution for paper trading.
        
        Args:
            order_request: Order request details
            
        Returns:
            Simulated order response
        """
        logger.info(
            "Simulating order",
            symbol=order_request.symbol,
            side=order_request.side.value,
            type=order_request.order_type.value,
            quantity=str(order_request.quantity),
        )
        
        # Simulate immediate fill for paper trading
        return OrderResponse(
            order_id=f"PAPER_{order_request.client_order_id}",
            client_order_id=order_request.client_order_id,
            symbol=order_request.symbol,
            status=OrderStatus.FILLED,
            side=order_request.side,
            quantity=order_request.quantity,
            price=order_request.price,
            executed_quantity=order_request.quantity,
            executed_price=order_request.price,
            timestamp=datetime.now(timezone.utc),
        )
    
    def _convert_order_response(self, response: Dict) -> OrderResponse:
        """Convert Binance order response to our format.
        
        Args:
            response: Raw Binance response
            
        Returns:
            Converted order response
        """
        return OrderResponse(
            order_id=str(response["orderId"]),
            client_order_id=response.get("clientOrderId"),
            symbol=response["symbol"],
            status=OrderStatus(response["status"]),
            side=OrderSide(response["side"]),
            quantity=Decimal(str(response["origQty"])),
            price=Decimal(str(response["price"])) if response["price"] != "0.00000000" else None,
            executed_quantity=Decimal(str(response["executedQty"])),
            executed_price=Decimal(str(response["cummulativeQuoteQty"])) / Decimal(str(response["executedQty"])) if response["executedQty"] != "0" else None,
            timestamp=datetime.fromtimestamp(response["time"] / 1000, tz=timezone.utc),
        )
