"""Autonomous trading bot with real-time streaming and continuous analysis."""

import asyncio
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .core.settings import get_settings
from .core.types import TradingMode
from .data.ingestion import DataIngestionService
from .streaming.binance_ws import BinanceWebSocket
from .streaming.data_buffer import DataBuffer
from .trading.trading_loop import AutonomousTradingLoop
from .api.server import create_app
from .monitoring.alerts import AlertManager, AlertLevel, AlertType
from .communication.telegram_bot import TelegramBot
from .communication.notification_manager import NotificationManager, NotificationChannel

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
console = Console()
app = typer.Typer(help="Autonomous Trading Bot - Real-time trading with LLM analysis")


class AutonomousTradingBot:
    """Main autonomous trading bot class."""
    
    def __init__(
        self,
        symbol: str,
        data_file: str,
        strategy: str = "llm",
        llm_provider: str = "openai",
        mode: str = "paper",
    ):
        """Initialize the autonomous trading bot.
        
        Args:
            symbol: Trading symbol
            data_file: Path to historical data file
            strategy: Trading strategy name
            llm_provider: LLM provider
            mode: Trading mode (paper/testnet/live)
        """
        self.symbol = symbol
        self.data_file = data_file
        self.strategy = strategy
        self.llm_provider = llm_provider
        self.mode = TradingMode(mode)
        
        self.settings = get_settings()
        self.running = False
        
        # Components
        self.trading_loop: Optional[AutonomousTradingLoop] = None
        self.websocket: Optional[BinanceWebSocket] = None
        self.api_server_task: Optional[asyncio.Task] = None
        self.telegram_bot: Optional[TelegramBot] = None
        self.notification_manager: Optional[NotificationManager] = None
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.total_decisions = 0
        self.total_orders = 0
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            console.print("\n[yellow]⚠️  Received shutdown signal, stopping bot...[/yellow]")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> None:
        """Start the autonomous trading bot."""
        try:
            console.print(Panel.fit(
                f"""
[bold]🤖 Autonomous Trading Bot Starting[/bold]

Symbol: {self.symbol}
Strategy: {self.strategy}
LLM Provider: {self.llm_provider}
Mode: {self.mode.value}
Data File: {self.data_file}
                """,
                title="Configuration",
                border_style="blue"
            ))
            
            # Load historical data
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task1 = progress.add_task("Loading historical data...", total=None)
                
                data_service = DataIngestionService()
                historical_data = data_service.load_from_file(self.data_file, self.symbol)
                
                # Validate data quality
                quality_metrics = data_service.validate_data_quality(historical_data)
                if not quality_metrics["valid"]:
                    console.print(f"[red]❌ Data quality issues: {', '.join(quality_metrics['issues'])}[/red]")
                    raise typer.Exit(1)
                
                progress.update(task1, description="✅ Historical data loaded")
                
                # Initialize trading loop
                task2 = progress.add_task("Initializing trading loop...", total=None)
                
                self.trading_loop = AutonomousTradingLoop(
                    symbol=self.symbol,
                    initial_data=historical_data,
                    strategy_name=self.strategy,
                    llm_provider=self.llm_provider,
                    on_decision=self._on_trading_decision,
                    on_error=self._on_error,
                )
                
                progress.update(task2, description="✅ Trading loop initialized")
                
                # Initialize WebSocket
                task3 = progress.add_task("Connecting to Binance WebSocket...", total=None)
                
                self.websocket = BinanceWebSocket(
                    symbol=self.symbol,
                    timeframe="1m",
                    on_new_candle=self._on_new_candle,
                    on_error=self._on_websocket_error,
                )
                
                progress.update(task3, description="✅ WebSocket connected")
            
            # Start components
            self.running = True
            self.start_time = datetime.now(timezone.utc)
            
            # Start trading loop
            await self.trading_loop.start()
            
            # Start WebSocket streaming
            await self.websocket.connect()
            await self.websocket.start_streaming()
            
            # Start API server for Next.js UI
            import uvicorn
            app = create_app(trading_loop=self.trading_loop)
            config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
            server = uvicorn.Server(config)
            self.api_server_task = asyncio.create_task(server.serve())
            
            # Initialize notification manager
            self.notification_manager = NotificationManager()
            
            # Start Telegram bot if token is provided
            telegram_token = self.settings.llm.telegram_bot_token
            if telegram_token:
                self.telegram_bot = TelegramBot(
                    bot_token=telegram_token,
                    trading_loop=self.trading_loop,
                    alert_manager=self.trading_loop.alert_manager if hasattr(self.trading_loop, 'alert_manager') else None,
                )
                await self.telegram_bot.start()
                console.print("[green]📱 Telegram bot started successfully![/green]")
            
            console.print("[green]✅ Autonomous trading bot started successfully![/green]")
            console.print("[blue]📊 Bot is now running autonomously. Press Ctrl+C to stop.[/blue]")
            console.print(f"[cyan]🌐 Web dashboard available at: http://localhost:8000[/cyan]")
            if telegram_token:
                console.print("[cyan]📱 Telegram bot is active for remote control[/cyan]")
            
            # Display status periodically
            await self._status_display_loop()
        
        except Exception as e:
            logger.error("Failed to start autonomous trading bot", error=str(e))
            console.print(f"[red]❌ Error starting bot: {e}[/red]")
            await self.stop()
            raise typer.Exit(1)
    
    async def stop(self) -> None:
        """Stop the autonomous trading bot."""
        if not self.running:
            return
        
        console.print("[yellow]🛑 Stopping autonomous trading bot...[/yellow]")
        
        self.running = False
        
        try:
            # Stop Telegram bot
            if self.telegram_bot:
                await self.telegram_bot.stop()
            
            # Stop API server
            if self.api_server_task:
                self.api_server_task.cancel()
                try:
                    await self.api_server_task
                except asyncio.CancelledError:
                    pass
            
            # Stop WebSocket
            if self.websocket:
                await self.websocket.disconnect()
            
            # Stop trading loop
            if self.trading_loop:
                await self.trading_loop.stop()
            
            # Display final statistics
            self._display_final_statistics()
            
            console.print("[green]✅ Autonomous trading bot stopped successfully![/green]")
        
        except Exception as e:
            logger.error("Error stopping autonomous trading bot", error=str(e))
            console.print(f"[red]❌ Error stopping bot: {e}[/red]")
    
    async def _status_display_loop(self) -> None:
        """Display status information periodically."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                if self.trading_loop:
                    status = self.trading_loop.get_status()
                    self._display_status(status)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in status display loop", error=str(e))
    
    def _display_status(self, status: dict) -> None:
        """Display current status."""
        table = Table(title="🤖 Autonomous Trading Bot Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Symbol", status.get("symbol", "N/A"))
        table.add_row("Running", "✅ Yes" if status.get("running") else "❌ No")
        table.add_row("Strategy", status.get("strategy", "N/A"))
        table.add_row("LLM Provider", status.get("llm_provider", "N/A"))
        table.add_row("Analysis Count", str(status.get("analysis_count", 0)))
        table.add_row("Decision Count", str(status.get("decision_count", 0)))
        table.add_row("Order Count", str(status.get("order_count", 0)))
        
        buffer_info = status.get("buffer_info", {})
        table.add_row("Buffer Size", f"{buffer_info.get('current_size', 0)}/{buffer_info.get('max_size', 0)}")
        table.add_row("Last Update", buffer_info.get("last_update", "N/A"))
        
        scheduler_status = status.get("scheduler_status", {})
        table.add_row("Next Analysis", scheduler_status.get("next_analysis_time", "N/A"))
        
        order_status = status.get("order_manager_status", {})
        table.add_row("Open Orders", f"{order_status.get('open_orders', 0)}/{order_status.get('max_orders', 0)}")
        
        console.print(table)
    
    def _display_final_statistics(self) -> None:
        """Display final statistics."""
        if not self.start_time:
            return
        
        duration = datetime.now(timezone.utc) - self.start_time
        
        stats_panel = Panel.fit(
            f"""
