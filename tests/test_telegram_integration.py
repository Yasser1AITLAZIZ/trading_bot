"""Integration tests for Telegram bot functionality."""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from src.communication.telegram_bot import TelegramBot
from src.communication.notification_manager import NotificationManager, NotificationChannel
from src.core.types import TradingDecision, TradingAction
from src.monitoring.alerts import Alert, AlertLevel, AlertType


class TestTelegramBotIntegration:
    """Integration tests for Telegram bot functionality."""
    
    @pytest.fixture
    def mock_trading_loop(self):
        """Create a mock trading loop for testing."""
        loop = Mock()
        loop.running = True
        loop.symbol = "BTCUSDT"
        loop.strategy = "llm"
        loop.llm_provider = "openai"
        loop.analysis_count = 10
        loop.decision_count = 5
        loop.order_count = 3
        loop.start_time = datetime.now(timezone.utc)
        
        # Mock order manager
        loop.order_manager = Mock()
        loop.order_manager.get_open_orders.return_value = {}
        loop.order_manager.get_order_history.return_value = []
        loop.order_manager.get_performance_metrics.return_value = {
            "total_orders": 10,
            "successful_orders": 8,
            "success_rate": 0.8,
            "total_volume": 1000.0,
        }
        
        # Mock data buffer
        loop.data_buffer = Mock()
        loop.data_buffer.get_buffer_info.return_value = {
            "current_size": 100,
            "max_size": 480,
            "utilization": 0.21,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }
        
        # Mock state manager
        loop.state_manager = Mock()
        loop.state_manager.get_decision_history.return_value = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "BUY",
                "quantity": 0.001,
                "price": 50000.0,
                "confidence": 0.85,
                "reasoning": "Strong bullish signal",
                "risk_score": 0.25,
            }
        ]
        
        return loop
    
    @pytest.fixture
    def mock_alert_manager(self):
        """Create a mock alert manager for testing."""
        manager = Mock()
        manager.get_alert_history.return_value = [
            Alert(
                alert_type=AlertType.BOT_STARTED,
                level=AlertLevel.INFO,
                message="Bot started successfully",
            ),
            Alert(
                alert_type=AlertType.TRADING_DECISION,
                level=AlertLevel.INFO,
                message="Trading decision made",
            ),
        ]
        manager.get_alert_summary.return_value = {
            "total_alerts": 2,
            "level_counts": {
                "info": 2,
                "warning": 0,
                "error": 0,
                "critical": 0,
            },
            "type_counts": {
                "bot_started": 1,
                "trading_decision": 1,
            },
        }
        return manager
    
    @pytest.fixture
    def telegram_bot(self, mock_trading_loop, mock_alert_manager):
        """Create a Telegram bot instance for testing."""
        with patch('src.communication.telegram_bot.Application'):
            bot = TelegramBot(
                bot_token="test_token",
                trading_loop=mock_trading_loop,
                alert_manager=mock_alert_manager,
                allowed_users=[123456789],
            )
            return bot
    
    def test_telegram_bot_initialization(self, telegram_bot):
        """Test Telegram bot initialization."""
        assert telegram_bot.bot_token == "test_token"
        assert telegram_bot.allowed_users == [123456789]
        assert telegram_bot.running is False
        assert telegram_bot.message_count == 0
        assert telegram_bot.command_count == 0
    
    def test_user_permission_check(self, telegram_bot):
        """Test user permission checking."""
        # Test allowed user
        assert telegram_bot._check_user_permission(123456789) is True
        
        # Test disallowed user
        assert telegram_bot._check_user_permission(987654321) is False
        
        # Test with no restrictions
        telegram_bot.allowed_users = []
        assert telegram_bot._check_user_permission(123456789) is True
        assert telegram_bot._check_user_permission(987654321) is True
    
    @pytest.mark.asyncio
    async def test_telegram_bot_start_stop(self, telegram_bot):
        """Test Telegram bot start and stop functionality."""
        with patch.object(telegram_bot.application, 'initialize', new_callable=AsyncMock) as mock_init, \
             patch.object(telegram_bot.application, 'start', new_callable=AsyncMock) as mock_start, \
             patch.object(telegram_bot.application, 'updater') as mock_updater:
            
            mock_updater.start_polling = AsyncMock()
            mock_updater.stop = AsyncMock()
            
            # Test start
            await telegram_bot.start()
            assert telegram_bot.running is True
            mock_init.assert_called_once()
            mock_start.assert_called_once()
            mock_updater.start_polling.assert_called_once()
            
            # Test stop
            await telegram_bot.stop()
            assert telegram_bot.running is False
            mock_updater.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_notification_sending(self, telegram_bot):
        """Test alert notification sending."""
        with patch.object(telegram_bot.application, 'bot') as mock_bot:
            mock_bot.send_message = AsyncMock()
            
            # Create test alert
            alert = Alert(
                alert_type=AlertType.BOT_STARTED,
                level=AlertLevel.INFO,
                message="Test alert message",
            )
            
            # Send alert notification
            await telegram_bot.send_alert_notification(alert)
            
            # Verify message was sent
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args[1]['chat_id'] == 123456789
            assert "INFO Alert" in call_args[1]['text']
            assert "Test alert message" in call_args[1]['text']
    
    @pytest.mark.asyncio
    async def test_trading_decision_notification(self, telegram_bot):
        """Test trading decision notification sending."""
        with patch.object(telegram_bot.application, 'bot') as mock_bot:
            mock_bot.send_message = AsyncMock()
            
            # Create test decision
            decision = TradingDecision(
                action=TradingAction.BUY,
                symbol="BTCUSDT",
                quantity=0.001,
                price=50000.0,
                confidence=0.85,
                reasoning="Test trading decision",
                risk_score=0.25,
            )
            
            # Send decision notification
            await telegram_bot.send_trading_decision(decision)
            
            # Verify message was sent
            mock_bot.send_message.assert_called_once()
            call_args = mock_bot.send_message.call_args
            assert call_args[1]['chat_id'] == 123456789
            assert "Trading Decision" in call_args[1]['text']
            assert "BUY" in call_args[1]['text']
            assert "BTCUSDT" in call_args[1]['text']
    
    def test_telegram_bot_status(self, telegram_bot):
        """Test Telegram bot status reporting."""
        status = telegram_bot.get_status()
        
        # Verify status structure
        assert "running" in status
        assert "start_time" in status
        assert "message_count" in status
        assert "command_count" in status
        assert "allowed_users_count" in status
        assert "trading_loop_available" in status
        assert "alert_manager_available" in status
        
        # Verify values
        assert status["running"] is False
        assert status["message_count"] == 0
        assert status["command_count"] == 0
        assert status["allowed_users_count"] == 1
        assert status["trading_loop_available"] is True
        assert status["alert_manager_available"] is True


