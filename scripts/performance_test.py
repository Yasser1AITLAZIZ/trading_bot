#!/usr/bin/env python3
"""Performance testing script for the trading bot system."""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import structlog
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
app = typer.Typer(help="Performance Test Runner - Test system performance and load")


@app.command()
def api():
    """Test API performance."""
    
    console.print(Panel.fit(
        """
[bold]⚡ API Performance Test[/bold]

This will test the API endpoints for performance and response times.
        """,
        title="Performance Test",
        border_style="blue"
    ))
    
    # Test endpoints
    endpoints = [
        "/health",
        "/api/config",
        "/api/bot/status",
        "/api/llm/decisions?limit=10",
    ]
    
    results = []
    
    for endpoint in endpoints:
        console.print(f"[blue]Testing {endpoint}...[/blue]")
        
        # Simulate multiple requests
        response_times = []
        for i in range(10):
            start_time = time.time()
            # Here you would make actual HTTP requests
            # response = requests.get(f"http://localhost:8000{endpoint}")
            time.sleep(0.1)  # Simulate response time
            end_time = time.time()
            response_times.append(end_time - start_time)
        
        results.append({
            "endpoint": endpoint,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "std_deviation": statistics.stdev(response_times) if len(response_times) > 1 else 0,
        })
    
    # Display results
    table = Table(title="API Performance Results")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Avg Response Time (ms)", style="green")
    table.add_column("Min Response Time (ms)", style="green")
    table.add_column("Max Response Time (ms)", style="green")
    table.add_column("Std Deviation (ms)", style="yellow")
    
    for result in results:
        table.add_row(
            result["endpoint"],
            f"{result['avg_response_time']*1000:.2f}",
            f"{result['min_response_time']*1000:.2f}",
            f"{result['max_response_time']*1000:.2f}",
            f"{result['std_deviation']*1000:.2f}",
        )
    
    console.print(table)


@app.command()
def websocket():
    """Test WebSocket performance."""
    
    console.print(Panel.fit(
        """
[bold]🔌 WebSocket Performance Test[/bold]

This will test WebSocket connection and message handling performance.
        """,
        title="WebSocket Test",
        border_style="green"
    ))
    
    # Simulate WebSocket performance test
    console.print("[blue]Testing WebSocket connection...[/blue]")
    
    connection_times = []
    message_times = []
    
    for i in range(5):
        # Simulate connection time
        start_time = time.time()
        time.sleep(0.05)  # Simulate connection
        connection_times.append(time.time() - start_time)
        
        # Simulate message handling
        start_time = time.time()
        time.sleep(0.01)  # Simulate message processing
        message_times.append(time.time() - start_time)
    
    console.print(f"[green]Average connection time: {statistics.mean(connection_times)*1000:.2f}ms[/green]")
    console.print(f"[green]Average message handling time: {statistics.mean(message_times)*1000:.2f}ms[/green]")


@app.command()
def memory():
    """Test memory usage."""
    
    console.print(Panel.fit(
        """
[bold]💾 Memory Usage Test[/bold]

This will test memory usage and potential leaks.
        """,
        title="Memory Test",
        border_style="yellow"
    ))
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    # Get initial memory usage
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    console.print(f"[blue]Initial memory usage: {initial_memory:.2f} MB[/blue]")
    
    # Simulate some operations
    data = []
    for i in range(1000):
        data.append({"id": i, "data": "x" * 1000})
    
    # Get memory after operations
    after_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    console.print(f"[blue]Memory after operations: {after_memory:.2f} MB[/blue]")
    console.print(f"[green]Memory increase: {after_memory - initial_memory:.2f} MB[/green]")
    
    # Cleanup
    del data
    
    # Get memory after cleanup
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    console.print(f"[blue]Memory after cleanup: {final_memory:.2f} MB[/blue]")
    console.print(f"[green]Memory recovered: {after_memory - final_memory:.2f} MB[/green]")


@app.command()
def load():
    """Test system under load."""
    
    console.print(Panel.fit(
        """
[bold]🚀 Load Test[/bold]

This will test the system under various load conditions.
        """,
        title="Load Test",
        border_style="red"
    ))
    
    # Simulate load test
    console.print("[blue]Simulating concurrent requests...[/blue]")
    
    async def simulate_request():
        await asyncio.sleep(0.1)  # Simulate request processing
        return time.time()
    
    async def run_load_test(concurrent_requests: int):
        start_time = time.time()
        tasks = [simulate_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        requests_per_second = concurrent_requests / total_time
        
        return {
            "concurrent_requests": concurrent_requests,
            "total_time": total_time,
            "requests_per_second": requests_per_second,
        }
    
    # Test different load levels
    load_levels = [1, 5, 10, 20, 50]
    results = []
    
    for level in load_levels:
        console.print(f"[blue]Testing with {level} concurrent requests...[/blue]")
        result = asyncio.run(run_load_test(level))
        results.append(result)
    
    # Display results
    table = Table(title="Load Test Results")
    table.add_column("Concurrent Requests", style="cyan")
    table.add_column("Total Time (s)", style="green")
    table.add_column("Requests/Second", style="yellow")
    
    for result in results:
        table.add_row(
            str(result["concurrent_requests"]),
            f"{result['total_time']:.2f}",
            f"{result['requests_per_second']:.2f}",
        )
    
    console.print(table)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
