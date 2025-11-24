'use client'

import { Zap, ArrowRight, CheckCircle2, MessageSquare } from 'lucide-react'

interface QuickRecommendationsProps {
  recommendations: string[]
  issueCount: number
}

export function QuickRecommendations({ recommendations, issueCount }: QuickRecommendationsProps) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl shadow-sm border-2 border-green-200 p-8">
        <div className="flex items-center justify-center gap-3 mb-4">
          <CheckCircle2 className="h-8 w-8 text-green-600" />
          <h3 className="text-2xl font-bold text-green-900">Perfect ATS Formatting! 🎉</h3>
        </div>
        <p className="text-center text-green-700">
          Your resume follows all ATS best practices. No formatting changes needed!
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-md border border-primary-200 overflow-hidden">
      {/* Compact Header with Badge */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-white" />
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white">Quick Fixes</h3>
              <span className="bg-white/30 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
                TIER 1
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1 text-white">
            <span className="text-xl font-bold">{issueCount}</span>
            <span className="text-primary-100 text-xs">
              issue{issueCount !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Compact Recommendations List */}
      <div className="p-5">
        <div className="space-y-2">
          {recommendations.map((recommendation, idx) => (
            <div
              key={idx}
              className="group flex items-start gap-3 p-3 bg-gray-50 hover:bg-primary-50 rounded-lg border border-gray-200 hover:border-primary-300 transition-all duration-200"
            >
              <div className="flex-shrink-0 mt-0.5">
                <div className="bg-primary-100 text-primary-700 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold">
                  {idx + 1}
                </div>
              </div>
              <div className="flex-1">
                <p className="text-gray-800 text-sm leading-relaxed">
                  {recommendation}
                </p>
              </div>
              <ArrowRight className="flex-shrink-0 h-4 w-4 text-gray-400 group-hover:text-primary-600 transition-colors mt-0.5" />
            </div>
          ))}
        </div>

        {/* Compact Tier Info */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-3 border border-blue-200">
            <div className="flex items-start gap-2">
              <MessageSquare className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-xs text-blue-700 leading-relaxed">
                  <strong>Need more details?</strong> Scroll down to <strong>AI Diagnostic (Tier 2)</strong> 
                  for detailed explanations with exact locations and step-by-step instructions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Compact Footer */}
      <div className="bg-gray-50 px-5 py-2 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span className="flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-primary-600" />
            Rule-based detection
          </span>
          <span className="text-gray-500">
            ⚡ Instant • Free
          </span>
        </div>
      </div>
    </div>
  )
}

