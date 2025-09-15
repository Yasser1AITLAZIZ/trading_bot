"""API server for trading bot monitoring and control."""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pandas as pd
from pathlib import Path

from ..core.settings import get_settings
from ..llm.factory import get_llm_client
from ..execution.binance_client import BinanceClient
from ..communication.telegram_bot import TelegramBot
from ..communication.notification_manager import NotificationPriority
from ..data.ingestion import DataIngestionService
from ..core.types import OHLCVData

logger = structlog.get_logger(__name__)


# Pydantic models for API
class ConnectivityTestRequest(BaseModel):
    """Request model for connectivity tests."""
    provider: str = Field(..., description="Provider to test (llm, binance, telegram)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for the test")


class ConnectivityTestResponse(BaseModel):
    """Response model for connectivity tests."""
    success: bool = Field(..., description="Whether the test was successful")
    message: str = Field(..., description="Test result message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional test details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConfigurationRequest(BaseModel):
    """Request model for configuration updates."""
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    binance_config: Dict[str, Any] = Field(default_factory=dict)
    telegram_config: Dict[str, Any] = Field(default_factory=dict)
    trading_config: Dict[str, Any] = Field(default_factory=dict)


class FileUploadResponse(BaseModel):
    """Response model for file uploads."""
    success: bool = Field(..., description="Whether the upload was successful")
    filename: str = Field(..., description="Uploaded filename")
    records_count: int = Field(..., description="Number of records processed")
    data_info: Dict[str, Any] = Field(default_factory=dict, description="Data information")
    message: str = Field(..., description="Upload result message")


class BotStartRequest(BaseModel):
    """Request model for starting the bot."""
    symbol: str = Field(..., description="Trading symbol")
    strategy: str = Field(default="llm", description="Trading strategy")
    llm_provider: str = Field(default="openai", description="LLM provider")
    mode: str = Field(default="paper", description="Trading mode")
    data_file: str = Field(..., description="Path to historical data file")


class LLMDecisionLog(BaseModel):
    """Model for LLM decision logging."""
    timestamp: datetime = Field(..., description="Decision timestamp")
    symbol: str = Field(..., description="Trading symbol")
    action: str = Field(..., description="Trading action (BUY/SELL/HOLD)")
    confidence: float = Field(..., description="Decision confidence (0-1)")
    reasoning: str = Field(..., description="LLM reasoning for the decision")
    market_data: Dict[str, Any] = Field(default_factory=dict, description="Market data at decision time")
    risk_score: float = Field(..., description="Risk assessment score")
    technical_indicators: Dict[str, Any] = Field(default_factory=dict, description="Technical indicators")


class TradingBotAPI:
    """API server for trading bot monitoring and control."""
    
    def __init__(self, trading_loop=None):
        """Initialize the API server.
        
        Args:
            trading_loop: Reference to trading loop
        """
        self.trading_loop = trading_loop
        self.settings = get_settings()
        self.data_service = DataIngestionService()
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # LLM decision log
        self.llm_decisions: List[LLMDecisionLog] = []
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="GenAI Trading Bot API",
            description="API for monitoring and controlling the GenAI Trading Bot",
            version="1.0.0"
        )
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:8000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Initialized Trading Bot API")
    
    def _setup_routes(self) -> None:
        """Setup API routes."""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}
        
        # Configuration endpoints
        @self.app.get("/api/config")
        async def get_configuration():
            """Get current configuration."""
            return {
                "llm": self.settings.llm.dict(),
                "binance": self.settings.binance.dict(),
                "telegram": {
                    "bot_token": self.settings.llm.telegram_bot_token,
                    "chat_id": self.settings.llm.telegram_chat_id,
                    "allowed_users": self.settings.llm.telegram_allowed_users,
                },
                "trading": self.settings.trading.dict(),
                "streaming": self.settings.streaming.dict(),
            }
        
        @self.app.post("/api/config")
        async def update_configuration(config: ConfigurationRequest):
            """Update configuration."""
            try:
                # Update settings (this would need to be implemented in settings)
                # For now, we'll just return success
                return {"success": True, "message": "Configuration updated"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Connectivity test endpoints
        @self.app.post("/api/test/connectivity", response_model=ConnectivityTestResponse)
        async def test_connectivity(request: ConnectivityTestRequest):
            """Test connectivity to external services."""
            try:
                if request.provider == "llm":
                    return await self._test_llm_connectivity(request.config)
                elif request.provider == "binance":
                    return await self._test_binance_connectivity(request.config)
                elif request.provider == "telegram":
                    return await self._test_telegram_connectivity(request.config)
                else:
                    raise HTTPException(status_code=400, detail="Invalid provider")
            except Exception as e:
                return ConnectivityTestResponse(
                    success=False,
                    message=f"Test failed: {str(e)}",
                    details={"error": str(e)}
                )
        
        # File upload endpoints
        @self.app.post("/api/upload/data", response_model=FileUploadResponse)
        async def upload_historical_data(file: UploadFile = File(...)):
            """Upload historical data file."""
            try:
                # Validate file type
                if not file.filename.endswith('.csv'):
                    raise HTTPException(status_code=400, detail="Only CSV files are supported")
                
                # Read file content
                content = await file.read()
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
                    tmp_file.write(content)
                    tmp_file_path = tmp_file.name
                
                try:
                    # Validate and process data
                    df = pd.read_csv(tmp_file_path)
                    data_info = self.data_service.validate_data_quality(df.to_dict('records'))
                    
                    if not data_info["valid"]:
                        raise HTTPException(status_code=400, detail=f"Invalid data: {', '.join(data_info['issues'])}")
                    
                    # Save to data directory
                    data_dir = Path("data/historical")
                    data_dir.mkdir(parents=True, exist_ok=True)
                    
                    final_path = data_dir / file.filename
                    df.to_csv(final_path, index=False)
                    
                    return FileUploadResponse(
                        success=True,
                        filename=file.filename,
                        records_count=len(df),
                        data_info=data_info,
                        message="Data uploaded successfully"
                    )
                
                finally:
                    # Clean up temporary file
                    os.unlink(tmp_file_path)
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # Bot control endpoints
        @self.app.post("/api/bot/start")
        async def start_bot(request: BotStartRequest):
            """Start the trading bot."""
            try:
                if self.trading_loop and self.trading_loop.running:
                    return {"success": False, "message": "Bot is already running"}
                
                # This would start the bot (implementation depends on your bot structure)
                return {"success": True, "message": "Bot start requested"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/api/bot/stop")
        async def stop_bot():
            """Stop the trading bot."""
            try:
                if self.trading_loop:
                    await self.trading_loop.stop()
                return {"success": True, "message": "Bot stopped"}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/bot/status")
        async def get_bot_status():
            """Get bot status."""
            if self.trading_loop:
                return self.trading_loop.get_status()
            else:
                return {"running": False, "message": "Bot not initialized"}
        
        # LLM decision logging
        @self.app.post("/api/llm/decision")
        async def log_llm_decision(decision: LLMDecisionLog):
            """Log an LLM decision."""
            self.llm_decisions.append(decision)
            return {"success": True, "message": "Decision logged"}
        
        @self.app.get("/api/llm/decisions")
        async def get_llm_decisions(limit: int = 100):
            """Get LLM decision history."""
            return {
                "decisions": [d.dict() for d in self.llm_decisions[-limit:]],
                "total_count": len(self.llm_decisions)
            }
        
        # WebSocket endpoint for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
    
    async def _test_llm_connectivity(self, config: Dict[str, Any]) -> ConnectivityTestResponse:
        """Test LLM connectivity."""
        try:
            provider = config.get("provider", self.settings.llm.primary_provider)
            llm_client = get_llm_client(provider)
            
            # Test with simple prompt
            test_prompt = "Hello, this is a connectivity test. Please respond with 'OK'."
            response = llm_client.generate(test_prompt)
            
            if response and len(response) > 0:
                return ConnectivityTestResponse(
                    success=True,
                    message=f"LLM {provider} is responding correctly",
                    details={
                        "provider": provider,
                        "response_length": len(response),
                        "response_preview": response[:100] + "..." if len(response) > 100 else response
                    }
                )
            else:
                return ConnectivityTestResponse(
                    success=False,
                    message=f"LLM {provider} returned empty response",
                    details={"provider": provider}
                )
        except Exception as e:
            return ConnectivityTestResponse(
                success=False,
                message=f"LLM connectivity test failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _test_binance_connectivity(self, config: Dict[str, Any]) -> ConnectivityTestResponse:
        """Test Binance API connectivity."""
        try:
            mode = config.get("mode", self.settings.binance.mode)
            binance_client = BinanceClient(mode)
            
            # Test API connectivity
            account_info = binance_client.get_account_info()
            
            if account_info:
                return ConnectivityTestResponse(
                    success=True,
                    message=f"Binance API is responding (mode: {mode})",
                    details={
                        "mode": mode,
                        "account_type": account_info.get("accountType", "unknown"),
                        "can_trade": account_info.get("canTrade", False)
                    }
                )
            else:
                return ConnectivityTestResponse(
                    success=False,
                    message="Binance API returned empty response",
                    details={"mode": mode}
                )
        except Exception as e:
            return ConnectivityTestResponse(
                success=False,
                message=f"Binance connectivity test failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _test_telegram_connectivity(self, config: Dict[str, Any]) -> ConnectivityTestResponse:
        """Test Telegram bot connectivity."""
        try:
            bot_token = config.get("bot_token", self.settings.llm.telegram_bot_token)
            
            if not bot_token:
                return ConnectivityTestResponse(
                    success=False,
                    message="Telegram bot token not configured",
                    details={"error": "Missing bot token"}
                )
            
            # Test bot connectivity
            telegram_bot = TelegramBot(
                bot_token=bot_token,
                trading_loop=None,
                alert_manager=None
            )
            
            # Get bot info
            bot_info = await telegram_bot.get_bot_info()
            
            return ConnectivityTestResponse(
                success=True,
                message="Telegram bot is responding correctly",
                details={
                    "bot_username": bot_info.get("username", "unknown"),
                    "bot_name": bot_info.get("first_name", "unknown"),
                    "can_join_groups": bot_info.get("can_join_groups", False)
                }
            )
        except Exception as e:
            return ConnectivityTestResponse(
                success=False,
                message=f"Telegram connectivity test failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def broadcast_update(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast update to all connected WebSocket clients."""
        if not self.active_connections:
            return
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.active_connections.remove(connection)


# Global API instance
api_instance: Optional[TradingBotAPI] = None


def get_api() -> TradingBotAPI:
    """Get the global API instance."""
    global api_instance
    if api_instance is None:
        api_instance = TradingBotAPI()
    return api_instance


def create_app(trading_loop=None) -> FastAPI:
    """Create FastAPI application."""
    global api_instance
    api_instance = TradingBotAPI(trading_loop)
    return api_instance.app
