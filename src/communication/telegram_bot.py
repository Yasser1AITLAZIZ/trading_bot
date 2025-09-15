"""Telegram bot for trading bot communication and control."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from ..core.settings import get_settings
from ..core.types import TradingDecision, TradingMode
from ..monitoring.alerts import Alert, AlertLevel, AlertType

logger = structlog.get_logger(__name__)


class TelegramBotError(Exception):
    """Exception raised during Telegram bot operations."""
    pass


class TelegramBot:
    """Telegram bot for trading bot communication and control."""
    
    def __init__(
        self,
        bot_token: str,
        trading_loop=None,
        alert_manager=None,
        allowed_users: Optional[List[int]] = None,
    ):
        """Initialize the Telegram bot.
        
        Args:
            bot_token: Telegram bot token
            trading_loop: Reference to trading loop
            alert_manager: Reference to alert manager
            allowed_users: List of allowed user IDs (None for all users)
        """
        self.bot_token = bot_token
        self.trading_loop = trading_loop
        self.alert_manager = alert_manager
        self.allowed_users = allowed_users or []
        
        self.settings = get_settings()
        self.running = False
        
        # Initialize Telegram application
        self.application = Application.builder().token(bot_token).build()
        
        # Setup handlers
        self._setup_handlers()
        
        # Statistics
        self.message_count = 0
        self.command_count = 0
        self.start_time = None
        
        logger.info("Initialized Telegram bot", allowed_users_count=len(self.allowed_users))
    
    def _setup_handlers(self) -> None:
        """Setup Telegram bot handlers."""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("orders", self._handle_orders))
        self.application.add_handler(CommandHandler("decisions", self._handle_decisions))
        self.application.add_handler(CommandHandler("performance", self._handle_performance))
        self.application.add_handler(CommandHandler("alerts", self._handle_alerts))
        self.application.add_handler(CommandHandler("stop", self._handle_stop))
        self.application.add_handler(CommandHandler("start_bot", self._handle_start_bot))
        self.application.add_handler(CommandHandler("config", self._handle_config))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Message handler for unknown commands
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_unknown))
        
        logger.info("Setup Telegram bot handlers")
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        if self.running:
            logger.warning("Telegram bot is already running")
            return
        
        try:
            self.running = True
            self.start_time = datetime.now(timezone.utc)
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
        
        except Exception as e:
            logger.error("Failed to start Telegram bot", error=str(e))
            raise TelegramBotError(f"Failed to start bot: {e}")
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Stop the bot
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("Telegram bot stopped")
        
        except Exception as e:
            logger.error("Error stopping Telegram bot", error=str(e))
    
    def _check_user_permission(self, user_id: int) -> bool:
        """Check if user has permission to use the bot.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if user has permission
        """
        if not self.allowed_users:
            return True  # No restrictions
        
        return user_id in self.allowed_users
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        welcome_text = """
🤖 **GenAI Trading Bot**

Welcome to the trading bot control panel!

**Available Commands:**
/status - Get bot status
/orders - View current orders
/decisions - View recent decisions
/performance - View performance metrics
/alerts - View recent alerts
/config - View configuration
/help - Show this help message

**Control Commands:**
/start_bot - Start trading bot
/stop - Stop trading bot

