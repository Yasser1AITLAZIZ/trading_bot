"""Feature engineering module for calculating technical indicators."""

import math
from typing import List, Optional

import numpy as np
import pandas as pd
import structlog

from ..core.types import OHLCVData, TechnicalIndicators
from ..core.utils import safe_divide

logger = structlog.get_logger(__name__)


class FeatureEngineeringError(Exception):
    """Exception raised during feature engineering."""
    pass


class TechnicalIndicatorCalculator:
    """Calculator for technical indicators from OHLCV data."""
    
    def __init__(self, rsi_period: int = 14, sma_period: int = 20, ema_period: int = 20, atr_period: int = 14):
        """Initialize the technical indicator calculator.
        
        Args:
            rsi_period: Period for RSI calculation
            sma_period: Period for SMA calculation
            ema_period: Period for EMA calculation
            atr_period: Period for ATR calculation
        """
        self.rsi_period = rsi_period
        self.sma_period = sma_period
        self.ema_period = ema_period
        self.atr_period = atr_period
    
    def calculate_all_indicators(self, data: List[OHLCVData]) -> TechnicalIndicators:
        """Calculate all technical indicators from OHLCV data.
        
        Args:
            data: List of OHLCV data points
            
        Returns:
            Technical indicators object
        """
        if len(data) < max(self.rsi_period, self.sma_period, self.ema_period, self.atr_period):
            raise FeatureEngineeringError(
                f"Insufficient data points. Need at least {max(self.rsi_period, self.sma_period, self.ema_period, self.atr_period)} points"
            )
        
        # Convert to pandas DataFrame for easier calculations
        df = self._to_dataframe(data)
        
        # Calculate indicators
        rsi = self._calculate_rsi(df)
        sma_20 = self._calculate_sma(df, self.sma_period)
        ema_20 = self._calculate_ema(df, self.ema_period)
        atr = self._calculate_atr(df, self.atr_period)
        volatility = self._calculate_volatility(df)
        log_returns = self._calculate_log_returns(df)
        
        return TechnicalIndicators(
            rsi=rsi,
            sma_20=sma_20,
            ema_20=ema_20,
            atr=atr,
            volatility=volatility,
            log_returns=log_returns,
        )
    
    def _to_dataframe(self, data: List[OHLCVData]) -> pd.DataFrame:
        """Convert OHLCV data to pandas DataFrame.
        
        Args:
            data: List of OHLCV data points
            
        Returns:
            DataFrame with OHLCV data
        """
        df_data = []
        for point in data:
            df_data.append({
                "timestamp": point.timestamp,
                "open": float(point.open),
                "high": float(point.high),
                "low": float(point.low),
                "close": float(point.close),
                "volume": float(point.volume),
            })
        
        return pd.DataFrame(df_data)
    
    def _calculate_rsi(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate Relative Strength Index (RSI).
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            RSI value or None if insufficient data
        """
        if len(df) < self.rsi_period + 1:
            return None
        
        # Calculate price changes
        df["price_change"] = df["close"].diff()
        
        # Separate gains and losses
        df["gain"] = df["price_change"].where(df["price_change"] > 0, 0)
        df["loss"] = -df["price_change"].where(df["price_change"] < 0, 0)
        
        # Calculate average gains and losses
        avg_gain = df["gain"].rolling(window=self.rsi_period).mean().iloc[-1]
        avg_loss = df["loss"].rolling(window=self.rsi_period).mean().iloc[-1]
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_sma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate Simple Moving Average (SMA).
        
        Args:
            df: DataFrame with OHLCV data
            period: SMA period
            
        Returns:
            SMA value or None if insufficient data
        """
        if len(df) < period:
            return None
        
        sma = df["close"].rolling(window=period).mean().iloc[-1]
        return round(float(sma), 2)
    
    def _calculate_ema(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate Exponential Moving Average (EMA).
        
        Args:
            df: DataFrame with OHLCV data
            period: EMA period
            
        Returns:
            EMA value or None if insufficient data
        """
        if len(df) < period:
            return None
        
        ema = df["close"].ewm(span=period).mean().iloc[-1]
        return round(float(ema), 2)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate Average True Range (ATR).
        
        Args:
            df: DataFrame with OHLCV data
            period: ATR period
            
        Returns:
            ATR value or None if insufficient data
        """
        if len(df) < period + 1:
            return None
        
        # Calculate True Range
        df["high_low"] = df["high"] - df["low"]
        df["high_close_prev"] = abs(df["high"] - df["close"].shift(1))
        df["low_close_prev"] = abs(df["low"] - df["close"].shift(1))
        
        df["true_range"] = df[["high_low", "high_close_prev", "low_close_prev"]].max(axis=1)
        
        # Calculate ATR as SMA of True Range
        atr = df["true_range"].rolling(window=period).mean().iloc[-1]
        
        return round(float(atr), 2)
    
    def _calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> Optional[float]:
        """Calculate price volatility (standard deviation of returns).
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for volatility calculation
            
        Returns:
            Volatility value or None if insufficient data
        """
        if len(df) < period + 1:
            return None
        
        # Calculate returns
        df["returns"] = df["close"].pct_change()
        
        # Calculate volatility as standard deviation of returns
        volatility = df["returns"].rolling(window=period).std().iloc[-1]
        
        return round(float(volatility), 4)
    
    def _calculate_log_returns(self, df: pd.DataFrame) -> List[float]:
        """Calculate logarithmic returns.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of log returns
        """
        if len(df) < 2:
            return []
        
        log_returns = []
        for i in range(1, len(df)):
            current_price = df["close"].iloc[i]
            previous_price = df["close"].iloc[i-1]
            
            if previous_price > 0:
                log_return = math.log(current_price / previous_price)
                log_returns.append(round(log_return, 6))
        
        return log_returns


class MarketSignalGenerator:
    """Generator for market signals based on technical indicators."""
    
    def __init__(self):
        """Initialize the market signal generator."""
        pass
    
    def generate_signals(
        self,
        data: List[OHLCVData],
        indicators: TechnicalIndicators,
    ) -> dict:
        """Generate market signals from data and indicators.
        
        Args:
            data: List of OHLCV data points
            indicators: Technical indicators
            
        Returns:
            Dictionary containing market signals
        """
        if not data:
            raise FeatureEngineeringError("No data provided for signal generation")
        
        current_price = float(data[-1].close)
        
        # Determine trend
        trend = self._determine_trend(data, indicators)
        
        # Determine momentum
        momentum = self._determine_momentum(indicators)
        
        # Determine volatility regime
        volatility_regime = self._determine_volatility_regime(indicators)
        
        # Calculate support and resistance levels
        support_resistance = self._calculate_support_resistance(data)
        
        return {
            "trend": trend,
            "momentum": momentum,
            "volatility_regime": volatility_regime,
            "support_resistance": support_resistance,
        }
    
    def _determine_trend(self, data: List[OHLCVData], indicators: TechnicalIndicators) -> str:
        """Determine market trend.
        
        Args:
            data: List of OHLCV data points
            indicators: Technical indicators
            
        Returns:
            Trend classification (bullish/bearish/sideways)
        """
        current_price = float(data[-1].close)
        
        # Use SMA and EMA for trend determination
        if indicators.sma_20 and indicators.ema_20:
            if current_price > indicators.sma_20 and current_price > indicators.ema_20:
                if indicators.sma_20 > indicators.ema_20:
                    return "bullish"
                else:
                    return "sideways"
            elif current_price < indicators.sma_20 and current_price < indicators.ema_20:
                if indicators.sma_20 < indicators.ema_20:
                    return "bearish"
                else:
                    return "sideways"
            else:
                return "sideways"
        
        # Fallback: simple price comparison
        if len(data) >= 20:
            price_20_ago = float(data[-20].close)
            if current_price > price_20_ago * 1.02:  # 2% higher
                return "bullish"
            elif current_price < price_20_ago * 0.98:  # 2% lower
                return "bearish"
        
        return "sideways"
    
    def _determine_momentum(self, indicators: TechnicalIndicators) -> str:
        """Determine market momentum.
        
        Args:
            indicators: Technical indicators
            
        Returns:
            Momentum classification (strong/weak/neutral)
        """
        if indicators.rsi is None:
            return "neutral"
        
        if indicators.rsi > 70:
            return "strong"  # Overbought
        elif indicators.rsi < 30:
            return "strong"  # Oversold
        elif indicators.rsi > 60 or indicators.rsi < 40:
            return "weak"
        else:
            return "neutral"
    
    def _determine_volatility_regime(self, indicators: TechnicalIndicators) -> str:
        """Determine volatility regime.
        
        Args:
            indicators: Technical indicators
            
        Returns:
            Volatility regime (high/low/normal)
        """
        if indicators.volatility is None:
            return "normal"
        
        # Simple volatility classification
        if indicators.volatility > 0.05:  # 5% volatility
            return "high"
        elif indicators.volatility < 0.01:  # 1% volatility
            return "low"
        else:
            return "normal"
    
    def _calculate_support_resistance(self, data: List[OHLCVData], lookback: int = 20) -> dict:
        """Calculate support and resistance levels.
        
        Args:
            data: List of OHLCV data points
            lookback: Number of periods to look back
            
        Returns:
            Dictionary with support and resistance levels
        """
        if len(data) < lookback:
            return {}
        
        recent_data = data[-lookback:]
        highs = [float(point.high) for point in recent_data]
        lows = [float(point.low) for point in recent_data]
        
        # Simple support and resistance calculation
        resistance = max(highs)
        support = min(lows)
        
        # Calculate additional levels
        price_range = resistance - support
        resistance_2 = resistance - (price_range * 0.5)
        support_2 = support + (price_range * 0.5)
        
        return {
            "resistance": round(resistance, 2),
            "resistance_2": round(resistance_2, 2),
            "support": round(support, 2),
            "support_2": round(support_2, 2),
        }
