// Global type definitions for the trading bot UI

export interface BotStatus {
  running: boolean
  symbol: string
  strategy: string
  analysis_count: number
  decision_count: number
  order_count: number
  start_time: string
  buffer_info: {
    current_size: number
    max_size: number
    utilization: number
  }
}

export interface Order {
  id: string
  symbol: string
  side: string
  quantity: number
  price: number
  status: string
  timestamp: string
}

export interface PerformanceMetrics {
  total_orders: number
  successful_orders: number
  success_rate: number
  total_volume: number
  total_profit: number
  daily_pnl: number
}

export interface LLMDecision {
  timestamp: string
  symbol: string
  action: string
  confidence: number
  reasoning: string
  market_data: any
  risk_score: number
  technical_indicators: any
  outcome?: string
  profit_loss?: number
}

export interface SystemLog {
  timestamp: string
  level: string
  message: string
  component: string
  details?: any
}

export interface TradingSession {
  id: string
  start_time: string
  end_time?: string
  symbol: string
  strategy: string
  total_decisions: number
  successful_decisions: number
  total_pnl: number
  status: string
}

export interface ConnectivityTest {
  llm: boolean | null
  binance: boolean | null
  telegram: boolean | null
}

export interface DataInfo {
  filename: string
  records: number
  timeframe: string
  duration: string
  valid: boolean
}

export interface Configuration {
  llm: {
    provider: string
    apiKey: string
    model: string
    temperature: number
  }
  binance: {
    apiKey: string
    secretKey: string
    mode: string
  }
  telegram: {
    botToken: string
    chatId: string
    allowedUsers: string
  }
  trading: {
    maxOrders: number
    analysisInterval: number
    maxDailyLoss: number
  }
}
