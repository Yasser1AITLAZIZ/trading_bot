# GenAI Trading Bot

A modular, AI-powered trading bot that analyzes historical trading data using Large Language Models (LLMs) and executes trades via the Binance API. Built with Python 3.9+ and designed for extensibility and safety.

## 🚀 Features

- **Multi-LLM Support**: OpenAI, Anthropic Claude, and Google Gemini
- **Modular Architecture**: Pluggable strategies and extensible design
- **Risk Management**: Built-in risk controls and position sizing
- **Multiple Trading Modes**: Paper trading, testnet, and live trading
- **Technical Analysis**: RSI, moving averages, ATR, and volatility indicators
- **Data Validation**: Comprehensive data quality checks
- **Structured Logging**: JSON logging with correlation IDs
- **CLI Interface**: Rich command-line interface with progress indicators
- **🌐 Web Dashboard**: Real-time monitoring interface with live updates
- **📡 WebSocket Streaming**: Continuous data streaming from Binance
- **🚨 Alert System**: Configurable alerts for trading events and system health
- **💾 State Persistence**: Automatic state saving and recovery
- **🔄 Autonomous Operation**: Continuous trading with minimal intervention
- **📱 Telegram Integration**: Remote control and notifications via Telegram bot
- **🔔 Multi-Channel Notifications**: Log, Telegram, and webhook notifications

## 🏗️ Architecture

```
src/
├── api/            # FastAPI server for Next.js UI
├── core/           # Core types, settings, and utilities
├── data/           # Data ingestion, validation, and feature engineering
├── llm/            # Multi-provider LLM client abstraction
├── strategy/       # Pluggable trading strategies
├── execution/      # Trade execution and risk management
├── streaming/      # Real-time data streaming and buffering
├── trading/        # Autonomous trading loop and order management
├── monitoring/     # Alert system and dashboard components
├── communication/  # Telegram bot and notification system
├── app.py          # Main CLI orchestrator
├── autonomous_trading.py  # Autonomous trading bot
├── api_cli.py      # API server CLI
└── telegram_bot_cli.py    # Telegram bot CLI

ui/                 # Next.js frontend application
├── app/            # Next.js app router pages
│   ├── config/     # Configuration and startup page
│   ├── dashboard/  # Performance monitoring dashboard
│   └── journal/    # Trading journal and logs
├── components/     # Reusable React components
└── styles/         # Tailwind CSS styles
```

### Key Components

- **Data Module**: Handles CSV/JSON/Parquet data ingestion with validation
- **LLM Abstraction**: Unified interface for multiple LLM providers
- **Strategy Framework**: Protocol-based strategy system with LLM and technical strategies
- **Execution Engine**: Binance API integration with risk management
- **Order Router**: Manages trade execution across different modes
- **Streaming Module**: Real-time WebSocket data streaming and circular buffer management
- **Trading Module**: Autonomous trading loop with continuous analysis and order management
- **API Module**: FastAPI server for Next.js frontend integration
- **Monitoring Module**: Alert system and performance metrics
- **State Management**: Persistent state storage and recovery for trading sessions
- **Communication Module**: Telegram bot integration and multi-channel notifications
- **Next.js UI**: Modern web interface with configuration, dashboard, and journal pages
- **Notification System**: Configurable alerts across multiple channels (Log, Telegram, Webhook)

## 📦 Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd trading_bot
```

2. **Install dependencies**:
```bash
pip install -e .
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## 🔧 Configuration

Create a `.env` file with your API keys:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Binance API Keys (for testnet/live trading)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here

# Application Settings
ENVIRONMENT=development
DEBUG=true
BINANCE_MODE=paper

# Telegram Bot (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

## 🚀 Quick Start

### 1. Validate Sample Data
```bash
python -m src.app validate-data --data examples/sample_data.csv
```

### 2. Test LLM Connectivity
```bash
python -m src.app test-llm --provider openai
```

### 3. Run Trading Bot (Paper Mode)
```bash
python -m src.app run \
  --data examples/sample_data.csv \
  --symbol BTCUSDT \
  --strategy llm \
  --llm-provider openai \
  --mode paper \
  --risk 0.01 \
  --confidence 0.7
```

### 4. Start Autonomous Trading Bot
```bash
python -m src.autonomous_trading start \
  --data examples/sample_data.csv \
  --symbol BTCUSDT \
  --strategy llm \
  --llm-provider openai \
  --mode paper
```

