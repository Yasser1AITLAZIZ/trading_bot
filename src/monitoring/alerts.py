"""Alert system for trading bot monitoring and notifications."""

import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import structlog

from ..core.settings import get_settings
from ..core.types import TradingDecision

logger = structlog.get_logger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    
    # System alerts
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_ERROR = "bot_error"
    
    # Trading alerts
    TRADING_DECISION = "trading_decision"
    ORDER_EXECUTED = "order_executed"
    ORDER_FAILED = "order_failed"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    
    # Data alerts
    DATA_STALE = "data_stale"
    DATA_MISSING = "data_missing"
    WEBSOCKET_DISCONNECTED = "websocket_disconnected"
    
    # Performance alerts
    LOW_SUCCESS_RATE = "low_success_rate"
    HIGH_ERROR_RATE = "high_error_rate"
    PERFORMANCE_DEGRADED = "performance_degraded"


class Alert:
    """Alert object."""
    
    def __init__(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Initialize an alert.
        
        Args:
            alert_type: Type of alert
            level: Alert severity level
            message: Alert message
            details: Additional alert details
            timestamp: Alert timestamp
        """
        self.alert_type = alert_type
        self.level = level
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.id = f"{self.alert_type}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary.
        
        Returns:
            Dictionary representation of alert
        """
        return {
            "id": self.id,
            "type": self.alert_type.value,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class AlertRule:
    """Alert rule for triggering alerts based on conditions."""
    
    def __init__(
        self,
        name: str,
        alert_type: AlertType,
        level: AlertLevel,
        condition: Callable[[Dict[str, Any]], bool],
        message_template: str,
        cooldown_seconds: int = 300,  # 5 minutes default
    ):
        """Initialize an alert rule.
        
        Args:
            name: Rule name
            alert_type: Type of alert to trigger
            level: Alert severity level
            condition: Function that returns True if alert should trigger
            message_template: Message template for the alert
            cooldown_seconds: Minimum time between alerts of this type
        """
        self.name = name
        self.alert_type = alert_type
        self.level = level
        self.condition = condition
        self.message_template = message_template
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered: Optional[datetime] = None
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        """Check if alert should trigger.
        
        Args:
            data: Data to evaluate
            
        Returns:
            True if alert should trigger
        """
        # Check cooldown
        if self.last_triggered:
            time_since_last = (datetime.now(timezone.utc) - self.last_triggered).total_seconds()
            if time_since_last < self.cooldown_seconds:
                return False
        
        # Check condition
        try:
            return self.condition(data)
        except Exception as e:
            logger.error("Error evaluating alert condition", rule=self.name, error=str(e))
            return False
    
    def trigger(self, data: Dict[str, Any]) -> Alert:
        """Trigger the alert.
        
        Args:
            data: Data for the alert
            
        Returns:
            Generated alert
        """
        self.last_triggered = datetime.now(timezone.utc)
        
        # Format message
        try:
            message = self.message_template.format(**data)
        except KeyError as e:
            message = f"{self.message_template} (Error formatting: {e})"
        
        return Alert(
            alert_type=self.alert_type,
            level=self.level,
            message=message,
            details=data,
        )


class AlertManager:
    """Manager for handling alerts and notifications."""
    
    def __init__(self):
        """Initialize the alert manager."""
        self.settings = get_settings()
        self.rules: List[AlertRule] = []
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000
        
        # Notification callbacks
        self.notification_callbacks: List[Callable[[Alert], None]] = []
        
        # Setup default rules
        self._setup_default_rules()
        
        logger.info("Initialized alert manager")
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules."""
        
        # Bot status rules
        self.add_rule(AlertRule(
            name="bot_stopped",
            alert_type=AlertType.BOT_STOPPED,
            level=AlertLevel.ERROR,
            condition=lambda data: not data.get("running", True),
            message_template="Trading bot has stopped running",
            cooldown_seconds=60,
        ))
        
        # Risk management rules
        self.add_rule(AlertRule(
            name="risk_limit_exceeded",
            alert_type=AlertType.RISK_LIMIT_EXCEEDED,
            level=AlertLevel.CRITICAL,
            condition=lambda data: data.get("risk_exceeded", False),
            message_template="Risk limit exceeded: {risk_details}",
            cooldown_seconds=300,
        ))
        
        # Data quality rules
        self.add_rule(AlertRule(
            name="data_stale",
            alert_type=AlertType.DATA_STALE,
            level=AlertLevel.WARNING,
            condition=lambda data: data.get("data_age_hours", 0) > 1,
            message_template="Data is stale: {data_age_hours:.1f} hours old",
            cooldown_seconds=600,
        ))
        
        # WebSocket connection rules
        self.add_rule(AlertRule(
            name="websocket_disconnected",
            alert_type=AlertType.WEBSOCKET_DISCONNECTED,
            level=AlertLevel.ERROR,
            condition=lambda data: not data.get("websocket_connected", True),
            message_template="WebSocket connection lost",
            cooldown_seconds=60,
        ))
        
        # Performance rules
        self.add_rule(AlertRule(
            name="low_success_rate",
            alert_type=AlertType.LOW_SUCCESS_RATE,
            level=AlertLevel.WARNING,
            condition=lambda data: data.get("success_rate", 1.0) < 0.5,
            message_template="Low success rate: {success_rate:.1%}",
            cooldown_seconds=900,
        ))
        
        # Order execution rules
        self.add_rule(AlertRule(
            name="order_failed",
            alert_type=AlertType.ORDER_FAILED,
            level=AlertLevel.ERROR,
            condition=lambda data: data.get("order_failed", False),
            message_template="Order execution failed: {order_details}",
            cooldown_seconds=60,
        ))
        
        logger.info("Setup default alert rules", count=len(self.rules))
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule.
        
        Args:
            rule: Alert rule to add
        """
        self.rules.append(rule)
        logger.info("Added alert rule", rule=rule.name)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove an alert rule.
        
        Args:
            rule_name: Name of rule to remove
            
        Returns:
            True if rule was removed
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                logger.info("Removed alert rule", rule=rule_name)
                return True
        return False
    
    def add_notification_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add a notification callback.
        
        Args:
            callback: Function to call when alert is triggered
        """
        self.notification_callbacks.append(callback)
        logger.info("Added notification callback")
    
    async def evaluate_alerts(self, data: Dict[str, Any]) -> List[Alert]:
        """Evaluate all alert rules against data.
        
        Args:
            data: Data to evaluate
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        for rule in self.rules:
            try:
                if rule.should_trigger(data):
                    alert = rule.trigger(data)
                    triggered_alerts.append(alert)
                    
                    # Add to history
                    self.alert_history.append(alert)
                    
                    # Trim history
                    if len(self.alert_history) > self.max_history_size:
                        self.alert_history = self.alert_history[-self.max_history_size:]
                    
                    logger.info(
                        "Alert triggered",
                        rule=rule.name,
                        level=alert.level.value,
                        message=alert.message,
                    )
            
            except Exception as e:
                logger.error("Error evaluating alert rule", rule=rule.name, error=str(e))
        
        # Send notifications
        for alert in triggered_alerts:
            await self._send_notifications(alert)
        
        return triggered_alerts
    
    async def _send_notifications(self, alert: Alert) -> None:
        """Send notifications for an alert.
        
        Args:
            alert: Alert to send notifications for
        """
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error("Error sending notification", error=str(e))
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        return self.alert_history[-limit:] if self.alert_history else []
    
    def get_alerts_by_level(self, level: AlertLevel, limit: int = 100) -> List[Alert]:
        """Get alerts by severity level.
        
        Args:
            level: Alert level to filter by
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts with specified level
        """
        filtered_alerts = [alert for alert in self.alert_history if alert.level == level]
        return filtered_alerts[-limit:] if filtered_alerts else []
    
    def get_alerts_by_type(self, alert_type: AlertType, limit: int = 100) -> List[Alert]:
        """Get alerts by type.
        
        Args:
            alert_type: Alert type to filter by
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts with specified type
        """
        filtered_alerts = [alert for alert in self.alert_history if alert.alert_type == alert_type]
        return filtered_alerts[-limit:] if filtered_alerts else []
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert summary for the last N hours.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Alert summary
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
        
        # Count by level
        level_counts = {}
        for level in AlertLevel:
            level_counts[level.value] = len([
                alert for alert in recent_alerts if alert.level == level
            ])
        
        # Count by type
        type_counts = {}
        for alert_type in AlertType:
            type_counts[alert_type.value] = len([
                alert for alert in recent_alerts if alert.alert_type == alert_type
            ])
        
        return {
            "period_hours": hours,
            "total_alerts": len(recent_alerts),
            "level_counts": level_counts,
            "type_counts": type_counts,
            "most_common_type": max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None,
            "most_common_level": max(level_counts.items(), key=lambda x: x[1])[0] if level_counts else None,
        }
    
    def clear_history(self) -> None:
        """Clear alert history."""
        self.alert_history.clear()
        logger.info("Cleared alert history")
    
    def get_rules_status(self) -> List[Dict[str, Any]]:
        """Get status of all alert rules.
        
        Returns:
            List of rule status information
        """
        return [
            {
                "name": rule.name,
                "type": rule.alert_type.value,
                "level": rule.level.value,
                "cooldown_seconds": rule.cooldown_seconds,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                "active": True,
            }
            for rule in self.rules
        ]
