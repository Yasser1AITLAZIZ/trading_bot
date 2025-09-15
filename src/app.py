"""Main application orchestrator with CLI interface."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import structlog
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.settings import get_settings, reload_settings
from .core.types import TradingMode, StrategyConfig
from .data.ingestion import DataIngestionService
from .data.features import TechnicalIndicatorCalculator, MarketSignalGenerator
from .data.cache import DataCache
from .llm.factory import get_llm_client, get_fallback_llm_client
from .strategy.registry import get_strategy, get_strategy_with_fallback
from .execution.order_router import OrderRouter

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
app = typer.Typer(help="GenAI Trading Bot - AI-powered trading with multi-LLM support")


@app.command()
def run(
    data_file: str = typer.Option(..., "--data", "-d", help="Path to historical data file (CSV/JSON/Parquet)"),
    symbol: str = typer.Option("BTCUSDT", "--symbol", "-s", help="Trading symbol"),
    strategy: str = typer.Option("llm", "--strategy", help="Trading strategy (llm, technical)"),
    llm_provider: str = typer.Option("openai", "--llm-provider", help="LLM provider (openai, anthropic, gemini)"),
    mode: str = typer.Option("paper", "--mode", help="Trading mode (paper, testnet, live)"),
    risk_per_trade: float = typer.Option(0.01, "--risk", help="Risk per trade (0.01 = 1%)"),
    confidence_threshold: float = typer.Option(0.7, "--confidence", help="Minimum confidence threshold"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results"),
):
    """Run the trading bot with specified parameters."""
    
    try:
        # Validate inputs
        trading_mode = TradingMode(mode)
        if trading_mode == TradingMode.LIVE:
            console.print("[red]⚠️  LIVE TRADING MODE - This will execute real trades![/red]")
            if not typer.confirm("Are you sure you want to continue?"):
                console.print("Aborted.")
                raise typer.Abort()
        
        # Display configuration
        config_panel = Panel.fit(
            f"""
