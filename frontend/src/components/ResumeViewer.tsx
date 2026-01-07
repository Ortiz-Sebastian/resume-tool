'use client'

import { useState, useEffect } from 'react'
import { FileText, Eye, AlertCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ResumeViewerProps {
  resumeId: number
  scoreData: any
}

export function ResumeViewer({ resumeId, scoreData }: ResumeViewerProps) {
  const [parsedData, setParsedData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

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
        setError(err.response?.data?.detail || 'Failed to load parsed resume')
        setLoading(false)
      }
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
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
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center">
          <Eye className="h-7 w-7 mr-2 text-primary-600" />
          Resume Comparison
        </h2>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Original Format */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-4">
            <h3 className="text-lg font-semibold text-white flex items-center">
              <FileText className="h-5 w-5 mr-2" />
              Original Resume
            </h3>
          </div>
          <div className="p-6 h-[600px] overflow-y-auto scrollbar-hide">
            <div className="prose prose-sm max-w-none">
              {parsedData?.raw_text && parsedData.raw_text.trim().length > 0 ? (
                <pre className="whitespace-pre-wrap text-sm font-mono text-gray-700">
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

        {/* ATS View */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-green-600 to-green-700 px-6 py-4">
            <h3 className="text-lg font-semibold text-white flex items-center">
              <Eye className="h-5 w-5 mr-2" />
              ATS View
            </h3>
          </div>
          <div className="p-6 h-[600px] overflow-y-auto scrollbar-hide">
            <div className="space-y-6">
              {/* Name */}
              {parsedData?.name && (
                <div>
                  <div className="text-2xl font-bold text-gray-900">{parsedData.name}</div>
                </div>
              )}

              {/* Contact */}
              {(parsedData?.contact_info?.email || parsedData?.contact_info?.phone || parsedData?.email || parsedData?.phone) && (
                <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                  {(parsedData.contact_info?.email || parsedData.email) && (
                    <span>📧 {parsedData.contact_info?.email || parsedData.email}</span>
                  )}
                  {(parsedData.contact_info?.phone || parsedData.phone) && (
                    <span>📞 {parsedData.contact_info?.phone || parsedData.phone}</span>
                  )}
                  {(parsedData.contact_info?.linkedin || parsedData.linkedin) && (
                    <span>💼 {parsedData.contact_info?.linkedin || parsedData.linkedin}</span>
                  )}
                  {(parsedData.contact_info?.location || parsedData.location) && (
                    <span>📍 {parsedData.contact_info?.location || parsedData.location}</span>
                  )}
                </div>
              )}

              {/* Summary */}
              {parsedData?.summary && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">SUMMARY</h4>
                  <p className="text-gray-700">{parsedData.summary}</p>
                </div>
              )}

              {/* Skills */}
              {parsedData?.skills && parsedData.skills.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">SKILLS</h4>
                  <div className="flex flex-wrap gap-2">
                    {parsedData.skills.map((skill: string, idx: number) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Experience */}
              {parsedData?.experience && parsedData.experience.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">EXPERIENCE</h4>
                  <div className="space-y-4">
                    {parsedData.experience.map((exp: any, idx: number) => (
                      <div key={idx} className="border-l-2 border-primary-300 pl-4">
                        <div className="font-semibold text-gray-900">
                          {exp.title || 'Position'}
                        </div>
                        {exp.company && (
                          <div className="text-sm text-gray-600">{exp.company}</div>
                        )}
                        {exp.dates && (
                          <div className="text-sm text-gray-500">{exp.dates}</div>
                        )}
                        {exp.location && (
                          <div className="text-sm text-gray-500">{exp.location}</div>
                        )}
                        {exp.description && (
                          <p className="text-sm text-gray-600 mt-1">{exp.description}</p>
                        )}
                        {exp.bullets && exp.bullets.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {exp.bullets.map((bullet: string, bidx: number) => (
                              <li key={bidx} className="text-sm text-gray-600">• {bullet}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Education */}
              {parsedData?.education && parsedData.education.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">EDUCATION</h4>
                  <div className="space-y-3">
                    {parsedData.education.map((edu: any, idx: number) => (
                      <div key={idx}>
                        <div className="font-semibold text-gray-900">
                          {edu.degree || 'Degree'}
                        </div>
                        {edu.institution && (
                          <div className="text-sm text-gray-600">{edu.institution}</div>
                        )}
                        {edu.graduation_date && (
                          <div className="text-sm text-gray-500">{edu.graduation_date}</div>
                        )}
                        {edu.gpa && (
                          <div className="text-sm text-gray-500">GPA: {edu.gpa}</div>
                        )}
                        {edu.major && (
                          <div className="text-sm text-gray-600">Major: {edu.major}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Certifications */}
              {parsedData?.certifications && parsedData.certifications.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">CERTIFICATIONS</h4>
                  <ul className="space-y-2">
                    {parsedData.certifications.map((cert: any, idx: number) => (
                      <li key={idx} className="text-gray-700">
                        • {typeof cert === 'string' ? cert : cert.name || 'Unknown Certification'}
                        {cert.issuer && <span className="text-gray-500 text-sm ml-2">({cert.issuer})</span>}
                        {cert.date && <span className="text-gray-500 text-sm ml-2">- {cert.date}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

