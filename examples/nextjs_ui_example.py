#!/usr/bin/env python3
"""Example demonstrating Next.js UI integration with the trading bot."""

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


def test_api_connectivity():
    """Test API server connectivity."""
    console.print(Panel.fit(
        "🔌 Testing API Connectivity",
        title="API Test",
        border_style="blue"
    ))
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            console.print("✅ API server is running")
            return True
        else:
            console.print(f"❌ API server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Cannot connect to API server: {e}")
        console.print("💡 Make sure to start the API server first:")
        console.print("   python -m src.api_cli")
        return False


def test_ui_connectivity():
    """Test Next.js UI connectivity."""
    console.print(Panel.fit(
        "🎨 Testing UI Connectivity",
        title="UI Test",
        border_style="green"
    ))
    
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            console.print("✅ Next.js UI is running")
            return True
        else:
            console.print(f"❌ UI returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Cannot connect to UI: {e}")
        console.print("💡 Make sure to start the Next.js UI first:")
        console.print("   cd ui && npm run dev")
        return False


def test_connectivity_endpoints():
    """Test connectivity test endpoints."""
    console.print(Panel.fit(
        "🧪 Testing Connectivity Endpoints",
        title="Connectivity Tests",
        border_style="yellow"
    ))
    
    # Test LLM connectivity (mock)
    console.print("Testing LLM connectivity...")
    try:
        response = requests.post(
            "http://localhost:8000/api/test/connectivity",
            json={
                "provider": "llm",
                "config": {
                    "provider": "openai",
                    "apiKey": "test-key",
                    "model": "gpt-4"
                }
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                console.print("✅ LLM connectivity test passed")
            else:
                console.print(f"⚠️ LLM connectivity test failed: {result.get('message')}")
        else:
            console.print(f"❌ LLM test returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        console.print(f"❌ LLM test failed: {e}")
    
    # Test Binance connectivity (mock)
    console.print("Testing Binance connectivity...")
    try:
        response = requests.post(
            "http://localhost:8000/api/test/connectivity",
            json={
                "provider": "binance",
                "config": {
                    "apiKey": "test-key",
                    "secretKey": "test-secret",
                    "mode": "paper"
                }
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                console.print("✅ Binance connectivity test passed")
            else:
                console.print(f"⚠️ Binance connectivity test failed: {result.get('message')}")
        else:
            console.print(f"❌ Binance test returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Binance test failed: {e}")


def test_file_upload():
    """Test file upload functionality."""
    console.print(Panel.fit(
        "📁 Testing File Upload",
        title="Upload Test",
        border_style="cyan"
    ))
    
    try:
        with open("examples/sample_data.csv", "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            response = requests.post(
                "http://localhost:8000/api/upload/data",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                console.print("✅ File upload successful")
                console.print(f"   Filename: {result.get('filename')}")
                console.print(f"   Records: {result.get('records_count')}")
                return True
            else:
                console.print(f"❌ Upload failed: {result.get('message')}")
                return False
        else:
            console.print(f"❌ Upload returned status {response.status_code}")
            return False
    except FileNotFoundError:
        console.print("❌ Sample data file not found")
        return False
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Upload failed: {e}")
        return False


def test_bot_control():
    """Test bot control endpoints."""
    console.print(Panel.fit(
        "🤖 Testing Bot Control",
        title="Bot Control",
        border_style="magenta"
    ))
    
    # Get bot status
    try:
        response = requests.get("http://localhost:8000/api/bot/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            console.print("✅ Bot status retrieved")
            console.print(f"   Running: {status.get('running', False)}")
            return True
        else:
            console.print(f"❌ Status check returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Status check failed: {e}")
        return False


def test_llm_decisions():
    """Test LLM decision logging."""
    console.print(Panel.fit(
        "🧠 Testing LLM Decision Logging",
        title="LLM Decisions",
        border_style="red"
    ))
    
    # Log a test decision
    test_decision = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "BTCUSDT",
        "action": "BUY",
        "confidence": 0.85,
        "reasoning": "Strong bullish momentum with RSI oversold and volume spike",
        "market_data": {
            "price": 50000.0,
            "volume": 1000.0,
            "volatility": 2.5
        },
        "risk_score": 0.25,
        "technical_indicators": {
            "rsi": 30.5,
            "sma": 49500.0,
            "ema": 49800.0
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/llm/decision",
            json=test_decision,
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                console.print("✅ LLM decision logged successfully")
                
                # Retrieve decisions
                response = requests.get("http://localhost:8000/api/llm/decisions?limit=5", timeout=5)
                if response.status_code == 200:
                    decisions = response.json()
                    console.print(f"✅ Retrieved {len(decisions.get('decisions', []))} decisions")
                    return True
                else:
                    console.print(f"❌ Failed to retrieve decisions: {response.status_code}")
                    return False
            else:
                console.print(f"❌ Decision logging failed: {result.get('message')}")
                return False
        else:
            console.print(f"❌ Decision logging returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Decision logging failed: {e}")
        return False


def display_results(results):
    """Display test results in a table."""
    table = Table(title="Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="green")
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        table.add_row(test_name, status)
    
    console.print(table)
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    success_rate = (passed / total) * 100
    
    if success_rate == 100:
        console.print(f"\n🎉 All tests passed! ({passed}/{total})")
    elif success_rate >= 80:
        console.print(f"\n⚠️ Most tests passed ({passed}/{total} - {success_rate:.1f}%)")
    else:
        console.print(f"\n❌ Many tests failed ({passed}/{total} - {success_rate:.1f}%)")


def main():
    """Main example function."""
    console.print(Panel.fit(
        """
[bold]🚀 Next.js UI Integration Example[/bold]

This example demonstrates the integration between the Next.js UI
and the FastAPI backend for the GenAI Trading Bot.
        """,
        title="UI Integration Example",
        border_style="blue"
    ))
    
    console.print("\n[bold]Prerequisites:[/bold]")
    console.print("1. API server running on http://localhost:8000")
    console.print("2. Next.js UI running on http://localhost:3000")
    console.print("3. Sample data file available")
    
    console.print("\n[bold]Starting tests...[/bold]")
    
    # Run tests
    results = {}
    
    results["API Connectivity"] = test_api_connectivity()
    results["UI Connectivity"] = test_ui_connectivity()
    
    if results["API Connectivity"]:
        results["Connectivity Endpoints"] = test_connectivity_endpoints()
        results["File Upload"] = test_file_upload()
        results["Bot Control"] = test_bot_control()
        results["LLM Decisions"] = test_llm_decisions()
    else:
        console.print("\n⚠️ Skipping API-dependent tests due to connectivity issues")
        results["Connectivity Endpoints"] = False
        results["File Upload"] = False
        results["Bot Control"] = False
        results["LLM Decisions"] = False
    
    # Display results
    display_results(results)
    
    # Next steps
    console.print(Panel.fit(
        """
[bold]🎯 Next Steps:[/bold]

1. [bold]Access the UI:[/bold] http://localhost:3000
2. [bold]Configure:[/bold] Set up environment variables
3. [bold]Test:[/bold] Use connectivity tests
4. [bold]Upload:[/bold] Upload historical data
5. [bold]Launch:[/bold] Start the trading bot
6. [bold]Monitor:[/bold] Watch the dashboard
7. [bold]Analyze:[/bold] Review the journal

[bold]📚 Documentation:[/bold]
- API Docs: http://localhost:8000/docs
- Configuration: http://localhost:3000/config
- Dashboard: http://localhost:3000/dashboard
- Journal: http://localhost:3000/journal
        """,
        title="Next Steps",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
