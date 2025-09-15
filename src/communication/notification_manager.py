"""Notification manager for handling various notification channels."""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import structlog

from ..core.settings import get_settings
from ..core.types import TradingDecision
from ..monitoring.alerts import Alert, AlertLevel

logger = structlog.get_logger(__name__)


class NotificationChannel(str, Enum):
    """Available notification channels."""
    
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification:
    """Notification object."""
    
    def __init__(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Initialize a notification.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Notification priority
            channels: Channels to send to (None for all)
            metadata: Additional metadata
            timestamp: Notification timestamp
        """
        self.title = title
        self.message = message
        self.priority = priority
        self.channels = channels or [NotificationChannel.LOG]
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.id = f"notif_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary.
        
        Returns:
            Dictionary representation of notification
        """
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "channels": [ch.value for ch in self.channels],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationManager:
    """Manager for handling notifications across multiple channels."""
    
    def __init__(self):
        """Initialize the notification manager."""
        self.settings = get_settings()
        
        # Notification channels
        self.channels: Dict[NotificationChannel, Callable] = {}
        self.channel_configs: Dict[NotificationChannel, Dict[str, Any]] = {}
        
        # Notification history
        self.notification_history: List[Notification] = []
        self.max_history_size = 1000
        
        # Statistics
        self.total_sent = 0
        self.failed_sends = 0
        self.channel_stats: Dict[NotificationChannel, Dict[str, int]] = {}
        
        # Initialize default channels
        self._setup_default_channels()
        
        logger.info("Initialized notification manager")
    
    def _setup_default_channels(self) -> None:
        """Setup default notification channels."""
        
        # Log channel (always available)
        self.register_channel(
            NotificationChannel.LOG,
            self._send_log_notification,
            {"level": "INFO"}
        )
        
        # Initialize channel stats
        for channel in NotificationChannel:
            self.channel_stats[channel] = {
                "sent": 0,
                "failed": 0,
                "total": 0,
            }
    
    def register_channel(
        self,
        channel: NotificationChannel,
        handler: Callable[[Notification], None],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a notification channel.
        
        Args:
            channel: Notification channel
            handler: Handler function for the channel
            config: Channel configuration
        """
        self.channels[channel] = handler
        self.channel_configs[channel] = config or {}
        
        logger.info("Registered notification channel", channel=channel.value)
    
    def unregister_channel(self, channel: NotificationChannel) -> None:
        """Unregister a notification channel.
        
        Args:
            channel: Notification channel to unregister
        """
        if channel in self.channels:
            del self.channels[channel]
            del self.channel_configs[channel]
            logger.info("Unregistered notification channel", channel=channel.value)
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send a notification through specified channels.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if at least one channel succeeded
        """
        success = False
        
        try:
            # Add to history
            self.notification_history.append(notification)
            
            # Trim history
            if len(self.notification_history) > self.max_history_size:
                self.notification_history = self.notification_history[-self.max_history_size:]
            
            # Send through each channel
            for channel in notification.channels:
                if channel in self.channels:
                    try:
                        handler = self.channels[channel]
                        
                        # Handle async and sync handlers
                        if asyncio.iscoroutinefunction(handler):
                            await handler(notification)
                        else:
                            handler(notification)
                        
                        # Update stats
                        self.channel_stats[channel]["sent"] += 1
                        self.channel_stats[channel]["total"] += 1
                        self.total_sent += 1
                        success = True
                        
                        logger.debug(
                            "Notification sent successfully",
                            channel=channel.value,
                            notification_id=notification.id,
                        )
                    
                    except Exception as e:
                        self.channel_stats[channel]["failed"] += 1
                        self.channel_stats[channel]["total"] += 1
                        self.failed_sends += 1
                        
                        logger.error(
                            "Failed to send notification",
                            channel=channel.value,
                            notification_id=notification.id,
                            error=str(e),
                        )
                else:
                    logger.warning(
                        "Channel not registered",
                        channel=channel.value,
                        notification_id=notification.id,
                    )
            
            if success:
                logger.info(
                    "Notification sent",
                    notification_id=notification.id,
                    channels=[ch.value for ch in notification.channels],
                    priority=notification.priority.value,
                )
            
            return success
        
        except Exception as e:
            logger.error("Error sending notification", error=str(e))
            return False
    
    async def send_alert_notification(self, alert: Alert) -> None:
        """Send alert as notification.
        
        Args:
            alert: Alert to send as notification
        """
        # Map alert level to notification priority
        priority_mapping = {
            AlertLevel.INFO: NotificationPriority.LOW,
            AlertLevel.WARNING: NotificationPriority.NORMAL,
            AlertLevel.ERROR: NotificationPriority.HIGH,
            AlertLevel.CRITICAL: NotificationPriority.URGENT,
        }
        
        priority = priority_mapping.get(alert.level, NotificationPriority.NORMAL)
        
        # Determine channels based on priority
        if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
            channels = [NotificationChannel.LOG, NotificationChannel.TELEGRAM]
        else:
            channels = [NotificationChannel.LOG]
        
        notification = Notification(
            title=f"Trading Bot Alert - {alert.alert_type.value}",
            message=alert.message,
            priority=priority,
            channels=channels,
            metadata={
                "alert_type": alert.alert_type.value,
                "alert_level": alert.level.value,
                "alert_id": alert.id,
            },
        )
        
        await self.send_notification(notification)
    
    async def send_trading_decision_notification(self, decision: TradingDecision) -> None:
        """Send trading decision as notification.
        
        Args:
            decision: Trading decision to send
        """
        action_emoji = "🟢" if decision.action.value == "BUY" else "🔴" if decision.action.value == "SELL" else "⏸️"
        
        title = f"Trading Decision - {decision.action.value if decision.action else 'HOLD'}"
        message = f"""
{action_emoji} {decision.action.value if decision.action else 'HOLD'} {decision.symbol}

Quantity: {decision.quantity}
Price: ${decision.price or 'Market'}
Confidence: {decision.confidence:.1%}
Risk Score: {decision.risk_score:.1%}

Reasoning: {decision.reasoning}
        """.strip()
        
        # Determine priority based on confidence and risk
        if decision.confidence > 0.8 and decision.risk_score < 0.3:
            priority = NotificationPriority.HIGH
            channels = [NotificationChannel.LOG, NotificationChannel.TELEGRAM]
        elif decision.confidence > 0.6:
            priority = NotificationPriority.NORMAL
            channels = [NotificationChannel.LOG, NotificationChannel.TELEGRAM]
        else:
            priority = NotificationPriority.LOW
            channels = [NotificationChannel.LOG]
        
        notification = Notification(
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            metadata={
                "decision_action": decision.action.value if decision.action else 'HOLD',
                "decision_symbol": decision.symbol,
                "decision_confidence": decision.confidence,
                "decision_risk_score": decision.risk_score,
            },
        )
        
        await self.send_notification(notification)
    
    async def send_system_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> None:
        """Send system notification.
        
        Args:
            title: Notification title
            message: Notification message
            priority: Notification priority
        """
        channels = [NotificationChannel.LOG]
        
        if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
            channels.append(NotificationChannel.TELEGRAM)
        
        notification = Notification(
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            metadata={"type": "system"},
        )
        
        await self.send_notification(notification)
    
    def _send_log_notification(self, notification: Notification) -> None:
        """Send notification to log.
        
        Args:
            notification: Notification to log
        """
        log_level = self.channel_configs.get(NotificationChannel.LOG, {}).get("level", "INFO")
        
        log_message = f"[{notification.priority.value.upper()}] {notification.title}: {notification.message}"
        
        if log_level == "DEBUG":
            logger.debug(log_message, notification_id=notification.id)
        elif log_level == "INFO":
            logger.info(log_message, notification_id=notification.id)
        elif log_level == "WARNING":
            logger.warning(log_message, notification_id=notification.id)
        elif log_level == "ERROR":
            logger.error(log_message, notification_id=notification.id)
        else:
            logger.info(log_message, notification_id=notification.id)
    
    def get_notification_history(self, limit: int = 100) -> List[Notification]:
        """Get notification history.
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of recent notifications
        """
        return self.notification_history[-limit:] if self.notification_history else []
    
    def get_channel_statistics(self) -> Dict[str, Any]:
        """Get channel statistics.
        
        Returns:
            Dictionary with channel statistics
        """
        return {
            "total_sent": self.total_sent,
            "failed_sends": self.failed_sends,
            "success_rate": (
                self.total_sent / (self.total_sent + self.failed_sends)
                if (self.total_sent + self.failed_sends) > 0 else 0
            ),
            "channels": {
                channel.value: stats for channel, stats in self.channel_stats.items()
            },
            "registered_channels": [ch.value for ch in self.channels.keys()],
        }
    
    def get_notification_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get notification summary for the last N hours.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Notification summary
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_notifications = [
            notif for notif in self.notification_history
            if notif.timestamp >= cutoff_time
        ]
        
        # Count by priority
        priority_counts = {}
        for priority in NotificationPriority:
            priority_counts[priority.value] = len([
                notif for notif in recent_notifications if notif.priority == priority
            ])
        
        # Count by channel
        channel_counts = {}
        for channel in NotificationChannel:
            channel_counts[channel.value] = len([
                notif for notif in recent_notifications if channel in notif.channels
            ])
        
        return {
            "period_hours": hours,
            "total_notifications": len(recent_notifications),
            "priority_counts": priority_counts,
            "channel_counts": channel_counts,
            "most_common_priority": max(priority_counts.items(), key=lambda x: x[1])[0] if priority_counts else None,
            "most_used_channel": max(channel_counts.items(), key=lambda x: x[1])[0] if channel_counts else None,
        }
    
    def clear_history(self) -> None:
        """Clear notification history."""
        self.notification_history.clear()
        logger.info("Cleared notification history")
