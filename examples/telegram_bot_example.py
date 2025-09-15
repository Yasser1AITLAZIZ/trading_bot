"""Example of using the Telegram bot for trading bot communication with the new architecture."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from src.core.types import OHLCVData, TradingDecision, TradingAction
from src.communication.telegram_bot import TelegramBot
from src.communication.notification_manager import NotificationManager, NotificationChannel


async def example_telegram_bot():
    """Example of Telegram bot functionality."""
    
    print("📱 Starting Telegram Bot Example")
    
    # Note: You need to set TELEGRAM_BOT_TOKEN in your environment
    # Get your bot token from @BotFather on Telegram
    
    # Initialize notification manager
    notification_manager = NotificationManager()
    
    # Register Telegram channel (you would need a real bot token)
    # notification_manager.register_channel(
    #     NotificationChannel.TELEGRAM,
    #     lambda notif: print(f"📱 Telegram: {notif.title} - {notif.message}"),
    #     {"bot_token": "YOUR_BOT_TOKEN"}
    # )
    
    print("📱 Notification manager initialized")
    
    # Simulate trading decisions
    decisions = [
        TradingDecision(
            action=TradingAction.BUY,
            symbol="BTCUSDT",
            quantity=Decimal("0.001"),
            price=Decimal("50000.0"),
            confidence=0.85,
            reasoning="Strong bullish momentum with RSI oversold and volume spike",
            risk_score=0.25,
        ),
        TradingDecision(
            action=TradingAction.SELL,
            symbol="BTCUSDT",
            quantity=Decimal("0.001"),
            price=Decimal("51000.0"),
            confidence=0.78,
            reasoning="Profit target reached with resistance at 51k level",
            risk_score=0.15,
        ),
        TradingDecision(
            action=None,  # HOLD
            symbol="BTCUSDT",
            quantity=Decimal("0.0"),
            price=Decimal("50500.0"),
            confidence=0.45,
            reasoning="Market consolidating, waiting for clearer direction",
            risk_score=0.35,
        ),
    ]
    
    print("🎯 Simulating trading decisions...")
    
    # Send trading decision notifications
    for i, decision in enumerate(decisions):
        print(f"\n📊 Decision {i+1}:")
        print(f"Action: {decision.action.value if decision.action else 'HOLD'}")
        print(f"Symbol: {decision.symbol}")
        print(f"Confidence: {decision.confidence:.1%}")
        print(f"Reasoning: {decision.reasoning}")
        
        # Send notification
        await notification_manager.send_trading_decision_notification(decision)
        
        # Wait between decisions
        await asyncio.sleep(2)
    
    print("\n🚨 Simulating system alerts...")
    
    # Send system notifications
    system_notifications = [
        {
            "title": "Bot Started",
            "message": "Trading bot has started successfully",
            "priority": "normal"
        },
        {
            "title": "High Risk Alert",
            "message": "Risk limit exceeded: 5.2% daily loss",
            "priority": "urgent"
        },
        {
            "title": "Data Stale",
            "message": "Market data is 2.5 hours old",
            "priority": "high"
        },
    ]
    
    for notif_data in system_notifications:
        print(f"\n📢 {notif_data['title']}: {notif_data['message']}")
        
        await notification_manager.send_system_notification(
            title=notif_data['title'],
            message=notif_data['message'],
            priority=notif_data['priority']
        )
        
        await asyncio.sleep(1)
    
    print("\n📊 Getting notification statistics...")
    
    # Get statistics
    stats = notification_manager.get_channel_statistics()
    print(f"Total notifications sent: {stats['total_sent']}")
    print(f"Failed sends: {stats['failed_sends']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    
    # Get summary
    summary = notification_manager.get_notification_summary(hours=1)
    print(f"\nSummary (last hour):")
    print(f"Total notifications: {summary['total_notifications']}")
    print(f"Most common priority: {summary['most_common_priority']}")
    
    print("\n✅ Telegram bot example completed")
    print("\n📱 To use the real Telegram bot:")
    print("1. Create a bot with @BotFather on Telegram")
    print("2. Get your bot token")
    print("3. Set TELEGRAM_BOT_TOKEN environment variable")
    print("4. Start the autonomous trading bot")
    print("5. Send /start to your bot on Telegram")


async def example_telegram_commands():
    """Example of Telegram bot commands."""
    
    print("\n🤖 Telegram Bot Commands Example")
    print("Available commands when using the real bot:")
    
    commands = [
        ("/start", "Welcome message and quick access buttons"),
        ("/help", "Show all available commands"),
        ("/status", "Get current bot status and metrics"),
        ("/orders", "View current orders and order history"),
        ("/decisions", "View recent trading decisions"),
        ("/performance", "View performance statistics"),
        ("/alerts", "View recent alerts and warnings"),
        ("/config", "View current configuration"),
        ("/start_bot", "Start the trading bot"),
        ("/stop", "Stop the trading bot"),
    ]
    
    for command, description in commands:
        print(f"  {command:<15} - {description}")
    
    print("\n📱 Quick Access Buttons:")
    print("  📊 Status      - Get bot status")
    print("  📋 Orders      - View orders")
    print("  🎯 Decisions   - View decisions")
    print("  📈 Performance - View performance")
    print("  🚨 Alerts      - View alerts")
    print("  ⚙️ Config      - View configuration")
    
    print("\n🔒 Security:")
    print("  - Only allowed users can use the bot")
    print("  - Set TELEGRAM_ALLOWED_USERS environment variable")
    print("  - Format: TELEGRAM_ALLOWED_USERS=123456789,987654321")


if __name__ == "__main__":
    print("📱 Telegram Bot Communication Example")
    print("This example demonstrates:")
    print("• Trading decision notifications")
    print("• System alert notifications")
    print("• Notification channel management")
    print("• Telegram bot command structure")
    print()
    
    asyncio.run(example_telegram_bot())
    asyncio.run(example_telegram_commands())
