'use client'

import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react'

interface DataValidationProps {
  validationResults: {
    education?: {
      has_issues: boolean
      issues: Array<{
        entry_index: number
        entry: any
        severity: 'low' | 'medium' | 'high'
        message: string
        field: string
      }>
      valid_entries: number
      total_entries: number
    }
    experience?: {
      has_issues: boolean
      issues: Array<{
        entry_index: number
        entry: any
        severity: 'low' | 'medium' | 'high'
        message: string
        field: string
      }>
      valid_entries: number
      total_entries: number
    }
    overall?: {
      has_issues: boolean
      total_issues: number
    }
  }
  parsedData?: any
}

export function DataValidation({ validationResults, parsedData }: DataValidationProps) {
  if (!validationResults || !validationResults.overall?.has_issues) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center text-center">
          <div>
            <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Validation Issues</h3>
            <p className="text-gray-600">All extracted data appears to be accurate and correctly classified.</p>
          </div>
        </div>
      </div>
    )
  }

  const getSeverityColor = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'medium':
        return 'bg-orange-50 border-orange-200 text-orange-800'
      case 'low':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getSeverityIcon = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return <AlertCircle className="h-5 w-5 text-red-600" />
      case 'medium':
        return <AlertTriangle className="h-5 w-5 text-orange-600" />
      case 'low':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />
      default:
        return <AlertCircle className="h-5 w-5 text-gray-600" />
    }
  }

  const educationIssues = validationResults.education?.issues || []
  const experienceIssues = validationResults.experience?.issues || []

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-2">
          <AlertCircle className="h-6 w-6 text-orange-600" />
          Data Validation Issues
        </h3>
        <p className="text-gray-600 text-sm">
          Found {validationResults.overall?.total_issues || 0} issue(s) with the accuracy of extracted data.
          These entries may be misclassified or incomplete.
        </p>
      </div>

      <div className="space-y-6">
        {/* Education Issues */}
        {educationIssues.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-600" />
              Education ({educationIssues.length} issue{educationIssues.length !== 1 ? 's' : ''})
            </h4>
            <div className="space-y-3">
              {educationIssues.map((issue, idx) => {
                const entry = parsedData?.education?.[issue.entry_index]
                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                  >
                    <div className="flex items-start gap-3">
                      {getSeverityIcon(issue.severity)}
                      <div className="flex-1">
                        <div className="font-semibold mb-1">{issue.message}</div>
                        {entry && (
                          <div className="mt-2 text-sm bg-white bg-opacity-50 p-2 rounded border border-current border-opacity-20">
                            <div className="font-medium mb-1">Extracted Entry:</div>
                            {entry.degree && (
                              <div><strong>Degree:</strong> {entry.degree}</div>
                            )}
                            {entry.institution && (
                              <div><strong>Institution:</strong> {entry.institution}</div>
                            )}
                            {entry.organization && (
                              <div><strong>Organization:</strong> {entry.organization}</div>
                            )}
                            {!entry.degree && !entry.institution && !entry.organization && (
                              <div className="text-gray-500 italic">Empty entry</div>
                            )}
                          </div>
                        )}
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full capitalize ${
                        issue.severity === 'high' ? 'bg-red-200 text-red-900' :
                        issue.severity === 'medium' ? 'bg-orange-200 text-orange-900' :
                        'bg-yellow-200 text-yellow-900'
                      }`}>
                        {issue.severity}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Experience Issues */}
        {experienceIssues.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-600" />
              Experience ({experienceIssues.length} issue{experienceIssues.length !== 1 ? 's' : ''})
            </h4>
            <div className="space-y-3">
              {experienceIssues.map((issue, idx) => {
                const entry = parsedData?.experience?.[issue.entry_index]
                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                  >
                    <div className="flex items-start gap-3">
                      {getSeverityIcon(issue.severity)}
                      <div className="flex-1">
                        <div className="font-semibold mb-1">{issue.message}</div>
                        {entry && (
                          <div className="mt-2 text-sm bg-white bg-opacity-50 p-2 rounded border border-current border-opacity-20">
                            <div className="font-medium mb-1">Extracted Entry:</div>
                            {entry.title && (
                              <div><strong>Title:</strong> {entry.title}</div>
                            )}
                            {entry.position && (
                              <div><strong>Position:</strong> {entry.position}</div>
                            )}
                            {entry.company && (
                              <div><strong>Company:</strong> {entry.company}</div>
                            )}
                            {entry.organization && (
                              <div><strong>Organization:</strong> {entry.organization}</div>
                            )}
                            {!entry.title && !entry.position && !entry.company && !entry.organization && (
                              <div className="text-gray-500 italic">Empty entry</div>
                            )}
                          </div>
                        )}
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full capitalize ${
                        issue.severity === 'high' ? 'bg-red-200 text-red-900' :
                        issue.severity === 'medium' ? 'bg-orange-200 text-orange-900' :
                        'bg-yellow-200 text-yellow-900'
                      }`}>
                        {issue.severity}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

