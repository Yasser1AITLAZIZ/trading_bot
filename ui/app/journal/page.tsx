'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  FileText, 
  Search, 
  Filter, 
  Download, 
  Calendar,
  Clock,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Bot,
  Brain,
  DollarSign
} from 'lucide-react'
import toast from 'react-hot-toast'

interface LLMDecision {
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

interface SystemLog {
  timestamp: string
  level: string
  message: string
  component: string
  details?: any
}

interface TradingSession {
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

export default function JournalPage() {
  const router = useRouter()
  
  // State management
  const [llmDecisions, setLlmDecisions] = useState<LLMDecision[]>([])
  const [systemLogs, setSystemLogs] = useState<SystemLog[]>([])
  const [tradingSessions, setTradingSessions] = useState<TradingSession[]>([])
  const [loading, setLoading] = useState(true)
  
  // Filters and search
  const [searchTerm, setSearchTerm] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState('all')
  const [actionFilter, setActionFilter] = useState('all')
  const [selectedTab, setSelectedTab] = useState<'decisions' | 'logs' | 'sessions'>('decisions')

  // Load data on mount
  useEffect(() => {
    loadJournalData()
  }, [])

  const loadJournalData = async () => {
    try {
      // Load LLM decisions
      const decisionsResponse = await fetch('/api/llm/decisions?limit=100')
      if (decisionsResponse.ok) {
        const decisions = await decisionsResponse.json()
        setLlmDecisions(decisions.decisions || [])
      }

      // Load system logs
      const logsResponse = await fetch('/api/logs?limit=100')
      if (logsResponse.ok) {
        const logs = await logsResponse.json()
        setSystemLogs(logs.logs || [])
      }

      // Load trading sessions
      const sessionsResponse = await fetch('/api/sessions')
      if (sessionsResponse.ok) {
        const sessions = await sessionsResponse.json()
        setTradingSessions(sessions.sessions || [])
      }

    } catch (error) {
      console.error('Failed to load journal data:', error)
      toast.error('Failed to load journal data')
    } finally {
      setLoading(false)
    }
  }

  const exportData = async (type: string) => {
    try {
      const response = await fetch(`/api/export/${type}`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${type}_export_${new Date().toISOString().split('T')[0]}.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        toast.success(`${type} data exported successfully`)
      }
    } catch (error) {
      toast.error('Failed to export data')
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

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'info':
        return 'text-primary-600 bg-primary-100'
      case 'warning':
        return 'text-warning-600 bg-warning-100'
      case 'error':
        return 'text-danger-600 bg-danger-100'
      case 'critical':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return 'text-success-600 bg-success-100'
      case 'completed':
        return 'text-primary-600 bg-primary-100'
      case 'stopped':
        return 'text-danger-600 bg-danger-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const filteredDecisions = llmDecisions.filter(decision => {
    const matchesSearch = decision.reasoning.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         decision.symbol.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesAction = actionFilter === 'all' || decision.action.toLowerCase() === actionFilter
    const matchesDate = !dateFilter || decision.timestamp.startsWith(dateFilter)
    
    return matchesSearch && matchesAction && matchesDate
  })

  const filteredLogs = systemLogs.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         log.component.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesLevel = levelFilter === 'all' || log.level.toLowerCase() === levelFilter
    const matchesDate = !dateFilter || log.timestamp.startsWith(dateFilter)
    
    return matchesSearch && matchesLevel && matchesDate
  })

