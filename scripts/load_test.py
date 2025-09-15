#!/usr/bin/env python3
"""Load testing script for the trading bot system."""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
import structlog
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
app = typer.Typer(help="Load Test Runner - Test system under various load conditions")


@app.command()
def api(
    url: str = typer.Option("http://localhost:8000", help="API base URL"),
    concurrent: int = typer.Option(10, help="Number of concurrent requests"),
    requests: int = typer.Option(100, help="Total number of requests"),
    duration: int = typer.Option(60, help="Test duration in seconds"),
):
    """Run API load test."""
    
    console.print(Panel.fit(
        f"""
[bold]🚀 API Load Test[/bold]

URL: {url}
Concurrent Requests: {concurrent}
Total Requests: {requests}
Duration: {duration}s
        """,
        title="Load Test",
        border_style="blue"
    ))
    
    async def make_request(session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
        """Make a single API request."""
        start_time = time.time()
        try:
            async with session.get(f"{url}{endpoint}") as response:
                await response.text()
                end_time = time.time()
                return {
                    "status": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status < 400,
                }
        except Exception as e:
            end_time = time.time()
            return {
                "status": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
            }
    
    async def run_load_test():
        """Run the load test."""
        endpoints = [
            "/health",
            "/api/config",
            "/api/bot/status",
        ]
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running load test...", total=requests)
                
                for i in range(requests):
                    # Select endpoint round-robin
                    endpoint = endpoints[i % len(endpoints)]
                    
                    # Create concurrent requests
                    tasks = [make_request(session, endpoint) for _ in range(concurrent)]
                    batch_results = await asyncio.gather(*tasks)
                    results.extend(batch_results)
                    
                    progress.update(task, advance=concurrent)
                    
                    # Small delay between batches
                    await asyncio.sleep(0.1)
        
        return results
    
    # Run the test
    start_time = time.time()
    results = asyncio.run(run_load_test())
    end_time = time.time()
    
    # Analyze results
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r["success"])
    failed_requests = total_requests - successful_requests
    
    response_times = [r["response_time"] for r in results]
    avg_response_time = statistics.mean(response_times)
    min_response_time = min(response_times)
    max_response_time = max(response_times)
    p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
    p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
    
    total_time = end_time - start_time
    requests_per_second = total_requests / total_time
    
    # Display results
    table = Table(title="Load Test Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Requests", str(total_requests))
    table.add_row("Successful Requests", str(successful_requests))
    table.add_row("Failed Requests", str(failed_requests))
    table.add_row("Success Rate", f"{(successful_requests/total_requests)*100:.2f}%")
    table.add_row("Total Time", f"{total_time:.2f}s")
    table.add_row("Requests/Second", f"{requests_per_second:.2f}")
    table.add_row("Avg Response Time", f"{avg_response_time*1000:.2f}ms")
    table.add_row("Min Response Time", f"{min_response_time*1000:.2f}ms")
    table.add_row("Max Response Time", f"{max_response_time*1000:.2f}ms")
    table.add_row("95th Percentile", f"{p95_response_time*1000:.2f}ms")
    table.add_row("99th Percentile", f"{p99_response_time*1000:.2f}ms")
    
    console.print(table)
    
    # Status summary
    if successful_requests / total_requests >= 0.95:
        console.print("[green]✅ Load test PASSED - System handled load well[/green]")
    else:
        console.print("[red]❌ Load test FAILED - System struggled under load[/red]")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()