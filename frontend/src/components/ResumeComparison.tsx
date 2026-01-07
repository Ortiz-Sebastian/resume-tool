'use client'

import { useState, useEffect, useMemo } from 'react'
import { FileText, Eye, AlertCircle, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ResumeComparisonProps {
  resumeId: number
  scoreData: any
}

interface ExtractionStatus {
  field: string
  label: string
  originalValue: string | null
  extractedValue: string | null
  status: 'found' | 'missing' | 'partial'
  weight: number  // Importance weight for scoring
}

// Field weights - higher = more important for ATS
const FIELD_WEIGHTS = {
  name: 1.5,        // Critical - always needed
  email: 1.5,       // Critical - primary contact
  phone: 1.0,       // Important
  skills: 1.5,      // Very important for ATS matching
  experience: 2.0,  // Most important section
  education: 1.0,   // Important
}

export function ResumeComparison({ resumeId, scoreData }: ResumeComparisonProps) {
  const [parsedData, setParsedData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [activeView, setActiveView] = useState<'side-by-side' | 'extraction'>('side-by-side')

  useEffect(() => {
    if (resumeId) {
      setParsedData(null) // Reset data when resumeId changes
      setError('')
      fetchParsedData()
    }
  }, [resumeId])

  const fetchParsedData = async (retryCount = 0) => {
    const maxRetries = 30 // 30 retries = ~60 seconds max wait time
    const retryDelay = 2000 // 2 seconds between retries
    
    try {
      if (retryCount === 0) {
        setLoading(true)
      }
      const response = await axios.get(`${API_URL}/api/resume/${resumeId}/parsed`)
      
      // Check if we got a 202 (parsing in progress)
      if (response.status === 202) {
        if (retryCount < maxRetries) {
          // Wait and retry
          setTimeout(() => {
            fetchParsedData(retryCount + 1)
          }, retryDelay)
          return
        } else {
          setError('Parsing is taking longer than expected. Please refresh the page.')
          setLoading(false)
          return
        }
      }
      
      // Success - data is ready
      const parsedDataFromResponse = response.data.parsed_data
      
      if (!parsedDataFromResponse) {
        setError('No parsed data received from server')
        setLoading(false)
        return
      }
      
      setParsedData(parsedDataFromResponse)
      setError('')
      setLoading(false)
    } catch (err: any) {
      // Check if it's a 202 status (parsing in progress)
      if (err.response?.status === 202) {
        if (retryCount < maxRetries) {
          setTimeout(() => {
            fetchParsedData(retryCount + 1)
          }, retryDelay)
          return
        } else {
          setError('Parsing is taking longer than expected. Please refresh the page.')
          setLoading(false)
        }
      } else {
        console.error('[ResumeComparison] Error:', err)
        setError(err.response?.data?.detail || 'Failed to load parsed resume')
        setLoading(false)
      }
    }
  }

  // Calculate extraction status for each field
  const extractionStatus = useMemo<ExtractionStatus[]>(() => {
    if (!parsedData) return []

    const statuses: ExtractionStatus[] = []

    // Contact Info
    const contact = parsedData.contact_info || {}
    statuses.push({
      field: 'name',
      label: 'Name',
      originalValue: parsedData.raw_text?.split('\n')[0] || null,
      extractedValue: parsedData.name || null,
      status: parsedData.name ? 'found' : 'missing',
      weight: FIELD_WEIGHTS.name
    })

    statuses.push({
      field: 'email',
      label: 'Email',
      originalValue: null,
      extractedValue: contact.email || parsedData.email || null,
      status: (contact.email || parsedData.email) ? 'found' : 'missing',
      weight: FIELD_WEIGHTS.email
    })

    statuses.push({
      field: 'phone',
      label: 'Phone',
      originalValue: null,
      extractedValue: contact.phone || parsedData.phone || null,
      status: (contact.phone || parsedData.phone) ? 'found' : 'missing',
      weight: FIELD_WEIGHTS.phone
    })

    // Skills
    const skills = parsedData.skills || []
    statuses.push({
      field: 'skills',
      label: 'Skills',
      originalValue: null,
      extractedValue: skills.length > 0 ? `${skills.length} skills found` : null,
      status: skills.length > 5 ? 'found' : skills.length > 0 ? 'partial' : 'missing',
      weight: FIELD_WEIGHTS.skills
    })

    // Experience
    const experience = parsedData.experience || []
    statuses.push({
      field: 'experience',
      label: 'Experience',
      originalValue: null,
      extractedValue: experience.length > 0 ? `${experience.length} positions found` : null,
      status: experience.length > 0 ? 'found' : 'missing',
      weight: FIELD_WEIGHTS.experience
    })

    // Education
    const education = parsedData.education || []
    statuses.push({
      field: 'education',
      label: 'Education',
      originalValue: null,
      weight: FIELD_WEIGHTS.education,
      extractedValue: education.length > 0 ? `${education.length} entries found` : null,
      status: education.length > 0 ? 'found' : 'missing'
    })

    return statuses
  }, [parsedData])

  // Calculate overall extraction score (weighted)
  const extractionScore = useMemo(() => {
    if (extractionStatus.length === 0) return 0
    
    // Calculate weighted score
    let earnedPoints = 0
    let totalPossiblePoints = 0
    
    extractionStatus.forEach(item => {
      totalPossiblePoints += item.weight
      
      if (item.status === 'found') {
        earnedPoints += item.weight  // Full points
      } else if (item.status === 'partial') {
        earnedPoints += item.weight * 0.5  // Half points
      }
      // 'missing' = 0 points
    })
    
    return totalPossiblePoints > 0 
      ? Math.round((earnedPoints / totalPossiblePoints) * 100)
      : 0
  }, [extractionStatus])

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-red-200 p-8">
        <div className="flex items-center text-red-600">
          <AlertCircle className="h-5 w-5 mr-2" />
          <span>{error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with View Toggle */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center">
          <Eye className="h-7 w-7 mr-2 text-blue-600" />
          Resume Comparison
        </h2>
        <div className="flex items-center gap-2 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setActiveView('side-by-side')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeView === 'side-by-side'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Side by Side
          </button>
          <button
            onClick={() => setActiveView('extraction')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeView === 'extraction'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Extraction Status
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 bg-gray-50 px-4 py-3 rounded-lg text-sm">
        <span className="font-medium text-gray-700">Legend:</span>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500"></span>
          <span className="text-gray-600">Extracted</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
          <span className="text-gray-600">Partial</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500"></span>
          <span className="text-gray-600">Missing</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-gray-600">Extraction Score:</span>
          <span className={`font-bold ${
            extractionScore >= 80 ? 'text-green-600' :
            extractionScore >= 60 ? 'text-yellow-600' : 'text-red-600'
          }`}>{extractionScore}%</span>
        </div>
      </div>

      {activeView === 'extraction' ? (
        /* Extraction Status View */
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
            <h3 className="text-lg font-semibold text-white">ATS Extraction Summary</h3>
            <p className="text-blue-100 text-sm mt-1">What the ATS was able to extract from your resume</p>
          </div>
          <div className="p-6">
            {/* Weight explanation */}
            <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
              <strong>Weighted Scoring:</strong> Critical fields (Name, Email, Experience, Skills) count more toward your score.
            </div>
            <div className="grid gap-4">
              {extractionStatus.map((item) => (
                <div
                  key={item.field}
                  className={`flex items-center justify-between p-4 rounded-lg border-2 ${
                    item.status === 'found' ? 'bg-green-50 border-green-200' :
                    item.status === 'partial' ? 'bg-yellow-50 border-yellow-200' :
                    'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {item.status === 'found' ? (
                      <CheckCircle className="h-6 w-6 text-green-600" />
                    ) : item.status === 'partial' ? (
                      <AlertTriangle className="h-6 w-6 text-yellow-600" />
                    ) : (
                      <XCircle className="h-6 w-6 text-red-600" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900">{item.label}</span>
                        {/* Importance badge */}
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          item.weight >= 1.5 ? 'bg-purple-100 text-purple-700' :
                          item.weight >= 1.0 ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {item.weight >= 1.5 ? 'Critical' :
                           item.weight >= 1.0 ? 'Important' :
                           'Optional'}
                        </span>
                      </div>
                      <div className={`text-sm ${
                        item.status === 'found' ? 'text-green-700' :
                        item.status === 'partial' ? 'text-yellow-700' :
                        'text-red-700'
                      }`}>
                        {item.status === 'found' ? 'Successfully extracted' :
                         item.status === 'partial' ? 'Partially extracted' :
                         'Not found by ATS'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-2">
                    {item.extractedValue ? (
                      <span className="text-sm text-gray-700 bg-white px-3 py-1 rounded-full">
                        {item.extractedValue}
                      </span>
                    ) : (
                      <span className="text-sm text-red-600 font-medium">
                        ⚠️ Missing
                      </span>
                    )}
                    {/* Weight indicator */}
                    <span className="text-xs text-gray-400" title="Weight for scoring">
                      ×{item.weight}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Side by Side View */
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Original Format */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="bg-gradient-to-r from-gray-700 to-gray-800 px-6 py-4">
              <h3 className="text-lg font-semibold text-white flex items-center">
                <FileText className="h-5 w-5 mr-2" />
                Your Resume (Original)
              </h3>
              <p className="text-gray-300 text-sm mt-1">How you see your resume</p>
            </div>
            <div className="p-6 h-[600px] overflow-y-auto">
              <div className="prose prose-sm max-w-none">
                {parsedData?.raw_text && parsedData.raw_text.trim().length > 0 ? (
                  <pre className="whitespace-pre-wrap text-sm font-mono text-gray-700 leading-relaxed">
                    {parsedData.raw_text}
                  </pre>
                ) : (
                  <div className="text-gray-500">
                    <p>Original text not available</p>
                    <p className="text-xs mt-2">Debug: parsedData is {parsedData ? 'defined' : 'undefined'}</p>
                    <p className="text-xs">raw_text is {parsedData?.raw_text ? `defined (type: ${typeof parsedData.raw_text}, length: ${parsedData.raw_text?.length || 0})` : 'undefined'}</p>
                    <p className="text-xs">Keys: {parsedData ? Object.keys(parsedData).join(', ') : 'N/A'}</p>
                    {parsedData && (
                      <pre className="text-xs mt-2 bg-gray-100 p-2 rounded overflow-auto max-h-40">
                        {JSON.stringify(parsedData, null, 2).substring(0, 500)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ATS View with Color Coding */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
              <h3 className="text-lg font-semibold text-white flex items-center">
                <Eye className="h-5 w-5 mr-2" />
                ATS View (What Gets Parsed)
              </h3>
              <p className="text-blue-100 text-sm mt-1">What the ATS actually extracts</p>
            </div>
            <div className="p-6 h-[600px] overflow-y-auto">
              <div className="space-y-6">
                {/* Name */}
                <div className={`p-3 rounded-lg ${parsedData?.name ? 'bg-green-50 border-l-4 border-green-500' : 'bg-red-50 border-l-4 border-red-500'}`}>
                  <div className="text-xs font-medium uppercase tracking-wide mb-1 ${parsedData?.name ? 'text-green-600' : 'text-red-600'}">
                    {parsedData?.name ? '✓ NAME EXTRACTED' : '✗ NAME NOT FOUND'}
                  </div>
                  {parsedData?.name ? (
                    <div className="text-2xl font-bold text-gray-900">{parsedData.name}</div>
                  ) : (
                    <div className="text-red-600 text-sm">ATS could not extract your name</div>
                  )}
                </div>

                {/* Contact Info */}
                <div className="space-y-2">
                  <div className="text-xs font-medium uppercase tracking-wide text-gray-500">CONTACT INFO</div>
                  <div className="flex flex-wrap gap-2">
                    {/* Email */}
                    <span className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1 ${
                      (parsedData?.contact_info?.email || parsedData?.email)
                        ? 'bg-green-100 text-green-800 border border-green-200'
                        : 'bg-red-100 text-red-800 border border-red-200'
                    }`}>
                      {(parsedData?.contact_info?.email || parsedData?.email) ? (
                        <>
                          <CheckCircle className="h-3 w-3" />
                          📧 {parsedData.contact_info?.email || parsedData.email}
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3" />
                          📧 Email missing
                        </>
                      )}
                    </span>

                    {/* Phone */}
                    <span className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-1 ${
                      (parsedData?.contact_info?.phone || parsedData?.phone)
                        ? 'bg-green-100 text-green-800 border border-green-200'
                        : 'bg-red-100 text-red-800 border border-red-200'
                    }`}>
                      {(parsedData?.contact_info?.phone || parsedData?.phone) ? (
                        <>
                          <CheckCircle className="h-3 w-3" />
                          📞 {parsedData.contact_info?.phone || parsedData.phone}
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3" />
                          📞 Phone missing
                        </>
                      )}
                    </span>

                    {/* LinkedIn - only show if found, no warning if missing */}
                    {(parsedData?.contact_info?.linkedin || parsedData?.linkedin) && (
                      <span className="px-3 py-1.5 rounded-full text-sm flex items-center gap-1 bg-green-100 text-green-800 border border-green-200">
                        <CheckCircle className="h-3 w-3" />
                        💼 LinkedIn found
                      </span>
                    )}

                    {/* Location - only show if found, no warning if missing */}
                    {(parsedData?.contact_info?.location || parsedData?.location) && (
                      <span className="px-3 py-1.5 rounded-full text-sm flex items-center gap-1 bg-green-100 text-green-800 border border-green-200">
                        <CheckCircle className="h-3 w-3" />
                        📍 {parsedData.contact_info?.location || parsedData.location}
                      </span>
                    )}
                  </div>
                </div>

                {/* Skills */}
                <div className={`p-4 rounded-lg ${
                  parsedData?.skills?.length > 5 ? 'bg-green-50 border border-green-200' :
                  parsedData?.skills?.length > 0 ? 'bg-yellow-50 border border-yellow-200' :
                  'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-medium uppercase tracking-wide text-gray-600">SKILLS</div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      parsedData?.skills?.length > 5 ? 'bg-green-200 text-green-800' :
                      parsedData?.skills?.length > 0 ? 'bg-yellow-200 text-yellow-800' :
                      'bg-red-200 text-red-800'
                    }`}>
                      {parsedData?.skills?.length || 0} extracted
                    </span>
                  </div>
                  {parsedData?.skills && parsedData.skills.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {parsedData.skills.map((skill: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-white text-gray-800 rounded-full text-sm border border-gray-200"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-red-600 text-sm flex items-center gap-2">
                      <XCircle className="h-4 w-4" />
                      No skills extracted - check if skills are in a table or unusual format
                    </div>
                  )}
                </div>

                {/* Experience */}
                <div className={`p-4 rounded-lg ${
                  parsedData?.experience?.length > 0 ? 'bg-green-50 border border-green-200' :
                  'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-xs font-medium uppercase tracking-wide text-gray-600">EXPERIENCE</div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      parsedData?.experience?.length > 0 ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'
                    }`}>
                      {parsedData?.experience?.length || 0} positions
                    </span>
                  </div>
                  {parsedData?.experience && parsedData.experience.length > 0 ? (
                    <div className="space-y-4">
                      {parsedData.experience.map((exp: any, idx: number) => {
                        // Format dates
                        let dateRange = ""
                        if (exp.start_date && exp.start_date.trim()) {
                          const start = exp.start_date.trim()
                          const end = (exp.end_date && exp.end_date.trim()) ? exp.end_date.trim() : "Present"
                          dateRange = `${start} - ${end}`
                        } else if (exp.end_date && exp.end_date.trim()) {
                          dateRange = `Until ${exp.end_date.trim()}`
                        } else if (exp.dates && exp.dates.trim()) {
                          dateRange = exp.dates.trim()
                        }
                        
                        return (
                          <div key={idx} className="bg-white p-3 rounded-lg border border-gray-200">
                            <div className="font-semibold text-gray-900 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4 text-green-600" />
                              {exp.title || <span className="text-yellow-600">Title not parsed</span>}
                            </div>
                            {exp.company && (
                              <div className="text-sm text-gray-600">{exp.company}</div>
                            )}
                            {dateRange && (
                              <div className="text-sm text-gray-500">{dateRange}</div>
                            )}
                            {exp.location && (
                              <div className="text-sm text-gray-500">{exp.location}</div>
                            )}
                            {exp.description && (
                              <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">{exp.description}</div>
                            )}
                            {exp.highlights && exp.highlights.length > 0 && (
                              <ul className="mt-2 space-y-1">
                                {exp.highlights.map((highlight: string, hIdx: number) => (
                                  <li key={hIdx} className="text-sm text-gray-700">• {highlight}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="text-red-600 text-sm flex items-center gap-2">
                      <XCircle className="h-4 w-4" />
                      No experience extracted - major formatting issue detected
                    </div>
                  )}
                </div>

                {/* Education */}
                <div className={`p-4 rounded-lg ${
                  parsedData?.education?.length > 0 ? 'bg-green-50 border border-green-200' :
                  'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-xs font-medium uppercase tracking-wide text-gray-600">EDUCATION</div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      parsedData?.education?.length > 0 ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'
                    }`}>
                      {parsedData?.education?.length || 0} entries
                    </span>
                  </div>
                  {parsedData?.education && parsedData.education.length > 0 ? (
                    <div className="space-y-3">
                      {parsedData.education.map((edu: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded-lg border border-gray-200">
                          <div className="font-semibold text-gray-900 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            {edu.degree || <span className="text-yellow-600">Degree not parsed</span>}
                          </div>
                          {edu.institution && (
                            <div className="text-sm text-gray-600">{edu.institution}</div>
                          )}
                          {edu.graduation_date && (
                            <div className="text-sm text-gray-500">{edu.graduation_date}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-red-600 text-sm flex items-center gap-2">
                      <XCircle className="h-4 w-4" />
                      No education extracted
                    </div>
                  )}
                </div>

                {/* Projects */}
                {(parsedData?.projects && parsedData.projects.length > 0) && (
                  <div className="p-4 rounded-lg bg-green-50 border border-green-200">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-600">PROJECTS</div>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-200 text-green-800">
                        {parsedData.projects.length} {parsedData.projects.length === 1 ? 'project' : 'projects'}
                      </span>
                    </div>
                    <div className="space-y-3">
                      {parsedData.projects.map((project: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded-lg border border-gray-200">
                          <div className="font-semibold text-gray-900 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            {project.name || <span className="text-yellow-600">Project name not parsed</span>}
                          </div>
                          {project.description && (
                            <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">{project.description}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Achievements */}
                {(parsedData?.achievements && parsedData.achievements.length > 0) && (
                  <div className="p-4 rounded-lg bg-green-50 border border-green-200">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-600">ACHIEVEMENTS</div>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-200 text-green-800">
                        {parsedData.achievements.length} {parsedData.achievements.length === 1 ? 'achievement' : 'achievements'}
                      </span>
                    </div>
                    <div className="space-y-3">
                      {parsedData.achievements.map((achievement: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded-lg border border-gray-200">
                          <div className="font-semibold text-gray-900 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            {achievement.name || <span className="text-yellow-600">Achievement name not parsed</span>}
                          </div>
                          {achievement.description && (
                            <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">{achievement.description}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Associations / Extracurriculars */}
                {(parsedData?.associations && parsedData.associations.length > 0) && (
                  <div className="p-4 rounded-lg bg-green-50 border border-green-200">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-gray-600">ASSOCIATIONS / EXTRACURRICULARS</div>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-200 text-green-800">
                        {parsedData.associations.length} {parsedData.associations.length === 1 ? 'entry' : 'entries'}
                      </span>
                    </div>
                    <div className="space-y-3">
                      {parsedData.associations.map((association: any, idx: number) => (
                        <div key={idx} className="bg-white p-3 rounded-lg border border-gray-200">
                          <div className="font-semibold text-gray-900 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            {association.name || <span className="text-yellow-600">Association name not parsed</span>}
                          </div>
                          {association.role && (
                            <div className="mt-1 text-sm text-gray-600">{association.role}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

