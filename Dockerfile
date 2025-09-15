# Multi-stage Docker build for GenAI Trading Bot

# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir build
RUN python -m build

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash trading
RUN mkdir -p /app/data /app/logs /app/backups
RUN chown -R trading:trading /app

# Install Python dependencies
COPY --from=builder /app/dist/*.whl ./
RUN pip install --no-cache-dir *.whl

# Copy application code
COPY src/ ./src/
COPY examples/ ./examples/
COPY scripts/ ./scripts/
COPY *.md ./
COPY *.ini ./

# Set permissions
RUN chown -R trading:trading /app

# Switch to non-root user
USER trading

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV BINANCE_MODE=paper
ENV TRADING_TRADING_ENABLED=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m scripts.health_check || exit 1

# Default command
CMD ["python", "-m", "src.autonomous_trading", "start", "--data", "examples/sample_data.csv", "--symbol", "BTCUSDT", "--strategy", "llm", "--llm-provider", "openai", "--mode", "paper"]

# Expose ports
EXPOSE 8000
