"""Example of using the autonomous trading bot with the new architecture."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from src.core.types import OHLCVData
from src.trading.trading_loop import AutonomousTradingLoop
from src.streaming.data_buffer import DataBuffer


async def example_autonomous_trading():
    """Example of autonomous trading with simulated data."""
    
    # Create sample historical data (8 hours of 1-minute data)
    historical_data = []
    base_price = 50000
    base_time = datetime.now(timezone.utc)
    
    for i in range(480):  # 8 hours = 480 minutes
        price = base_price + (i * 10)  # Simulate upward trend
        timestamp = base_time.replace(minute=i % 60, hour=base_time.hour + (i // 60))
        
        historical_data.append(OHLCVData(
            timestamp=timestamp,
            open=Decimal(str(price)),
            high=Decimal(str(price + 50)),
            low=Decimal(str(price - 50)),
            close=Decimal(str(price + 25)),
            volume=Decimal("1000.0"),
            symbol="BTCUSDT"
        ))
    
    print(f"Created {len(historical_data)} historical data points")
    print(f"Time range: {historical_data[0].timestamp} to {historical_data[-1].timestamp}")
    
    # Initialize trading loop
    trading_loop = AutonomousTradingLoop(
        symbol="BTCUSDT",
        initial_data=historical_data,
        strategy_name="llm",
        llm_provider="openai",
        on_decision=on_trading_decision,
        on_error=on_error,
    )
    
    # Start trading loop
    await trading_loop.start()
    
    # Simulate adding new data points
    for i in range(10):  # Add 10 more minutes of data
        new_price = base_price + (480 + i) * 10
        new_timestamp = historical_data[-1].timestamp.replace(
            minute=(historical_data[-1].timestamp.minute + 1) % 60,
            hour=historical_data[-1].timestamp.hour + ((historical_data[-1].timestamp.minute + 1) // 60)
        )
        
        new_candle = OHLCVData(
            timestamp=new_timestamp,
            open=Decimal(str(new_price)),
            high=Decimal(str(new_price + 50)),
            low=Decimal(str(new_price - 50)),
            close=Decimal(str(new_price + 25)),
            volume=Decimal("1000.0"),
            symbol="BTCUSDT"
        )
        
        trading_loop.add_new_candle(new_candle)
        print(f"Added new candle: {new_candle.timestamp} - Price: {new_candle.close}")
        
        # Wait a bit between candles
        await asyncio.sleep(1)
    
    # Let it run for a bit
    await asyncio.sleep(30)
    
    # Stop trading loop
    await trading_loop.stop()
    
    # Display final status
    status = trading_loop.get_status()
    print("\n=== Final Status ===")
    print(f"Analysis Count: {status['analysis_count']}")
    print(f"Decision Count: {status['decision_count']}")
    print(f"Order Count: {status['order_count']}")


def on_trading_decision(decision):
    """Handle trading decision callback."""
    print(f"\n🤖 Trading Decision:")
    print(f"Action: {decision.action.value if decision.action else 'HOLD'}")
    print(f"Symbol: {decision.symbol}")
    print(f"Quantity: {decision.quantity}")
    print(f"Price: ${decision.price}")
    print(f"Confidence: {decision.confidence:.1%}")
    print(f"Reasoning: {decision.reasoning}")


def on_error(error):
    """Handle error callback."""
    print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    print("🚀 Starting Autonomous Trading Example")
    asyncio.run(example_autonomous_trading())
    print("✅ Example completed")
