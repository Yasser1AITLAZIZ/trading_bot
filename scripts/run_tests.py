#!/usr/bin/env python3
"""Test runner script for the trading bot system."""

import subprocess
import sys
import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
app = typer.Typer(help="Test Runner - Run tests for the trading bot system")


@app.command()
def all():
    """Run all tests."""
    
    console.print(Panel.fit(
        """
[bold]🧪 Running All Tests[/bold]

This will run all tests including unit, integration, and system tests.
        """,
        title="Test Suite",
        border_style="blue"
    ))
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--asyncio-mode=auto"
        ], capture_output=False)
        
        if result.returncode == 0:
            console.print("[green]✅ All tests passed![/green]")
        else:
            console.print("[red]❌ Some tests failed![/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Test execution error: {e}[/red]")
        sys.exit(1)


@app.command()
def unit():
    """Run unit tests only."""
    
    console.print(Panel.fit(
        """
[bold]🔬 Running Unit Tests[/bold]

This will run only unit tests (fast tests).
        """,
        title="Unit Tests",
        border_style="green"
    ))
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "-m", "unit",
            "--tb=short"
        ], capture_output=False)
        
        if result.returncode == 0:
            console.print("[green]✅ Unit tests passed![/green]")
        else:
            console.print("[red]❌ Some unit tests failed![/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Test execution error: {e}[/red]")
        sys.exit(1)


@app.command()
def integration():
    """Run integration tests only."""
    
    console.print(Panel.fit(
        """
[bold]🔗 Running Integration Tests[/bold]

This will run only integration tests (slower tests).
        """,
        title="Integration Tests",
        border_style="yellow"
    ))
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "-m", "integration",
            "--tb=short",
            "--asyncio-mode=auto"
        ], capture_output=False)
        
        if result.returncode == 0:
            console.print("[green]✅ Integration tests passed![/green]")
        else:
            console.print("[red]❌ Some integration tests failed![/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Test execution error: {e}[/red]")
        sys.exit(1)


@app.command()
def telegram():
    """Run Telegram bot tests only."""
    
    console.print(Panel.fit(
        """
[bold]📱 Running Telegram Bot Tests[/bold]

This will run only Telegram bot related tests.
        """,
        title="Telegram Tests",
        border_style="cyan"
    ))
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_telegram_integration.py", 
            "-v", 
            "--tb=short",
            "--asyncio-mode=auto"
        ], capture_output=False)
        
        if result.returncode == 0:
            console.print("[green]✅ Telegram tests passed![/green]")
        else:
            console.print("[red]❌ Some Telegram tests failed![/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Test execution error: {e}[/red]")
        sys.exit(1)


@app.command()
def coverage():
    """Run tests with coverage report."""
    
    console.print(Panel.fit(
        """
[bold]📊 Running Tests with Coverage[/bold]

This will run all tests and generate a coverage report.
        """,
        title="Coverage Tests",
        border_style="magenta"
    ))
    
    try:
        # Run tests with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term",
            "-v",
            "--tb=short",
            "--asyncio-mode=auto"
        ], capture_output=False)
        
        if result.returncode == 0:
            console.print("[green]✅ Tests with coverage completed![/green]")
            console.print("[blue]📊 Coverage report generated in htmlcov/[/blue]")
        else:
            console.print("[red]❌ Some tests failed![/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Test execution error: {e}[/red]")
        sys.exit(1)


@app.command()
def quick():
    """Run quick tests (unit tests only, no slow tests)."""
    
    console.print(Panel.fit(
        """
[bold]⚡ Running Quick Tests[/bold]

This will run only fast unit tests, skipping slow integration tests.
        """,
        title="Quick Tests",
        border_style="green"
    ))
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "-m", "not slow",
            "--tb=short"
        ], capture_output=False)
        
        if result.returncode == 0:
            console.print("[green]✅ Quick tests passed![/green]")
        else:
            console.print("[red]❌ Some quick tests failed![/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Test execution error: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
