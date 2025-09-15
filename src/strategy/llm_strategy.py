"""LLM-powered trading strategy implementation."""

from decimal import Decimal
from typing import Dict, List

import structlog

from .base import BaseStrategy
from ..core.types import OHLCVData, TechnicalIndicators, TradingDecision, StrategyConfig, OrderSide
from ..llm.base import BaseLLMClient

logger = structlog.get_logger(__name__)


class LLMStrategy(BaseStrategy):
    """LLM-powered trading strategy that uses AI for decision making."""
    
    def __init__(self, llm_client: BaseLLMClient):
        """Initialize the LLM strategy.
        
        Args:
            llm_client: LLM client for AI-powered decisions
        """
        super().__init__(
            name="LLM Strategy",
            description="AI-powered trading strategy using LLM for decision making",
            llm_client=llm_client
        )
    
    def decide(
        self,
        data: List[OHLCVData],
        indicators: TechnicalIndicators,
        signals: Dict[str, str],
        config: StrategyConfig,
    ) -> TradingDecision:
        """Make a trading decision using LLM analysis.
        
        Args:
            data: Historical OHLCV data
            indicators: Technical indicators
            signals: Market signals
            config: Strategy configuration
            
        Returns:
            Trading decision
        """
        if not self.llm_client:
            raise StrategyError("LLM client is required for LLM strategy")
        
        # Prepare market analysis
        market_analysis = self._prepare_market_analysis(data, indicators, signals)
        
        # Generate LLM prompt
        prompt = self._create_decision_prompt(market_analysis, config)
        
        # Get LLM decision
        try:
            llm_response = self.llm_client.generate(prompt, temperature=0.1, max_tokens=500)
            decision_data = self._parse_llm_response(llm_response.content)
            
            # Validate and create trading decision
            return self._create_trading_decision(decision_data, data, config)
        
        except Exception as e:
            logger.error("LLM decision failed", error=str(e))
            # Fallback to no-action decision
            return self._create_no_action_decision(data, "LLM decision failed")
    
    def _prepare_market_analysis(
        self,
        data: List[OHLCVData],
        indicators: TechnicalIndicators,
        signals: Dict[str, str],
    ) -> Dict:
        """Prepare market analysis for LLM.
        
        Args:
            data: Historical OHLCV data
            indicators: Technical indicators
            signals: Market signals
            
        Returns:
            Market analysis dictionary
        """
        current_price = float(data[-1].close)
        symbol = data[-1].symbol
        
        # Calculate price change over different periods
        price_changes = {}
        if len(data) >= 5:
            price_changes["5_period"] = (current_price - float(data[-5].close)) / float(data[-5].close)
        if len(data) >= 20:
            price_changes["20_period"] = (current_price - float(data[-20].close)) / float(data[-20].close)
        
        # Prepare analysis
        analysis = {
            "symbol": symbol,
            "current_price": current_price,
            "price_changes": price_changes,
            "technical_indicators": {
                "rsi": indicators.rsi,
                "sma_20": indicators.sma_20,
                "ema_20": indicators.ema_20,
                "atr": indicators.atr,
                "volatility": indicators.volatility,
            },
            "market_signals": signals,
            "recent_volumes": [float(point.volume) for point in data[-10:]] if len(data) >= 10 else [],
        }
        
        return analysis
    
    def _create_decision_prompt(self, market_analysis: Dict, config: StrategyConfig) -> str:
        """Create LLM prompt for trading decision.
        
        Args:
            market_analysis: Market analysis data
            config: Strategy configuration
            
        Returns:
            LLM prompt string
        """
        prompt = f"""
        You are an expert trading analyst. Analyze the following market data and make a trading decision.

        Market Data:
        - Symbol: {market_analysis['symbol']}
        - Current Price: ${market_analysis['current_price']:.2f}
        - Price Changes: {market_analysis['price_changes']}
        - Technical Indicators:
          * RSI: {market_analysis['technical_indicators']['rsi']}
          * SMA(20): {market_analysis['technical_indicators']['sma_20']}
          * EMA(20): {market_analysis['technical_indicators']['ema_20']}
          * ATR: {market_analysis['technical_indicators']['atr']}
          * Volatility: {market_analysis['technical_indicators']['volatility']}
        - Market Signals:
          * Trend: {market_analysis['market_signals'].get('trend', 'unknown')}
          * Momentum: {market_analysis['market_signals'].get('momentum', 'unknown')}
          * Volatility Regime: {market_analysis['market_signals'].get('volatility_regime', 'unknown')}

        Strategy Configuration:
        - Max Risk per Trade: {config.max_risk_per_trade:.1%}
        - Stop Loss: {config.stop_loss_pct:.1%}
        - Take Profit: {config.take_profit_pct:.1%}
        - Min Confidence: {config.min_confidence:.1%}

        Based on this analysis, provide a trading decision in the following JSON format:
        {{
            "action": "BUY" | "SELL" | "HOLD",
            "confidence": 0.0-1.0,
            "reasoning": "Brief explanation of the decision",
            "risk_score": 0.0-1.0
        }}

        Consider:
        1. Technical indicators and their signals
        2. Market trend and momentum
        3. Risk management parameters
        4. Current volatility conditions
        5. Price action and volume patterns

        Only recommend BUY or SELL if you have high confidence (>70%) and clear signals.
        """
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract decision data.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed decision data
        """
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback parsing if JSON extraction fails
        response_lower = response.lower()
        
        action = "HOLD"
        if "buy" in response_lower and "sell" not in response_lower:
            action = "BUY"
        elif "sell" in response_lower and "buy" not in response_lower:
            action = "SELL"
        
        # Extract confidence (look for numbers between 0-1 or 0-100)
        confidence = 0.5
        confidence_match = re.search(r'(?:confidence|conf):\s*(\d+(?:\.\d+)?)', response_lower)
        if confidence_match:
            conf_value = float(confidence_match.group(1))
            if conf_value > 1:
                confidence = conf_value / 100
            else:
                confidence = conf_value
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": response[:200] + "..." if len(response) > 200 else response,
            "risk_score": 0.5,  # Default risk score
        }
    
    def _create_trading_decision(
        self,
        decision_data: Dict,
        data: List[OHLCVData],
        config: StrategyConfig,
    ) -> TradingDecision:
        """Create trading decision from parsed LLM response.
        
        Args:
            decision_data: Parsed decision data
            data: Historical OHLCV data
            config: Strategy configuration
            
        Returns:
            Trading decision
        """
        current_price = float(data[-1].close)
        symbol = data[-1].symbol
        action = decision_data.get("action", "HOLD")
        confidence = decision_data.get("confidence", 0.0)
        reasoning = decision_data.get("reasoning", "No reasoning provided")
        risk_score = decision_data.get("risk_score", 0.5)
        
        # Check confidence threshold
        if confidence < config.min_confidence:
            return self._create_no_action_decision(data, f"Confidence too low: {confidence:.1%}")
        
        # Check if action is HOLD
        if action == "HOLD":
            return self._create_no_action_decision(data, reasoning)
        
        # Create buy/sell decision
        side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
        
        # Calculate position size (simplified - would need account balance in real implementation)
        account_balance = 10000.0  # Placeholder
        stop_loss_price = self.calculate_stop_loss(current_price, side.value, config.stop_loss_pct)
        take_profit_price = self.calculate_take_profit(current_price, side.value, config.take_profit_pct)
        
        quantity = self.calculate_position_size(
            account_balance,
            current_price,
            stop_loss_price,
            config.max_risk_per_trade,
        )
        
        return TradingDecision(
            action=side,
            symbol=symbol,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(current_price)),
            stop_loss=Decimal(str(stop_loss_price)),
            take_profit=Decimal(str(take_profit_price)),
            confidence=confidence,
            reasoning=reasoning,
            risk_score=risk_score,
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
            reasoning=reasoning,
            risk_score=0.0,
        )