class TestNotificationManagerIntegration:
    """Integration tests for notification manager with Telegram."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create a notification manager for testing."""
        manager = NotificationManager()
        return manager
    
    @pytest.mark.asyncio
    async def test_trading_decision_notification(self, notification_manager):
        """Test trading decision notification through notification manager."""
        # Create test decision
        decision = TradingDecision(
            action=TradingAction.SELL,
            symbol="ETHUSDT",
            quantity=0.01,
            price=3000.0,
            confidence=0.75,
            reasoning="Profit target reached",
            risk_score=0.20,
        )
        
        # Send notification
        await notification_manager.send_trading_decision_notification(decision)
        
        # Verify notification was sent
        stats = notification_manager.get_channel_statistics()
        assert stats["total_sent"] >= 1
        
        # Verify notification history
        history = notification_manager.get_notification_history(limit=1)
        assert len(history) >= 1
        assert "SELL" in history[0].message
        assert "ETHUSDT" in history[0].message
    
    @pytest.mark.asyncio
    async def test_alert_notification(self, notification_manager):
        """Test alert notification through notification manager."""
        # Create test alert
        alert = Alert(
            alert_type=AlertType.RISK_LIMIT_EXCEEDED,
            level=AlertLevel.CRITICAL,
            message="Risk limit exceeded: 5.2% daily loss",
        )
        
        # Send notification
        await notification_manager.send_alert_notification(alert)
        
        # Verify notification was sent
        stats = notification_manager.get_channel_statistics()
        assert stats["total_sent"] >= 1
        
        # Verify notification history
        history = notification_manager.get_notification_history(limit=1)
        assert len(history) >= 1
        assert "Risk limit exceeded" in history[0].message
        assert history[0].priority.value == "urgent"
    
    @pytest.mark.asyncio
    async def test_system_notification(self, notification_manager):
        """Test system notification through notification manager."""
        # Send system notification
        await notification_manager.send_system_notification(
            title="System Test",
            message="This is a system test notification",
            priority=NotificationPriority.HIGH
        )
        
        # Verify notification was sent
        stats = notification_manager.get_channel_statistics()
        assert stats["total_sent"] >= 1
        
        # Verify notification history
        history = notification_manager.get_notification_history(limit=1)
        assert len(history) >= 1
        assert history[0].title == "System Test"
        assert history[0].priority == NotificationPriority.HIGH
    
    def test_notification_statistics(self, notification_manager):
        """Test notification statistics."""
        stats = notification_manager.get_channel_statistics()
        
        # Verify stats structure
        assert "total_sent" in stats
        assert "failed_sends" in stats
        assert "success_rate" in stats
        assert "channels" in stats
        assert "registered_channels" in stats
        
        # Verify values
        assert stats["total_sent"] >= 0
        assert stats["failed_sends"] >= 0
        assert 0 <= stats["success_rate"] <= 1
        assert "log" in stats["registered_channels"]
    
    def test_notification_summary(self, notification_manager):
        """Test notification summary."""
        summary = notification_manager.get_notification_summary(hours=24)
        
        # Verify summary structure
        assert "period_hours" in summary
        assert "total_notifications" in summary
        assert "priority_counts" in summary
        assert "channel_counts" in summary
        
        # Verify values
        assert summary["period_hours"] == 24
        assert summary["total_notifications"] >= 0
        assert "low" in summary["priority_counts"]
        assert "normal" in summary["priority_counts"]
        assert "high" in summary["priority_counts"]
        assert "urgent" in summary["priority_counts"]


