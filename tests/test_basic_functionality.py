"""Basic functionality tests for the trading bot."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from src.core.types import OHLCVData, TradingMode, OrderSide, OrderType
from src.core.settings import get_settings
from src.data.ingestion import DataIngestionService
from src.data.features import TechnicalIndicatorCalculator, MarketSignalGenerator
from src.strategy.technical_strategy import TechnicalStrategy
from src.core.types import StrategyConfig


class TestBasicFunctionality:
    """Test basic functionality of the trading bot components."""
    
    def test_ohlcv_data_creation(self):
        """Test OHLCV data creation and validation."""
        ohlcv = OHLCVData(
            timestamp=datetime.now(timezone.utc),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.50"),
            symbol="BTCUSDT"
        )
        
        assert ohlcv.symbol == "BTCUSDT"
        assert ohlcv.open == Decimal("50000.00")
        assert ohlcv.high == Decimal("51000.00")
        assert ohlcv.low == Decimal("49000.00")
        assert ohlcv.close == Decimal("50500.00")
        assert ohlcv.volume == Decimal("1000.50")
    
    def test_technical_indicator_calculation(self):
        """Test technical indicator calculation."""
        # Create sample data
        data = []
        base_price = 50000
        for i in range(30):
            price = base_price + (i * 100)
            data.append(OHLCVData(
                timestamp=datetime.now(timezone.utc),
                open=Decimal(str(price)),
                high=Decimal(str(price + 50)),
                low=Decimal(str(price - 50)),
                close=Decimal(str(price + 25)),
                volume=Decimal("1000.0"),
                symbol="BTCUSDT"
            ))
        
        # Calculate indicators
        calculator = TechnicalIndicatorCalculator()
        indicators = calculator.calculate_all_indicators(data)
        
        # Basic validation
        assert indicators.rsi is not None
        assert indicators.sma_20 is not None
        assert indicators.ema_20 is not None
        assert indicators.atr is not None
        assert indicators.volatility is not None
        assert len(indicators.log_returns) > 0
    
    def test_market_signal_generation(self):
        """Test market signal generation."""
        # Create sample data
        data = []
        base_price = 50000
        for i in range(30):
            price = base_price + (i * 100)
            data.append(OHLCVData(
                timestamp=datetime.now(timezone.utc),
                open=Decimal(str(price)),
                high=Decimal(str(price + 50)),
                low=Decimal(str(price - 50)),
                close=Decimal(str(price + 25)),
                volume=Decimal("1000.0"),
                symbol="BTCUSDT"
            ))
        
        # Calculate indicators
        calculator = TechnicalIndicatorCalculator()
        indicators = calculator.calculate_all_indicators(data)
        
        # Generate signals
        signal_generator = MarketSignalGenerator()
        signals = signal_generator.generate_signals(data, indicators)
        
        # Basic validation
        assert "trend" in signals
        assert "momentum" in signals
        assert "volatility_regime" in signals
        assert "support_resistance" in signals
    
    def test_technical_strategy_decision(self):
        """Test technical strategy decision making."""
        # Create sample data
        data = []
        base_price = 50000
        for i in range(30):
            price = base_price + (i * 100)
            data.append(OHLCVData(
                timestamp=datetime.now(timezone.utc),
                open=Decimal(str(price)),
                high=Decimal(str(price + 50)),
                low=Decimal(str(price - 50)),
                close=Decimal(str(price + 25)),
                volume=Decimal("1000.0"),
                symbol="BTCUSDT"
            ))
        
        # Calculate indicators and signals
        calculator = TechnicalIndicatorCalculator()
        indicators = calculator.calculate_all_indicators(data)
        
        signal_generator = MarketSignalGenerator()
        signals = signal_generator.generate_signals(data, indicators)
        
        # Create strategy
        strategy = TechnicalStrategy()
        config = StrategyConfig(
            name="test",
            description="Test strategy",
            max_risk_per_trade=0.01,
            min_confidence=0.5
        )
        
        # Make decision
        decision = strategy.decide(data, indicators, signals, config)
        
        # Basic validation
        assert decision.symbol == "BTCUSDT"
        assert decision.confidence >= 0.0
        assert decision.confidence <= 1.0
        assert decision.risk_score >= 0.0
        assert decision.risk_score <= 1.0
        assert len(decision.reasoning) > 0
    
    def test_settings_loading(self):
        """Test settings loading and validation."""
        settings = get_settings()
        
        # Basic validation
        assert settings.app_name == "GenAI Trading Bot"
        assert settings.environment in ["development", "testing", "production"]
        assert settings.llm.primary_provider in ["openai", "anthropic", "gemini"]
        assert settings.binance.mode in ["paper", "testnet", "live"]
    
    def test_data_ingestion_service(self):
        """Test data ingestion service."""
        service = DataIngestionService()
        
        # Test with sample data
        sample_data = [
            OHLCVData(
                timestamp=datetime.now(timezone.utc),
                open=Decimal("50000.00"),
                high=Decimal("51000.00"),
                low=Decimal("49000.00"),
                close=Decimal("50500.00"),
                volume=Decimal("1000.50"),
                symbol="BTCUSDT"
            )
        ]
        
        # Validate data quality
        quality_metrics = service.validate_data_quality(sample_data)
        
        assert quality_metrics["valid"] is True
        assert quality_metrics["total_points"] == 1
        assert quality_metrics["symbol"] == "BTCUSDT"


if __name__ == "__main__":
    pytest.main([__file__])
