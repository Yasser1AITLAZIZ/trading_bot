import React from 'react'
import { cn, getStatusColor, getActionColor, getLevelColor } from '@/lib/utils'

interface StatusIndicatorProps {
  status: string
  type?: 'status' | 'action' | 'level'
  className?: string
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ 
  status, 
  type = 'status', 
  className 
}) => {
  const getColorClasses = () => {
    switch (type) {
      case 'action':
        return getActionColor(status)
      case 'level':
        return getLevelColor(status)
      default:
        return getStatusColor(status)
    }
  }

  return (
    <span className={cn(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
      getColorClasses(),
      className
    )}>
      {status.toUpperCase()}
    </span>
  )
}

export { StatusIndicator }
