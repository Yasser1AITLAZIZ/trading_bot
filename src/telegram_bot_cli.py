"""CLI for testing and managing the Telegram bot."""

import asyncio
import signal
import sys
from typing import Optional

import structlog
import typer
from rich.console import Console
from rich.panel import Panel

from .communication.telegram_bot import TelegramBot
from .communication.notification_manager import NotificationManager, NotificationChannel, NotificationPriority

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
app = typer.Typer(help="Telegram Bot CLI - Test and manage the Telegram bot")


@app.command()
def test(
    bot_token: str = typer.Option(..., "--token", help="Telegram bot token"),
    user_id: int = typer.Option(..., "--user-id", help="Your Telegram user ID"),
):
    """Test the Telegram bot with a simple message."""
    
    console.print(Panel.fit(
        f"""
[bold]📱 Telegram Bot Test[/bold]

Bot Token: {bot_token[:10]}...
User ID: {user_id}

[bold]Instructions:[/bold]
1. Start a chat with your bot on Telegram
2. Send /start to initialize the bot
3. Use the commands to test functionality
4. Press Ctrl+C to stop the test
        """,
        title="Bot Test",
        border_style="blue"
    ))
    
    async def run_test():
        try:
            # Initialize bot
            bot = TelegramBot(
                bot_token=bot_token,
                allowed_users=[user_id],
            )
            
            # Start bot
            await bot.start()
            console.print("[green]✅ Telegram bot started successfully![/green]")
            console.print("[blue]📱 Send /start to your bot on Telegram to begin testing[/blue]")
            console.print("[yellow]Press Ctrl+C to stop the test[/yellow]")
            
            # Keep running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️  Stopping bot test...[/yellow]")
            
            # Stop bot
            await bot.stop()
            console.print("[green]✅ Bot test completed![/green]")
        
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(1)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        console.print("\n[yellow]⚠️  Received shutdown signal[/yellow]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run test
    asyncio.run(run_test())


@app.command()
def send_message(
    bot_token: str = typer.Option(..., "--token", help="Telegram bot token"),
    chat_id: int = typer.Option(..., "--chat-id", help="Chat ID to send message to"),
    message: str = typer.Option(..., "--message", help="Message to send"),
):
    """Send a test message to a specific chat."""
    
    async def send_test_message():
        try:
            # Initialize bot
            bot = TelegramBot(bot_token=bot_token)
            await bot.start()
            
            # Send message
            await bot.application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            
            console.print(f"[green]✅ Message sent successfully to chat {chat_id}[/green]")
            
            # Stop bot
            await bot.stop()
        
        except Exception as e:
            console.print(f"[red]❌ Error sending message: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(send_test_message())


@app.command()
def test_notifications():
    """Test notification system without Telegram."""
    
    console.print(Panel.fit(
        """
[bold]🔔 Notification System Test[/bold]

This will test the notification system without requiring a Telegram bot token.
        """,
        title="Notification Test",
        border_style="green"
    ))
    
    async def run_notification_test():
        try:
            # Initialize notification manager
            notification_manager = NotificationManager()
            
            console.print("[blue]📢 Sending test notifications...[/blue]")
            
            # Test different notification types
            test_notifications = [
                {
                    "title": "Test Info",
                    "message": "This is an informational notification",
                    "priority": NotificationPriority.LOW,
                },
                {
                    "title": "Test Warning",
                    "message": "This is a warning notification",
                    "priority": NotificationPriority.NORMAL,
                },
                {
                    "title": "Test Error",
                    "message": "This is an error notification",
                    "priority": NotificationPriority.HIGH,
                },
                {
                    "title": "Test Critical",
                    "message": "This is a critical notification",
                    "priority": NotificationPriority.URGENT,
                },
            ]
            
            for notif_data in test_notifications:
                from .communication.notification_manager import Notification
                
                notification = Notification(
                    title=notif_data["title"],
                    message=notif_data["message"],
                    priority=notif_data["priority"],
                    channels=[NotificationChannel.LOG],
                )
                
                success = await notification_manager.send_notification(notification)
                
                if success:
                    console.print(f"[green]✅ Sent: {notif_data['title']}[/green]")
                else:
                    console.print(f"[red]❌ Failed: {notif_data['title']}[/red]")
                
                await asyncio.sleep(0.5)
            
            # Get statistics
            stats = notification_manager.get_channel_statistics()
            console.print(f"\n[blue]📊 Statistics:[/blue]")
            console.print(f"Total sent: {stats['total_sent']}")
            console.print(f"Failed: {stats['failed_sends']}")
            console.print(f"Success rate: {stats['success_rate']:.1%}")
            
            console.print("\n[green]✅ Notification test completed![/green]")
        
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_notification_test())


@app.command()
def get_bot_info(
    bot_token: str = typer.Option(..., "--token", help="Telegram bot token"),
):
    """Get information about the Telegram bot."""
    
    async def get_info():
        try:
            # Initialize bot
            bot = TelegramBot(bot_token=bot_token)
            await bot.start()
            
            # Get bot info
            bot_info = await bot.application.bot.get_me()
            
            console.print(Panel.fit(
                f"""
[bold]🤖 Bot Information[/bold]

Name: {bot_info.first_name}
Username: @{bot_info.username}
ID: {bot_info.id}
Can Join Groups: {bot_info.can_join_groups}
Can Read All Group Messages: {bot_info.can_read_all_group_messages}
Supports Inline Queries: {bot_info.supports_inline_queries}
            """,
                title="Bot Info",
                border_style="blue"
            ))
            
            # Stop bot
            await bot.stop()
        
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(get_info())


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
