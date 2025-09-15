#!/usr/bin/env python3
"""Example demonstrating Docker deployment for the trading bot."""

import subprocess
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def check_docker_installation():
    """Check if Docker is installed and running."""
    console.print(Panel.fit(
        "🐳 Checking Docker Installation",
        title="Docker Check",
        border_style="blue"
    ))
    
    try:
        # Check Docker version
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"✅ Docker installed: {result.stdout.strip()}")
        else:
            console.print("❌ Docker not found")
            return False
        
        # Check Docker Compose version
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"✅ Docker Compose installed: {result.stdout.strip()}")
        else:
            console.print("❌ Docker Compose not found")
            return False
        
        # Check if Docker daemon is running
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("✅ Docker daemon is running")
            return True
        else:
            console.print("❌ Docker daemon is not running")
            console.print("💡 Start Docker Desktop or Docker daemon")
            return False
            
    except FileNotFoundError:
        console.print("❌ Docker not found in PATH")
        console.print("💡 Install Docker Desktop from https://www.docker.com/products/docker-desktop")
        return False


def show_docker_commands():
    """Show Docker commands for the trading bot."""
    console.print(Panel.fit(
        "📋 Docker Commands for Trading Bot",
        title="Docker Commands",
        border_style="green"
    ))
    
    commands = [
        ("docker-compose up -d", "Start all services in background"),
        ("docker-compose up -d --build", "Rebuild and start services"),
        ("docker-compose --profile bot up -d", "Start with trading bot"),
        ("docker-compose --profile redis up -d", "Start with Redis"),
        ("docker-compose --profile postgres up -d", "Start with PostgreSQL"),
        ("docker-compose logs -f", "View logs from all services"),
        ("docker-compose logs -f trading-bot-api", "View API server logs"),
        ("docker-compose logs -f trading-bot-ui", "View UI logs"),
        ("docker-compose ps", "Show running containers"),
        ("docker-compose down", "Stop all services"),
        ("docker-compose down -v", "Stop and remove volumes"),
        ("docker-compose restart trading-bot-api", "Restart API server"),
        ("docker-compose restart trading-bot-ui", "Restart UI"),
    ]
    
    table = Table(title="Docker Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    for command, description in commands:
        table.add_row(command, description)
    
    console.print(table)


def show_docker_architecture():
    """Show Docker architecture."""
    console.print(Panel.fit(
        """
[bold]🏗️ Docker Architecture[/bold]

[bold]Services:[/bold]
- [bold]trading-bot-api[/bold] (Port 8000) - FastAPI backend
- [bold]trading-bot-ui[/bold] (Port 3000) - Next.js frontend
- [bold]trading-bot[/bold] (Optional) - Trading bot instance
- [bold]redis[/bold] (Port 6379) - Caching (optional)
- [bold]postgres[/bold] (Port 5432) - Database (optional)

[bold]Networks:[/bold]
- [bold]trading-network[/bold] - Internal communication

[bold]Volumes:[/bold]
- [bold]data/[/bold] - Historical data and logs
- [bold]logs/[/bold] - Application logs
- [bold]backups/[/bold] - Backup files
- [bold]redis_data[/bold] - Redis data (if enabled)
- [bold]postgres_data[/bold] - PostgreSQL data (if enabled)

[bold]Environment:[/bold]
- [bold].env[/bold] - Environment variables
- [bold]docker-compose.yml[/bold] - Service configuration
- [bold]docker-compose.test.yml[/bold] - Test configuration
        """,
        title="Docker Architecture",
        border_style="yellow"
    ))


def show_deployment_steps():
    """Show deployment steps."""
    console.print(Panel.fit(
        """
[bold]🚀 Deployment Steps[/bold]

[bold]1. Prerequisites:[/bold]
   - Docker Desktop installed and running
   - Environment variables configured
   - Historical data prepared

[bold]2. Configuration:[/bold]
   - Copy env.example to .env
   - Set API keys and configuration
   - Prepare historical data files

[bold]3. Build and Start:[/bold]
   - docker-compose up -d --build
   - Wait for services to be ready
   - Check health endpoints

[bold]4. Access Services:[/bold]
   - UI: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

[bold]5. Configuration:[/bold]
   - Use UI to configure bot
   - Test connectivity
   - Upload historical data
   - Launch trading bot

[bold]6. Monitoring:[/bold]
   - View dashboard for real-time status
   - Check logs for issues
   - Monitor performance

[bold]7. Maintenance:[/bold]
   - Regular backups
   - Log rotation
   - Updates and patches
        """,
        title="Deployment Steps",
        border_style="cyan"
    ))


def show_troubleshooting():
    """Show troubleshooting guide."""
    console.print(Panel.fit(
        """
[bold]🔧 Troubleshooting[/bold]

[bold]Common Issues:[/bold]

[bold]1. Services not starting:[/bold]
   - Check Docker daemon is running
   - Verify docker-compose.yml syntax
   - Check port conflicts
   - View logs: docker-compose logs

[bold]2. API connection failed:[/bold]
   - Check API server logs
   - Verify port 8000 is available
   - Test health endpoint
   - Check environment variables

[bold]3. UI not loading:[/bold]
   - Check UI container logs
   - Verify port 3000 is available
   - Check API connectivity
   - Verify Next.js build

[bold]4. Bot not starting:[/bold]
   - Check all connectivity tests
   - Verify data file uploaded
   - Check trading configuration
   - Review error logs

[bold]5. Performance issues:[/bold]
   - Monitor resource usage
   - Check memory limits
   - Optimize configuration
   - Scale services if needed

[bold]Debug Commands:[/bold]
- docker-compose logs -f [service]
- docker-compose exec [service] bash
- docker system prune -f
- docker-compose down -v && docker-compose up -d
        """,
        title="Troubleshooting",
        border_style="red"
    ))


def show_environment_setup():
    """Show environment setup."""
    console.print(Panel.fit(
        """
[bold]⚙️ Environment Setup[/bold]

[bold]1. Create .env file:[/bold]
   cp env.example .env

[bold]2. Configure variables:[/bold]
   # LLM Configuration
   LLM_PRIMARY_PROVIDER=openai
   LLM_OPENAI_API_KEY=your_key_here
   
   # Binance Configuration
   BINANCE_API_KEY=your_key_here
   BINANCE_SECRET_KEY=your_secret_here
   BINANCE_MODE=paper
   
   # Telegram Configuration (Optional)
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id
   
   # Trading Configuration
   TRADING_MAX_CONCURRENT_ORDERS=2
   TRADING_MAX_DAILY_LOSS=0.05

[bold]3. Prepare data:[/bold]
   mkdir -p data/historical
   cp examples/sample_data.csv data/historical/

[bold]4. Start services:[/bold]
   docker-compose up -d

[bold]5. Verify:[/bold]
   curl http://localhost:8000/health
   curl http://localhost:3000
        """,
        title="Environment Setup",
        border_style="magenta"
    ))


def main():
    """Main example function."""
    console.print(Panel.fit(
        """
[bold]🐳 Docker Deployment Example[/bold]

This example demonstrates how to deploy the GenAI Trading Bot
using Docker and Docker Compose.
        """,
        title="Docker Example",
        border_style="blue"
    ))
    
    # Check Docker installation
    docker_ok = check_docker_installation()
    
    if not docker_ok:
        console.print("\n❌ Docker setup required before proceeding")
        console.print("Please install and start Docker Desktop")
        return
    
    console.print("\n" + "="*60)
    
    # Show Docker architecture
    show_docker_architecture()
    
    console.print("\n" + "="*60)
    
    # Show Docker commands
    show_docker_commands()
    
    console.print("\n" + "="*60)
    
    # Show deployment steps
    show_deployment_steps()
    
    console.print("\n" + "="*60)
    
    # Show environment setup
    show_environment_setup()
    
    console.print("\n" + "="*60)
    
    # Show troubleshooting
    show_troubleshooting()
    
    console.print(Panel.fit(
        """
[bold]🎯 Quick Start:[/bold]

1. [bold]Setup Environment:[/bold]
   cp env.example .env
   # Edit .env with your API keys

2. [bold]Start Services:[/bold]
   docker-compose up -d

3. [bold]Access UI:[/bold]
   open http://localhost:3000

4. [bold]Configure Bot:[/bold]
   - Set environment variables
   - Test connectivity
   - Upload data
   - Launch bot

[bold]🔗 Useful URLs:[/bold]
- UI: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
        """,
        title="Quick Start",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