  const filteredSessions = tradingSessions.filter(session => {
    const matchesSearch = session.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         session.strategy.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesDate = !dateFilter || session.start_time.startsWith(dateFilter)
    
    return matchesSearch && matchesDate
  })

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <FileText className="h-8 w-8 animate-pulse text-primary-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading journal...</p>
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
              <FileText className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Trading Journal</h1>
                <p className="text-sm text-gray-500">LLM decisions, system logs, and trading history</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => exportData('decisions')}
                className="btn-outline"
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </button>
              <button
                onClick={() => router.push('/dashboard')}
                className="btn-outline"
              >
                Dashboard
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input pl-10"
                  placeholder="Search..."
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="input"
              />
            </div>
            {selectedTab === 'decisions' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="input"
                >
                  <option value="all">All Actions</option>
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                  <option value="hold">Hold</option>
                </select>
              </div>
            )}
            {selectedTab === 'logs' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Level</label>
                <select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                  className="input"
                >
                  <option value="all">All Levels</option>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="error">Error</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {[
                { id: 'decisions', label: 'LLM Decisions', icon: Brain, count: filteredDecisions.length },
                { id: 'logs', label: 'System Logs', icon: AlertTriangle, count: filteredLogs.length },
                { id: 'sessions', label: 'Trading Sessions', icon: Bot, count: filteredSessions.length }
              ].map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setSelectedTab(tab.id as any)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                      selectedTab === tab.id
                        ? 'border-primary-500 text-primary-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tab.label}</span>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      selectedTab === tab.id ? 'bg-primary-100 text-primary-600' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {tab.count}
                    </span>
                  </button>
                )
              })}
            </nav>
          </div>

          <div className="p-6">
            {/* LLM Decisions Tab */}
            {selectedTab === 'decisions' && (
              <div className="space-y-4">
                {filteredDecisions.length === 0 ? (
                  <div className="text-center py-8">
                    <Brain className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No LLM decisions found</p>
                  </div>
                ) : (
                  filteredDecisions.map((decision, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center space-x-3">
                          <span className={`status-indicator ${getActionColor(decision.action)}`}>
                            {decision.action.toUpperCase()}
                          </span>
                          <div>
                            <h3 className="text-lg font-medium text-gray-900">{decision.symbol}</h3>
                            <p className="text-sm text-gray-500">
                              {new Date(decision.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium text-gray-900">
                            Confidence: {(decision.confidence * 100).toFixed(1)}%
                          </p>
                          <p className="text-sm text-gray-500">
                            Risk Score: {(decision.risk_score * 100).toFixed(1)}%
                          </p>
                        </div>
                      </div>
                      
                      <div className="mb-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">LLM Reasoning:</h4>
                        <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                          {decision.reasoning}
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Market Data:</h4>
                          <div className="text-sm text-gray-600 space-y-1">
                            <p>Price: ${decision.market_data?.price?.toFixed(2) || 'N/A'}</p>
                            <p>Volume: {decision.market_data?.volume?.toLocaleString() || 'N/A'}</p>
                            <p>Volatility: {decision.market_data?.volatility?.toFixed(2) || 'N/A'}%</p>
                          </div>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Technical Indicators:</h4>
                          <div className="text-sm text-gray-600 space-y-1">
                            <p>RSI: {decision.technical_indicators?.rsi?.toFixed(2) || 'N/A'}</p>
                            <p>SMA: ${decision.technical_indicators?.sma?.toFixed(2) || 'N/A'}</p>
                            <p>EMA: ${decision.technical_indicators?.ema?.toFixed(2) || 'N/A'}</p>
                          </div>
                        </div>
                      </div>

                      {decision.outcome && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-700">Outcome:</span>
                            <span className={`status-indicator ${
                              decision.profit_loss && decision.profit_loss > 0 
                                ? 'text-success-600 bg-success-100' 
                                : 'text-danger-600 bg-danger-100'
                            }`}>
                              {decision.outcome}
                            </span>
                          </div>
                          {decision.profit_loss && (
                            <p className={`text-sm font-medium mt-1 ${
                              decision.profit_loss > 0 ? 'text-success-600' : 'text-danger-600'
                            }`}>
                              P&L: ${decision.profit_loss.toFixed(2)}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* System Logs Tab */}
            {selectedTab === 'logs' && (
              <div className="space-y-4">
                {filteredLogs.length === 0 ? (
                  <div className="text-center py-8">
                    <AlertTriangle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No system logs found</p>
                  </div>
                ) : (
                  filteredLogs.map((log, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-3">
                          <span className={`status-indicator ${getLevelColor(log.level)}`}>
                            {log.level.toUpperCase()}
                          </span>
                          <div>
                            <h3 className="text-sm font-medium text-gray-900">{log.component}</h3>
                            <p className="text-xs text-gray-500">
                              {new Date(log.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-gray-700 mb-2">{log.message}</p>
                      {log.details && (
                        <details className="text-xs text-gray-600">
                          <summary className="cursor-pointer hover:text-gray-800">Details</summary>
                          <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Trading Sessions Tab */}
            {selectedTab === 'sessions' && (
              <div className="space-y-4">
                {filteredSessions.length === 0 ? (
                  <div className="text-center py-8">
                    <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No trading sessions found</p>
                  </div>
                ) : (
                  filteredSessions.map((session, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">
                            {session.symbol} - {session.strategy}
                          </h3>
                          <p className="text-sm text-gray-500">
                            {new Date(session.start_time).toLocaleString()}
                            {session.end_time && ` - ${new Date(session.end_time).toLocaleString()}`}
                          </p>
                        </div>
                        <span className={`status-indicator ${getStatusColor(session.status)}`}>
                          {session.status.toUpperCase()}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="text-center">
                          <p className="text-2xl font-bold text-primary-600">{session.total_decisions}</p>
                          <p className="text-sm text-gray-600">Total Decisions</p>
                        </div>
                        <div className="text-center">
                          <p className="text-2xl font-bold text-success-600">{session.successful_decisions}</p>
                          <p className="text-sm text-gray-600">Successful</p>
                        </div>
                        <div className="text-center">
                          <p className="text-2xl font-bold text-warning-600">
                            {session.total_decisions > 0 ? ((session.successful_decisions / session.total_decisions) * 100).toFixed(1) : 0}%
                          </p>
                          <p className="text-sm text-gray-600">Success Rate</p>
                        </div>
                        <div className="text-center">
                          <p className={`text-2xl font-bold ${session.total_pnl >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                            ${session.total_pnl.toFixed(2)}
                          </p>
                          <p className="text-sm text-gray-600">Total P&L</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
