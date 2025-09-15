'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Bot, BarChart3, FileText, Settings } from 'lucide-react'

export default function HomePage() {
  const router = useRouter()

  const navigationItems = [
    {
      title: 'Configuration & Startup',
      description: 'Configure environment variables, upload data, and start the bot',
      icon: Settings,
      href: '/config',
      color: 'bg-primary-500 hover:bg-primary-600'
    },
    {
      title: 'Dashboard',
      description: 'Monitor bot performance, trades, and real-time operations',
      icon: BarChart3,
      href: '/dashboard',
      color: 'bg-success-500 hover:bg-success-600'
    },
    {
      title: 'Journal & History',
      description: 'View LLM decisions, trading history, and system logs',
      icon: FileText,
      href: '/journal',
      color: 'bg-warning-500 hover:bg-warning-600'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Bot className="h-8 w-8 text-primary-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">GenAI Trading Bot</h1>
                <p className="text-sm text-gray-500">Autonomous AI-powered trading system</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                <span className="inline-block w-2 h-2 bg-success-400 rounded-full mr-2"></span>
                System Ready
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Welcome to GenAI Trading Bot
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Configure your trading bot, monitor performance, and analyze decisions with our comprehensive platform.
          </p>
        </div>

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {navigationItems.map((item, index) => {
            const Icon = item.icon
            return (
              <div
                key={index}
                className="group cursor-pointer"
                onClick={() => router.push(item.href)}
              >
                <div className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 p-8 h-full">
                  <div className="flex flex-col items-center text-center">
                    <div className={`p-4 rounded-full ${item.color} text-white mb-6 group-hover:scale-110 transition-transform duration-300`}>
                      <Icon className="h-8 w-8" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      {item.title}
                    </h3>
                    <p className="text-gray-600 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Quick Stats */}
        <div className="mt-16 bg-white rounded-xl shadow-lg p-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">System Overview</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">Ready</div>
              <div className="text-sm text-gray-500">System Status</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-success-600">0</div>
              <div className="text-sm text-gray-500">Active Trades</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-warning-600">0</div>
              <div className="text-sm text-gray-500">LLM Decisions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">Paper</div>
              <div className="text-sm text-gray-500">Trading Mode</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
