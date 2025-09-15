'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  CheckCircle, 
  XCircle, 
  Upload, 
  Play, 
  Settings, 
  Database, 
  Bot,
  AlertCircle,
  Loader2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useDropzone } from 'react-dropzone'

interface StepStatus {
  completed: boolean
  current: boolean
  error?: string
}

interface ConnectivityTest {
  llm: boolean | null
  binance: boolean | null
  telegram: boolean | null
}

interface DataInfo {
  filename: string
  records: number
  timeframe: string
  duration: string
  valid: boolean
}

export default function ConfigPage() {
  const router = useRouter()
  
  // Step management
  const [currentStep, setCurrentStep] = useState(1)
  const [steps, setSteps] = useState<StepStatus[]>([
    { completed: false, current: true },   // Step 1: Environment
    { completed: false, current: false },  // Step 2: Data Upload
    { completed: false, current: false },  // Step 3: Launch
  ])

  // Configuration state
  const [config, setConfig] = useState({
    llm: {
      provider: 'openai',
      apiKey: '',
      model: 'gpt-4',
      temperature: 0.7
    },
    binance: {
      apiKey: '',
      secretKey: '',
      mode: 'paper'
    },
    telegram: {
      botToken: '',
      chatId: '',
      allowedUsers: ''
    },
    trading: {
      maxOrders: 2,
      analysisInterval: 60,
      maxDailyLoss: 0.05
    }
  })

  // Connectivity tests
  const [connectivityTests, setConnectivityTests] = useState<ConnectivityTest>({
    llm: null,
    binance: null,
    telegram: null
  })
  const [testingConnectivity, setTestingConnectivity] = useState<string | null>(null)

  // Data upload
  const [uploadedData, setUploadedData] = useState<DataInfo | null>(null)
  const [uploading, setUploading] = useState(false)

  // Bot launch
  const [launching, setLaunching] = useState(false)

  // Load configuration on mount
  useEffect(() => {
    loadConfiguration()
  }, [])

  const loadConfiguration = async () => {
    try {
      const response = await fetch('/api/config')
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
      }
    } catch (error) {
      console.error('Failed to load configuration:', error)
    }
  }

  const saveConfiguration = async () => {
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      
      if (response.ok) {
        toast.success('Configuration saved successfully')
        return true
      } else {
        throw new Error('Failed to save configuration')
      }
    } catch (error) {
      toast.error('Failed to save configuration')
      return false
    }
  }

  const testConnectivity = async (provider: keyof ConnectivityTest) => {
    setTestingConnectivity(provider)
    
    try {
      const response = await fetch('/api/test/connectivity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          config: config[provider === 'llm' ? 'llm' : provider === 'binance' ? 'binance' : 'telegram']
        })
      })

      const result = await response.json()
      
      setConnectivityTests(prev => ({
        ...prev,
        [provider]: result.success
      }))

      if (result.success) {
        toast.success(`${provider.toUpperCase()} connectivity test passed`)
      } else {
        toast.error(`${provider.toUpperCase()} connectivity test failed: ${result.message}`)
      }
    } catch (error) {
      setConnectivityTests(prev => ({
        ...prev,
        [provider]: false
      }))
      toast.error(`${provider.toUpperCase()} connectivity test failed`)
    } finally {
      setTestingConnectivity(null)
    }
  }

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload/data', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()
      
      if (result.success) {
        // Analyze the uploaded data
        const dataInfo: DataInfo = {
          filename: result.filename,
          records: result.records_count,
          timeframe: '1m', // This would be detected from the data
          duration: `${Math.round(result.records_count / 60)}h`, // Assuming 1-minute intervals
          valid: true
        }
        
        setUploadedData(dataInfo)
        toast.success('Data uploaded successfully')
        
        // Move to next step
        completeStep(1)
        setCurrentStep(2)
      } else {
        throw new Error(result.message)
      }
    } catch (error) {
      toast.error('Failed to upload data')
    } finally {
      setUploading(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv']
    },
    multiple: false
  })

  const completeStep = (stepIndex: number) => {
    setSteps(prev => prev.map((step, index) => ({
      ...step,
      completed: index === stepIndex ? true : step.completed,
      current: index === stepIndex + 1 ? true : false
    })))
  }

  const canLaunchBot = () => {
    return (
      connectivityTests.llm === true &&
      connectivityTests.binance === true &&
      uploadedData !== null &&
      steps[0].completed &&
      steps[1].completed
    )
  }

  const launchBot = async () => {
    if (!canLaunchBot()) return

    setLaunching(true)
    
    try {
      const response = await fetch('/api/bot/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: 'BTCUSDT',
          strategy: 'llm',
          llm_provider: config.llm.provider,
          mode: config.binance.mode,
          data_file: uploadedData?.filename
        })
      })

      const result = await response.json()
      
      if (result.success) {
        toast.success('Bot launched successfully!')
        completeStep(2)
        setCurrentStep(3)
        
        // Redirect to dashboard after a delay
        setTimeout(() => {
          router.push('/dashboard')
        }, 2000)
      } else {
        throw new Error(result.message)
      }
    } catch (error) {
      toast.error('Failed to launch bot')
    } finally {
      setLaunching(false)
    }
  }

  const StepIndicator = ({ step, index }: { step: StepStatus, index: number }) => {
    const stepNames = ['Environment Config', 'Data Upload', 'Launch Bot']
    
    return (
      <div className="flex items-center">
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          step.completed 
            ? 'bg-success-600 text-white' 
            : step.current 
            ? 'bg-primary-600 text-white' 
            : 'bg-gray-200 text-gray-600'
        }`}>
          {step.completed ? (
            <CheckCircle className="h-5 w-5" />
          ) : (
            <span>{index + 1}</span>
          )}
        </div>
        <div className="ml-4">
          <p className={`text-sm font-medium ${
            step.completed || step.current ? 'text-gray-900' : 'text-gray-500'
          }`}>
            {stepNames[index]}
          </p>
          {step.error && (
            <p className="text-sm text-danger-600">{step.error}</p>
          )}
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
              <Settings className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Bot Configuration</h1>
                <p className="text-sm text-gray-500">Setup and launch your trading bot</p>
              </div>
            </div>
            <button
              onClick={() => router.push('/')}
              className="btn-outline"
            >
              Back to Home
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Step Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={index} className="flex items-center">
                <StepIndicator step={step} index={index} />
                {index < steps.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-4 ${
                    step.completed ? 'bg-success-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step 1: Environment Configuration */}
        {currentStep === 1 && (
          <div className="space-y-8">
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Settings className="h-5 w-5 mr-2" />
                  Environment Configuration
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Configure API keys and test connectivity
                </p>
              </div>
              <div className="card-body space-y-6">
                {/* LLM Configuration */}
                <div>
                  <h3 className="text-md font-medium text-gray-900 mb-4">LLM Configuration</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Provider
                      </label>
                      <select
                        value={config.llm.provider}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          llm: { ...prev.llm, provider: e.target.value }
                        }))}
                        className="input"
                      >
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="gemini">Google Gemini</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Model
                      </label>
                      <input
                        type="text"
                        value={config.llm.model}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          llm: { ...prev.llm, model: e.target.value }
                        }))}
                        className="input"
                        placeholder="gpt-4"
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        API Key
                      </label>
                      <input
                        type="password"
                        value={config.llm.apiKey}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          llm: { ...prev.llm, apiKey: e.target.value }
                        }))}
                        className="input"
                        placeholder="sk-..."
                      />
                    </div>
                  </div>
                  <div className="mt-3">
                    <button
                      onClick={() => testConnectivity('llm')}
                      disabled={testingConnectivity === 'llm' || !config.llm.apiKey}
                      className="btn-outline"
                    >
                      {testingConnectivity === 'llm' ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : connectivityTests.llm === true ? (
                        <CheckCircle className="h-4 w-4 mr-2 text-success-600" />
                      ) : connectivityTests.llm === false ? (
                        <XCircle className="h-4 w-4 mr-2 text-danger-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 mr-2" />
                      )}
                      Test LLM Connectivity
                    </button>
                  </div>
                </div>

                {/* Binance Configuration */}
                <div>
                  <h3 className="text-md font-medium text-gray-900 mb-4">Binance Configuration</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        API Key
                      </label>
                      <input
                        type="password"
                        value={config.binance.apiKey}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          binance: { ...prev.binance, apiKey: e.target.value }
                        }))}
                        className="input"
                        placeholder="Your Binance API Key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Secret Key
                      </label>
                      <input
                        type="password"
                        value={config.binance.secretKey}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          binance: { ...prev.binance, secretKey: e.target.value }
                        }))}
                        className="input"
                        placeholder="Your Binance Secret Key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Trading Mode
                      </label>
                      <select
                        value={config.binance.mode}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          binance: { ...prev.binance, mode: e.target.value }
                        }))}
                        className="input"
                      >
                        <option value="paper">Paper Trading</option>
                        <option value="testnet">Testnet</option>
                        <option value="live">Live Trading</option>
                      </select>
                    </div>
                  </div>
                  <div className="mt-3">
                    <button
                      onClick={() => testConnectivity('binance')}
                      disabled={testingConnectivity === 'binance' || !config.binance.apiKey || !config.binance.secretKey}
                      className="btn-outline"
                    >
                      {testingConnectivity === 'binance' ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : connectivityTests.binance === true ? (
                        <CheckCircle className="h-4 w-4 mr-2 text-success-600" />
                      ) : connectivityTests.binance === false ? (
                        <XCircle className="h-4 w-4 mr-2 text-danger-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 mr-2" />
                      )}
                      Test Binance Connectivity
                    </button>
                  </div>
                </div>

                {/* Telegram Configuration (Optional) */}
                <div>
                  <h3 className="text-md font-medium text-gray-900 mb-4">Telegram Configuration (Optional)</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Bot Token
                      </label>
                      <input
                        type="password"
                        value={config.telegram.botToken}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          telegram: { ...prev.telegram, botToken: e.target.value }
                        }))}
                        className="input"
                        placeholder="Your Telegram Bot Token"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Chat ID
                      </label>
                      <input
                        type="text"
                        value={config.telegram.chatId}
                        onChange={(e) => setConfig(prev => ({
                          ...prev,
                          telegram: { ...prev.telegram, chatId: e.target.value }
                        }))}
                        className="input"
                        placeholder="Your Chat ID"
                      />
                    </div>
                  </div>
                  <div className="mt-3">
                    <button
                      onClick={() => testConnectivity('telegram')}
                      disabled={testingConnectivity === 'telegram' || !config.telegram.botToken}
                      className="btn-outline"
                    >
                      {testingConnectivity === 'telegram' ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : connectivityTests.telegram === true ? (
                        <CheckCircle className="h-4 w-4 mr-2 text-success-600" />
                      ) : connectivityTests.telegram === false ? (
                        <XCircle className="h-4 w-4 mr-2 text-danger-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 mr-2" />
                      )}
                      Test Telegram Connectivity
                    </button>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end space-x-4 pt-6 border-t">
                  <button
                    onClick={saveConfiguration}
                    className="btn-secondary"
                  >
                    Save Configuration
                  </button>
                  <button
                    onClick={() => {
                      if (connectivityTests.llm === true && connectivityTests.binance === true) {
                        completeStep(0)
                        setCurrentStep(2)
                      } else {
                        toast.error('Please test connectivity for LLM and Binance first')
                      }
                    }}
                    disabled={connectivityTests.llm !== true || connectivityTests.binance !== true}
                    className="btn-primary"
                  >
                    Continue to Data Upload
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Data Upload */}
        {currentStep === 2 && (
          <div className="space-y-8">
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Database className="h-5 w-5 mr-2" />
                  Historical Data Upload
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Upload your historical trading data (CSV format)
                </p>
              </div>
              <div className="card-body">
                {!uploadedData ? (
                  <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                      isDragActive 
                        ? 'border-primary-400 bg-primary-50' 
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <input {...getInputProps()} />
                    <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-lg font-medium text-gray-900 mb-2">
                      {isDragActive ? 'Drop the CSV file here' : 'Upload Historical Data'}
                    </p>
                    <p className="text-sm text-gray-600 mb-4">
                      Drag and drop a CSV file, or click to select
                    </p>
                    <p className="text-xs text-gray-500">
                      Expected format: timestamp, open, high, low, close, volume, symbol
                    </p>
                    {uploading && (
                      <div className="mt-4">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto text-primary-600" />
                        <p className="text-sm text-gray-600 mt-2">Uploading and validating data...</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-success-50 border border-success-200 rounded-lg p-6">
                    <div className="flex items-center mb-4">
                      <CheckCircle className="h-6 w-6 text-success-600 mr-3" />
                      <h3 className="text-lg font-medium text-success-900">Data Uploaded Successfully</h3>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-600">Filename</p>
                        <p className="font-medium">{uploadedData.filename}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Records</p>
                        <p className="font-medium">{uploadedData.records.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Timeframe</p>
                        <p className="font-medium">{uploadedData.timeframe}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Duration</p>
                        <p className="font-medium">{uploadedData.duration}</p>
                      </div>
                    </div>
                    <div className="mt-4">
                      <button
                        onClick={() => {
                          setUploadedData(null)
                          setSteps(prev => prev.map((step, index) => ({
                            ...step,
                            completed: index === 1 ? false : step.completed
                          })))
                        }}
                        className="btn-outline text-sm"
                      >
                        Upload Different File
                      </button>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-between pt-6 border-t mt-6">
                  <button
                    onClick={() => setCurrentStep(1)}
                    className="btn-outline"
                  >
                    Back to Configuration
                  </button>
                  <button
                    onClick={() => {
                      if (uploadedData) {
                        completeStep(1)
                        setCurrentStep(3)
                      } else {
                        toast.error('Please upload historical data first')
                      }
                    }}
                    disabled={!uploadedData}
                    className="btn-primary"
                  >
                    Continue to Launch
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Launch Bot */}
        {currentStep === 3 && (
          <div className="space-y-8">
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Bot className="h-5 w-5 mr-2" />
                  Launch Trading Bot
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Review configuration and launch your bot
                </p>
              </div>
              <div className="card-body">
                {/* Configuration Summary */}
                <div className="bg-gray-50 rounded-lg p-6 mb-6">
                  <h3 className="text-md font-medium text-gray-900 mb-4">Configuration Summary</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">LLM Configuration</h4>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-gray-600">Provider:</span> {config.llm.provider}</p>
                        <p><span className="text-gray-600">Model:</span> {config.llm.model}</p>
                        <p><span className="text-gray-600">Status:</span> 
                          <span className={`ml-2 ${connectivityTests.llm ? 'text-success-600' : 'text-danger-600'}`}>
                            {connectivityTests.llm ? 'Connected' : 'Not Connected'}
                          </span>
                        </p>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Binance Configuration</h4>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-gray-600">Mode:</span> {config.binance.mode}</p>
                        <p><span className="text-gray-600">API Key:</span> {config.binance.apiKey ? '***' + config.binance.apiKey.slice(-4) : 'Not set'}</p>
                        <p><span className="text-gray-600">Status:</span> 
                          <span className={`ml-2 ${connectivityTests.binance ? 'text-success-600' : 'text-danger-600'}`}>
                            {connectivityTests.binance ? 'Connected' : 'Not Connected'}
                          </span>
                        </p>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Data Configuration</h4>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-gray-600">File:</span> {uploadedData?.filename}</p>
                        <p><span className="text-gray-600">Records:</span> {uploadedData?.records.toLocaleString()}</p>
                        <p><span className="text-gray-600">Duration:</span> {uploadedData?.duration}</p>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Trading Configuration</h4>
                      <div className="space-y-1 text-sm">
                        <p><span className="text-gray-600">Max Orders:</span> {config.trading.maxOrders}</p>
                        <p><span className="text-gray-600">Analysis Interval:</span> {config.trading.analysisInterval}s</p>
                        <p><span className="text-gray-600">Max Daily Loss:</span> {config.trading.maxDailyLoss * 100}%</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Launch Button */}
                <div className="text-center">
                  <button
                    onClick={launchBot}
                    disabled={!canLaunchBot() || launching}
                    className={`btn-primary text-lg px-8 py-3 ${
                      !canLaunchBot() ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {launching ? (
                      <>
                        <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                        Launching Bot...
                      </>
                    ) : (
                      <>
                        <Play className="h-5 w-5 mr-2" />
                        Launch Trading Bot
                      </>
                    )}
                  </button>
                  
                  {!canLaunchBot() && (
                    <p className="text-sm text-gray-500 mt-3">
                      Complete all previous steps to launch the bot
                    </p>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex justify-between pt-6 border-t mt-6">
                  <button
                    onClick={() => setCurrentStep(2)}
                    className="btn-outline"
                  >
                    Back to Data Upload
                  </button>
                  <button
                    onClick={() => router.push('/dashboard')}
                    className="btn-secondary"
                  >
                    Go to Dashboard
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
