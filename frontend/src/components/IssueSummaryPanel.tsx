'use client'

import { AlertTriangle, CheckCircle2, XCircle, AlertCircle, Info, Lightbulb } from 'lucide-react'

interface IssueSummary {
  total_issues: number
  critical: number
  high: number
  medium: number
  low: number
}

interface IssueSummaryPanelProps {
  summary: IssueSummary
  suggestions: string[]
  issues?: string[]  // List of actual issues detected
}

export function IssueSummaryPanel({ summary, suggestions, issues = [] }: IssueSummaryPanelProps) {
  const { total_issues, critical, high, medium, low } = summary

  const getOverallStatus = () => {
    if (critical > 0) return {
      color: 'red',
      icon: <XCircle className="h-6 w-6" />,
      text: 'Critical Issues Found',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-900'
    }
    if (high > 0) return {
      color: 'orange',
      icon: <AlertTriangle className="h-6 w-6" />,
      text: 'High Priority Issues',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      textColor: 'text-orange-900'
    }
    if (medium > 0) return {
      color: 'yellow',
      icon: <AlertCircle className="h-6 w-6" />,
      text: 'Medium Priority Issues',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      textColor: 'text-yellow-900'
    }
    if (low > 0) return {
      color: 'blue',
      icon: <Info className="h-6 w-6" />,
      text: 'Minor Issues Detected',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-900'
    }
    return {
      color: 'green',
      icon: <CheckCircle2 className="h-6 w-6" />,
      text: 'No Issues Detected',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-900'
    }
  }

  const status = getOverallStatus()

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <div className={`${status.bgColor} ${status.borderColor} border rounded-xl p-6`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={status.textColor}>
              {status.icon}
            </div>
            <div>
              <h3 className={`text-lg font-semibold ${status.textColor}`}>
                {status.text}
              </h3>
              <p className={`text-sm ${status.textColor} opacity-80`}>
                {total_issues === 0 
                  ? 'Your resume follows ATS best practices!'
                  : `${total_issues} formatting issue${total_issues !== 1 ? 's' : ''} detected that may affect ATS parsing`
                }
              </p>
            </div>
          </div>
          <div className={`text-3xl font-bold ${status.textColor}`}>
            {total_issues}
          </div>
        </div>
      </div>

      {/* Issue Breakdown */}
      {total_issues > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h4 className="text-md font-semibold text-gray-900 mb-4">Issue Breakdown</h4>
          <div className="space-y-3">
            {critical > 0 && (
              <div className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-xl">🔴</span>
                  <span className="font-medium text-red-900">Critical</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-red-900">{critical}</span>
                  <span className="text-sm text-red-600">Must fix immediately</span>
                </div>
              </div>
            )}

            {high > 0 && (
              <div className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-xl">🟠</span>
                  <span className="font-medium text-orange-900">High Priority</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-orange-900">{high}</span>
                  <span className="text-sm text-orange-600">Fix as soon as possible</span>
                </div>
              </div>
            )}

            {medium > 0 && (
              <div className="flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-xl">🟡</span>
                  <span className="font-medium text-yellow-900">Medium Priority</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-yellow-900">{medium}</span>
                  <span className="text-sm text-yellow-600">Recommended to fix</span>
                </div>
              </div>
            )}

            {low > 0 && (
              <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-xl">🔵</span>
                  <span className="font-medium text-blue-900">Low Priority</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-blue-900">{low}</span>
                  <span className="text-sm text-blue-600">Minor improvement</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Issues Detected - List of actual issues */}
      {issues && issues.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Info className="h-5 w-5 text-gray-600" />
            <h4 className="text-md font-semibold text-gray-900">Issues Detected</h4>
          </div>
          <ul className="space-y-2">
            {issues.map((issue, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm text-gray-700 p-2 bg-yellow-50 rounded-lg border border-yellow-200">
                <span className="text-yellow-600 font-bold mt-0.5">🟡</span>
                <span className="flex-1">{issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {suggestions && suggestions.length > 0 && (
        <div className="bg-gradient-to-br from-primary-50 to-white rounded-xl shadow-sm border border-primary-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Lightbulb className="h-5 w-5 text-primary-600" />
            <h4 className="text-md font-semibold text-gray-900">Recommendations</h4>
          </div>
          <ul className="space-y-3">
            {suggestions.map((suggestion, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm text-gray-700">
                <span className="text-primary-600 font-bold mt-0.5">•</span>
                <span className="flex-1">{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Help Text */}
      <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-gray-500 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-gray-600 space-y-2">
            <p>
              <strong className="text-gray-900">How to use this feedback:</strong>
            </p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Hover over colored boxes on the PDF to see detailed explanations</li>
              <li>Click on boxes to see specific issue descriptions</li>
              <li>Fix critical and high priority issues first</li>
              <li>Re-upload your resume after making changes to see improvement</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}