[bold]Trading Bot Configuration[/bold]
Data File: {data_file}
Symbol: {symbol}
Strategy: {strategy}
LLM Provider: {llm_provider}
Mode: {mode}
Risk per Trade: {risk_per_trade:.1%}
Confidence Threshold: {confidence_threshold:.1%}
            """,
            title="Configuration",
            border_style="blue"
        )
        console.print(config_panel)
        
        # Run the trading bot
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Load and validate data
            task1 = progress.add_task("Loading historical data...", total=None)
            data_service = DataIngestionService()
            ohlcv_data = data_service.load_from_file(data_file, symbol)
            
            # Validate data quality
            quality_metrics = data_service.validate_data_quality(ohlcv_data)
            if not quality_metrics["valid"]:
                console.print(f"[red]❌ Data quality issues: {', '.join(quality_metrics['issues'])}[/red]")
                raise typer.Exit(1)
            
            progress.update(task1, description="✅ Data loaded successfully")
            
            # Calculate technical indicators
            task2 = progress.add_task("Calculating technical indicators...", total=None)
            indicator_calculator = TechnicalIndicatorCalculator()
            indicators = indicator_calculator.calculate_all_indicators(ohlcv_data)
            
            # Generate market signals
            signal_generator = MarketSignalGenerator()
            signals = signal_generator.generate_signals(ohlcv_data, indicators)
            
            progress.update(task2, description="✅ Technical analysis completed")
            
            # Initialize strategy
            task3 = progress.add_task("Initializing trading strategy...", total=None)
            strategy_config = StrategyConfig(
                name=strategy,
                description=f"{strategy} strategy",
                max_risk_per_trade=risk_per_trade,
                min_confidence=confidence_threshold,
            )
            
            trading_strategy = get_strategy_with_fallback(
                primary_name=strategy,
                fallback_name="technical",
                llm_provider=llm_provider
            )
            
            if not trading_strategy:
                console.print("[red]❌ Failed to initialize trading strategy[/red]")
                raise typer.Exit(1)
            
            progress.update(task3, description="✅ Strategy initialized")
            
            # Initialize order router
            task4 = progress.add_task("Initializing order router...", total=None)
            order_router = OrderRouter(trading_mode)
            session_id = order_router.start_session(strategy, Decimal("10000"))  # $10k initial balance
            
            progress.update(task4, description="✅ Order router initialized")
            
            # Make trading decision
            task5 = progress.add_task("Making trading decision...", total=None)
            decision = trading_strategy.decide(ohlcv_data, indicators, signals, strategy_config)
            
            progress.update(task5, description="✅ Trading decision made")
            
            # Execute decision
            task6 = progress.add_task("Executing trade...", total=None)
            order_response = order_router.execute_decision(decision)
            
            progress.update(task6, description="✅ Trade execution completed")
        
        # Display results
        display_results(decision, order_response, quality_metrics, indicators, signals)
        
        # Save results if output file specified
        if output_file:
            save_results(output_file, decision, order_response, quality_metrics, indicators, signals)
        
        # End session
        session = order_router.end_session()
        if session:
            console.print(f"\n[green]✅ Trading session completed: {session.session_id}[/green]")
    
    except Exception as e:
        logger.error("Trading bot execution failed", error=str(e))
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate_data(
    data_file: str = typer.Option(..., "--data", "-d", help="Path to historical data file"),
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Trading symbol"),
):
    """Validate historical data quality."""
    
    try:
        console.print(f"[blue]📊 Validating data file: {data_file}[/blue]")
        
        data_service = DataIngestionService()
        ohlcv_data = data_service.load_from_file(data_file, symbol)
        quality_metrics = data_service.validate_data_quality(ohlcv_data)
        
        # Display quality metrics
        table = Table(title="Data Quality Report")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        
        table.add_row("Total Data Points", str(quality_metrics["total_points"]), "✅")
        table.add_row("Symbol", quality_metrics["symbol"], "✅")
        table.add_row("Start Time", quality_metrics["start_time"].strftime("%Y-%m-%d %H:%M:%S"), "✅")
        table.add_row("End Time", quality_metrics["end_time"].strftime("%Y-%m-%d %H:%M:%S"), "✅")
        table.add_row("Data Age (hours)", f"{quality_metrics['age_hours']:.1f}", "✅" if quality_metrics["age_hours"] < 24 else "⚠️")
        table.add_row("Missing Periods", str(quality_metrics["missing_periods"]), "✅" if quality_metrics["missing_periods"] == 0 else "⚠️")
        table.add_row("Invalid Prices", str(quality_metrics["invalid_prices"]), "✅" if quality_metrics["invalid_prices"] == 0 else "❌")
        table.add_row("Negative Volumes", str(quality_metrics["negative_volumes"]), "✅" if quality_metrics["negative_volumes"] == 0 else "❌")
        
        console.print(table)
        
        if quality_metrics["valid"]:
            console.print("[green]✅ Data validation passed![/green]")
        else:
            console.print("[red]❌ Data validation failed![/red]")
            console.print(f"Issues: {', '.join(quality_metrics['issues'])}")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test_llm(
    provider: str = typer.Option("openai", "--provider", help="LLM provider to test"),
    prompt: str = typer.Option("What is the current market sentiment for Bitcoin?", "--prompt", help="Test prompt"),
):
    """Test LLM provider connectivity and response."""
    
    try:
        console.print(f"[blue]🤖 Testing LLM provider: {provider}[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Connecting to LLM provider...", total=None)
            
            try:
                llm_client = get_llm_client(provider=provider)
                progress.update(task, description="✅ Connected to LLM provider")
                
                task = progress.add_task("Sending test prompt...", total=None)
                response = llm_client.generate(prompt, temperature=0.1, max_tokens=200)
                progress.update(task, description="✅ Received response")
        
        # Display results
        result_panel = Panel.fit(
            f"""
[bold]LLM Test Results[/bold]
Provider: {provider}
Model: {response.model}
Latency: {response.latency_ms:.0f}ms
Tokens Used: {response.usage.get('total_tokens', 'N/A')}

[bold]Response:[/bold]
{response.content}
            """,
            title="LLM Test",
            border_style="green"
        )
        console.print(result_panel)
        
        console.print("[green]✅ LLM test completed successfully![/green]")
    
    except Exception as e:
        console.print(f"[red]❌ LLM test failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_strategies():
    """List available trading strategies."""
    
    from .strategy.registry import list_available_strategies
    
    strategies = list_available_strategies()
    
    table = Table(title="Available Trading Strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    
    for strategy_name in strategies:
        if strategy_name == "llm":
            description = "AI-powered strategy using LLM for decision making"
        elif strategy_name == "technical":
            description = "Technical analysis-based strategy using traditional indicators"
        else:
            description = "Custom strategy"
        
        table.add_row(strategy_name, description)
    
    console.print(table)


@app.command()
def config():
    """Display current configuration."""
    
    settings = get_settings()
    
    config_panel = Panel.fit(
        f"""
