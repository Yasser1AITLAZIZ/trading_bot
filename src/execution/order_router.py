"""Order router for managing trade execution with different modes."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import structlog

from ..core.settings import get_settings
from ..core.types import OrderRequest, OrderResponse, TradingDecision, TradingMode, TradingSession
from ..core.utils import generate_correlation_id, generate_client_order_id
from .binance_client import BinanceClient
from .risk_manager import RiskManager

logger = structlog.get_logger(__name__)


class OrderRouterError(Exception):
    """Exception raised during order routing operations."""
    pass


class OrderRouter:
    """Order router for managing trade execution with risk management."""
    
    def __init__(self, mode: TradingMode = TradingMode.PAPER):
        """Initialize the order router.
        
        Args:
            mode: Trading mode
        """
        self.settings = get_settings()
        self.mode = mode
        self.binance_client = BinanceClient(mode)
        self.risk_manager = RiskManager(mode)
        self.session: Optional[TradingSession] = None
        self.active_orders: Dict[str, OrderResponse] = {}
    
    def start_session(self, strategy_name: str, initial_balance: Decimal) -> str:
        """Start a new trading session.
        
        Args:
            strategy_name: Name of the active strategy
            initial_balance: Initial account balance
            
        Returns:
            Session ID
        """
        session_id = generate_correlation_id()
        
        self.session = TradingSession(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            mode=self.mode,
            strategy=strategy_name,
            initial_balance=initial_balance,
            current_balance=initial_balance,
        )
        
        logger.info(
            "Started trading session",
            session_id=session_id,
            mode=self.mode.value,
            strategy=strategy_name,
            initial_balance=str(initial_balance),
        )
        
        return session_id
    
    def end_session(self) -> Optional[TradingSession]:
        """End the current trading session.
        
        Returns:
            Completed trading session or None if no active session
        """
        if not self.session:
            return None
        
        self.session.end_time = datetime.now(timezone.utc)
        
        logger.info(
            "Ended trading session",
            session_id=self.session.session_id,
            total_trades=self.session.total_trades,
            successful_trades=self.session.successful_trades,
            pnl=str(self.session.pnl),
        )
        
        completed_session = self.session
        self.session = None
        return completed_session
    
    def execute_decision(self, decision: TradingDecision) -> Optional[OrderResponse]:
        """Execute a trading decision.
        
        Args:
            decision: Trading decision to execute
            
        Returns:
            Order response or None if execution failed
        """
        if not self.session:
            raise OrderRouterError("No active trading session")
        
        # Check if decision is a no-action decision
        if decision.quantity == 0:
            logger.info("No action decision", reasoning=decision.reasoning)
            return None
        
        try:
            # Get current account balance
            account_balance = self._get_account_balance()
            
            # Validate decision against risk management
            if not self.risk_manager.validate_trading_decision(decision, account_balance):
                logger.warning("Trading decision failed risk validation", symbol=decision.symbol)
                return None
            
            # Create order request
            order_request = OrderRequest(
                symbol=decision.symbol,
                side=decision.action,
                order_type="MARKET",  # Default to market order
                quantity=decision.quantity,
                price=decision.price,
                client_order_id=generate_client_order_id(decision.symbol, decision.action.value),
            )
            
            # Adjust order size for risk management
            order_request = self.risk_manager.adjust_order_size(order_request, account_balance)
            
            # Execute order
            order_response = self._execute_order(order_request)
            
            if order_response:
                # Update session statistics
                self._update_session_stats(order_response)
                
                # Record trade for risk management
                order_value = order_response.quantity * (order_response.executed_price or order_response.price or Decimal("0"))
                self.risk_manager.record_trade(order_value, Decimal("0"))  # PnL calculated separately
            
            return order_response
        
        except Exception as e:
            logger.error("Failed to execute trading decision", error=str(e))
            raise OrderRouterError(f"Failed to execute trading decision: {e}")
    
    def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get status of an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order response or None if not found
        """
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        
        try:
            # Query from exchange
            order_response = self.binance_client.get_order_status("", order_id)  # Symbol not needed for order ID lookup
            return order_response
        except Exception as e:
            logger.error("Failed to get order status", order_id=order_id, error=str(e))
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            True if order was cancelled successfully
        """
        try:
            success = self.binance_client.cancel_order("", order_id)  # Symbol not needed for order ID lookup
            if success and order_id in self.active_orders:
                del self.active_orders[order_id]
            return success
        except Exception as e:
            logger.error("Failed to cancel order", order_id=order_id, error=str(e))
            return False
    
    def get_session_status(self) -> Optional[Dict]:
        """Get current session status.
        
        Returns:
            Session status dictionary or None if no active session
        """
        if not self.session:
            return None
        
        return {
            "session_id": self.session.session_id,
            "strategy": self.session.strategy,
            "mode": self.session.mode.value,
            "start_time": self.session.start_time.isoformat(),
            "total_trades": self.session.total_trades,
            "successful_trades": self.session.successful_trades,
            "current_balance": str(self.session.current_balance),
            "pnl": str(self.session.pnl),
            "active_orders": len(self.active_orders),
            "risk_status": self.risk_manager.get_risk_status(),
        }
    
    def _execute_order(self, order_request: OrderRequest) -> Optional[OrderResponse]:
        """Execute an order through the Binance client.
        
        Args:
            order_request: Order request to execute
            
        Returns:
            Order response or None if execution failed
        """
        try:
            # Place order
            order_response = self.binance_client.place_order(order_request)
            
            # Store in active orders
            self.active_orders[order_response.order_id] = order_response
            
            logger.info(
                "Order executed successfully",
                order_id=order_response.order_id,
                symbol=order_response.symbol,
                side=order_response.side.value,
                quantity=str(order_response.quantity),
                status=order_response.status.value,
            )
            
            return order_response
        
        except Exception as e:
            logger.error("Order execution failed", error=str(e))
            return None
    
    def _get_account_balance(self) -> Decimal:
        """Get current account balance.
        
        Returns:
            Current account balance
        """
        if not self.session:
            return Decimal("0")
        
        # In a real implementation, this would query the exchange
        # For now, return the session's current balance
        return self.session.current_balance
    
    def _update_session_stats(self, order_response: OrderResponse) -> None:
        """Update session statistics after order execution.
        
        Args:
            order_response: Executed order response
        """
        if not self.session:
            return
        
        self.session.total_trades += 1
        
        # Consider order successful if it's filled
        if order_response.status.value in ["FILLED", "PARTIALLY_FILLED"]:
            self.session.successful_trades += 1
        
        # Update balance (simplified - would need proper PnL calculation)
        if order_response.executed_quantity > 0:
            order_value = order_response.executed_quantity * (order_response.executed_price or Decimal("0"))
            if order_response.side.value == "BUY":
                self.session.current_balance -= order_value
            else:  # SELL
                self.session.current_balance += order_value
        
        # Calculate PnL (simplified)
        self.session.pnl = self.session.current_balance - self.session.initial_balance
