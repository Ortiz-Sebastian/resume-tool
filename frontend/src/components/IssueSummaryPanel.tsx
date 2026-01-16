'use client'

import { useState, useEffect } from 'react'
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
  issueDetails?: Array<{  // Detailed issue info for fix mode
    code: string
    message: string
    severity: 'critical' | 'high' | 'medium' | 'low'
    blocks?: Array<{
      page: number
      bbox: number[]
      text_preview: string
    }>
    detected_reason?: string
    expected_section?: string
  }>
  onIssueClick?: (issueId: string) => void  // Callback when issue is clicked
}

export function IssueSummaryPanel({ summary, suggestions, issues = [], issueDetails = [], onIssueClick }: IssueSummaryPanelProps) {
  const { total_issues, critical, high, medium, low } = summary

  // Debug logging
  useEffect(() => {
    console.log('IssueSummaryPanel - Issues:', issues)
    console.log('IssueSummaryPanel - IssueDetails:', issueDetails)
    console.log('IssueSummaryPanel - onIssueClick:', typeof onIssueClick)
  }, [issues, issueDetails, onIssueClick])

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
            {issues.map((issue, idx) => {
              // Try to find matching issue detail - match by message (exact or contains) or by code
              const issueDetail = issueDetails.find(d => {
                if (!d || !d.message) return false
                // Normalize strings for comparison
                const issueLower = issue.toLowerCase().trim()
                const messageLower = (d.message || '').toLowerCase().trim()
                const codeLower = (d.code || '').toLowerCase().trim()
                
                // Try exact match first
                if (messageLower === issueLower || codeLower === issueLower) return true
                
                // Try substring match (message contains issue or vice versa)
                if (messageLower.includes(issueLower) || issueLower.includes(messageLower)) return true
                
                // Try matching first few words
                const issueWords = issueLower.split(/\s+/).slice(0, 3).join(' ')
                const messageWords = messageLower.split(/\s+/).slice(0, 3).join(' ')
                if (issueWords && messageWords && (messageWords.includes(issueWords) || issueWords.includes(messageWords))) return true
                
                return false
              })
              
              const severity = issueDetail?.severity || 'medium'
              const hasBlocks = issueDetail?.blocks && Array.isArray(issueDetail.blocks) && issueDetail.blocks.length > 0
              const isClickable = hasBlocks && onIssueClick && issueDetail
              
              // Debug logging for first issue
              if (idx === 0) {
                console.log('IssueSummaryPanel - First issue:', issue)
                console.log('IssueSummaryPanel - Found detail:', issueDetail)
                console.log('IssueSummaryPanel - Has blocks:', hasBlocks)
                console.log('IssueSummaryPanel - Is clickable:', isClickable)
              }
              
              const getSeverityStyles = (sev: string) => {
                switch (sev) {
                  case 'critical': return { bg: 'bg-red-50', border: 'border-red-200', icon: '🔴', text: 'text-red-700' }
                  case 'high': return { bg: 'bg-orange-50', border: 'border-orange-200', icon: '🟠', text: 'text-orange-700' }
                  case 'medium': return { bg: 'bg-yellow-50', border: 'border-yellow-200', icon: '🟡', text: 'text-yellow-700' }
                  case 'low': return { bg: 'bg-blue-50', border: 'border-blue-200', icon: '🔵', text: 'text-blue-700' }
                  default: return { bg: 'bg-yellow-50', border: 'border-yellow-200', icon: '🟡', text: 'text-yellow-700' }
                }
              }
              
              const styles = getSeverityStyles(severity)
              
              return (
                <li 
                  key={idx} 
                  className={`flex items-start gap-3 text-sm text-gray-700 p-3 rounded-lg border ${styles.bg} ${styles.border} ${
                    isClickable ? 'cursor-pointer hover:shadow-md transition-shadow' : ''
                  }`}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    if (isClickable && issueDetail && onIssueClick) {
                      console.log('IssueSummaryPanel - Clicking issue:', issueDetail.code, issueDetail)
                      onIssueClick(issueDetail.code)
                    } else {
                      console.log('IssueSummaryPanel - Issue not clickable:', { isClickable, hasIssueDetail: !!issueDetail, hasOnClick: !!onIssueClick })
                    }
                  }}
                  title={isClickable ? 'Click to view on PDF' : undefined}
                >
                  <span className={`${styles.text} font-bold mt-0.5`}>{styles.icon}</span>
                  <span className="flex-1">{issue}</span>
                  {isClickable && (
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <span>📍</span>
                      <span>View</span>
                    </span>
                  )}
                </li>
              )
            })}
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


