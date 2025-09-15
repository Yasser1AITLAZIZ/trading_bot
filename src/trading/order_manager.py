"""Order manager for handling multiple concurrent orders."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Callable
import structlog

from ..core.settings import get_settings
from ..core.types import TradingDecision, OrderRequest, OrderResponse, TradingMode
from ..execution.binance_client import BinanceClient
from ..execution.risk_manager import RiskManager

logger = structlog.get_logger(__name__)


class OrderManagerError(Exception):
    """Exception raised during order management operations."""
    pass


class OrderManager:
    """Manager for handling multiple concurrent orders."""
    
    def __init__(
        self,
        max_orders: int = 2,
        symbol: str = "BTCUSDT",
        mode: TradingMode = TradingMode.PAPER,
        on_order_update: Optional[Callable[[OrderResponse], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Initialize the order manager.
        
        Args:
            max_orders: Maximum number of concurrent orders
            symbol: Trading symbol
            mode: Trading mode (paper/testnet/live)
            on_order_update: Callback for order updates
            on_error: Callback for error handling
        """
        self.max_orders = max_orders
        self.symbol = symbol
        self.mode = mode
        self.on_order_update = on_order_update
        self.on_error = on_error
        
        self.settings = get_settings()
        self.running = False
        
        # Initialize components
        self.binance_client = BinanceClient(mode)
        self.risk_manager = RiskManager(mode)
        
        # Order tracking
        self.open_orders: Dict[str, OrderResponse] = {}
        self.order_history: List[OrderResponse] = []
        self.pending_orders: Dict[str, OrderRequest] = {}
        
        # Statistics
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.start_time = None
        
        # Task management
        self.order_check_task: Optional[asyncio.Task] = None
        
        logger.info(
            "Initialized order manager",
            max_orders=max_orders,
            symbol=symbol,
            mode=mode.value,
        )
    
    async def start(self) -> None:
        """Start the order manager."""
        if self.running:
            logger.warning("Order manager is already running")
            return
        
        self.running = True
        self.start_time = datetime.now(timezone.utc)
        
        # Start order checking task
        self.order_check_task = asyncio.create_task(self._order_check_loop())
        
        logger.info("Started order manager")
    
    async def stop(self) -> None:
        """Stop the order manager."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel order checking task
        if self.order_check_task:
            self.order_check_task.cancel()
            try:
                await self.order_check_task
            except asyncio.CancelledError:
                pass
            self.order_check_task = None
        
        logger.info("Stopped order manager")
    
    async def _order_check_loop(self) -> None:
        """Main loop for checking order status."""
        try:
            while self.running:
                await self.check_open_orders()
                await asyncio.sleep(10)  # Check every 10 seconds
        
        except asyncio.CancelledError:
            logger.info("Order check loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in order check loop", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def execute_decision(self, decision: TradingDecision) -> bool:
        """Execute a trading decision.
        
        Args:
            decision: Trading decision to execute
            
        Returns:
            True if order was executed successfully
        """
        try:
            # Check if we can open a new order
            if not self.can_open_new_order():
                logger.warning(
                    "Cannot open new order - limit reached",
                    current_orders=len(self.open_orders),
                    max_orders=self.max_orders,
                )
                return False
            
            # Check if decision is valid
            if decision.quantity <= 0:
                logger.warning("Invalid decision - zero quantity", decision=decision)
                return False
            
            # Get current account balance (simplified)
            account_balance = Decimal("10000")  # Placeholder
            
            # Validate decision against risk management
            if not self.risk_manager.validate_trading_decision(decision, account_balance):
                logger.warning("Decision failed risk validation", decision=decision)
                return False
            
            # Create order request
            order_request = OrderRequest(
                symbol=decision.symbol,
                side=decision.action,
                order_type="MARKET",  # Default to market order
                quantity=decision.quantity,
                price=decision.price,
            )
            
            # Adjust order size for risk management
            order_request = self.risk_manager.adjust_order_size(order_request, account_balance)
            
            # Execute order
            order_response = await self._execute_order(order_request)
            
            if order_response:
                # Track the order
                self.open_orders[order_response.order_id] = order_response
                self.order_history.append(order_response)
                self.total_orders += 1
                
                logger.info(
                    "Order executed successfully",
                    order_id=order_response.order_id,
                    symbol=order_response.symbol,
                    side=order_response.side.value,
                    quantity=order_response.quantity,
                )
                
                return True
            else:
                self.failed_orders += 1
                logger.error("Failed to execute order", decision=decision)
                return False
        
        except Exception as e:
            self.failed_orders += 1
            logger.error("Error executing decision", error=str(e), decision=decision)
            if self.on_error:
                self.on_error(e)
            return False
    
    async def _execute_order(self, order_request: OrderRequest) -> Optional[OrderResponse]:
        """Execute an order via Binance client.
        
        Args:
            order_request: Order request to execute
            
        Returns:
            Order response or None if failed
        """
        try:
            # Place order
            order_response = self.binance_client.place_order(order_request)
            
            # Notify callback
            if self.on_order_update:
                self.on_order_update(order_response)
            
            return order_response
        
        except Exception as e:
            logger.error("Error executing order", error=str(e), order_request=order_request)
            return None
    
    async def check_open_orders(self) -> None:
        """Check status of all open orders."""
        try:
            if not self.open_orders:
                return
            
            orders_to_remove = []
            
            for order_id, order in self.open_orders.items():
                try:
                    # Get updated order status
                    updated_order = self.binance_client.get_order_status(self.symbol, order_id)
                    
                    # Check if order status changed
                    if updated_order.status != order.status:
                        logger.info(
                            "Order status changed",
                            order_id=order_id,
                            old_status=order.status.value,
                            new_status=updated_order.status.value,
                        )
                        
                        # Update order
                        self.open_orders[order_id] = updated_order
                        
                        # Notify callback
                        if self.on_order_update:
                            self.on_order_update(updated_order)
                        
                        # Remove if order is completed
                        if updated_order.status.value in ["FILLED", "CANCELED", "REJECTED", "EXPIRED"]:
                            orders_to_remove.append(order_id)
                            
                            if updated_order.status.value == "FILLED":
                                self.successful_orders += 1
                            else:
                                self.failed_orders += 1
                
                except Exception as e:
                    logger.error("Error checking order status", order_id=order_id, error=str(e))
            
            # Remove completed orders
            for order_id in orders_to_remove:
                del self.open_orders[order_id]
        
        except Exception as e:
            logger.error("Error checking open orders", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if order was cancelled successfully
        """
        try:
            if order_id not in self.open_orders:
                logger.warning("Order not found", order_id=order_id)
                return False
            
            # Cancel order via Binance
            success = self.binance_client.cancel_order(self.symbol, order_id)
            
            if success:
                # Remove from open orders
                del self.open_orders[order_id]
                logger.info("Order cancelled successfully", order_id=order_id)
            
            return success
        
        except Exception as e:
            logger.error("Error cancelling order", order_id=order_id, error=str(e))
            if self.on_error:
                self.on_error(e)
            return False
    
    async def cancel_all_orders(self) -> int:
        """Cancel all open orders.
        
        Returns:
            Number of orders cancelled
        """
        try:
            cancelled_count = 0
            
            for order_id in list(self.open_orders.keys()):
                if await self.cancel_order(order_id):
                    cancelled_count += 1
            
            logger.info("Cancelled all orders", count=cancelled_count)
            return cancelled_count
        
        except Exception as e:
            logger.error("Error cancelling all orders", error=str(e))
            if self.on_error:
                self.on_error(e)
            return 0
    
    def can_open_new_order(self) -> bool:
        """Check if a new order can be opened.
        
        Returns:
            True if new order can be opened
        """
        return len(self.open_orders) < self.max_orders
    
    def get_open_orders(self) -> Dict[str, OrderResponse]:
        """Get all open orders.
        
        Returns:
            Dictionary of open orders
        """
        return self.open_orders.copy()
    
    def get_order_history(self, limit: int = 100) -> List[OrderResponse]:
        """Get order history.
        
        Args:
            limit: Maximum number of orders to return
            
        Returns:
            List of recent orders
        """
        return self.order_history[-limit:] if self.order_history else []
    
    def set_max_orders(self, max_orders: int) -> None:
        """Update maximum number of concurrent orders.
        
        Args:
            max_orders: New maximum number of orders
        """
        if max_orders <= 0:
            raise OrderManagerError("Max orders must be positive")
        
        old_max = self.max_orders
        self.max_orders = max_orders
        
        logger.info(
            "Updated max orders",
            old_max=old_max,
            new_max=max_orders,
            current_orders=len(self.open_orders),
        )
    
    def get_status(self) -> Dict[str, any]:
        """Get order manager status.
        
        Returns:
            Dictionary with order manager status
        """
        return {
            "symbol": self.symbol,
            "mode": self.mode.value,
            "running": self.running,
            "max_orders": self.max_orders,
            "open_orders": len(self.open_orders),
            "total_orders": self.total_orders,
            "successful_orders": self.successful_orders,
            "failed_orders": self.failed_orders,
            "success_rate": (
                self.successful_orders / self.total_orders
                if self.total_orders > 0 else 0
            ),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "can_open_new": self.can_open_new_order(),
            "open_order_ids": list(self.open_orders.keys()),
        }
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.order_history:
            return {
                "total_orders": 0,
                "success_rate": 0,
                "average_execution_time": 0,
                "total_volume": 0,
            }
        
        # Calculate metrics
        successful_orders = [o for o in self.order_history if o.status.value == "FILLED"]
        total_volume = sum(float(o.quantity) for o in successful_orders)
        
        return {
            "total_orders": len(self.order_history),
            "successful_orders": len(successful_orders),
            "success_rate": len(successful_orders) / len(self.order_history),
            "total_volume": total_volume,
            "average_volume": total_volume / len(successful_orders) if successful_orders else 0,
        }
