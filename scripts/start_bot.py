#!/usr/bin/env python3
"""Production startup script for the trading bot."""

import asyncio
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import structlog
import typer
from rich.console import Console
from rich.panel import Panel

from src.autonomous_trading import AutonomousTradingBot

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
app = typer.Typer(help="Production Bot Starter - Start the trading bot in production mode")


class ProductionBotManager:
    """Manager for production bot operations."""
    
    def __init__(self):
        """Initialize the production bot manager."""
        self.bot = None
        self.running = False
        self.start_time = None
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_delay = 30  # seconds
    
    async def start_bot(
        self,
        symbol: str,
        data_file: str,
        strategy: str = "llm",
        llm_provider: str = "openai",
        mode: str = "paper",
    ) -> None:
        """Start the trading bot with production settings.
        
        Args:
            symbol: Trading symbol
            data_file: Path to historical data file
            strategy: Trading strategy
            llm_provider: LLM provider
            mode: Trading mode
        """
        self.start_time = datetime.now(timezone.utc)
        
        console.print(Panel.fit(
            f"""
[bold]🚀 Starting Production Trading Bot[/bold]

Symbol: {symbol}
Strategy: {strategy}
LLM Provider: {llm_provider}
Mode: {mode}
Data File: {data_file}

[bold]Production Features:[/bold]
• Automatic restart on failure
• Health monitoring
• Graceful shutdown handling
• Comprehensive logging
• Web dashboard: http://localhost:8000
• Telegram bot (if configured)
            """,
            title="Production Startup",
            border_style="green"
        ))
        
        # Validate data file
        if not Path(data_file).exists():
            console.print(f"[red]❌ Data file not found: {data_file}[/red]")
            raise typer.Exit(1)
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Start bot with restart logic
        await self._start_with_restart(symbol, data_file, strategy, llm_provider, mode)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            console.print(f"\n[yellow]⚠️  Received signal {signum}, initiating graceful shutdown...[/yellow]")
            asyncio.create_task(self._graceful_shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _start_with_restart(
        self,
        symbol: str,
        data_file: str,
        strategy: str,
        llm_provider: str,
        mode: str,
    ) -> None:
        """Start bot with automatic restart on failure."""
        while self.restart_count < self.max_restarts and not self.running:
            try:
                console.print(f"[blue]🔄 Starting bot (attempt {self.restart_count + 1}/{self.max_restarts})[/blue]")
                
                # Create and start bot
                self.bot = AutonomousTradingBot(
                    symbol=symbol,
                    data_file=data_file,
                    strategy=strategy,
                    llm_provider=llm_provider,
                    mode=mode,
                )
                
                self.running = True
                await self.bot.start()
                
                # If we reach here, bot stopped normally
                console.print("[green]✅ Bot stopped normally[/green]")
                break
            
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️  Bot interrupted by user[/yellow]")
                break
            
            except Exception as e:
                self.restart_count += 1
                logger.error("Bot crashed", error=str(e), restart_count=self.restart_count)
                console.print(f"[red]❌ Bot crashed: {e}[/red]")
                
                if self.restart_count < self.max_restarts:
                    console.print(f"[yellow]⏳ Restarting in {self.restart_delay} seconds...[/yellow]")
                    await asyncio.sleep(self.restart_delay)
                else:
                    console.print(f"[red]❌ Maximum restart attempts ({self.max_restarts}) reached[/red]")
                    raise typer.Exit(1)
            
            finally:
                self.running = False
                if self.bot:
                    try:
                        await self.bot.stop()
                    except Exception as e:
                        logger.error("Error stopping bot", error=str(e))
        
        # Display final statistics
        self._display_final_stats()
    
    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown."""
        console.print("[yellow]🛑 Initiating graceful shutdown...[/yellow]")
        
        if self.bot and self.running:
            try:
                await self.bot.stop()
                console.print("[green]✅ Bot stopped gracefully[/green]")
            except Exception as e:
                logger.error("Error during graceful shutdown", error=str(e))
                console.print(f"[red]❌ Error during shutdown: {e}[/red]")
        
        self.running = False
        self._display_final_stats()
        sys.exit(0)
    
    def _display_final_stats(self) -> None:
        """Display final statistics."""
        if self.start_time:
            duration = datetime.now(timezone.utc) - self.start_time
            
            stats_panel = Panel.fit(
                f"""
[bold]📊 Final Statistics[/bold]

Total Runtime: {duration}
Restart Count: {self.restart_count}
Max Restarts: {self.max_restarts}
Final Status: {'Running' if self.running else 'Stopped'}
                """,
                title="Session Summary",
                border_style="blue"
            )
            
            console.print(stats_panel)


@app.command()
def start(
    symbol: str = typer.Option("BTCUSDT", "--symbol", "-s", help="Trading symbol"),
    data_file: str = typer.Option(..., "--data", "-d", help="Path to historical data file"),
    strategy: str = typer.Option("llm", "--strategy", help="Trading strategy"),
    llm_provider: str = typer.Option("openai", "--llm-provider", help="LLM provider"),
    mode: str = typer.Option("paper", "--mode", help="Trading mode (paper/testnet/live)"),
    max_restarts: int = typer.Option(5, "--max-restarts", help="Maximum restart attempts"),
    restart_delay: int = typer.Option(30, "--restart-delay", help="Restart delay in seconds"),
):
    """Start the trading bot in production mode."""
    
    # Validate mode
    if mode == "live":
        console.print("[red]⚠️  LIVE TRADING MODE - This will execute real trades![/red]")
        if not typer.confirm("Are you sure you want to continue with live trading?"):
            console.print("Aborted.")
            raise typer.Abort()
    
    # Create production manager
    manager = ProductionBotManager()
    manager.max_restarts = max_restarts
    manager.restart_delay = restart_delay
    
    try:
        # Start the bot
        asyncio.run(manager.start_bot(symbol, data_file, strategy, llm_provider, mode))
    
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def health():
    """Run health check before starting bot."""
    
    console.print(Panel.fit(
        """
[bold]🔍 Running Health Check[/bold]

This will check all system components before starting the bot.
        """,
        title="Health Check",
        border_style="blue"
    ))
    
    try:
        # Import and run health check
        import subprocess
        result = subprocess.run([sys.executable, "scripts/health_check.py"], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✅ Health check passed![/green]")
            console.print(result.stdout)
        else:
            console.print("[red]❌ Health check failed![/red]")
            console.print(result.stdout)
            console.print(result.stderr)
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Health check error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def backup():
    """Create backup before starting bot."""
    
    console.print(Panel.fit(
        """
[bold]💾 Creating Backup[/bold]

This will create a backup of current data before starting the bot.
        """,
        title="Backup Creation",
        border_style="yellow"
    ))
    
    try:
        # Import and run backup
        import subprocess
        result = subprocess.run([sys.executable, "scripts/backup_restore.py", "create"], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✅ Backup created successfully![/green]")
            console.print(result.stdout)
        else:
            console.print("[red]❌ Backup failed![/red]")
            console.print(result.stdout)
            console.print(result.stderr)
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Backup error: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
