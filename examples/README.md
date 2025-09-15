# GenAI Trading Bot Examples

This directory contains examples and sample data for the GenAI Trading Bot with Next.js UI.

## 🚀 Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Start the complete system
docker-compose up -d

# Access the Next.js UI
open http://localhost:3000
```

### 2. Manual Setup

```bash
# Start API server
python -m src.api_cli

# Start Next.js UI (in another terminal)
cd ui
npm install
npm run dev
```

## 📊 Sample Data

### `sample_data.csv`
A sample dataset containing 96 hours of Bitcoin (BTCUSDT) price data with the following structure:
- **timestamp**: UTC timestamp in ISO format
- **open**: Opening price
- **high**: Highest price in the period
- **low**: Lowest price in the period
- **close**: Closing price
- **volume**: Trading volume
- **symbol**: Trading symbol (BTCUSDT)

## 🎯 Usage Examples

### 1. Configuration and Startup

1. **Access the UI**: http://localhost:3000
2. **Go to Configuration**: Click "Configuration & Startup"
3. **Set Environment Variables**:
   - LLM Provider (OpenAI, Anthropic, Gemini)
   - Binance API Keys
   - Telegram Bot Token (optional)
4. **Test Connectivity**: Use the test buttons
5. **Upload Data**: Upload `sample_data.csv`
6. **Launch Bot**: Click "Launch Trading Bot"

### 2. Monitoring

1. **Dashboard**: http://localhost:3000/dashboard
   - Real-time bot status
   - Performance metrics
   - Trading decisions
   - Order management

2. **Journal**: http://localhost:3000/journal
   - LLM decision history
   - System logs
   - Trading sessions
   - Export functionality

### 3. API Usage

```bash
# Health check
curl http://localhost:8000/health

# Get configuration
curl http://localhost:8000/api/config

# Test connectivity
curl -X POST http://localhost:8000/api/test/connectivity \
  -H "Content-Type: application/json" \
  -d '{"provider": "llm", "config": {"provider": "openai"}}'

# Upload data
curl -X POST http://localhost:8000/api/upload/data \
  -F "file=@examples/sample_data.csv"

# Start bot
curl -X POST http://localhost:8000/api/bot/start \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "strategy": "llm", "data_file": "sample_data.csv"}'
```

## 🔧 Environment Setup

Create a `.env` file in the project root:

```bash
# LLM Configuration
LLM_PRIMARY_PROVIDER=openai
LLM_OPENAI_API_KEY=your_openai_api_key_here
LLM_OPENAI_MODEL=gpt-4

# Binance Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
BINANCE_MODE=paper

# Telegram Configuration (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ALLOWED_USERS=123456789,987654321

# Trading Configuration
TRADING_MAX_CONCURRENT_ORDERS=2
TRADING_MAX_DAILY_LOSS=0.05
STREAMING_ANALYSIS_INTERVAL=60
```

## 📱 Telegram Bot

### Setup
1. Create a bot with @BotFather on Telegram
2. Get your bot token
3. Set `TELEGRAM_BOT_TOKEN` in your `.env` file
4. Start the trading bot
5. Send `/start` to your bot

### Commands
- `/start` - Welcome message
- `/status` - Bot status and metrics
- `/orders` - View current orders
- `/decisions` - Recent trading decisions
- `/performance` - Performance statistics
- `/alerts` - Recent alerts
- `/config` - Current configuration

## 🧪 Testing

### Run Tests
```bash
# Backend tests
python -m scripts.run_tests

# Integration tests
python -m scripts.integration-tests

# Performance tests
python -m scripts.performance-test

# Security tests
python -m scripts.security-test
```

### Frontend Tests
```bash
cd ui
npm test
npm run test:coverage
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# Start with bot
docker-compose --profile bot up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

## 📈 Expected Workflow

1. **Setup**: Configure environment variables
2. **Test**: Verify connectivity to all services
3. **Upload**: Upload historical data
4. **Launch**: Start the trading bot
5. **Monitor**: Watch real-time dashboard
6. **Analyze**: Review decisions in journal
7. **Control**: Use Telegram for remote control

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check if API server is running on port 8000
   - Verify environment variables
   - Check firewall settings

2. **UI Not Loading**
   - Ensure Next.js is running on port 3000
   - Check browser console for errors
   - Verify API connectivity

3. **Bot Not Starting**
   - Check all connectivity tests pass
   - Verify data file is uploaded
   - Check logs for errors

4. **Telegram Bot Not Responding**
   - Verify bot token is correct
   - Check if user is in allowed users list
   - Ensure bot is started with the main application

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Start with debug
docker-compose up -d
```

## 📚 Next Steps

1. **Custom Strategies**: Implement your own trading strategies
2. **Live Trading**: Configure for live trading with proper risk management
3. **Data Sources**: Integrate with real-time data sources
4. **Backtesting**: Use historical data for strategy validation
5. **Monitoring**: Set up alerts and notifications
6. **Scaling**: Deploy to production with proper infrastructure

## 🔗 Useful Links

- **Main UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Configuration**: http://localhost:3000/config
- **Dashboard**: http://localhost:3000/dashboard
- **Journal**: http://localhost:3000/journal