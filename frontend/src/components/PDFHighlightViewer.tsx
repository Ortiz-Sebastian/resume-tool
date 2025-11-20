'use client'

import { useState, useRef, useEffect } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { AlertTriangle, Info, XCircle, AlertCircle } from 'lucide-react'
import 'react-pdf/dist/esm/Page/AnnotationLayer.css'
import 'react-pdf/dist/esm/Page/TextLayer.css'

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`

interface Highlight {
  page: number
  bbox: number[] // [x0, y0, x1, y1]
  severity: 'critical' | 'high' | 'medium' | 'low'
  issue_type: string
  message: string
  tooltip: string
}

interface PDFHighlightViewerProps {
  pdfUrl: string
  highlights: Highlight[]
  resumeId: number
}

const SEVERITY_COLORS = {
  critical: {
    bg: 'rgba(239, 68, 68, 0.2)',
    border: '#EF4444',
    label: 'Critical',
    icon: '🔴',
    textColor: 'text-red-700'
  },
  high: {
    bg: 'rgba(249, 115, 22, 0.2)',
    border: '#F97316',
    label: 'High',
    icon: '🟠',
    textColor: 'text-orange-700'
  },
  medium: {
    bg: 'rgba(234, 179, 8, 0.2)',
    border: '#EAB308',
    label: 'Medium',
    icon: '🟡',
    textColor: 'text-yellow-700'
  },
  low: {
    bg: 'rgba(59, 130, 246, 0.2)',
    border: '#3B82F6',
    label: 'Low',
    icon: '🔵',
    textColor: 'text-blue-700'
  }
}

export function PDFHighlightViewer({ pdfUrl, highlights, resumeId }: PDFHighlightViewerProps) {
  const [hoveredHighlight, setHoveredHighlight] = useState<number | null>(null)
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(1)
  const [pageWidth, setPageWidth] = useState<number>(0)
  const [pageHeight, setPageHeight] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const containerRef = useRef<HTMLDivElement>(null)

  // Debug: Log highlights data
  useEffect(() => {
    console.log('PDFHighlightViewer - Highlights:', highlights)
  }, [highlights])

  useEffect(() => {
    if (containerRef.current) {
      const width = containerRef.current.offsetWidth * 0.9
      setPageWidth(width)
    }
  }, [])

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
  }

  const onDocumentLoadError = (error: Error) => {
    console.error('Error loading PDF:', error)
    setError('Failed to load PDF. Please try again.')
    setLoading(false)
  }

  const onPageLoadSuccess = (page: any) => {
    const viewport = page.getViewport({ scale: 1 })
    setPageHeight(viewport.height)
  }

  return (
    <div className="relative bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">
          Original Resume with ATS Issues Highlighted
        </h3>
        <div className="flex items-center gap-4 text-sm text-white">
          <span>{highlights.length} issue{highlights.length !== 1 ? 's' : ''} detected</span>
          {hoveredHighlight !== null && (
            <span className="bg-white text-primary-600 px-2 py-1 rounded font-bold">
              Hovering: {hoveredHighlight + 1}
            </span>
          )}
        </div>
      </div>

      <div 
        ref={containerRef}
        className="relative bg-gray-100 overflow-auto" 
        style={{ height: '800px', position: 'relative' }}
      >
        {loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
              <XCircle className="h-12 w-12 text-red-500 mx-auto mb-3" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {!error && (
          <>
            {/* PDF Container */}
            <div className="relative mx-auto bg-white shadow-lg">
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={null}
              >
                <div className="relative">
                  <Page
                    pageNumber={pageNumber}
                    width={pageWidth || undefined}
                    onLoadSuccess={onPageLoadSuccess}
                    renderTextLayer={true}
                    renderAnnotationLayer={false}
                  />

                  {/* Highlight Overlays */}
                  {!loading && pageWidth > 0 && (
                    <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 100 }}>
                      {highlights
                        .map((highlight, idx) => ({ highlight, idx }))
                        .filter(({ highlight }) => highlight.page === pageNumber)
                        .sort((a, b) => {
                          // Calculate area of each highlight
                          const areaA = (a.highlight.bbox[2] - a.highlight.bbox[0]) * (a.highlight.bbox[3] - a.highlight.bbox[1])
                          const areaB = (b.highlight.bbox[2] - b.highlight.bbox[0]) * (b.highlight.bbox[3] - b.highlight.bbox[1])
                          // Larger areas first (rendered first = lower z-index)
                          return areaB - areaA
                        })
                        .map(({ highlight, idx }, sortedIdx) => {
                        const colors = SEVERITY_COLORS[highlight.severity]
                        const [x0, y0, x1, y1] = highlight.bbox
                        
                        // Scale coordinates to fit container
                        // PDF coordinates are in points (72 points = 1 inch)
                        // A4 page is typically 595pt x 842pt
                        const scale = pageWidth / 595
                        
                        // Calculate area to determine if this is a large highlight
                        const area = (x1 - x0) * (y1 - y0)
                        const isLargeHighlight = area > 200000 // Covers significant portion of page
                        
                        console.log('Rendering highlight:', idx, 'Area:', area, 'IsLarge:', isLargeHighlight, 'Hovered:', hoveredHighlight)
                        
                        return (
                          <div
                            key={idx}
                            className={`absolute transition-all duration-200 ${isLargeHighlight ? 'pointer-events-none' : 'pointer-events-auto cursor-help'}`}
                            style={{
                              left: `${x0 * scale}px`,
                              top: `${y0 * scale}px`,
                              width: `${(x1 - x0) * scale}px`,
                              height: `${(y1 - y0) * scale}px`,
                              backgroundColor: isLargeHighlight ? 'transparent' : colors.bg,
                              border: `${isLargeHighlight ? '3px dashed' : '2px solid'} ${colors.border}`,
                              borderRadius: '4px',
                              boxShadow: hoveredHighlight === idx ? `0 0 0 4px ${colors.bg}` : 'none',
                              // Smaller highlights get higher z-index
                              zIndex: hoveredHighlight === idx ? 9999 : (100 + sortedIdx)
                            }}
                            onMouseEnter={() => {
                              if (!isLargeHighlight) {
                                console.log('Mouse entered highlight:', idx)
                                setHoveredHighlight(idx)
                              }
                            }}
                            onMouseLeave={() => {
                              if (!isLargeHighlight) {
                                console.log('Mouse left highlight:', idx)
                                setHoveredHighlight(null)
                              }
                            }}
                          >
                            {/* Issue marker badge - For large highlights, make it clickable */}
                            {isLargeHighlight ? (
                              <div 
                                className="absolute top-2 right-2 px-3 py-1 rounded-full flex items-center gap-2 text-xs font-bold shadow-lg cursor-pointer pointer-events-auto"
                                style={{
                                  backgroundColor: colors.border,
                                  color: 'white'
                                }}
                                onMouseEnter={() => {
                                  console.log('Mouse entered large highlight badge:', idx)
                                  setHoveredHighlight(idx)
                                }}
                                onMouseLeave={() => {
                                  console.log('Mouse left large highlight badge:', idx)
                                  setHoveredHighlight(null)
                                }}
                              >
                                <span>!</span>
                                <span className="text-xs">{colors.label}</span>
                              </div>
                            ) : (
                              <div 
                                className="absolute -top-3 -right-3 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shadow-lg pointer-events-none"
                                style={{
                                  backgroundColor: colors.border,
                                  color: 'white'
                                }}
                              >
                                !
                              </div>
                            )}

                            {/* Tooltip - Render with fixed positioning */}
                            {hoveredHighlight === idx && (
                              <div 
                                className="fixed p-4 bg-gray-900 text-white rounded-lg shadow-2xl pointer-events-none"
                                style={{
                                  width: '380px',
                                  left: '50%',
                                  top: '50%',
                                  transform: 'translate(-50%, -50%)',
                                  zIndex: 99999,
                                  maxWidth: '90vw'
                                }}
                              >
                                <div className="flex items-start gap-3">
                                  <span className="text-2xl flex-shrink-0">{colors.icon}</span>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                                      <span className="font-semibold text-lg">{colors.label} Issue</span>
                                      <span className="text-xs bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
                                        {highlight.issue_type.replace(/_/g, ' ').toUpperCase()}
                                      </span>
                                    </div>
                                    <p className="text-sm text-gray-200 leading-relaxed mb-2">
                                      {highlight.tooltip}
                                    </p>
                                    <div className="text-xs text-gray-400 border-t border-gray-700 pt-2">
                                      💡 Hover away to close
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </Document>

              {/* Page Navigation */}
              {numPages > 1 && (
                <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-white rounded-lg shadow-lg px-4 py-2 flex items-center gap-4">
                  <button
                    onClick={() => setPageNumber(Math.max(1, pageNumber - 1))}
                    disabled={pageNumber <= 1}
                    className="px-3 py-1 bg-primary-600 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    ← Prev
                  </button>
                  <span className="text-sm font-medium">
                    Page {pageNumber} of {numPages}
                  </span>
                  <button
                    onClick={() => setPageNumber(Math.min(numPages, pageNumber + 1))}
                    disabled={pageNumber >= numPages}
                    className="px-3 py-1 bg-primary-600 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Legend */}
      <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <span className="text-sm font-medium text-gray-700">Severity Legend:</span>
          <div className="flex items-center gap-6">
            {Object.entries(SEVERITY_COLORS).map(([severity, config]) => (
              <div key={severity} className="flex items-center gap-2">
                <div 
                  className="w-4 h-4 rounded border-2"
                  style={{
                    backgroundColor: config.bg,
                    borderColor: config.border
                  }}
                />
                <span className="text-sm text-gray-600">{config.icon} {config.label}</span>
              </div>
            ))}
          </div>
          <span className="text-xs text-gray-500">Hover over highlights for details</span>
        </div>
      </div>
    </div>
  )
}

