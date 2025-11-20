'use client'

import { useState, useEffect } from 'react'
import { Lightbulb, ExternalLink, Loader2, AlertCircle, BookOpen } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface SkillSuggestionsProps {
  resumeId: number
  topRole: any
}

export function SkillSuggestions({ resumeId, topRole }: SkillSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    if (topRole) {
      fetchSuggestions()
    }
  }, [resumeId, topRole])

  const fetchSuggestions = async () => {
    try {
      setLoading(true)
      const response = await axios.post(`${API_URL}/api/suggest`, {
        resume_id: resumeId,
        target_role: topRole.role_title
      })
      setSuggestions(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load skill suggestions')
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

  if (!suggestions) return null

  const getImportanceBadge = (importance: string) => {
    const badges = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      recommended: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      'nice-to-have': 'bg-blue-100 text-blue-800 border-blue-300',
    }
    return badges[importance as keyof typeof badges] || badges['nice-to-have']
  }

  const getImportanceIcon = (importance: string) => {
    if (importance === 'critical') return '🔥'
    if (importance === 'recommended') return '⭐'
    return '💡'
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
          <Lightbulb className="h-7 w-7 mr-2 text-primary-600" />
          Skill Suggestions
        </h2>
        <p className="text-gray-600">
          Recommended skills to improve your match for{' '}
          <span className="font-semibold text-primary-700">{suggestions.target_role}</span>
        </p>
      </div>

      {/* Current Skills Overview */}
      {suggestions.current_skills && suggestions.current_skills.length > 0 && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="font-semibold text-green-900 mb-2 flex items-center">
            <BookOpen className="h-4 w-4 mr-2" />
            Your Current Skills ({suggestions.current_skills.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {suggestions.current_skills.slice(0, 10).map((skill: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
              >
                {skill}
              </span>
            ))}
            {suggestions.current_skills.length > 10 && (
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                +{suggestions.current_skills.length - 10} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Suggested Skills */}
      <div className="space-y-4">
        {suggestions.suggested_skills && suggestions.suggested_skills.length > 0 ? (
          suggestions.suggested_skills.map((suggestion: any, idx: number) => (
            <div
              key={idx}
              className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start space-x-3 flex-1">
                  <span className="text-2xl">{getImportanceIcon(suggestion.importance)}</span>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                      {suggestion.skill}
                    </h3>
                    <span
                      className={`inline-block px-2 py-1 rounded-md text-xs font-medium border ${getImportanceBadge(
                        suggestion.importance
                      )}`}
                    >
                      {suggestion.importance.replace('-', ' ').toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-gray-700 mb-4 ml-11">{suggestion.reason}</p>

              {/* Learning Resources */}
              {suggestion.learning_resources && suggestion.learning_resources.length > 0 && (
                <div className="ml-11">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Learning Resources:</h4>
                  <div className="space-y-2">
                    {suggestion.learning_resources.map((resource: string, resIdx: number) => (
                      <a
                        key={resIdx}
                        href={resource}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center text-sm text-primary-600 hover:text-primary-700 hover:underline"
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        <span className="truncate">{resource}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>No additional skills suggested at this time.</p>
            <p className="text-sm mt-2">Your current skills align well with this role!</p>
          </div>
        )}
      </div>

      {/* Action CTA */}
      {suggestions.suggested_skills && suggestions.suggested_skills.length > 0 && (
        <div className="mt-6 p-4 bg-primary-50 border border-primary-200 rounded-lg">
          <h3 className="font-semibold text-primary-900 mb-2">Next Steps</h3>
          <p className="text-sm text-primary-800 mb-3">
            Focus on the critical skills first to maximize your chances of landing a {suggestions.target_role} role.
            Start with online courses, documentation, and hands-on projects.
          </p>
          <div className="flex items-center space-x-2 text-sm text-primary-700">
            <span className="font-medium">Pro tip:</span>
            <span>Add these skills to your resume once you've gained practical experience with them.</span>
          </div>
        </div>
      )}
    </div>
  )
}