class TestTelegramCommandHandlers:
    """Test Telegram bot command handlers."""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update."""
        update = Mock()
        update.effective_user.id = 123456789
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context."""
        context = Mock()
        return context
    
    @pytest.mark.asyncio
    async def test_start_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /start command handler."""
        await telegram_bot._handle_start(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "GenAI Trading Bot" in call_args[0][0]
        assert "Available Commands" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_help_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /help command handler."""
        await telegram_bot._handle_help(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "GenAI Trading Bot - Help" in call_args[0][0]
        assert "Status Commands" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_status_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /status command handler."""
        await telegram_bot._handle_status(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Trading Bot Status" in call_args[0][0]
        assert "BTCUSDT" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_orders_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /orders command handler."""
        await telegram_bot._handle_orders(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Orders Status" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_decisions_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /decisions command handler."""
        await telegram_bot._handle_decisions(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Recent Trading Decisions" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_performance_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /performance command handler."""
        await telegram_bot._handle_performance(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Performance Metrics" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_alerts_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /alerts command handler."""
        await telegram_bot._handle_alerts(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Recent Alerts" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_config_command_handler(self, telegram_bot, mock_update, mock_context):
        """Test /config command handler."""
        await telegram_bot._handle_config(mock_update, mock_context)
        
        # Verify reply was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Bot Configuration" in call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