[bold]📊 Final Statistics[/bold]

Duration: {duration}
Total Decisions: {self.total_decisions}
Total Orders: {self.total_orders}

Strategy: {self.strategy}
LLM Provider: {self.llm_provider}
Mode: {self.mode.value}
            """,
            title="Session Summary",
            border_style="green"
        )
        
        console.print(stats_panel)
    
    def _on_trading_decision(self, decision) -> None:
        """Handle trading decision callback."""
        self.total_decisions += 1
        
        action_emoji = "🟢" if decision.action.value == "BUY" else "🔴" if decision.action.value == "SELL" else "⏸️"
        
        console.print(f"""
{action_emoji} [bold]Trading Decision[/bold]
Action: {decision.action.value if decision.action else 'HOLD'}
Symbol: {decision.symbol}
Quantity: {decision.quantity}
Price: ${decision.price}
Confidence: {decision.confidence:.1%}
Risk Score: {decision.risk_score:.1%}

Reasoning: {decision.reasoning}
        """)
        
        # Send notification if available
        if self.notification_manager:
            asyncio.create_task(
                self.notification_manager.send_trading_decision_notification(decision)
            )
        
        # Send to Telegram bot if available
        if self.telegram_bot:
            asyncio.create_task(
                self.telegram_bot.send_trading_decision(decision)
            )
    
    def _on_new_candle(self, candle) -> None:
        """Handle new candle data."""
        if self.trading_loop:
            self.trading_loop.add_new_candle(candle)
    
    def _on_error(self, error: Exception) -> None:
        """Handle error callback."""
        console.print(f"[red]❌ Error: {error}[/red]")
        logger.error("Trading loop error", error=str(error))
        
        # Send error notification if available
        if self.notification_manager:
            asyncio.create_task(
                self.notification_manager.send_system_notification(
                    title="Trading Bot Error",
                    message=f"An error occurred: {str(error)}",
                    priority=NotificationPriority.HIGH
                )
            )
    
    def _on_websocket_error(self, error: Exception) -> None:
        """Handle WebSocket error callback."""
        console.print(f"[red]❌ WebSocket Error: {error}[/red]")
        logger.error("WebSocket error", error=str(error))


@app.command()
def start(
    symbol: str = typer.Option("BTCUSDT", "--symbol", "-s", help="Trading symbol"),
    data_file: str = typer.Option(..., "--data", "-d", help="Path to historical data file"),
    strategy: str = typer.Option("llm", "--strategy", help="Trading strategy"),
    llm_provider: str = typer.Option("openai", "--llm-provider", help="LLM provider"),
    mode: str = typer.Option("paper", "--mode", help="Trading mode (paper/testnet/live)"),
):
    """Start the autonomous trading bot."""
    
    # Validate mode
    if mode == "live":
        console.print("[red]⚠️  LIVE TRADING MODE - This will execute real trades![/red]")
        if not typer.confirm("Are you sure you want to continue?"):
            console.print("Aborted.")
            raise typer.Abort()
    
    # Validate data file
    if not Path(data_file).exists():
        console.print(f"[red]❌ Data file not found: {data_file}[/red]")
        raise typer.Exit(1)
    
    # Create and start bot
    bot = AutonomousTradingBot(
        symbol=symbol,
        data_file=data_file,
        strategy=strategy,
        llm_provider=llm_provider,
        mode=mode,
    )
    
    # Run the bot
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    symbol: str = typer.Option("BTCUSDT", "--symbol", "-s", help="Trading symbol"),
):
    """Check the status of the autonomous trading bot."""
    
    # This would connect to a running bot instance
    # For now, just show configuration
    settings = get_settings()
    
    status_panel = Panel.fit(
        f"""
[bold]🤖 Autonomous Trading Bot Status[/bold]

Symbol: {symbol}
Configuration:
- Analysis Interval: {settings.streaming.analysis_interval}s
- Max Orders: {settings.trading.max_concurrent_orders}
- Buffer Size: {settings.streaming.buffer_max_size}
- Mode: {settings.binance.mode}

Note: This command will be enhanced to connect to running bot instances.
        """,
        title="Bot Status",
        border_style="blue"
    )
    
    console.print(status_panel)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
