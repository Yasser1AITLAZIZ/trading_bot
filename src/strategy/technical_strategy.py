"""Technical analysis-based trading strategy implementation."""

from decimal import Decimal
from typing import Dict, List

import structlog

from .base import BaseStrategy
from ..core.types import OHLCVData, TechnicalIndicators, TradingDecision, StrategyConfig, OrderSide

logger = structlog.get_logger(__name__)


class TechnicalStrategy(BaseStrategy):
    """Technical analysis-based trading strategy using traditional indicators."""
    
    def __init__(self):
        """Initialize the technical strategy."""
        super().__init__(
            name="Technical Strategy",
            description="Technical analysis-based strategy using RSI, moving averages, and trend analysis"
        )
    
    def decide(
        self,
        data: List[OHLCVData],
        indicators: TechnicalIndicators,
        signals: Dict[str, str],
        config: StrategyConfig,
    ) -> TradingDecision:
        """Make a trading decision based on technical analysis.
        
        Args:
            data: Historical OHLCV data
            indicators: Technical indicators
            signals: Market signals
            config: Strategy configuration
            
        Returns:
            Trading decision
        """
        current_price = float(data[-1].close)
        symbol = data[-1].symbol
        
        # Analyze technical signals
        analysis = self._analyze_technical_signals(indicators, signals, current_price)
        
        # Make decision based on analysis
        if analysis["signal_strength"] >= config.min_confidence:
            if analysis["signal"] == "BUY":
                return self._create_buy_decision(data, config, analysis)
            elif analysis["signal"] == "SELL":
                return self._create_sell_decision(data, config, analysis)
        
        # No clear signal - hold
        return self._create_no_action_decision(data, analysis["reasoning"])
    
    def _analyze_technical_signals(
        self,
        indicators: TechnicalIndicators,
        signals: Dict[str, str],
        current_price: float,
    ) -> Dict:
        """Analyze technical signals to determine trading signal.
        
        Args:
            indicators: Technical indicators
            signals: Market signals
            current_price: Current price
            
        Returns:
            Analysis results
        """
        signal_score = 0.0
        signal_reasons = []
        
        # RSI Analysis
        if indicators.rsi is not None:
            if indicators.rsi < 30:  # Oversold
                signal_score += 0.3
                signal_reasons.append(f"RSI oversold ({indicators.rsi:.1f})")
            elif indicators.rsi > 70:  # Overbought
                signal_score -= 0.3
                signal_reasons.append(f"RSI overbought ({indicators.rsi:.1f})")
            elif 40 <= indicators.rsi <= 60:  # Neutral
                signal_reasons.append(f"RSI neutral ({indicators.rsi:.1f})")
        
        # Moving Average Analysis
        if indicators.sma_20 is not None and indicators.ema_20 is not None:
            if current_price > indicators.sma_20 and current_price > indicators.ema_20:
                signal_score += 0.2
                signal_reasons.append("Price above moving averages")
            elif current_price < indicators.sma_20 and current_price < indicators.ema_20:
                signal_score -= 0.2
                signal_reasons.append("Price below moving averages")
            
            # MA crossover
            if indicators.sma_20 > indicators.ema_20:
                signal_score += 0.1
                signal_reasons.append("SMA above EMA (bullish)")
            elif indicators.sma_20 < indicators.ema_20:
                signal_score -= 0.1
                signal_reasons.append("SMA below EMA (bearish)")
        
        # Trend Analysis
        trend = signals.get("trend", "sideways")
        if trend == "bullish":
            signal_score += 0.2
            signal_reasons.append("Bullish trend")
        elif trend == "bearish":
            signal_score -= 0.2
            signal_reasons.append("Bearish trend")
        else:
            signal_reasons.append("Sideways trend")
        
        # Momentum Analysis
        momentum = signals.get("momentum", "neutral")
        if momentum == "strong":
            signal_score += 0.1
            signal_reasons.append("Strong momentum")
        elif momentum == "weak":
            signal_score -= 0.1
            signal_reasons.append("Weak momentum")
        
        # Volatility Analysis
        volatility_regime = signals.get("volatility_regime", "normal")
        if volatility_regime == "high":
            signal_score *= 0.8  # Reduce confidence in high volatility
            signal_reasons.append("High volatility - reduced confidence")
        elif volatility_regime == "low":
            signal_score *= 1.1  # Slightly increase confidence in low volatility
            signal_reasons.append("Low volatility - increased confidence")
        
        # Determine final signal
        if signal_score > 0.3:
            signal = "BUY"
            confidence = min(signal_score, 1.0)
        elif signal_score < -0.3:
            signal = "SELL"
            confidence = min(abs(signal_score), 1.0)
        else:
            signal = "HOLD"
            confidence = 0.0
        
        return {
            "signal": signal,
            "signal_strength": confidence,
            "reasoning": "; ".join(signal_reasons),
            "score": signal_score,
        }
    
    def _create_buy_decision(
        self,
        data: List[OHLCVData],
        config: StrategyConfig,
        analysis: Dict,
    ) -> TradingDecision:
        """Create a buy decision.
        
        Args:
            data: Historical OHLCV data
            config: Strategy configuration
            analysis: Technical analysis results
            
        Returns:
            Buy trading decision
        """
        current_price = float(data[-1].close)
        symbol = data[-1].symbol
        
        # Calculate position size (simplified)
        account_balance = 10000.0  # Placeholder
        stop_loss_price = self.calculate_stop_loss(current_price, "BUY", config.stop_loss_pct)
        take_profit_price = self.calculate_take_profit(current_price, "BUY", config.take_profit_pct)
        
        quantity = self.calculate_position_size(
            account_balance,
            current_price,
            stop_loss_price,
            config.max_risk_per_trade,
        )
        
        return TradingDecision(
            action=OrderSide.BUY,
            symbol=symbol,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(current_price)),
            stop_loss=Decimal(str(stop_loss_price)),
            take_profit=Decimal(str(take_profit_price)),
            confidence=analysis["signal_strength"],
            reasoning=f"BUY: {analysis['reasoning']}",
            risk_score=0.3,  # Moderate risk for technical signals
        )
    
    def _create_sell_decision(
        self,
        data: List[OHLCVData],
        config: StrategyConfig,
        analysis: Dict,
    ) -> TradingDecision:
        """Create a sell decision.
        
        Args:
            data: Historical OHLCV data
            config: Strategy configuration
            analysis: Technical analysis results
            
        Returns:
            Sell trading decision
        """
        current_price = float(data[-1].close)
        symbol = data[-1].symbol
        
        # Calculate position size (simplified)
        account_balance = 10000.0  # Placeholder
        stop_loss_price = self.calculate_stop_loss(current_price, "SELL", config.stop_loss_pct)
        take_profit_price = self.calculate_take_profit(current_price, "SELL", config.take_profit_pct)
        
        quantity = self.calculate_position_size(
            account_balance,
            current_price,
            stop_loss_price,
            config.max_risk_per_trade,
        )
        
        return TradingDecision(
            action=OrderSide.SELL,
            symbol=symbol,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(current_price)),
            stop_loss=Decimal(str(stop_loss_price)),
            take_profit=Decimal(str(take_profit_price)),
            confidence=analysis["signal_strength"],
            reasoning=f"SELL: {analysis['reasoning']}",
            risk_score=0.3,  # Moderate risk for technical signals
        )
    
    def _create_no_action_decision(self, data: List[OHLCVData], reasoning: str) -> TradingDecision:
        """Create a no-action trading decision.
        
        Args:
            data: Historical OHLCV data
            reasoning: Reasoning for no action
            
        Returns:
            No-action trading decision
        """
        return TradingDecision(
            action=OrderSide.BUY,  # Dummy action
            symbol=data[-1].symbol,
            quantity=Decimal("0"),
            price=Decimal("0"),
            stop_loss=None,
            take_profit=None,
            confidence=0.0,
            reasoning=f"HOLD: {reasoning}",
            risk_score=0.0,
        )
