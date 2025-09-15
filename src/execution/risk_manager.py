"""Risk management module for trade execution."""

from decimal import Decimal
from typing import Dict, List, Optional

import structlog

from ..core.settings import get_settings
from ..core.types import OrderRequest, TradingDecision, TradingMode
from ..core.utils import calculate_risk_amount, clamp

logger = structlog.get_logger(__name__)


class RiskManagementError(Exception):
    """Exception raised during risk management operations."""
    pass


class RiskManager:
    """Risk management system for trade execution."""
    
    def __init__(self, mode: TradingMode = TradingMode.PAPER):
        """Initialize the risk manager.
        
        Args:
            mode: Trading mode
        """
        self.settings = get_settings()
        self.mode = mode
        self.daily_trades = 0
        self.daily_pnl = Decimal("0")
        self.max_daily_loss = Decimal(str(self.settings.binance.max_daily_loss))
        self.max_daily_trades = self.settings.binance.max_daily_trades
    
    def validate_order(self, order_request: OrderRequest, account_balance: Decimal) -> bool:
        """Validate an order against risk management rules.
        
        Args:
            order_request: Order request to validate
            account_balance: Current account balance
            
        Returns:
            True if order passes risk validation
        """
        try:
            # Check daily trade limit
            if not self._check_daily_trade_limit():
                logger.warning("Daily trade limit exceeded", daily_trades=self.daily_trades, limit=self.max_daily_trades)
                return False
            
            # Check daily loss limit
            if not self._check_daily_loss_limit():
                logger.warning("Daily loss limit exceeded", daily_pnl=self.daily_pnl, limit=self.max_daily_loss)
                return False
            
            # Check order size limits
            if not self._check_order_size_limits(order_request, account_balance):
                return False
            
            # Check position size limits
            if not self._check_position_size_limits(order_request, account_balance):
                return False
            
            # Check risk per trade
            if not self._check_risk_per_trade(order_request, account_balance):
                return False
            
            logger.info("Order passed risk validation", symbol=order_request.symbol, side=order_request.side.value)
            return True
        
        except Exception as e:
            logger.error("Risk validation failed", error=str(e))
            return False
    
    def validate_trading_decision(self, decision: TradingDecision, account_balance: Decimal) -> bool:
        """Validate a trading decision against risk management rules.
        
        Args:
            decision: Trading decision to validate
            account_balance: Current account balance
            
        Returns:
            True if decision passes risk validation
        """
        try:
            # Check if decision is a no-action decision
            if decision.quantity == 0:
                return True
            
            # Check confidence threshold
            if decision.confidence < 0.5:  # Minimum confidence threshold
                logger.warning("Decision confidence too low", confidence=decision.confidence)
                return False
            
            # Check risk score
            if decision.risk_score > 0.8:  # High risk threshold
                logger.warning("Decision risk score too high", risk_score=decision.risk_score)
                return False
            
            # Create order request for validation
            order_request = OrderRequest(
                symbol=decision.symbol,
                side=decision.action,
                order_type="MARKET",  # Default to market order
                quantity=decision.quantity,
                price=decision.price,
            )
            
            return self.validate_order(order_request, account_balance)
        
        except Exception as e:
            logger.error("Decision validation failed", error=str(e))
            return False
    
    def adjust_order_size(self, order_request: OrderRequest, account_balance: Decimal) -> OrderRequest:
        """Adjust order size to comply with risk management rules.
        
        Args:
            order_request: Original order request
            account_balance: Current account balance
            
        Returns:
            Adjusted order request
        """
        try:
            adjusted_request = order_request.model_copy()
            
            # Calculate maximum allowed quantity based on risk limits
            max_risk_amount = calculate_risk_amount(account_balance, self.settings.binance.max_risk_per_trade)
            
            # Estimate position value
            if order_request.price:
                position_value = order_request.quantity * order_request.price
            else:
                # For market orders, estimate using current price (would need market data in real implementation)
                position_value = order_request.quantity * Decimal("50000")  # Placeholder BTC price
            
            # Adjust quantity if position value exceeds risk limits
            if position_value > max_risk_amount:
                max_quantity = max_risk_amount / (order_request.price or Decimal("50000"))
                adjusted_request.quantity = max_quantity
                logger.info(
                    "Adjusted order quantity for risk management",
                    original_quantity=str(order_request.quantity),
                    adjusted_quantity=str(adjusted_request.quantity),
                    max_risk_amount=str(max_risk_amount),
                )
            
            # Apply minimum and maximum order size limits
            min_order_size = Decimal(str(self.settings.binance.min_order_size))
            max_order_size = Decimal(str(self.settings.binance.max_order_size))
            
            if order_request.price:
                order_value = adjusted_request.quantity * order_request.price
                if order_value < min_order_size:
                    adjusted_request.quantity = min_order_size / order_request.price
                elif order_value > max_order_size:
                    adjusted_request.quantity = max_order_size / order_request.price
            
            return adjusted_request
        
        except Exception as e:
            logger.error("Failed to adjust order size", error=str(e))
            return order_request
    
    def record_trade(self, order_value: Decimal, pnl: Decimal) -> None:
        """Record a completed trade for risk tracking.
        
        Args:
            order_value: Order value
            pnl: Profit and loss from the trade
        """
        self.daily_trades += 1
        self.daily_pnl += pnl
        
        logger.info(
            "Recorded trade",
            daily_trades=self.daily_trades,
            daily_pnl=str(self.daily_pnl),
            trade_pnl=str(pnl),
        )
    
    def reset_daily_counters(self) -> None:
        """Reset daily counters (typically called at start of new trading day)."""
        self.daily_trades = 0
        self.daily_pnl = Decimal("0")
        logger.info("Reset daily risk counters")
    
    def get_risk_status(self) -> Dict:
        """Get current risk management status.
        
        Returns:
            Dictionary with risk status information
        """
        return {
            "daily_trades": self.daily_trades,
            "max_daily_trades": self.max_daily_trades,
            "daily_pnl": str(self.daily_pnl),
            "max_daily_loss": str(self.max_daily_loss),
            "trades_remaining": max(0, self.max_daily_trades - self.daily_trades),
            "loss_buffer": str(self.max_daily_loss - self.daily_pnl),
            "risk_per_trade": self.settings.binance.max_risk_per_trade,
            "max_position_size": self.settings.binance.max_position_size,
        }
    
    def _check_daily_trade_limit(self) -> bool:
        """Check if daily trade limit is exceeded.
        
        Returns:
            True if within limits
        """
        return self.daily_trades < self.max_daily_trades
    
    def _check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit is exceeded.
        
        Returns:
            True if within limits
        """
        return self.daily_pnl > -self.max_daily_loss
    
    def _check_order_size_limits(self, order_request: OrderRequest, account_balance: Decimal) -> bool:
        """Check if order size is within limits.
        
        Args:
            order_request: Order request to check
            account_balance: Current account balance
            
        Returns:
            True if within limits
        """
        if not order_request.price:
            return True  # Market orders - can't check value without current price
        
        order_value = order_request.quantity * order_request.price
        min_order_size = Decimal(str(self.settings.binance.min_order_size))
        max_order_size = Decimal(str(self.settings.binance.max_order_size))
        
        if order_value < min_order_size:
            logger.warning("Order value below minimum", order_value=str(order_value), min_size=str(min_order_size))
            return False
        
        if order_value > max_order_size:
            logger.warning("Order value above maximum", order_value=str(order_value), max_size=str(max_order_size))
            return False
        
        return True
    
    def _check_position_size_limits(self, order_request: OrderRequest, account_balance: Decimal) -> bool:
        """Check if position size is within limits.
        
        Args:
            order_request: Order request to check
            account_balance: Current account balance
            
        Returns:
            True if within limits
        """
        if not order_request.price:
            return True  # Market orders - can't check value without current price
        
        position_value = order_request.quantity * order_request.price
        max_position_value = account_balance * Decimal(str(self.settings.binance.max_position_size))
        
        if position_value > max_position_value:
            logger.warning(
                "Position size exceeds limit",
                position_value=str(position_value),
                max_position_value=str(max_position_value),
                max_position_pct=self.settings.binance.max_position_size,
            )
            return False
        
        return True
    
    def _check_risk_per_trade(self, order_request: OrderRequest, account_balance: Decimal) -> bool:
        """Check if trade risk is within limits.
        
        Args:
            order_request: Order request to check
            account_balance: Current account balance
            
        Returns:
            True if within limits
        """
        # This is a simplified check - in reality, you'd need to calculate
        # the actual risk based on stop loss and position size
        max_risk_amount = calculate_risk_amount(account_balance, self.settings.binance.max_risk_per_trade)
        
        if not order_request.price:
            return True  # Market orders - can't check risk without current price
        
        # Estimate risk as a percentage of position value
        estimated_risk = order_request.quantity * order_request.price * Decimal("0.02")  # 2% risk estimate
        
        if estimated_risk > max_risk_amount:
            logger.warning(
                "Trade risk exceeds limit",
                estimated_risk=str(estimated_risk),
                max_risk_amount=str(max_risk_amount),
            )
            return False
        
        return True