[bold]Application Configuration[/bold]
Environment: {settings.environment}
Debug Mode: {settings.debug}
Max Workers: {settings.max_workers}

[bold]LLM Settings[/bold]
Primary Provider: {settings.llm.primary_provider}
Fallback Providers: {', '.join(settings.llm.fallback_providers)}
Max Requests/Min: {settings.llm.max_requests_per_minute}
Max Tokens/Min: {settings.llm.max_tokens_per_minute}

[bold]Binance Settings[/bold]
Mode: {settings.binance.mode}
Max Risk per Trade: {settings.binance.max_risk_per_trade:.1%}
Max Daily Trades: {settings.binance.max_daily_trades}
Max Daily Loss: {settings.binance.max_daily_loss:.1%}

[bold]Data Settings[/bold]
Data Directory: {settings.data.data_directory}
Cache Directory: {settings.data.cache_directory}
Cache TTL: {settings.data.cache_ttl_seconds}s
        """,
        title="Configuration",
        border_style="blue"
    )
    console.print(config_panel)


def display_results(decision, order_response, quality_metrics, indicators, signals):
    """Display trading results."""
    
    # Trading Decision
    decision_panel = Panel.fit(
        f"""
[bold]Trading Decision[/bold]
Action: {decision.action.value if decision.action else 'HOLD'}
Symbol: {decision.symbol}
Quantity: {decision.quantity}
Price: ${decision.price}
Confidence: {decision.confidence:.1%}
Risk Score: {decision.risk_score:.1%}

[bold]Reasoning:[/bold]
{decision.reasoning}
        """,
        title="Decision",
        border_style="green" if decision.action else "yellow"
    )
    console.print(decision_panel)
    
    # Technical Indicators
    indicators_panel = Panel.fit(
        f"""
[bold]Technical Indicators[/bold]
RSI: {indicators.rsi or 'N/A'}
SMA(20): {indicators.sma_20 or 'N/A'}
EMA(20): {indicators.ema_20 or 'N/A'}
ATR: {indicators.atr or 'N/A'}
Volatility: {indicators.volatility or 'N/A'}
        """,
        title="Technical Analysis",
        border_style="blue"
    )
    console.print(indicators_panel)
    
    # Market Signals
    signals_panel = Panel.fit(
        f"""
[bold]Market Signals[/bold]
Trend: {signals.get('trend', 'N/A')}
Momentum: {signals.get('momentum', 'N/A')}
Volatility Regime: {signals.get('volatility_regime', 'N/A')}
        """,
        title="Market Signals",
        border_style="cyan"
    )
    console.print(signals_panel)
    
    # Order Response (if any)
    if order_response:
        order_panel = Panel.fit(
            f"""
[bold]Order Execution[/bold]
Order ID: {order_response.order_id}
Status: {order_response.status.value}
Executed Quantity: {order_response.executed_quantity}
Executed Price: ${order_response.executed_price or 'N/A'}
            """,
            title="Order Response",
            border_style="green"
        )
        console.print(order_panel)


def save_results(output_file: str, decision, order_response, quality_metrics, indicators, signals):
    """Save results to file."""
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": {
            "action": decision.action.value if decision.action else None,
            "symbol": decision.symbol,
            "quantity": str(decision.quantity),
            "price": str(decision.price) if decision.price else None,
            "confidence": decision.confidence,
            "risk_score": decision.risk_score,
            "reasoning": decision.reasoning,
        },
        "order_response": {
            "order_id": order_response.order_id if order_response else None,
            "status": order_response.status.value if order_response else None,
            "executed_quantity": str(order_response.executed_quantity) if order_response else None,
            "executed_price": str(order_response.executed_price) if order_response and order_response.executed_price else None,
        } if order_response else None,
        "data_quality": quality_metrics,
        "technical_indicators": {
            "rsi": indicators.rsi,
            "sma_20": indicators.sma_20,
            "ema_20": indicators.ema_20,
            "atr": indicators.atr,
            "volatility": indicators.volatility,
        },
        "market_signals": signals,
    }
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    console.print(f"[green]✅ Results saved to: {output_file}[/green]")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
