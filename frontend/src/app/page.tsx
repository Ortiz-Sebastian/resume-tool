'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/FileUpload'
import { ResumeViewer } from '@/components/ResumeViewer'
import { ScoreCard } from '@/components/ScoreCard'
import { RoleMatches } from '@/components/RoleMatches'
import { PDFHighlightViewer } from '@/components/PDFHighlightViewer'
import { IssueSummaryPanel } from '@/components/IssueSummaryPanel'
import { SectionSummary } from '@/components/SectionSummary'
// TODO: Re-enable for later development
// import { SkillSuggestions } from '@/components/SkillSuggestions'
import { FileText, Target, Lightbulb, Upload } from 'lucide-react'

export default function Home() {
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [scoreData, setScoreData] = useState<any>(null)
  const [roleMatches, setRoleMatches] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'upload' | 'analyze'>('upload')
  const [sectionAnalysis, setSectionAnalysis] = useState<any>(null)

  const handleUploadSuccess = (id: number) => {
    setResumeId(id)
    setActiveTab('analyze')
  }

  const handleScoreReceived = (data: any) => {
    setScoreData(data)
  }

  const handleRoleMatchesReceived = (matches: any[]) => {
    setRoleMatches(matches)
  }

  const handleSectionAnalyzed = (analysis: any) => {
    // Merge section analysis highlights with existing scoreData highlights
    setSectionAnalysis(analysis)
    if (analysis.highlights && analysis.highlights.length > 0) {
      setScoreData((prev: any) => ({
        ...prev,
        highlights: [...(prev?.highlights || []), ...analysis.highlights]
      }))
    }
  }

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8 text-primary-600" />
              <h1 className="text-3xl font-bold text-gray-900">Resume Tool</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setActiveTab('upload')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'upload'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <Upload className="h-4 w-4" />
                <span>Upload</span>
              </button>
              {resumeId && (
                <button
                  onClick={() => setActiveTab('analyze')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    activeTab === 'analyze'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Target className="h-4 w-4" />
                  <span>Analyze</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'upload' && (
          <div className="space-y-8">
            {/* Hero Section */}
            <div className="text-center space-y-4">
              <h2 className="text-4xl font-bold text-gray-900">
                Analyze Your Resume
              </h2>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                Get instant ATS compatibility scores and role matches for your resume
              </p>
            </div>

            {/* Features */}
            <div className="grid md:grid-cols-2 gap-6 mb-12">
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <FileText className="h-6 w-6 text-primary-600" />
                  </div>
                  <h3 className="font-semibold text-lg">Visual ATS Analysis</h3>
                </div>
                <p className="text-gray-600">
                  See formatting issues highlighted directly on your PDF with actionable fixes
                </p>
              </div>

              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <Target className="h-6 w-6 text-primary-600" />
                  </div>
                  <h3 className="font-semibold text-lg">Role Matching</h3>
                </div>
                <p className="text-gray-600">
                  Discover which roles best match your experience and skills
                </p>
              </div>

              {/* TODO: Re-enable for later development */}
              {/* <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="p-2 bg-primary-100 rounded-lg">
                    <Lightbulb className="h-6 w-6 text-primary-600" />
                  </div>
                  <h3 className="font-semibold text-lg">Skill Suggestions</h3>
                </div>
                <p className="text-gray-600">
                  Get personalized suggestions to improve your resume for target roles
                </p>
              </div> */}
            </div>

            {/* Upload Component */}
            <FileUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        )}

        {activeTab === 'analyze' && resumeId && (
          <div className="space-y-8">
            {/* Section Summary - NEW! */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                📊 ATS Extraction Summary
              </h2>
              <p className="text-gray-600 mb-6">
                Compare what's in your resume vs. what the ATS extracted. Click sections to see why extraction failed.
              </p>
              <SectionSummary
                resumeId={resumeId}
                onSectionAnalyzed={handleSectionAnalyzed}
              />
            </div>

            {/* Score Overview */}
            <ScoreCard
              resumeId={resumeId}
              onScoreReceived={handleScoreReceived}
            />

            {/* ATS Highlighting Section */}
            {scoreData?.highlights && scoreData.highlights.length > 0 && (
              <div className="grid lg:grid-cols-3 gap-6">
                {/* PDF with Highlights (2 columns) */}
                <div className="lg:col-span-2">
                  <PDFHighlightViewer
                    pdfUrl={`http://localhost:8000/api/resume/${resumeId}/file`}
                    highlights={scoreData.highlights}
                    resumeId={resumeId}
                  />
                </div>

                {/* Issue Summary Panel (1 column) */}
                <div className="lg:col-span-1">
                  <IssueSummaryPanel
                    summary={scoreData.issue_summary}
                    suggestions={scoreData.suggestions || []}
                  />
                </div>
              </div>
            )}

            {/* Side by Side Viewer */}
            <ResumeViewer
              resumeId={resumeId}
              scoreData={scoreData}
            />

            {/* Role Matches */}
            <RoleMatches
              resumeId={resumeId}
              onMatchesReceived={handleRoleMatchesReceived}
            />

            {/* TODO: Skill Suggestions - Re-enable for later development */}
            {/* {roleMatches.length > 0 && (
              <SkillSuggestions
                resumeId={resumeId}
                topRole={roleMatches[0]}
              />
            )} */}
          </div>
        )}
      </div>
    </main>
  )
}

