#!/usr/bin/env python3
"""Example of using the API server for the trading bot."""

import asyncio
import json
import time
from datetime import datetime, timezone
from decimal import Decimal

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def start_api_server():
    """Start the API server."""
    console.print(Panel.fit(
        "🚀 Starting API Server",
        title="API Server",
        border_style="blue"
    ))
    
    console.print("To start the API server, run:")
    console.print("  python -m src.api_cli")
    console.print("  # or")
    console.print("  api-server")
    console.print("\nThe server will be available at: http://localhost:8000")


def test_api_endpoints():
    """Test all API endpoints."""
    console.print(Panel.fit(
        "🧪 Testing API Endpoints",
        title="API Tests",
        border_style="green"
    ))
    
    base_url = "http://localhost:8000"
    results = {}
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        results["Health Check"] = response.status_code == 200
        if results["Health Check"]:
            console.print("✅ Health check passed")
        else:
            console.print(f"❌ Health check failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        results["Health Check"] = False
        console.print(f"❌ Health check failed: {e}")
    
    # Test configuration endpoint
    try:
        response = requests.get(f"{base_url}/api/config", timeout=5)
        results["Get Config"] = response.status_code == 200
        if results["Get Config"]:
            console.print("✅ Get configuration passed")
        else:
            console.print(f"❌ Get configuration failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        results["Get Config"] = False
        console.print(f"❌ Get configuration failed: {e}")
    
    # Test connectivity endpoint
    try:
        response = requests.post(
            f"{base_url}/api/test/connectivity",
            json={"provider": "llm", "config": {"provider": "openai"}},
            timeout=10
        )
        results["Connectivity Test"] = response.status_code == 200
        if results["Connectivity Test"]:
            console.print("✅ Connectivity test passed")
        else:
            console.print(f"❌ Connectivity test failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        results["Connectivity Test"] = False
        console.print(f"❌ Connectivity test failed: {e}")
    
    # Test file upload
    try:
        with open("examples/sample_data.csv", "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            response = requests.post(f"{base_url}/api/upload/data", files=files, timeout=30)
        results["File Upload"] = response.status_code == 200
        if results["File Upload"]:
            console.print("✅ File upload passed")
        else:
            console.print(f"❌ File upload failed: {response.status_code}")
    except FileNotFoundError:
        results["File Upload"] = False
        console.print("❌ File upload failed: sample_data.csv not found")
    except requests.exceptions.RequestException as e:
        results["File Upload"] = False
        console.print(f"❌ File upload failed: {e}")
    
    # Test bot status
    try:
        response = requests.get(f"{base_url}/api/bot/status", timeout=5)
        results["Bot Status"] = response.status_code == 200
        if results["Bot Status"]:
            console.print("✅ Bot status passed")
        else:
            console.print(f"❌ Bot status failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        results["Bot Status"] = False
        console.print(f"❌ Bot status failed: {e}")
    
    # Test LLM decision logging
    try:
        decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": "BTCUSDT",
            "action": "BUY",
            "confidence": 0.85,
            "reasoning": "Test decision for API example",
            "market_data": {"price": 50000.0},
            "risk_score": 0.25,
            "technical_indicators": {"rsi": 30.5}
        }
        response = requests.post(f"{base_url}/api/llm/decision", json=decision, timeout=5)
        results["LLM Decision"] = response.status_code == 200
        if results["LLM Decision"]:
            console.print("✅ LLM decision logging passed")
        else:
            console.print(f"❌ LLM decision logging failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        results["LLM Decision"] = False
        console.print(f"❌ LLM decision logging failed: {e}")
    
    return results


def display_api_documentation():
    """Display API documentation."""
    console.print(Panel.fit(
        """
[bold]📚 API Documentation[/bold]

The API server provides the following endpoints:

[bold]Health & Status:[/bold]
- GET /health - Health check
- GET /api/bot/status - Bot status

[bold]Configuration:[/bold]
- GET /api/config - Get configuration
- POST /api/config - Update configuration

[bold]Connectivity Tests:[/bold]
- POST /api/test/connectivity - Test service connectivity

[bold]File Management:[/bold]
- POST /api/upload/data - Upload historical data

[bold]Bot Control:[/bold]
- POST /api/bot/start - Start trading bot
- POST /api/bot/stop - Stop trading bot

[bold]LLM Decisions:[/bold]
- POST /api/llm/decision - Log LLM decision
- GET /api/llm/decisions - Get decision history

[bold]WebSocket:[/bold]
- WS /ws - Real-time updates

[bold]📖 Full Documentation:[/bold] http://localhost:8000/docs
        """,
        title="API Documentation",
        border_style="cyan"
    ))


def demonstrate_workflow():
    """Demonstrate a complete workflow."""
    console.print(Panel.fit(
        "🔄 Complete Workflow Example",
        title="Workflow",
        border_style="yellow"
    ))
    
    console.print("1. [bold]Start API Server[/bold]")
    console.print("   python -m src.api_cli")
    
    console.print("\n2. [bold]Test Connectivity[/bold]")
    console.print("   curl -X POST http://localhost:8000/api/test/connectivity \\")
    console.print("     -H 'Content-Type: application/json' \\")
    console.print("     -d '{\"provider\": \"llm\", \"config\": {\"provider\": \"openai\"}}'")
    
    console.print("\n3. [bold]Upload Data[/bold]")
    console.print("   curl -X POST http://localhost:8000/api/upload/data \\")
    console.print("     -F 'file=@examples/sample_data.csv'")
    
    console.print("\n4. [bold]Start Bot[/bold]")
    console.print("   curl -X POST http://localhost:8000/api/bot/start \\")
    console.print("     -H 'Content-Type: application/json' \\")
    console.print("     -d '{\"symbol\": \"BTCUSDT\", \"strategy\": \"llm\", \"data_file\": \"sample_data.csv\"}'")
    
    console.print("\n5. [bold]Monitor Status[/bold]")
    console.print("   curl http://localhost:8000/api/bot/status")
    
    console.print("\n6. [bold]View Decisions[/bold]")
    console.print("   curl http://localhost:8000/api/llm/decisions")


def main():
    """Main example function."""
    console.print(Panel.fit(
        """
[bold]🚀 API Server Example[/bold]

This example demonstrates how to use the FastAPI server
for the GenAI Trading Bot.
        """,
        title="API Server Example",
        border_style="blue"
    ))
    
    # Start API server instructions
    start_api_server()
    
    console.print("\n" + "="*60)
    
    # Test API endpoints
    results = test_api_endpoints()
    
    # Display results
    table = Table(title="API Test Results")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Status", style="green")
    
    for endpoint, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        table.add_row(endpoint, status)
    
    console.print(table)
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    success_rate = (passed / total) * 100
    
    console.print(f"\n📊 Results: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if success_rate == 100:
        console.print("🎉 All API tests passed!")
    elif success_rate >= 80:
        console.print("⚠️ Most API tests passed")
    else:
        console.print("❌ Many API tests failed")
        console.print("💡 Make sure the API server is running on http://localhost:8000")
    
    console.print("\n" + "="*60)
    
    # Display documentation
    display_api_documentation()
    
    console.print("\n" + "="*60)
    
    # Demonstrate workflow
    demonstrate_workflow()
    
    console.print(Panel.fit(
        """
[bold]🎯 Next Steps:[/bold]

1. [bold]Start the API server[/bold] if not already running
2. [bold]Test all endpoints[/bold] to ensure functionality
3. [bold]Integrate with Next.js UI[/bold] for full experience
4. [bold]Use WebSocket[/bold] for real-time updates
5. [bold]Monitor logs[/bold] for debugging

[bold]🔗 Useful URLs:[/bold]
- API Server: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
        """,
        title="Next Steps",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
