#!/usr/bin/env python3
"""Integration test runner for the complete trading bot system."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
import structlog
import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
app = typer.Typer(help="Integration Test Runner - Run comprehensive integration tests")


@app.command()
def full():
    """Run full integration tests with Docker Compose."""
    
    console.print(Panel.fit(
        """
[bold]🧪 Running Full Integration Tests[/bold]

This will test the complete system with Docker Compose.
        """,
        title="Integration Tests",
        border_style="blue"
    ))
    
    try:
        # Start test services
        console.print("[blue]Starting test services...[/blue]")
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "up", "-d"
        ], check=True)
        
        # Wait for services to be ready
        console.print("[blue]Waiting for services to be ready...[/blue]")
        time.sleep(30)
        
        # Run backend tests
        console.print("[blue]Running backend tests...[/blue]")
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "exec", 
            "trading-bot-api-test", "python", "-m", "scripts.run_tests", "integration"
        ], check=True)
        
        # Run frontend tests
        console.print("[blue]Running frontend tests...[/blue]")
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "exec", 
            "trading-bot-ui-test", "npm", "test"
        ], check=True)
        
        # Run health checks
        console.print("[blue]Running health checks...[/blue]")
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "exec", 
            "trading-bot-api-test", "python", "-m", "scripts.health_check"
        ], check=True)
        
        console.print("[green]✅ All integration tests passed![/green]")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Integration tests failed: {e}[/red]")
        sys.exit(1)
    finally:
        # Cleanup
        console.print("[blue]Cleaning up test services...[/blue]")
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "down", "-v"
        ])


@app.command()
def api():
    """Run API integration tests."""
    
    console.print(Panel.fit(
        """
[bold]🔌 Running API Integration Tests[/bold]

This will test the API endpoints and connectivity.
        """,
        title="API Tests",
        border_style="green"
    ))
    
    try:
        # Start API service
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "up", "-d", "trading-bot-api-test"
        ], check=True)
        
        # Wait for service to be ready
        time.sleep(15)
        
        # Run API tests
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "exec", 
            "trading-bot-api-test", "python", "-m", "scripts.run_tests", "integration"
        ], check=True)
        
        console.print("[green]✅ API integration tests passed![/green]")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ API integration tests failed: {e}[/red]")
        sys.exit(1)
    finally:
        # Cleanup
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "down", "-v"
        ])


@app.command()
def ui():
    """Run UI integration tests."""
    
    console.print(Panel.fit(
        """
[bold]🎨 Running UI Integration Tests[/bold]

This will test the Next.js frontend.
        """,
        title="UI Tests",
        border_style="yellow"
    ))
    
    try:
        # Start UI service
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "up", "-d", "trading-bot-ui-test"
        ], check=True)
        
        # Wait for service to be ready
        time.sleep(20)
        
        # Run UI tests
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "exec", 
            "trading-bot-ui-test", "npm", "test"
        ], check=True)
        
        console.print("[green]✅ UI integration tests passed![/green]")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ UI integration tests failed: {e}[/red]")
        sys.exit(1)
    finally:
        # Cleanup
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "down", "-v"
        ])


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
