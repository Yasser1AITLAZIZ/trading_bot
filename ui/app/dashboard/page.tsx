'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Settings,
  Bot
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import toast from 'react-hot-toast'

interface BotStatus {
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

interface Order {
  id: string
  symbol: string
  side: string
  quantity: number
  price: number
  status: string
  timestamp: string
}

interface PerformanceMetrics {
  total_orders: number
  successful_orders: number
  success_rate: number
  total_volume: number
  total_profit: number
  daily_pnl: number
}

interface LLMDecision {
  timestamp: string
  action: string
  confidence: number
  reasoning: string
  risk_score: number
}

export default function DashboardPage() {
  const router = useRouter()
  const wsRef = useRef<WebSocket | null>(null)
  
  // State management
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null)
  const [llmDecisions, setLlmDecisions] = useState<LLMDecision[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  // Chart data
  const [priceData, setPriceData] = useState<any[]>([])
  const [performanceData, setPerformanceData] = useState<any[]>([])

  // WebSocket connection
  useEffect(() => {
    connectWebSocket()
    loadInitialData()
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      toast.success('Connected to bot')
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
      toast.error('Disconnected from bot')
      // Reconnect after 5 seconds
      setTimeout(connectWebSocket, 5000)
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      toast.error('Connection error')
    }
    
    wsRef.current = ws
  }

  const handleWebSocketMessage = (data: any) => {
    setLastUpdate(new Date())
    
    switch (data.type) {
      case 'status':
        setBotStatus(data.data)
        break
      case 'order':
        setOrders(prev => [data.data, ...prev.slice(0, 49)]) // Keep last 50 orders
        break
      case 'decision':
        setLlmDecisions(prev => [data.data, ...prev.slice(0, 49)]) // Keep last 50 decisions
        break
      case 'performance':
        setPerformance(data.data)
        break
      case 'alert':
        setAlerts(prev => [data.data, ...prev.slice(0, 19)]) // Keep last 20 alerts
        toast.error(data.data.message)
        break
      case 'price_update':
        setPriceData(prev => [...prev.slice(-99), data.data]) // Keep last 100 price points
        break
    }
  }

  const loadInitialData = async () => {
    try {
      // Load bot status
      const statusResponse = await fetch('/api/bot/status')
      if (statusResponse.ok) {
        const status = await statusResponse.json()
        setBotStatus(status)
      }

      // Load performance metrics
      const perfResponse = await fetch('/api/performance')
      if (perfResponse.ok) {
        const perf = await perfResponse.json()
        setPerformance(perf)
      }

      // Load recent decisions
      const decisionsResponse = await fetch('/api/llm/decisions?limit=10')
      if (decisionsResponse.ok) {
        const decisions = await decisionsResponse.json()
        setLlmDecisions(decisions.decisions || [])
      }

      // Generate sample data for charts
      generateSampleData()
      
    } catch (error) {
      console.error('Failed to load initial data:', error)
      toast.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const generateSampleData = () => {
    // Generate sample price data
    const now = new Date()
    const samplePriceData = []
    let price = 50000
    
    for (let i = 0; i < 100; i++) {
      const time = new Date(now.getTime() - (99 - i) * 60000) // 1 minute intervals
      price += (Math.random() - 0.5) * 100
      samplePriceData.push({
        time: time.toLocaleTimeString(),
        price: Math.round(price),
        volume: Math.random() * 1000
      })
    }
    setPriceData(samplePriceData)

    // Generate sample performance data
    const samplePerfData = []
    let cumulative = 0
    
    for (let i = 0; i < 24; i++) {
      const time = new Date(now.getTime() - (23 - i) * 3600000) // 1 hour intervals
      const pnl = (Math.random() - 0.5) * 100
      cumulative += pnl
      samplePerfData.push({
        time: time.toLocaleTimeString(),
        pnl: Math.round(pnl),
        cumulative: Math.round(cumulative),
        trades: Math.floor(Math.random() * 5)
      })
    }
    setPerformanceData(samplePerfData)
  }

  const refreshData = async () => {
    setLoading(true)
    await loadInitialData()
    toast.success('Data refreshed')
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return 'text-success-600 bg-success-100'
      case 'stopped':
        return 'text-danger-600 bg-danger-100'
      case 'error':
        return 'text-warning-600 bg-warning-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'buy':
        return 'text-success-600 bg-success-100'
      case 'sell':
        return 'text-danger-600 bg-danger-100'
      case 'hold':
        return 'text-gray-600 bg-gray-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <BarChart3 className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Trading Dashboard</h1>
                <p className="text-sm text-gray-500">
                  Real-time monitoring • Last update: {lastUpdate.toLocaleTimeString()}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={refreshData}
                className="btn-outline"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </button>
              <button
                onClick={() => router.push('/config')}
                className="btn-outline"
              >
                <Settings className="h-4 w-4 mr-2" />
                Config
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-2 bg-primary-100 rounded-lg">
                  <Bot className="h-6 w-6 text-primary-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Bot Status</p>
                  <p className={`text-lg font-semibold ${getStatusColor(botStatus?.running ? 'running' : 'stopped')}`}>
                    {botStatus?.running ? 'Running' : 'Stopped'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-2 bg-success-100 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-success-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Success Rate</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {performance?.success_rate ? `${(performance.success_rate * 100).toFixed(1)}%` : '0%'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-2 bg-warning-100 rounded-lg">
                  <DollarSign className="h-6 w-6 text-warning-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Daily P&L</p>
                  <p className={`text-lg font-semibold ${(performance?.daily_pnl || 0) >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                    ${performance?.daily_pnl?.toFixed(2) || '0.00'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="flex items-center">
                <div className="p-2 bg-gray-100 rounded-lg">
                  <Activity className="h-6 w-6 text-gray-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Orders</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {performance?.total_orders || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Price Chart */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Price Movement</h3>
              <p className="text-sm text-gray-600">{botStatus?.symbol || 'BTCUSDT'}</p>
            </div>
            <div className="card-body">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={priceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Line 
                      type="monotone" 
                      dataKey="price" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Performance Chart */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Performance</h3>
              <p className="text-sm text-gray-600">24h P&L</p>
            </div>
            <div className="card-body">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={performanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Bar 
                      dataKey="pnl" 
                      fill="#10b981"
                      radius={[2, 2, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* Data Tables Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent LLM Decisions */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Recent LLM Decisions</h3>
              <p className="text-sm text-gray-600">Latest AI trading decisions</p>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                {llmDecisions.slice(0, 5).map((decision, index) => (
                  <div key={index} className="border-l-4 border-primary-200 pl-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`status-indicator ${getActionColor(decision.action)}`}>
                        {decision.action.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500">
                        {new Date(decision.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-1">
                      Confidence: {(decision.confidence * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-600 line-clamp-2">
                      {decision.reasoning}
                    </p>
                  </div>
                ))}
                {llmDecisions.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No decisions yet</p>
                )}
              </div>
            </div>
          </div>

          {/* Recent Orders */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Recent Orders</h3>
              <p className="text-sm text-gray-600">Latest trading orders</p>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                {orders.slice(0, 5).map((order, index) => (
                  <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                    <div className="flex items-center space-x-3">
                      <span className={`status-indicator ${getActionColor(order.side)}`}>
                        {order.side.toUpperCase()}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {order.quantity} {order.symbol}
                        </p>
                        <p className="text-xs text-gray-500">
                          ${order.price.toFixed(2)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-medium ${
                        order.status === 'FILLED' ? 'text-success-600' : 'text-warning-600'
                      }`}>
                        {order.status}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(order.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {orders.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No orders yet</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Bot Information */}
        {botStatus && (
          <div className="mt-8">
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold text-gray-900">Bot Information</h3>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Trading Configuration</h4>
                    <div className="space-y-1 text-sm">
                      <p><span className="text-gray-600">Symbol:</span> {botStatus.symbol}</p>
                      <p><span className="text-gray-600">Strategy:</span> {botStatus.strategy}</p>
                      <p><span className="text-gray-600">Analysis Count:</span> {botStatus.analysis_count}</p>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Data Buffer</h4>
                    <div className="space-y-1 text-sm">
                      <p><span className="text-gray-600">Current Size:</span> {botStatus.buffer_info.current_size}</p>
                      <p><span className="text-gray-600">Max Size:</span> {botStatus.buffer_info.max_size}</p>
                      <p><span className="text-gray-600">Utilization:</span> {(botStatus.buffer_info.utilization * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Session Info</h4>
                    <div className="space-y-1 text-sm">
                      <p><span className="text-gray-600">Start Time:</span> {new Date(botStatus.start_time).toLocaleString()}</p>
                      <p><span className="text-gray-600">Decisions:</span> {botStatus.decision_count}</p>
                      <p><span className="text-gray-600">Orders:</span> {botStatus.order_count}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