Use the buttons below for quick access:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("📋 Orders", callback_data="orders"),
            ],
            [
                InlineKeyboardButton("🎯 Decisions", callback_data="decisions"),
                InlineKeyboardButton("📈 Performance", callback_data="performance"),
            ],
            [
                InlineKeyboardButton("🚨 Alerts", callback_data="alerts"),
                InlineKeyboardButton("⚙️ Config", callback_data="config"),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        self.command_count += 1
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        help_text = """
🤖 **GenAI Trading Bot - Help**

**Status Commands:**
/status - Get current bot status and metrics
/orders - View open orders and order history
/decisions - View recent trading decisions
/performance - View performance statistics
/alerts - View recent alerts and warnings

**Control Commands:**
/start_bot - Start the trading bot
/stop - Stop the trading bot
/config - View current configuration

**Information Commands:**
/help - Show this help message

**Quick Actions:**
Use the inline keyboard buttons for quick access to common functions.

**Note:** All commands require proper permissions.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        self.command_count += 1
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.trading_loop:
            await update.message.reply_text("❌ Trading loop not available.")
            return
        
        try:
            status = self.trading_loop.get_status()
            
            status_text = f"""
🤖 **Trading Bot Status**

**Basic Info:**
• Symbol: {status.get('symbol', 'N/A')}
• Strategy: {status.get('strategy', 'N/A')}
• LLM Provider: {status.get('llm_provider', 'N/A')}
• Running: {'✅ Yes' if status.get('running') else '❌ No'}

**Performance:**
• Analysis Count: {status.get('analysis_count', 0)}
• Decision Count: {status.get('decision_count', 0)}
• Order Count: {status.get('order_count', 0)}

**Data Buffer:**
• Size: {status.get('buffer_info', {}).get('current_size', 0)}/{status.get('buffer_info', {}).get('max_size', 0)}
• Utilization: {status.get('buffer_info', {}).get('utilization', 0):.1%}
• Last Update: {status.get('buffer_info', {}).get('last_update', 'N/A')}

**Orders:**
• Open Orders: {status.get('order_manager_status', {}).get('open_orders', 0)}/{status.get('order_manager_status', {}).get('max_orders', 0)}
• Total Orders: {status.get('order_manager_status', {}).get('total_orders', 0)}
• Success Rate: {status.get('order_manager_status', {}).get('success_rate', 0):.1%}
            """
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error getting status", error=str(e))
            await update.message.reply_text(f"❌ Error getting status: {str(e)}")
    
    async def _handle_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /orders command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.trading_loop:
            await update.message.reply_text("❌ Trading loop not available.")
            return
        
        try:
            order_manager = self.trading_loop.order_manager
            open_orders = order_manager.get_open_orders()
            order_history = order_manager.get_order_history(limit=10)
            performance = order_manager.get_performance_metrics()
            
            orders_text = f"""
📋 **Orders Status**

**Open Orders:** {len(open_orders)}
"""
            
            if open_orders:
                for order_id, order in open_orders.items():
                    orders_text += f"""
• Order {order_id[:8]}...
  - Side: {order.side.value}
  - Quantity: {order.quantity}
  - Status: {order.status.value}
  - Price: ${order.price}
"""
            
            orders_text += f"""

**Performance:**
• Total Orders: {performance.get('total_orders', 0)}
• Successful: {performance.get('successful_orders', 0)}
• Success Rate: {performance.get('success_rate', 0):.1%}
• Total Volume: {performance.get('total_volume', 0):.2f}

**Recent Orders:**
"""
            
            if order_history:
                for order in order_history[-5:]:  # Last 5 orders
                    orders_text += f"""
• {order.side.value} {order.quantity} @ ${order.price}
  Status: {order.status.value}
"""
            else:
                orders_text += "No recent orders."
            
            await update.message.reply_text(orders_text, parse_mode='Markdown')
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error getting orders", error=str(e))
            await update.message.reply_text(f"❌ Error getting orders: {str(e)}")
    
    async def _handle_decisions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /decisions command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.trading_loop:
            await update.message.reply_text("❌ Trading loop not available.")
            return
        
        try:
            state_manager = self.trading_loop.state_manager
            decisions = state_manager.get_decision_history(limit=10)
            
            decisions_text = """
🎯 **Recent Trading Decisions**

"""
            
            if decisions:
                for decision in decisions:
                    action_emoji = "🟢" if decision['action'] == 'BUY' else "🔴" if decision['action'] == 'SELL' else "⏸️"
                    decisions_text += f"""
{action_emoji} **{decision['action']}** {decision['quantity']} @ ${decision['price'] or 'Market'}
• Confidence: {decision['confidence']:.1%}
• Risk Score: {decision['risk_score']:.1%}
• Time: {decision['timestamp']}
• Reasoning: {decision['reasoning'][:100]}{'...' if len(decision['reasoning']) > 100 else ''}

"""
            else:
                decisions_text += "No recent decisions."
            
            await update.message.reply_text(decisions_text, parse_mode='Markdown')
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error getting decisions", error=str(e))
            await update.message.reply_text(f"❌ Error getting decisions: {str(e)}")
    
    async def _handle_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /performance command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.trading_loop:
            await update.message.reply_text("❌ Trading loop not available.")
            return
        
        try:
            status = self.trading_loop.get_status()
            order_manager = self.trading_loop.order_manager
            performance = order_manager.get_performance_metrics()
            
            performance_text = f"""
📈 **Performance Metrics**

**Trading Activity:**
• Analysis Count: {status.get('analysis_count', 0)}
• Decision Count: {status.get('decision_count', 0)}
• Order Count: {status.get('order_count', 0)}

**Order Performance:**
• Total Orders: {performance.get('total_orders', 0)}
• Successful Orders: {performance.get('successful_orders', 0)}
• Success Rate: {performance.get('success_rate', 0):.1%}
• Total Volume: {performance.get('total_volume', 0):.2f}
• Average Volume: {performance.get('average_volume', 0):.2f}

**System Health:**
• Buffer Utilization: {status.get('buffer_info', {}).get('utilization', 0):.1%}
• Data Points: {status.get('buffer_info', {}).get('current_size', 0)}/{status.get('buffer_info', {}).get('max_size', 0)}
• Uptime: {status.get('start_time', 'N/A')}
            """
            
            await update.message.reply_text(performance_text, parse_mode='Markdown')
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error getting performance", error=str(e))
            await update.message.reply_text(f"❌ Error getting performance: {str(e)}")
    
    async def _handle_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /alerts command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.alert_manager:
            await update.message.reply_text("❌ Alert manager not available.")
            return
        
        try:
            alerts = self.alert_manager.get_alert_history(limit=10)
            alert_summary = self.alert_manager.get_alert_summary(hours=24)
            
            alerts_text = f"""
🚨 **Recent Alerts**

**Summary (24h):**
• Total Alerts: {alert_summary.get('total_alerts', 0)}
• Most Common: {alert_summary.get('most_common_type', 'None')}
• Most Common Level: {alert_summary.get('most_common_level', 'None')}

**Recent Alerts:**
"""
            
            if alerts:
                for alert in alerts:
                    level_emoji = {
                        AlertLevel.INFO: "ℹ️",
                        AlertLevel.WARNING: "⚠️",
                        AlertLevel.ERROR: "❌",
                        AlertLevel.CRITICAL: "🚨"
                    }.get(alert.level, "📝")
                    
                    alerts_text += f"""
{level_emoji} **{alert.level.value.upper()}** - {alert.alert_type.value}
• Message: {alert.message}
• Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

"""
            else:
                alerts_text += "No recent alerts."
            
            await update.message.reply_text(alerts_text, parse_mode='Markdown')
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error getting alerts", error=str(e))
            await update.message.reply_text(f"❌ Error getting alerts: {str(e)}")
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.trading_loop:
            await update.message.reply_text("❌ Trading loop not available.")
            return
        
        try:
            await self.trading_loop.stop()
            await update.message.reply_text("🛑 Trading bot stopped successfully!")
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error stopping trading loop", error=str(e))
            await update.message.reply_text(f"❌ Error stopping bot: {str(e)}")
    
    async def _handle_start_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start_bot command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        if not self.trading_loop:
            await update.message.reply_text("❌ Trading loop not available.")
            return
        
        try:
            if self.trading_loop.running:
                await update.message.reply_text("✅ Trading bot is already running!")
            else:
                await self.trading_loop.start()
                await update.message.reply_text("🚀 Trading bot started successfully!")
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error starting trading loop", error=str(e))
            await update.message.reply_text(f"❌ Error starting bot: {str(e)}")
    
    async def _handle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /config command."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        try:
            config_text = f"""
⚙️ **Bot Configuration**

**Trading Settings:**
• Max Concurrent Orders: {self.settings.trading.max_concurrent_orders}
• Max Daily Trades: {self.settings.trading.max_daily_trades}
• Max Daily Loss: {self.settings.trading.max_daily_loss:.1%}
• Trading Enabled: {self.settings.trading.trading_enabled}

**Streaming Settings:**
• Analysis Interval: {self.settings.streaming.analysis_interval}s
• Buffer Max Size: {self.settings.streaming.buffer_max_size}
• WebSocket Retry Attempts: {self.settings.streaming.websocket_retry_attempts}

**LLM Settings:**
• Primary Provider: {self.settings.llm.primary_provider}
• Max Requests/Min: {self.settings.llm.max_requests_per_minute}
• Fallback Providers: {', '.join(self.settings.llm.fallback_providers)}

**Binance Settings:**
• Mode: {self.settings.binance.mode}
• Max Risk Per Trade: {self.settings.binance.max_risk_per_trade:.1%}
            """
            
            await update.message.reply_text(config_text, parse_mode='Markdown')
            self.command_count += 1
        
        except Exception as e:
            logger.error("Error getting config", error=str(e))
            await update.message.reply_text(f"❌ Error getting config: {str(e)}")
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self._check_user_permission(user_id):
            await query.answer("❌ You don't have permission to use this bot.")
            return
        
        await query.answer()
        
        # Handle different callback data
        if query.data == "status":
            await self._handle_status(update, context)
        elif query.data == "orders":
            await self._handle_orders(update, context)
        elif query.data == "decisions":
            await self._handle_decisions(update, context)
        elif query.data == "performance":
            await self._handle_performance(update, context)
        elif query.data == "alerts":
            await self._handle_alerts(update, context)
        elif query.data == "config":
            await self._handle_config(update, context)
    
    async def _handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle unknown messages."""
        user_id = update.effective_user.id
        
        if not self._check_user_permission(user_id):
            await update.message.reply_text("❌ You don't have permission to use this bot.")
            return
        
        await update.message.reply_text(
            "❓ Unknown command. Use /help to see available commands."
        )
    
    async def send_alert_notification(self, alert: Alert) -> None:
        """Send alert notification to all allowed users.
        
        Args:
            alert: Alert to send
        """
        if not self.running:
            return
        
        try:
            level_emoji = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }.get(alert.level, "📝")
            
            message = f"""
{level_emoji} **{alert.level.value.upper()} Alert**

**Type:** {alert.alert_type.value}
**Message:** {alert.message}
**Time:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Send to all allowed users
            if self.allowed_users:
                for user_id in self.allowed_users:
                    try:
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error("Failed to send alert to user", user_id=user_id, error=str(e))
            else:
                # If no restrictions, we can't send to all users
                logger.warning("Cannot send alert notification - no allowed users configured")
        
        except Exception as e:
            logger.error("Error sending alert notification", error=str(e))
    
    async def send_trading_decision(self, decision: TradingDecision) -> None:
        """Send trading decision notification.
        
        Args:
            decision: Trading decision to send
        """
        if not self.running:
            return
        
        try:
            action_emoji = "🟢" if decision.action.value == "BUY" else "🔴" if decision.action.value == "SELL" else "⏸️"
            
            message = f"""
{action_emoji} **Trading Decision**

**Action:** {decision.action.value if decision.action else 'HOLD'}
**Symbol:** {decision.symbol}
**Quantity:** {decision.quantity}
**Price:** ${decision.price or 'Market'}
**Confidence:** {decision.confidence:.1%}
**Risk Score:** {decision.risk_score:.1%}

**Reasoning:**
{decision.reasoning}
            """
            
            # Send to all allowed users
            if self.allowed_users:
                for user_id in self.allowed_users:
                    try:
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error("Failed to send decision to user", user_id=user_id, error=str(e))
        
        except Exception as e:
            logger.error("Error sending trading decision", error=str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get Telegram bot status.
        
        Returns:
            Dictionary with bot status
        """
        return {
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "message_count": self.message_count,
            "command_count": self.command_count,
            "allowed_users_count": len(self.allowed_users),
            "trading_loop_available": self.trading_loop is not None,
            "alert_manager_available": self.alert_manager is not None,
        }
