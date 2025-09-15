"""Integration tests for the complete trading bot system."""

import asyncio
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from src.core.types import OHLCVData, TradingDecision, TradingAction
from src.trading.trading_loop import AutonomousTradingLoop
from src.streaming.data_buffer import DataBuffer
from src.communication.notification_manager import NotificationManager, NotificationChannel
from src.monitoring.alerts import AlertManager, Alert, AlertLevel, AlertType


class TestTradingBotIntegration:
    """Integration tests for the complete trading bot system."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        data = []
        base_price = 50000
        base_time = datetime.now(timezone.utc)
        
        for i in range(100):  # 100 data points
            price = base_price + (i * 10)
            timestamp = base_time.replace(minute=i % 60, hour=base_time.hour + (i // 60))
            
            data.append(OHLCVData(
                timestamp=timestamp,
                open=Decimal(str(price)),
                high=Decimal(str(price + 50)),
                low=Decimal(str(price - 50)),
                close=Decimal(str(price + 25)),
                volume=Decimal("1000.0"),
                symbol="BTCUSDT"
            ))
        
        return data
    
    @pytest.fixture
    def mock_trading_loop(self, sample_data):
        """Create a mock trading loop for testing."""
        loop = Mock(spec=AutonomousTradingLoop)
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
    
    @pytest.mark.asyncio
    async def test_data_buffer_integration(self, sample_data):
        """Test data buffer integration with trading loop."""
        buffer = DataBuffer(max_size=50)
        
        # Add initial data
        for data_point in sample_data[:50]:
            buffer.add_new_candle(data_point)
        
        # Verify buffer state
        assert len(buffer.get_full_history()) == 50
        assert buffer.get_buffer_info()["current_size"] == 50
        assert buffer.get_buffer_info()["utilization"] == 1.0
        
        # Add more data (should trigger circular behavior)
        for data_point in sample_data[50:60]:
            buffer.add_new_candle(data_point)
        
        # Verify circular behavior
        assert len(buffer.get_full_history()) == 50
        assert buffer.get_buffer_info()["current_size"] == 50
        
        # Verify latest data is most recent
        latest = buffer.get_latest_candle()
        assert latest.timestamp == sample_data[59].timestamp
    
    @pytest.mark.asyncio
    async def test_notification_system_integration(self):
        """Test notification system integration."""
        notification_manager = NotificationManager()
        
        # Test trading decision notification
        decision = TradingDecision(
            action=TradingAction.BUY,
            symbol="BTCUSDT",
            quantity=Decimal("0.001"),
            price=Decimal("50000.0"),
            confidence=0.85,
            reasoning="Strong bullish momentum",
            risk_score=0.25,
        )
        
        # Send notification
        await notification_manager.send_trading_decision_notification(decision)
        
        # Verify notification was sent
        stats = notification_manager.get_channel_statistics()
        assert stats["total_sent"] >= 1
        
        # Test system notification
        await notification_manager.send_system_notification(
            title="Test Alert",
            message="This is a test notification",
            priority=NotificationPriority.HIGH
        )
        
        # Verify system notification
        stats = notification_manager.get_channel_statistics()
        assert stats["total_sent"] >= 2
    
    @pytest.mark.asyncio
    async def test_alert_system_integration(self):
        """Test alert system integration."""
        alert_manager = AlertManager()
        
        # Test alert evaluation
        test_data = {
            "running": False,  # Should trigger bot_stopped alert
            "success_rate": 0.3,  # Should trigger low_success_rate alert
            "websocket_connected": False,  # Should trigger websocket_disconnected alert
        }
        
        # Evaluate alerts
        triggered_alerts = await alert_manager.evaluate_alerts(test_data)
        
        # Verify alerts were triggered
        assert len(triggered_alerts) >= 2  # At least bot_stopped and low_success_rate
        
        # Check alert types
        alert_types = [alert.alert_type for alert in triggered_alerts]
        assert AlertType.BOT_STOPPED in alert_types
        assert AlertType.LOW_SUCCESS_RATE in alert_types
    
    @pytest.mark.asyncio
    async def test_trading_loop_status_integration(self, mock_trading_loop):
        """Test trading loop status integration."""
        status = mock_trading_loop.get_status()
        
        # Verify status structure
        assert "symbol" in status
        assert "running" in status
        assert "strategy" in status
        assert "analysis_count" in status
        assert "buffer_info" in status
        assert "order_manager_status" in status
        
        # Verify values
        assert status["symbol"] == "BTCUSDT"
        assert status["running"] is True
        assert status["strategy"] == "llm"
        assert status["analysis_count"] == 10
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, sample_data):
        """Test complete end-to-end workflow."""
        # Initialize components
        buffer = DataBuffer(max_size=100)
        notification_manager = NotificationManager()
        alert_manager = AlertManager()
        
        # Add data to buffer
        for data_point in sample_data:
            buffer.add_new_candle(data_point)
        
        # Simulate trading decision
        decision = TradingDecision(
            action=TradingAction.BUY,
            symbol="BTCUSDT",
            quantity=Decimal("0.001"),
            price=Decimal("50000.0"),
            confidence=0.85,
            reasoning="End-to-end test decision",
            risk_score=0.25,
        )
        
        # Send notification
        await notification_manager.send_trading_decision_notification(decision)
        
        # Evaluate alerts
        alert_data = {
            "running": True,
            "success_rate": 0.8,
            "websocket_connected": True,
        }
        alerts = await alert_manager.evaluate_alerts(alert_data)
        
        # Verify workflow
        assert len(buffer.get_full_history()) == 100
        assert notification_manager.get_channel_statistics()["total_sent"] >= 1
        assert len(alerts) == 0  # No alerts should be triggered with good data
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling across components."""
        notification_manager = NotificationManager()
        
        # Test error notification
        await notification_manager.send_system_notification(
            title="Test Error",
            message="This is a test error for integration testing",
            priority=NotificationPriority.ERROR
        )
        
        # Verify error notification
        stats = notification_manager.get_channel_statistics()
        assert stats["total_sent"] >= 1
        
        # Test alert for error condition
        alert_manager = AlertManager()
        error_data = {
            "running": False,
            "error_message": "Test error condition",
        }
        
        alerts = await alert_manager.evaluate_alerts(error_data)
        
        # Verify error alert
        assert len(alerts) >= 1
        assert any(alert.alert_type == AlertType.BOT_STOPPED for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_performance_metrics_integration(self, mock_trading_loop):
        """Test performance metrics integration."""
        # Get performance metrics
        order_manager = mock_trading_loop.order_manager
        performance = order_manager.get_performance_metrics()
        
        # Verify performance structure
        assert "total_orders" in performance
        assert "successful_orders" in performance
        assert "success_rate" in performance
        assert "total_volume" in performance
        
        # Verify values
        assert performance["total_orders"] == 10
        assert performance["successful_orders"] == 8
        assert performance["success_rate"] == 0.8
        assert performance["total_volume"] == 1000.0
    
    @pytest.mark.asyncio
    async def test_state_persistence_integration(self, mock_trading_loop):
        """Test state persistence integration."""
        state_manager = mock_trading_loop.state_manager
        
        # Get decision history
        decisions = state_manager.get_decision_history()
        
        # Verify decision structure
        assert len(decisions) >= 1
        decision = decisions[0]
        assert "timestamp" in decision
        assert "action" in decision
        assert "quantity" in decision
        assert "confidence" in decision
        assert "reasoning" in decision
        
        # Verify values
        assert decision["action"] == "BUY"
        assert decision["quantity"] == 0.001
        assert decision["confidence"] == 0.85
        assert decision["reasoning"] == "Strong bullish signal"


class TestSystemHealth:
    """Test system health and monitoring."""
    
    @pytest.mark.asyncio
    async def test_system_health_check(self):
        """Test system health monitoring."""
        from src.monitoring.dashboard import DashboardManager
        
        dashboard_manager = DashboardManager()
        
        # Test health status
        health = dashboard_manager.get_health_status()
        
        # Verify health structure
        assert "overall" in health
        assert "issues" in health
        assert "warnings" in health
        assert "last_check" in health
        
        # Verify health status
        assert health["overall"] in ["healthy", "warning", "error"]
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation(self):
        """Test metrics aggregation."""
        from src.monitoring.dashboard import DashboardManager
        
        dashboard_manager = DashboardManager()
        
        # Test performance summary
        summary = dashboard_manager.get_performance_summary(hours=24)
        
        # Verify summary structure
        assert "period_hours" in summary
        assert "total_analyses" in summary
        assert "total_decisions" in summary
        assert "total_orders" in summary
        assert "success_rate" in summary
        
        # Verify values
        assert summary["period_hours"] == 24
        assert summary["total_analyses"] >= 0
        assert summary["total_decisions"] >= 0
        assert summary["total_orders"] >= 0
        assert 0 <= summary["success_rate"] <= 1


class TestConfiguration:
    """Test configuration and settings."""
    
    def test_settings_validation(self):
        """Test settings validation."""
        from src.core.settings import get_settings
        
        settings = get_settings()
        
        # Verify settings structure
        assert hasattr(settings, 'llm')
        assert hasattr(settings, 'binance')
        assert hasattr(settings, 'streaming')
        assert hasattr(settings, 'trading')
        
        # Verify LLM settings
        assert settings.llm.primary_provider in ["openai", "anthropic", "gemini"]
        assert settings.llm.max_requests_per_minute > 0
        
        # Verify Binance settings
        assert settings.binance.mode in ["paper", "testnet", "live"]
        assert 0 < settings.binance.max_risk_per_trade < 1
        
        # Verify streaming settings
        assert settings.streaming.analysis_interval > 0
        assert settings.streaming.buffer_max_size > 0
        
        # Verify trading settings
        assert settings.trading.max_concurrent_orders > 0
        assert 0 < settings.trading.max_daily_loss < 1
    
    def test_environment_variables(self):
        """Test environment variable loading."""
        import os
        from src.core.settings import get_settings
        
        # Test with environment variables
        os.environ["LLM_PRIMARY_PROVIDER"] = "anthropic"
        os.environ["BINANCE_MODE"] = "testnet"
        os.environ["STREAMING_ANALYSIS_INTERVAL"] = "30"
        
        settings = get_settings()
        
        # Verify environment variables are loaded
        assert settings.llm.primary_provider == "anthropic"
        assert settings.binance.mode == "testnet"
        assert settings.streaming.analysis_interval == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
