"""Scheduler for managing analysis intervals and timing."""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Dict, Any
import structlog

from ..core.settings import get_settings

logger = structlog.get_logger(__name__)


class SchedulerError(Exception):
    """Exception raised during scheduler operations."""
    pass


class AnalysisScheduler:
    """Scheduler for managing periodic analysis tasks."""
    
    def __init__(
        self,
        interval_seconds: int = 60,  # 1 minute default
        on_analysis_time: Optional[Callable[[datetime], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Initialize the analysis scheduler.
        
        Args:
            interval_seconds: Analysis interval in seconds
            on_analysis_time: Callback function called at analysis time
            on_error: Callback function for error handling
        """
        self.interval_seconds = interval_seconds
        self.on_analysis_time = on_analysis_time
        self.on_error = on_error
        
        self.settings = get_settings()
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Statistics
        self.analysis_count = 0
        self.last_analysis_time = None
        self.next_analysis_time = None
        self.start_time = None
        
        # Error handling
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        logger.info(
            "Initialized analysis scheduler",
            interval_seconds=interval_seconds,
        )
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.start_time = datetime.now(timezone.utc)
        self.consecutive_errors = 0
        
        # Calculate next analysis time (aligned to minute boundaries)
        self._calculate_next_analysis_time()
        
        # Start the scheduler task
        self.task = asyncio.create_task(self._scheduler_loop())
        
        logger.info(
            "Started analysis scheduler",
            next_analysis_time=self.next_analysis_time,
            interval_seconds=self.interval_seconds,
        )
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        logger.info("Stopped analysis scheduler")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        try:
            while self.running:
                current_time = datetime.now(timezone.utc)
                
                # Check if it's time for analysis
                if self.next_analysis_time and current_time >= self.next_analysis_time:
                    await self._trigger_analysis(current_time)
                    self._calculate_next_analysis_time()
                
                # Sleep for a short interval to avoid busy waiting
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            raise
        except Exception as e:
            logger.error("Unexpected error in scheduler loop", error=str(e))
            if self.on_error:
                self.on_error(e)
    
    async def _trigger_analysis(self, analysis_time: datetime) -> None:
        """Trigger analysis at the scheduled time.
        
        Args:
            analysis_time: Time when analysis is triggered
        """
        try:
            self.analysis_count += 1
            self.last_analysis_time = analysis_time
            self.consecutive_errors = 0  # Reset error counter on success
            
            logger.debug(
                "Triggering analysis",
                analysis_count=self.analysis_count,
                analysis_time=analysis_time,
            )
            
            if self.on_analysis_time:
                await self._safe_callback(self.on_analysis_time, analysis_time)
            
        except Exception as e:
            self.consecutive_errors += 1
            logger.error(
                "Error during analysis trigger",
                error=str(e),
                consecutive_errors=self.consecutive_errors,
            )
            
            if self.on_error:
                self.on_error(e)
            
            # Stop scheduler if too many consecutive errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.error(
                    "Too many consecutive errors, stopping scheduler",
                    consecutive_errors=self.consecutive_errors,
                )
                await self.stop()
    
    async def _safe_callback(self, callback: Callable, *args, **kwargs) -> None:
        """Safely execute a callback function.
        
        Args:
            callback: Callback function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error("Error in callback function", error=str(e))
            raise
    
    def _calculate_next_analysis_time(self) -> None:
        """Calculate the next analysis time."""
        current_time = datetime.now(timezone.utc)
        
        if self.interval_seconds >= 60:
            # For intervals >= 1 minute, align to minute boundaries
            next_minute = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
            self.next_analysis_time = next_minute
        else:
            # For shorter intervals, use simple addition
            self.next_analysis_time = current_time + timedelta(seconds=self.interval_seconds)
    
    def set_interval(self, interval_seconds: int) -> None:
        """Update the analysis interval.
        
        Args:
            interval_seconds: New interval in seconds
        """
        if interval_seconds <= 0:
            raise SchedulerError("Interval must be positive")
        
        old_interval = self.interval_seconds
        self.interval_seconds = interval_seconds
        
        # Recalculate next analysis time if scheduler is running
        if self.running:
            self._calculate_next_analysis_time()
        
        logger.info(
            "Updated analysis interval",
            old_interval=old_interval,
            new_interval=interval_seconds,
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information.
        
        Returns:
            Dictionary with scheduler status
        """
        return {
            "running": self.running,
            "interval_seconds": self.interval_seconds,
            "analysis_count": self.analysis_count,
            "last_analysis_time": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "next_analysis_time": self.next_analysis_time.isoformat() if self.next_analysis_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "consecutive_errors": self.consecutive_errors,
            "max_consecutive_errors": self.max_consecutive_errors,
        }
    
    def get_time_until_next_analysis(self) -> Optional[float]:
        """Get seconds until next analysis.
        
        Returns:
            Seconds until next analysis or None if not running
        """
        if not self.running or not self.next_analysis_time:
            return None
        
        current_time = datetime.now(timezone.utc)
        time_diff = (self.next_analysis_time - current_time).total_seconds()
        return max(0, time_diff)


class TradingTimeManager:
    """Manager for trading time windows and market hours."""
    
    def __init__(self):
        """Initialize the trading time manager."""
        self.market_open = True  # Crypto markets are 24/7
        self.trading_windows: Dict[str, Dict[str, Any]] = {}
    
    def is_market_open(self) -> bool:
        """Check if market is currently open.
        
        Returns:
            True if market is open
        """
        # For crypto markets, always open
        return self.market_open
    
    def add_trading_window(
        self,
        name: str,
        start_time: str,  # Format: "HH:MM"
        end_time: str,    # Format: "HH:MM"
        timezone_str: str = "UTC",
    ) -> None:
        """Add a trading time window.
        
        Args:
            name: Name of the trading window
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            timezone_str: Timezone string
        """
        self.trading_windows[name] = {
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone_str,
        }
        
        logger.info(
            "Added trading window",
            name=name,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone_str,
        )
    
    def is_in_trading_window(self, window_name: str) -> bool:
        """Check if current time is within a trading window.
        
        Args:
            window_name: Name of the trading window
            
        Returns:
            True if within trading window
        """
        if window_name not in self.trading_windows:
            return False
        
        # For crypto markets, always in trading window
        return True
    
    def get_next_trading_window_start(self, window_name: str) -> Optional[datetime]:
        """Get the next start time for a trading window.
        
        Args:
            window_name: Name of the trading window
            
        Returns:
            Next start time or None if not found
        """
        if window_name not in self.trading_windows:
            return None
        
        # For crypto markets, always available
        return datetime.now(timezone.utc)
