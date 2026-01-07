'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ScoreCardProps {
  resumeId: number
  onScoreReceived: (data: any) => void
}

export function ScoreCard({ resumeId, onScoreReceived }: ScoreCardProps) {
  const [scoreData, setScoreData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    fetchScore()
  }, [resumeId])

  const fetchScore = async (retryCount = 0) => {
    const maxRetries = 30 // 30 retries = ~60 seconds max wait time
    const retryDelay = 2000 // 2 seconds between retries
    
    try {
      if (retryCount === 0) {
        setLoading(true)
      }
      const response = await axios.post(`${API_URL}/api/score/${resumeId}`)
      
      // Check if we got a 202 (parsing in progress)
      if (response.status === 202) {
        if (retryCount < maxRetries) {
          // Wait and retry
          setTimeout(() => {
            fetchScore(retryCount + 1)
          }, retryDelay)
          return
        } else {
          setError('Parsing is taking longer than expected. Please refresh the page.')
          setLoading(false)
          return
        }
      }
      
      // Success - data is ready
      setScoreData(response.data)
      onScoreReceived(response.data)
      setError('')
      setLoading(false)
    } catch (err: any) {
      // Check if it's a 202 status (parsing in progress)
      if (err.response?.status === 202) {
        if (retryCount < maxRetries) {
          setTimeout(() => {
            fetchScore(retryCount + 1)
          }, retryDelay)
          return
        } else {
          setError('Parsing is taking longer than expected. Please refresh the page.')
          setLoading(false)
        }
      } else {
        setError(err.response?.data?.detail || 'Failed to calculate score')
        setLoading(false)
      }
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

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreGradient = (score: number) => {
    if (score >= 80) return 'from-green-500 to-green-600'
    if (score >= 60) return 'from-yellow-500 to-yellow-600'
    return 'from-red-500 to-red-600'
  }

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <div className="bg-gradient-to-br from-primary-50 to-white rounded-xl shadow-lg border border-primary-200 p-8">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
              <TrendingUp className="h-7 w-7 mr-2 text-primary-600" />
              ATS Compatibility Score
            </h2>
            <p className="text-gray-600">How well your resume will perform with ATS systems</p>
          </div>
          <div className="flex flex-col items-center">
            <div className={`text-6xl font-bold ${getScoreColor(scoreData.overall_score)}`}>
              {scoreData.overall_score}
            </div>
            <div className="text-gray-500 text-sm font-medium mt-1">out of 100</div>
          </div>
        </div>

        {/* Score Breakdown */}
        <div className="grid md:grid-cols-4 gap-4 mt-8">
          <ScoreMetric
            label="Formatting"
            score={scoreData.formatting_score}
            gradient={getScoreGradient(scoreData.formatting_score)}
          />
          <ScoreMetric
            label="Keywords"
            score={scoreData.keyword_score}
            gradient={getScoreGradient(scoreData.keyword_score)}
          />
          <ScoreMetric
            label="Structure"
            score={scoreData.structure_score}
            gradient={getScoreGradient(scoreData.structure_score)}
          />
          <ScoreMetric
            label="Readability"
            score={scoreData.readability_score}
            gradient={getScoreGradient(scoreData.readability_score)}
          />
        </div>
      </div>

      {/* Recommendations removed - now shown in QuickRecommendations (Tier 1) component */}
    </div>
  )
}

interface ScoreMetricProps {
  label: string
  score: number
  gradient: string
}

function ScoreMetric({ label, score, gradient }: ScoreMetricProps) {
  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200">
      <div className="text-sm text-gray-600 mb-2">{label}</div>
      <div className="flex items-center justify-between">
        <div className={`text-2xl font-bold bg-gradient-to-r ${gradient} bg-clip-text text-transparent`}>
          {score}
        </div>
      </div>
      <div className="mt-2 bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${gradient} transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  )
}

