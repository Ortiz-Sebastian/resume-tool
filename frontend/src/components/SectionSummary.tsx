'use client'

import { useState, useEffect } from 'react'
import { CheckCircle, AlertCircle, XCircle, ChevronRight, Loader } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface SectionComparison {
  section_name: string
  status: string
  original_count?: number
  extracted_count?: number
  message: string
  details?: string
}

interface SectionAnalysis {
  section: string
  status: string
  formatting_issues: string[]
  recommendations: string[]
  highlights: any[]
  visual_location?: any
}

interface SectionSummaryProps {
  resumeId: number
  onSectionAnalyzed?: (analysis: SectionAnalysis) => void
}

export function SectionSummary({ resumeId, onSectionAnalyzed }: SectionSummaryProps) {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [analyzingSection, setAnalyzingSection] = useState<string | null>(null)
  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [sectionAnalysis, setSectionAnalysis] = useState<Record<string, SectionAnalysis>>({})

  useEffect(() => {
    fetchSummary()
  }, [resumeId])

  const fetchSummary = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/resume/${resumeId}/summary`)
      setSummary(response.data)
    } catch (err) {
      console.error('Failed to load summary:', err)
    } finally {
      setLoading(false)
    }
  }

  const analyzeSection = async (sectionName: string) => {
    try {
      setAnalyzingSection(sectionName)
      const response = await axios.post(`${API_URL}/api/analyze-section`, {
        resume_id: resumeId,
        section: sectionName
      })
      
      const analysis = response.data
      setSectionAnalysis(prev => ({
        ...prev,
        [sectionName]: analysis
      }))
      setExpandedSection(sectionName)
      
      // Notify parent component
      if (onSectionAnalyzed) {
        onSectionAnalyzed(analysis)
      }
    } catch (err) {
      console.error(`Failed to analyze ${sectionName}:`, err)
    } finally {
      setAnalyzingSection(null)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'perfect':
      case 'good':
        return <CheckCircle className="h-6 w-6 text-green-500" />
      case 'issues':
        return <AlertCircle className="h-6 w-6 text-yellow-500" />
      case 'missing':
      case 'critical':
        return <XCircle className="h-6 w-6 text-red-500" />
      default:
        return <AlertCircle className="h-6 w-6 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'perfect':
      case 'good':
        return 'bg-green-50 border-green-200'
      case 'issues':
        return 'bg-yellow-50 border-yellow-200'
      case 'missing':
      case 'critical':
        return 'bg-red-50 border-red-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const getSectionDisplayName = (sectionName: string) => {
    const names: Record<string, string> = {
      'contact_info': 'Contact Information',
      'skills': 'Skills',
      'experience': 'Work Experience',
      'education': 'Education',
      'certifications': 'Certifications'
    }
    return names[sectionName] || sectionName
  }

  const canAnalyzeSection = (sectionName: string) => {
    return ['skills', 'experience', 'education', 'contact_info'].includes(sectionName)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <Loader className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      </div>
    )
  }

  if (!summary) {
    return null
  }

  const overallStatus = summary.overall_status

  return (
    <div className="space-y-4">
      {/* Overall Status Banner */}
      <div className={`rounded-xl p-6 border ${
        overallStatus === 'good' ? 'bg-green-50 border-green-200' :
        overallStatus === 'needs_improvement' ? 'bg-yellow-50 border-yellow-200' :
        'bg-red-50 border-red-200'
      }`}>
        <h3 className="text-lg font-semibold mb-2">
          {overallStatus === 'good' && '✅ Resume Looks Good!'}
          {overallStatus === 'needs_improvement' && '⚠️ Some Sections Need Attention'}
          {overallStatus === 'critical' && '🔴 Multiple Issues Detected'}
        </h3>
        <p className="text-sm text-gray-700">
          {overallStatus === 'good' && 'ATS is extracting most of your resume content correctly.'}
          {overallStatus === 'needs_improvement' && 'A few sections have formatting issues that might hurt ATS readability.'}
          {overallStatus === 'critical' && 'Several sections have formatting problems. Click sections below to see how to fix them.'}
        </p>
      </div>

      {/* Section Cards */}
      <div className="space-y-3">
        {summary.sections.map((section: SectionComparison) => {
          const isExpanded = expandedSection === section.section_name
          const analysis = sectionAnalysis[section.section_name]
          const isAnalyzing = analyzingSection === section.section_name

          return (
            <div
              key={section.section_name}
              className={`rounded-xl border ${getStatusColor(section.status)} overflow-hidden`}
            >
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    {getStatusIcon(section.status)}
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900">
                        {getSectionDisplayName(section.section_name)}
                      </h4>
                      <p className="text-sm text-gray-600 mt-1">{section.message}</p>
                      {section.details && (
                        <p className="text-xs text-gray-500 mt-1">{section.details}</p>
                      )}
                      {section.extracted_count !== undefined && section.original_count !== undefined && (
                        <p className="text-xs text-gray-500 mt-1">
                          Extracted: {section.extracted_count} / {section.original_count}
                        </p>
                      )}
                    </div>
                  </div>

                  {canAnalyzeSection(section.section_name) && section.status !== 'perfect' && (
                    <button
                      onClick={() => {
                        if (isExpanded) {
                          setExpandedSection(null)
                        } else {
                          analyzeSection(section.section_name)
                        }
                      }}
                      disabled={isAnalyzing}
                      className="ml-4 flex items-center space-x-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                      {isAnalyzing ? (
                        <>
                          <Loader className="h-4 w-4 animate-spin" />
                          <span className="text-sm">Analyzing...</span>
                        </>
                      ) : (
                        <>
                          <span className="text-sm font-medium">
                            {isExpanded ? 'Hide Details' : 'Analyze Section'}
                          </span>
                          <ChevronRight className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                        </>
                      )}
                    </button>
                  )}
                </div>

                {/* Expanded Analysis */}
                {isExpanded && analysis && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h5 className="font-semibold text-gray-900 mb-2">Detected Issues:</h5>
                    {analysis.formatting_issues.length > 0 ? (
                      <ul className="space-y-1 mb-4">
                        {analysis.formatting_issues.map((issue, idx) => (
                          <li key={idx} className="text-sm text-gray-700 flex items-start">
                            <span className="text-red-500 mr-2">•</span>
                            <span>{issue}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-500 mb-4">No specific formatting issues detected.</p>
                    )}

                    {analysis.recommendations.length > 0 && (
                      <>
                        <h5 className="font-semibold text-gray-900 mb-2">Recommendations:</h5>
                        <ul className="space-y-1">
                          {analysis.recommendations.map((rec, idx) => (
                            <li key={idx} className="text-sm text-gray-700 flex items-start">
                              <span className="text-green-500 mr-2">✓</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

