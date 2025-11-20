'use client'

import { useState, useEffect } from 'react'
import { Target, TrendingUp, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RoleMatchesProps {
  resumeId: number
  onMatchesReceived: (matches: any[]) => void
}

export function RoleMatches({ resumeId, onMatchesReceived }: RoleMatchesProps) {
  const [matches, setMatches] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [expandedRole, setExpandedRole] = useState<number>(0)

  useEffect(() => {
    fetchRoleMatches()
  }, [resumeId])

  const fetchRoleMatches = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/roles/${resumeId}`, {
        params: { top_k: 5 }
      })
      setMatches(response.data.matches)
      onMatchesReceived(response.data.matches)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load role matches')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <Loader2 className="h-12 w-12 text-primary-600 animate-spin" />
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

  const getMatchColor = (score: number) => {
    if (score >= 70) return 'bg-green-500'
    if (score >= 50) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getMatchBgColor = (score: number) => {
    if (score >= 70) return 'bg-green-50 border-green-200'
    if (score >= 50) return 'bg-yellow-50 border-yellow-200'
    return 'bg-red-50 border-red-200'
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
        <Target className="h-7 w-7 mr-2 text-primary-600" />
        Best Role Matches
      </h2>

      <div className="space-y-4">
        {matches.map((match, idx) => (
          <div
            key={idx}
            className={`border rounded-lg overflow-hidden transition-all ${
              expandedRole === idx ? getMatchBgColor(match.match_score) : 'bg-white border-gray-200'
            }`}
          >
            <button
              onClick={() => setExpandedRole(expandedRole === idx ? -1 : idx)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-4 flex-1">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-100 text-primary-700 font-bold text-lg">
                    #{idx + 1}
                  </div>
                  <div className="text-left">
                    <h3 className="text-lg font-semibold text-gray-900">{match.role_title}</h3>
                    <p className="text-sm text-gray-600">{match.role_description}</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl font-bold text-gray-900">
                      {Math.round(match.match_score)}%
                    </span>
                    <div className={`w-3 h-3 rounded-full ${getMatchColor(match.match_score)}`} />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Match Score</div>
                </div>
                {expandedRole === idx ? (
                  <ChevronUp className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </button>

            {expandedRole === idx && (
              <div className="px-6 pb-6 space-y-4 border-t bg-white">
                {/* Matched Skills */}
                {match.matched_skills && match.matched_skills.length > 0 && (
                  <div className="pt-4">
                    <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                      <TrendingUp className="h-4 w-4 mr-2 text-green-600" />
                      Matching Skills ({match.matched_skills.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {match.matched_skills.map((skill: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium"
                        >
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Missing Skills */}
                {match.missing_skills && match.missing_skills.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                      <AlertCircle className="h-4 w-4 mr-2 text-orange-600" />
                      Skills to Develop ({match.missing_skills.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {match.missing_skills.map((skill: string, idx: number) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-medium"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggestions */}
                {match.suggestions && match.suggestions.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-3">Recommendations</h4>
                    <ul className="space-y-2">
                      {match.suggestions.map((suggestion: string, idx: number) => (
                        <li key={idx} className="flex items-start text-sm text-gray-700">
                          <span className="mr-2 text-primary-600">•</span>
                          <span>{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