### 5. Start API Server
```bash
python -m src.api_cli
# Or use the script
api-server
```

### 6. Test Telegram Bot
```bash
# Test notifications
python -m src.telegram_bot_cli test-notifications

# Test bot with token
python -m src.telegram_bot_cli test --token YOUR_BOT_TOKEN --user-id YOUR_USER_ID

# Get bot information
python -m src.telegram_bot_cli get-bot-info --token YOUR_BOT_TOKEN
```

### 7. Docker Deployment (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up -d

# Access the Next.js UI
open http://localhost:3000

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### 8. Production Deployment
```bash
# Health check
python -m scripts.health_check

# Create backup
python -m scripts.backup_restore create

# Start in production mode
python -m scripts.start_bot start --data your_data.csv --symbol BTCUSDT

# Run tests
python -m scripts.run_tests all
```

## 📊 Example Usage

### LLM-Powered Strategy
```bash
python -m src.app run \
  --data examples/sample_data.csv \
  --strategy llm \
  --llm-provider openai \
  --mode paper
```

### Technical Analysis Strategy
```bash
python -m src.app run \
  --data examples/sample_data.csv \
  --strategy technical \
  --mode paper
```

### Live Trading (⚠️ Use with caution)
```bash
python -m src.app run \
  --data examples/sample_data.csv \
  --strategy llm \
  --mode live \
  --risk 0.005  # 0.5% risk per trade
```

## 🛡️ Safety Features

- **Paper Trading by Default**: All trades are simulated unless explicitly configured for live trading
- **Risk Management**: Built-in position sizing and risk controls
- **Data Validation**: Comprehensive data quality checks
- **Rate Limiting**: LLM API rate limiting and circuit breakers
- **Structured Logging**: Full audit trail of all operations
- **Configuration Validation**: Pydantic-based settings validation

## 🔌 Extending the Bot

### Custom Strategies

Create a new strategy by extending the `BaseStrategy` class:

```python
from src.strategy.base import BaseStrategy
from src.core.types import TradingDecision, OHLCVData, TechnicalIndicators

class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("My Strategy", "Custom trading strategy")
    
    def decide(self, data, indicators, signals, config):
        # Your trading logic here
        return TradingDecision(...)
```

### Custom LLM Providers

Add new LLM providers by implementing the `BaseLLMClient` interface:

```python
from src.llm.base import BaseLLMClient

class MyLLMClient(BaseLLMClient):
    def _make_request(self, prompt, **kwargs):
        # Your LLM API integration
        pass
```

## 📈 Data Format

The bot expects OHLCV data in the following format:

```csv
timestamp,open,high,low,close,volume,symbol
2024-01-01T00:00:00Z,42000.00,42500.00,41800.00,42200.00,1250.50,BTCUSDT
2024-01-01T01:00:00Z,42200.00,42800.00,42100.00,42650.00,1180.25,BTCUSDT
```

Supported formats: CSV, JSON, Parquet

## 🧪 Testing

Run the test suite:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src

# Run linting
ruff check src/
black --check src/
mypy src/
```

## 📋 CLI Commands

- `run`: Execute the trading bot
- `validate-data`: Validate historical data quality
- `test-llm`: Test LLM provider connectivity
- `list-strategies`: List available trading strategies
- `config`: Display current configuration

## ⚠️ Risk Disclaimer

Trading cryptocurrencies involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software.

**Always test with paper trading first and never risk more than you can afford to lose.**

## 🔄 Roadmap

- [x] Real-time data integration
- [x] Autonomous trading loop
- [x] WebSocket streaming
- [x] Order management system
- [x] State persistence
- [x] Web dashboard
- [x] Real-time monitoring
- [x] Alert system
- [x] Telegram bot integration
- [x] Multi-channel notifications
- [x] Production deployment tools
- [x] Docker containerization
- [x] Health monitoring system
- [x] Backup and restore functionality
- [x] Comprehensive test suite
- [x] Next.js modern UI
- [x] API-first architecture
- [x] Real-time connectivity tests
- [x] LLM decision journaling
- [ ] Advanced backtesting framework
- [ ] Portfolio management
- [ ] Additional LLM providers
- [ ] Machine learning strategies
- [ ] Multi-exchange support
