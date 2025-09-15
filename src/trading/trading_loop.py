"""Main trading loop for autonomous trading operations."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Callable
import structlog

from ..core.settings import get_settings
from ..core.types import OHLCVData, TradingDecision, TradingMode
from ..data.features import TechnicalIndicatorCalculator, MarketSignalGenerator
from ..llm.factory import get_llm_client
from ..strategy.registry import get_strategy
from ..streaming.data_buffer import DataBuffer
from ..streaming.scheduler import AnalysisScheduler
from .order_manager import OrderManager
from .state_manager import StateManager

logger = structlog.get_logger(__name__)


class TradingLoopError(Exception):
    """Exception raised during trading loop operations."""
    pass


class AutonomousTradingLoop:
    """Main trading loop for autonomous trading operations."""
    
    def __init__(
        self,
        symbol: str,
        initial_data: List[OHLCVData],
        strategy_name: str = "llm",
        llm_provider: str = "openai",
        on_decision: Optional[Callable[[TradingDecision], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Initialize the autonomous trading loop.
        
        Args:
            symbol: Trading symbol
            initial_data: Initial historical data (8 hours)
            strategy_name: Name of trading strategy
            llm_provider: LLM provider to use
            on_decision: Callback for trading decisions
            on_error: Callback for error handling
        """
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.llm_provider = llm_provider
        self.on_decision = on_decision
        self.on_error = on_error
        
        self.settings = get_settings()
        self.running = False
        
        # Initialize components
        self.data_buffer = DataBuffer(
            initial_data=initial_data,
            max_size=self.settings.streaming.buffer_max_size,
            on_buffer_updated=self._on_buffer_updated,
        )
        
        self.scheduler = AnalysisScheduler(
            interval_seconds=self.settings.streaming.analysis_interval,
            on_analysis_time=self._on_analysis_time,
            on_error=self._on_scheduler_error,
        )
        
        self.order_manager = OrderManager(
            max_orders=self.settings.trading.max_concurrent_orders,
            symbol=symbol,
        )
        
        self.state_manager = StateManager(symbol)
        
        # Technical analysis components
        self.indicator_calculator = TechnicalIndicatorCalculator()
        self.signal_generator = MarketSignalGenerator()
        
        # Strategy
        self.strategy = None
        self._initialize_strategy()
        
        # Statistics
        self.analysis_count = 0
        self.decision_count = 0
        self.order_count = 0
        self.start_time = None
        
        logger.info(
            "Initialized autonomous trading loop",
            symbol=symbol,
            strategy=strategy_name,
            llm_provider=llm_provider,
            initial_data_points=len(initial_data),
        )
    
    def _initialize_strategy(self) -> None:
        """Initialize the trading strategy."""
        try:
            self.strategy = get_strategy(
                name=self.strategy_name,
                llm_provider=self.llm_provider,
            )
            
            if not self.strategy:
                raise TradingLoopError(f"Failed to initialize strategy: {self.strategy_name}")
            
            logger.info("Initialized trading strategy", strategy=self.strategy_name)
        
        except Exception as e:
            logger.error("Failed to initialize strategy", error=str(e))
            raise TradingLoopError(f"Strategy initialization failed: {e}")
    
    async def start(self) -> None:
        """Start the autonomous trading loop."""
        if self.running:
            logger.warning("Trading loop is already running")
            return
        
        try:
            self.running = True
            self.start_time = datetime.now(timezone.utc)
            
            # Load previous state if available
            await self.state_manager.load_state()
            
            # Start scheduler
            await self.scheduler.start()
            
            # Start order manager
            await self.order_manager.start()
            
            logger.info("Started autonomous trading loop", symbol=self.symbol)
            
            # Main loop
            await self._main_loop()
        
        except Exception as e:
            logger.error("Error starting trading loop", error=str(e))
            await self.stop()
            raise TradingLoopError(f"Failed to start trading loop: {e}")
    
    async def stop(self) -> None:
        """Stop the autonomous trading loop."""
        if not self.running:
            return
        
        self.running = False
        
        try:
            # Stop scheduler
            await self.scheduler.stop()
            
            # Stop order manager
            await self.order_manager.stop()
            
            # Save current state
            await self.state_manager.save_state()
            
            logger.info("Stopped autonomous trading loop", symbol=self.symbol)
        
        except Exception as e:
            logger.error("Error stopping trading loop", error=str(e))
    
    async def _main_loop(self) -> None:
        """Main trading loop."""
        try:
            while self.running:
                # Check for any pending tasks
                await self._check_pending_tasks()
                
                # Sleep briefly to avoid busy waiting
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")
            raise
        except Exception as e:
            logger.error("Unexpected error in trading loop", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def _check_pending_tasks(self) -> None:
        """Check for pending tasks and handle them."""
        try:
            # Check order status
            await self.order_manager.check_open_orders()
            
            # Update state
            await self.state_manager.update_state()
        
        except Exception as e:
            logger.error("Error checking pending tasks", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def _on_buffer_updated(self, data: List[OHLCVData]) -> None:
        """Handle buffer update events.
        
        Args:
            data: Updated data buffer
        """
        try:
            logger.debug(
                "Buffer updated",
                symbol=self.symbol,
                data_points=len(data),
                latest_time=data[-1].timestamp if data else None,
            )
        
        except Exception as e:
            logger.error("Error handling buffer update", error=str(e))
    
    async def _on_analysis_time(self, analysis_time: datetime) -> None:
        """Handle scheduled analysis time.
        
        Args:
            analysis_time: Time when analysis is triggered
        """
        try:
            self.analysis_count += 1
            
            logger.info(
                "Starting analysis",
                symbol=self.symbol,
                analysis_count=self.analysis_count,
                analysis_time=analysis_time,
            )
            
            # Get current data
            current_data = self.data_buffer.get_full_history()
            
            if len(current_data) < 20:  # Minimum data required
                logger.warning("Insufficient data for analysis", data_points=len(current_data))
                return
            
            # Calculate technical indicators
            indicators = self.indicator_calculator.calculate_all_indicators(current_data)
            
            # Generate market signals
            signals = self.signal_generator.generate_signals(current_data, indicators)
            
            # Make trading decision
            decision = await self._make_trading_decision(current_data, indicators, signals)
            
            if decision:
                await self._handle_trading_decision(decision)
        
        except Exception as e:
            logger.error("Error during analysis", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def _make_trading_decision(
        self,
        data: List[OHLCVData],
        indicators,
        signals: Dict[str, str],
    ) -> Optional[TradingDecision]:
        """Make a trading decision using the strategy.
        
        Args:
            data: Current market data
            indicators: Technical indicators
            signals: Market signals
            
        Returns:
            Trading decision or None
        """
        try:
            if not self.strategy:
                logger.error("No strategy available for decision making")
                return None
            
            # Create strategy configuration
            from ..core.types import StrategyConfig
            config = StrategyConfig(
                name=self.strategy_name,
                description=f"Autonomous trading for {self.symbol}",
                max_risk_per_trade=self.settings.binance.max_risk_per_trade,
                min_confidence=0.7,
            )
            
            # Make decision
            decision = self.strategy.decide(data, indicators, signals, config)
            
            self.decision_count += 1
            
            logger.info(
                "Trading decision made",
                symbol=self.symbol,
                action=decision.action.value if decision.action else "HOLD",
                confidence=decision.confidence,
                reasoning=decision.reasoning[:100] + "..." if len(decision.reasoning) > 100 else decision.reasoning,
            )
            
            return decision
        
        except Exception as e:
            logger.error("Error making trading decision", error=str(e))
            return None
    
    async def _handle_trading_decision(self, decision: TradingDecision) -> None:
        """Handle a trading decision.
        
        Args:
            decision: Trading decision to handle
        """
        try:
            # Notify callback
            if self.on_decision:
                self.on_decision(decision)
            
            # Execute decision if not HOLD
            if decision.quantity > 0:
                success = await self.order_manager.execute_decision(decision)
                
                if success:
                    self.order_count += 1
                    logger.info(
                        "Order executed successfully",
                        symbol=self.symbol,
                        action=decision.action.value,
                        quantity=decision.quantity,
                    )
                else:
                    logger.warning(
                        "Failed to execute order",
                        symbol=self.symbol,
                        action=decision.action.value,
                    )
            
            # Update state
            await self.state_manager.record_decision(decision)
        
        except Exception as e:
            logger.error("Error handling trading decision", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def _on_scheduler_error(self, error: Exception) -> None:
        """Handle scheduler errors.
        
        Args:
            error: Scheduler error
        """
        logger.error("Scheduler error", error=str(e))
        if self.on_error:
            self.on_error(error)
    
    def add_new_candle(self, candle: OHLCVData) -> None:
        """Add a new candle to the data buffer.
        
        Args:
            candle: New OHLCV data point
        """
        try:
            self.data_buffer.add_new_candle(candle)
        except Exception as e:
            logger.error("Error adding new candle", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    def get_status(self) -> Dict[str, any]:
        """Get trading loop status.
        
        Returns:
            Dictionary with trading loop status
        """
        return {
            "symbol": self.symbol,
            "running": self.running,
            "strategy": self.strategy_name,
            "llm_provider": self.llm_provider,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "analysis_count": self.analysis_count,
            "decision_count": self.decision_count,
            "order_count": self.order_count,
            "buffer_info": self.data_buffer.get_buffer_info(),
            "scheduler_status": self.scheduler.get_status(),
            "order_manager_status": self.order_manager.get_status(),
        }
    
    def update_config(self, **kwargs) -> None:
        """Update trading loop configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        try:
            if "analysis_interval" in kwargs:
                self.scheduler.set_interval(kwargs["analysis_interval"])
            
            if "max_orders" in kwargs:
                self.order_manager.set_max_orders(kwargs["max_orders"])
            
            logger.info("Updated trading loop configuration", updates=kwargs)
        
        except Exception as e:
            logger.error("Error updating configuration", error=str(e))
            if self.on_error:
                self.on_error(e)
