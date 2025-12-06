'use client'

import { useState } from 'react'
import { Send, Loader, Lightbulb, MapPin, CheckCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ATSDiagnosticProps {
  resumeId: number
}

interface DiagnosticResult {
  explanation: string
  location?: string
  recommendations: string[]
}

export function ATSDiagnostic({ resumeId }: ATSDiagnosticProps) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DiagnosticResult | null>(null)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!prompt.trim()) {
      return
    }

    try {
      setLoading(true)
      setError('')
      setResult(null)

      const response = await axios.post(`${API_URL}/api/llm-diagnostic`, {
        resume_id: resumeId,
        user_prompt: prompt.trim()
      })

      setResult(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get diagnostic. Make sure OPENAI_API_KEY is configured.')
    } finally {
      setLoading(false)
    }
  }

  const examplePrompts = [
    "I'm missing 5 skills that are on my resume",
    "My email address isn't showing up",
    "Only 2 of my 4 jobs were extracted",
    "My education section is completely missing"
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-300 rounded-xl p-6">
        <div className="flex items-start space-x-3">
          <Lightbulb className="h-6 w-6 text-purple-600 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-xl font-bold text-gray-900">
                🤖 AI Diagnostic
              </h3>
              <span className="bg-purple-100 text-purple-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-purple-300">
                TIER 2
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-2">
              <strong>Detailed, contextual analysis</strong> • Get specific explanations with exact locations and step-by-step fixes
            </p>
            <p className="text-sm text-gray-600 mb-3">
              Compare your original resume with the ATS view above. Notice something missing or wrong?
              Tell me what you see, and I'll explain exactly why it happened and how to fix it.
            </p>
            
            {/* Example prompts */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-600">Try these examples:</p>
              <div className="flex flex-wrap gap-2">
                {examplePrompts.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => setPrompt(example)}
                    className="text-xs px-3 py-1.5 bg-white border border-purple-200 rounded-lg hover:bg-purple-50 transition-colors"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g., 'I'm missing 5 skills' or 'My email isn't showing up'"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
          rows={3}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Loader className="h-5 w-5 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <Send className="h-5 w-5" />
              <span>Diagnose</span>
            </>
          )}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {/* Explanation */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-start space-x-3 mb-3">
              <Lightbulb className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 mb-2">Why this happened:</h4>
                <div className="text-sm text-gray-700 whitespace-pre-line">
                  {result.explanation}
                </div>
              </div>
            </div>
          </div>

          {/* Location */}
          {result.location && (
            <div className="p-6 bg-blue-50 border-b border-gray-200">
              <div className="flex items-start space-x-3">
                <MapPin className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 mb-2">Where to look:</h4>
                  <div className="text-sm text-gray-700 whitespace-pre-line">
                    {result.location}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recommendations */}
          {result.recommendations && result.recommendations.length > 0 && (
            <div className="p-6 bg-green-50">
              <div className="flex items-start space-x-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 mb-3">How to fix:</h4>
                  <ol className="space-y-2">
                    {result.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="flex-shrink-0 w-6 h-6 bg-green-600 text-white rounded-full flex items-center justify-center text-xs font-semibold">
                          {idx + 1}
                        </span>
                        <span className="text-sm text-gray-700 flex-1 pt-0.5">{rec}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

