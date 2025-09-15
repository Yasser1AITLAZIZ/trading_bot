"""Dashboard manager for aggregating and displaying trading metrics."""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import structlog

from ..core.settings import get_settings
from ..core.types import TradingDecision, OHLCVData

logger = structlog.get_logger(__name__)


class DashboardMetrics:
    """Container for dashboard metrics."""
    
    def __init__(self):
        """Initialize dashboard metrics."""
        self.timestamp = datetime.now(timezone.utc)
        self.bot_status = {}
        self.performance_metrics = {}
        self.order_metrics = {}
        self.buffer_metrics = {}
        self.risk_metrics = {}
        self.llm_metrics = {}


class DashboardManager:
    """Manager for dashboard metrics and real-time updates."""
    
    def __init__(self, trading_loop=None):
        """Initialize the dashboard manager.
        
        Args:
            trading_loop: Reference to the trading loop
        """
        self.trading_loop = trading_loop
        self.settings = get_settings()
        
        # Metrics history
        self.metrics_history: List[DashboardMetrics] = []
        self.max_history_size = 1000  # Keep last 1000 metrics
        
        # Real-time metrics
        self.current_metrics = DashboardMetrics()
        
        # Update interval
        self.update_interval = 5  # seconds
        self.update_task: Optional[asyncio.Task] = None
        self.running = False
        
        logger.info("Initialized dashboard manager")
    
    async def start(self) -> None:
        """Start the dashboard manager."""
        if self.running:
            return
        
        self.running = True
        self.update_task = asyncio.create_task(self._update_loop())
        
        logger.info("Started dashboard manager")
    
    async def stop(self) -> None:
        """Stop the dashboard manager."""
        if not self.running:
            return
        
        self.running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
        
        logger.info("Stopped dashboard manager")
    
    async def _update_loop(self) -> None:
        """Main update loop for dashboard metrics."""
        try:
            while self.running:
                await self._update_metrics()
                await asyncio.sleep(self.update_interval)
        
        except asyncio.CancelledError:
            logger.info("Dashboard update loop cancelled")
            raise
        except Exception as e:
            logger.error("Error in dashboard update loop", error=str(e))
    
    async def _update_metrics(self) -> None:
        """Update current metrics."""
        try:
            if not self.trading_loop:
                return
            
            # Get trading loop status
            status = self.trading_loop.get_status()
            
            # Update bot status
            self.current_metrics.bot_status = {
                "running": status.get("running", False),
                "symbol": status.get("symbol", ""),
                "strategy": status.get("strategy", ""),
                "llm_provider": status.get("llm_provider", ""),
                "start_time": status.get("start_time"),
                "uptime": self._calculate_uptime(status.get("start_time")),
            }
            
            # Update performance metrics
            self.current_metrics.performance_metrics = {
                "analysis_count": status.get("analysis_count", 0),
                "decision_count": status.get("decision_count", 0),
                "order_count": status.get("order_count", 0),
                "success_rate": self._calculate_success_rate(status),
            }
            
            # Update order metrics
            order_status = status.get("order_manager_status", {})
            self.current_metrics.order_metrics = {
                "open_orders": order_status.get("open_orders", 0),
                "max_orders": order_status.get("max_orders", 0),
                "total_orders": order_status.get("total_orders", 0),
                "successful_orders": order_status.get("successful_orders", 0),
                "failed_orders": order_status.get("failed_orders", 0),
                "success_rate": order_status.get("success_rate", 0),
            }
            
            # Update buffer metrics
            buffer_info = status.get("buffer_info", {})
            self.current_metrics.buffer_metrics = {
                "current_size": buffer_info.get("current_size", 0),
                "max_size": buffer_info.get("max_size", 0),
                "utilization": buffer_info.get("utilization", 0),
                "last_update": buffer_info.get("last_update"),
                "total_received": buffer_info.get("total_received", 0),
                "total_dropped": buffer_info.get("total_dropped", 0),
            }
            
            # Update risk metrics
            self.current_metrics.risk_metrics = {
                "max_risk_per_trade": self.settings.binance.max_risk_per_trade,
                "max_daily_trades": self.settings.trading.max_daily_trades,
                "max_daily_loss": self.settings.trading.max_daily_loss,
                "current_risk": self._calculate_current_risk(),
            }
            
            # Update LLM metrics
            self.current_metrics.llm_metrics = {
                "provider": status.get("llm_provider", ""),
                "primary_provider": self.settings.llm.primary_provider,
                "fallback_providers": self.settings.llm.fallback_providers,
                "max_requests_per_minute": self.settings.llm.max_requests_per_minute,
            }
            
            # Update timestamp
            self.current_metrics.timestamp = datetime.now(timezone.utc)
            
            # Add to history
            self.metrics_history.append(self.current_metrics)
            
            # Trim history
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        except Exception as e:
            logger.error("Error updating dashboard metrics", error=str(e))
    
    def _calculate_uptime(self, start_time: Optional[str]) -> Optional[str]:
        """Calculate bot uptime.
        
        Args:
            start_time: Bot start time as ISO string
            
        Returns:
            Uptime as formatted string
        """
        if not start_time:
            return None
        
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            uptime = datetime.now(timezone.utc) - start
            
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m {seconds}s"
        
        except Exception:
            return None
    
    def _calculate_success_rate(self, status: Dict[str, Any]) -> float:
        """Calculate overall success rate.
        
        Args:
            status: Trading loop status
            
        Returns:
            Success rate as float (0-1)
        """
        try:
            order_status = status.get("order_manager_status", {})
            total_orders = order_status.get("total_orders", 0)
            successful_orders = order_status.get("successful_orders", 0)
            
            if total_orders == 0:
                return 0.0
            
            return successful_orders / total_orders
        
        except Exception:
            return 0.0
    
    def _calculate_current_risk(self) -> Dict[str, Any]:
        """Calculate current risk metrics.
        
        Returns:
            Dictionary with current risk information
        """
        try:
            if not self.trading_loop:
                return {}
            
            order_manager = self.trading_loop.order_manager
            risk_status = order_manager.risk_manager.get_risk_status()
            
            return {
                "daily_trades": risk_status.get("daily_trades", 0),
                "daily_pnl": risk_status.get("daily_pnl", "0"),
                "trades_remaining": risk_status.get("trades_remaining", 0),
                "loss_buffer": risk_status.get("loss_buffer", "0"),
            }
        
        except Exception:
            return {}
    
    def get_current_metrics(self) -> DashboardMetrics:
        """Get current dashboard metrics.
        
        Returns:
            Current dashboard metrics
        """
        return self.current_metrics
    
    def get_metrics_history(self, limit: int = 100) -> List[DashboardMetrics]:
        """Get metrics history.
        
        Args:
            limit: Maximum number of metrics to return
            
        Returns:
            List of historical metrics
        """
        return self.metrics_history[-limit:] if self.metrics_history else []
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Performance summary
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter metrics within time range
            recent_metrics = [
                m for m in self.metrics_history
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    "period_hours": hours,
                    "total_analyses": 0,
                    "total_decisions": 0,
                    "total_orders": 0,
                    "success_rate": 0.0,
                    "average_analysis_interval": 0.0,
                }
            
            # Calculate summary
            total_analyses = recent_metrics[-1].performance_metrics.get("analysis_count", 0)
            total_decisions = recent_metrics[-1].performance_metrics.get("decision_count", 0)
            total_orders = recent_metrics[-1].performance_metrics.get("order_count", 0)
            success_rate = recent_metrics[-1].performance_metrics.get("success_rate", 0.0)
            
            # Calculate average analysis interval
            if len(recent_metrics) > 1:
                time_span = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
                average_interval = time_span / len(recent_metrics) if len(recent_metrics) > 0 else 0
            else:
                average_interval = 0
            
            return {
                "period_hours": hours,
                "total_analyses": total_analyses,
                "total_decisions": total_decisions,
                "total_orders": total_orders,
                "success_rate": success_rate,
                "average_analysis_interval": average_interval,
                "metrics_count": len(recent_metrics),
            }
        
        except Exception as e:
            logger.error("Error calculating performance summary", error=str(e))
            return {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the trading bot.
        
        Returns:
            Health status information
        """
        try:
            health_status = {
                "overall": "healthy",
                "issues": [],
                "warnings": [],
                "last_check": datetime.now(timezone.utc).isoformat(),
            }
            
            if not self.trading_loop:
                health_status["overall"] = "error"
                health_status["issues"].append("Trading loop not available")
                return health_status
            
            # Check bot status
            if not self.current_metrics.bot_status.get("running", False):
                health_status["overall"] = "error"
                health_status["issues"].append("Bot is not running")
            
            # Check buffer utilization
            buffer_util = self.current_metrics.buffer_metrics.get("utilization", 0)
            if buffer_util < 0.5:
                health_status["warnings"].append("Low buffer utilization")
            
            # Check success rate
            success_rate = self.current_metrics.performance_metrics.get("success_rate", 0)
            if success_rate < 0.5:
                health_status["warnings"].append("Low success rate")
            
            # Check for recent errors
            if self.current_metrics.buffer_metrics.get("total_dropped", 0) > 10:
                health_status["warnings"].append("High data drop rate")
            
            return health_status
        
        except Exception as e:
            logger.error("Error calculating health status", error=str(e))
            return {
                "overall": "error",
                "issues": [f"Health check failed: {str(e)}"],
                "warnings": [],
                "last_check": datetime.now(timezone.utc).isoformat(),
            }
