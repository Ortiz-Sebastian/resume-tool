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
  issue_id?: string  // For fix mode navigation
  blocks?: Array<{
    page: number
    bbox: number[]
    text_preview: string
  }>
  detected_reason?: string
  expected_section?: string
}

interface PDFHighlightViewerProps {
  pdfUrl: string
  highlights: Highlight[]
  resumeId: number
  scrollToIssueId?: string | null  // Issue ID to scroll to
  onScrollComplete?: () => void  // Callback when scroll completes
}

const SEVERITY_COLORS = {
  critical: {
    bg: 'rgba(239, 68, 68, 0.3)',  // Increased opacity for visibility
    border: '#EF4444',
    label: 'Critical',
    icon: '🔴',
    textColor: 'text-red-700'
  },
  high: {
    bg: 'rgba(249, 115, 22, 0.3)',  // Increased opacity for visibility
    border: '#F97316',
    label: 'High',
    icon: '🟠',
    textColor: 'text-orange-700'
  },
  medium: {
    bg: 'rgba(234, 179, 8, 0.3)',  // Increased opacity for visibility
    border: '#EAB308',
    label: 'Medium',
    icon: '🟡',
    textColor: 'text-yellow-700'
  },
  low: {
    bg: 'rgba(59, 130, 246, 0.3)',  // Increased opacity for visibility
    border: '#3B82F6',
    label: 'Low',
    icon: '🔵',
    textColor: 'text-blue-700'
  }
}

export function PDFHighlightViewer({ pdfUrl, highlights, resumeId, scrollToIssueId, onScrollComplete }: PDFHighlightViewerProps) {
  const [hoveredHighlight, setHoveredHighlight] = useState<number | null>(null)
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(1)
  const [pageWidth, setPageWidth] = useState<number>(0)
  const [pageHeight, setPageHeight] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [lockedHighlight, setLockedHighlight] = useState<number | null>(null)  // For fix mode lock
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const pageContainerRef = useRef<HTMLDivElement>(null)  // Ref for the page container (for highlight positioning)
  const widthContainerRef = useRef<HTMLDivElement>(null)  // Ref for width calculation

  // Debug: Log highlights data
  useEffect(() => {
    console.log('PDFHighlightViewer - Highlights:', highlights)
    console.log('PDFHighlightViewer - Highlights count:', highlights.length)
    console.log('PDFHighlightViewer - Highlights with bbox:', highlights.filter(h => h.bbox && Array.isArray(h.bbox) && h.bbox.length === 4).length)
    if (highlights.length > 0) {
      console.log('PDFHighlightViewer - First highlight:', highlights[0])
    }
  }, [highlights])

  useEffect(() => {
    const updateWidth = () => {
      if (scrollContainerRef.current) {
        const width = scrollContainerRef.current.offsetWidth * 0.95
        setPageWidth(width)
        console.log('PDFHighlightViewer - Container width:', scrollContainerRef.current.offsetWidth, 'Page width:', width)
      }
    }
    
    updateWidth()
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])

  // Auto-scroll to specific issue (fix mode)
  useEffect(() => {
    if (!scrollToIssueId || !highlights.length || loading) {
      console.log('PDFHighlightViewer - Scroll skipped:', { scrollToIssueId, highlightsLength: highlights.length, loading })
      return
    }

    console.log('PDFHighlightViewer - Looking for issue_id:', scrollToIssueId)
    console.log('PDFHighlightViewer - Available highlights:', highlights.map(h => ({ issue_id: h.issue_id, issue_type: h.issue_type, code: h.code })))

    // Find highlight with matching issue_id, issue_type, or code
    const targetIndex = highlights.findIndex(h => {
      const matchId = h.issue_id === scrollToIssueId
      const matchType = h.issue_type === scrollToIssueId
      const matchCode = h.code === scrollToIssueId
      return matchId || matchType || matchCode
    })
    
    if (targetIndex === -1) {
      console.log('PDFHighlightViewer - No matching highlight found for:', scrollToIssueId)
      if (onScrollComplete) onScrollComplete() // Still call completion to reset state
      return
    }

    const targetHighlight = highlights[targetIndex]
    console.log('PDFHighlightViewer - Found target highlight:', targetHighlight)
    
    // Switch to the correct page first
    const targetPage = targetHighlight.page || 1
    console.log('PDFHighlightViewer - Switching to page:', targetPage, 'Current page:', pageNumber)
    
    // Set page number - this will trigger a re-render
    if (pageNumber !== targetPage) {
      setPageNumber(targetPage)
      // Wait for page to change before locking highlight
      setTimeout(() => {
        setLockedHighlight(targetIndex)
        console.log('PDFHighlightViewer - Locked highlight index:', targetIndex, 'issue_id:', targetHighlight.issue_id)
      }, 100)
    } else {
      // Page is already correct, lock immediately
      setLockedHighlight(targetIndex)
      console.log('PDFHighlightViewer - Locked highlight index:', targetIndex, 'issue_id:', targetHighlight.issue_id)
    }
    
    // Wait for page to render, then scroll and ensure highlight is visible
    // Use a longer delay to ensure the page has fully rendered and highlight is locked
    const scrollDelay = pageNumber !== targetPage ? 800 : 500  // Longer delay if page changed
    setTimeout(() => {
      if (scrollContainerRef.current && targetHighlight.bbox && Array.isArray(targetHighlight.bbox) && targetHighlight.bbox.length === 4) {
        const actualPageWidth = pageWidth > 0 ? pageWidth : 600
        const scale = actualPageWidth / 595  // A4 page width in points
        const [x0, y0, x1, y1] = targetHighlight.bbox
        
        // Calculate scroll position - account for the page position in the container
        const scaledY = y0 * scale
        const scrollY = Math.max(0, scaledY - 150)  // Offset to show above highlight with more margin
        
        console.log('PDFHighlightViewer - Scrolling to:', { 
          scrollY, 
          bbox: targetHighlight.bbox, 
          scale,
          pageWidth: actualPageWidth,
          scaledY,
          containerHeight: scrollContainerRef.current.scrollHeight
        })
        
        // Scroll the container
        scrollContainerRef.current.scrollTo({
          top: scrollY,
          behavior: 'smooth'
        })
        
        // Also ensure the highlight is visible by scrolling again after a short delay
        setTimeout(() => {
          scrollContainerRef.current?.scrollTo({
            top: scrollY,
            behavior: 'smooth'
          })
        }, 200)
        
        // Call completion callback
        if (onScrollComplete) {
          setTimeout(() => onScrollComplete(), 1200)  // Wait longer for scroll animation and page render
        }
      } else {
        console.log('PDFHighlightViewer - Invalid bbox for scrolling:', targetHighlight.bbox)
        if (onScrollComplete) onScrollComplete()
      }
    }, scrollDelay)  // Dynamic delay based on whether page changed
  }, [scrollToIssueId, highlights, loading, pageWidth, onScrollComplete])

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
    // Calculate the actual scale based on the rendered page width
    const viewport = page.getViewport({ scale: 1 })
    const actualWidth = pageWidth > 0 ? pageWidth : 600
    const scale = actualWidth / viewport.width
    const scaledHeight = viewport.height * scale
    setPageHeight(scaledHeight)
    console.log('PDFHighlightViewer - Page loaded:', { viewportWidth: viewport.width, viewportHeight: viewport.height, actualWidth, scale, scaledHeight })
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
        ref={scrollContainerRef}
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
                <div className="relative" style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'flex-start' }}>
                  <div 
                    className="relative" 
                    ref={pageContainerRef}
                    style={{ 
                      position: 'relative', 
                      display: 'inline-block',
                      // Ensure this container matches the Page dimensions exactly
                      width: pageWidth > 0 ? `${pageWidth}px` : '600px',
                      minHeight: pageHeight > 0 ? `${pageHeight}px` : 'auto'
                    }}
                  >
                    <Page
                      pageNumber={pageNumber}
                      width={pageWidth > 0 ? pageWidth : 600}
                      onLoadSuccess={onPageLoadSuccess}
                      renderTextLayer={true}
                      renderAnnotationLayer={false}
                      className="shadow-lg"
                    />

                    {/* Highlight Overlays */}
                    {(() => {
                    // Always log the rendering attempt, even if conditions aren't met
                    console.log('PDFHighlightViewer - Render check:', {
                      loading,
                      pageWidth,
                      highlightsLength: highlights.length,
                      pageNumber,
                      shouldRender: !loading && pageWidth > 0 && highlights.length > 0
                    })
                    
                    if (loading || pageWidth === 0 || highlights.length === 0) {
                      return null
                    }
                    
                    console.log('PDFHighlightViewer - Attempting to render highlights. pageWidth:', pageWidth, 'pageNumber:', pageNumber, 'highlights count:', highlights.length)
                    
                    const validHighlights = highlights
                      .map((highlight, idx) => ({ highlight, idx }))
                      .filter(({ highlight }) => {
                        // Only show highlights with valid bbox and matching page
                        const hasValidBbox = highlight.bbox && 
                                             Array.isArray(highlight.bbox) && 
                                             highlight.bbox.length === 4 &&
                                             highlight.bbox.every((v: any) => typeof v === 'number' && !isNaN(v))
                        const matchesPage = highlight.page === pageNumber
                        
                        if (!hasValidBbox) {
                          console.log('PDFHighlightViewer - Invalid bbox for highlight:', highlight.code || highlight.issue_type, highlight.bbox)
                        }
                        if (!matchesPage && hasValidBbox) {
                          console.log('PDFHighlightViewer - Page mismatch:', highlight.page, 'vs', pageNumber, 'for', highlight.code || highlight.issue_type)
                        }
                        
                        return hasValidBbox && matchesPage
                      })
                      .sort((a, b) => {
                        // Calculate area of each highlight
                        const bboxA = a.highlight.bbox
                        const bboxB = b.highlight.bbox
                        const areaA = (bboxA[2] - bboxA[0]) * (bboxA[3] - bboxA[1])
                        const areaB = (bboxB[2] - bboxB[0]) * (bboxB[3] - bboxB[1])
                        // Larger areas first (rendered first = lower z-index)
                        return areaB - areaA
                      })
                    
                    console.log('PDFHighlightViewer - Valid highlights for page', pageNumber, ':', validHighlights.length, 'out of', highlights.length)
                    console.log('PDFHighlightViewer - Valid highlights details:', validHighlights.map(({ highlight, idx }) => ({
                      idx,
                      issue_type: highlight.issue_type,
                      issue_id: highlight.issue_id,
                      page: highlight.page,
                      bbox: highlight.bbox,
                      severity: highlight.severity
                    })))
                    
                    if (validHighlights.length === 0) {
                      console.log('PDFHighlightViewer - No valid highlights to render for page', pageNumber)
                      return null
                    }
                    
                    // Calculate scale based on actual rendered page dimensions
                    // Get the actual viewport from the page (if available) or use standard A4 dimensions
                    // Standard A4: 595pt x 842pt
                    const actualPageWidth = pageWidth > 0 ? pageWidth : 600
                    const scale = actualPageWidth / 595  // Scale factor for PDF coordinates
                    // Use pageHeight from state if available, otherwise calculate from A4 ratio
                    const actualPageHeight = pageHeight > 0 ? pageHeight : (actualPageWidth * (842 / 595))
                    
                    console.log('PDFHighlightViewer - Rendering highlights:', {
                      pageWidth: actualPageWidth,
                      pageHeight: actualPageHeight,
                      scale,
                      validHighlightsCount: validHighlights.length
                    })
                    
                    console.log('PDFHighlightViewer - Creating highlight overlay div:', {
                      actualPageWidth,
                      actualPageHeight,
                      scale,
                      validHighlightsCount: validHighlights.length,
                      pageNumber,
                      lockedHighlight
                    })
                    
                    // Calculate the actual rendered page height from react-pdf
                    // The Page component scales proportionally, so height = width * (842/595) for A4
                    const calculatedPageHeight = actualPageWidth * (842 / 595)
                    const finalPageHeight = pageHeight > 0 ? pageHeight : calculatedPageHeight
                    
                    console.log('PDFHighlightViewer - Overlay dimensions:', {
                      width: actualPageWidth,
                      height: finalPageHeight,
                      calculatedHeight: calculatedPageHeight,
                      pageHeightFromState: pageHeight
                    })
                    
                    return (
                      <div 
                        className="absolute pointer-events-none" 
                        style={{ 
                          zIndex: 1000,  // High z-index to ensure it's above PDF
                          top: 0,
                          left: 0,
                          width: `${actualPageWidth}px`,
                          height: `${finalPageHeight}px`,
                          // Ensure it's positioned exactly over the Page component
                          position: 'absolute',
                          // Temporary debug: Uncomment to see overlay bounds
                          // backgroundColor: 'rgba(255, 0, 0, 0.05)',
                          // border: '2px solid red'
                        }}
                        data-testid="highlight-overlay"
                      >
                        {validHighlights.map(({ highlight, idx }, sortedIdx) => {
                        const colors = SEVERITY_COLORS[highlight.severity]
                        const [x0, y0, x1, y1] = highlight.bbox
                        
                        // Scale the bbox coordinates to match the rendered page size
                        const scaledX0 = x0 * scale
                        const scaledY0 = y0 * scale
                        const scaledX1 = x1 * scale
                        const scaledY1 = y1 * scale
                        const scaledWidth = scaledX1 - scaledX0
                        const scaledHeight = scaledY1 - scaledY0
                        
                        // Calculate area to determine if this is a large highlight
                        const area = scaledWidth * scaledHeight
                        const isLargeHighlight = area > (actualPageWidth * actualPageHeight * 0.3) // 30% of page
                        
                        // Check if this highlight is locked - compare by issue_id/code/issue_type, not index
                        const lockedHighlightObj = lockedHighlight !== null ? highlights[lockedHighlight] : null
                        const isLocked = lockedHighlight !== null && (
                          lockedHighlight === idx || 
                          (lockedHighlightObj?.issue_id && lockedHighlightObj.issue_id === highlight.issue_id) ||
                          (lockedHighlightObj?.issue_type && lockedHighlightObj.issue_type === highlight.issue_type) ||
                          (lockedHighlightObj?.code && lockedHighlightObj.code === highlight.code) ||
                          // Fallback: match by issue_type if both are defined
                          (lockedHighlightObj?.issue_type && highlight.issue_type && lockedHighlightObj.issue_type === highlight.issue_type)
                        )
                        
                        console.log('PDFHighlightViewer - Rendering highlight:', {
                          idx,
                          issue_type: highlight.issue_type,
                          issue_id: highlight.issue_id,
                          originalBbox: [x0, y0, x1, y1],
                          scaledBbox: [scaledX0, scaledY0, scaledX1, scaledY1],
                          scaledSize: [scaledWidth, scaledHeight],
                          area,
                          isLargeHighlight,
                          scale,
                          isLocked,
                          colors: colors.border
                        })
                        
                        if (isLocked) {
                          console.log('PDFHighlightViewer - Highlight is LOCKED:', {
                            idx,
                            issue_type: highlight.issue_type,
                            issue_id: highlight.issue_id,
                            lockedIndex: lockedHighlight,
                            lockedObj: lockedHighlightObj
                          })
                        }
                        
                        // Log every highlight being rendered
                        console.log(`PDFHighlightViewer - Rendering highlight ${idx}:`, {
                          issue_type: highlight.issue_type,
                          position: { left: scaledX0, top: scaledY0, width: scaledWidth, height: scaledHeight },
                          isLocked,
                          isLargeHighlight,
                          colors: colors.border
                        })
                        
                        return (
                          <div
                            key={`highlight-${idx}-${highlight.issue_id || highlight.issue_type || 'unknown'}`}
                            className={`absolute transition-all duration-200 ${isLargeHighlight ? 'pointer-events-none' : 'pointer-events-auto cursor-help'}`}
                            style={{
                              left: `${scaledX0}px`,
                              top: `${scaledY0}px`,
                              width: `${scaledWidth}px`,
                              height: `${scaledHeight}px`,
                              backgroundColor: isLargeHighlight ? 'transparent' : colors.bg,
                              border: `${isLargeHighlight ? '3px dashed' : isLocked ? '4px solid' : '2px solid'} ${colors.border}`,
                              borderRadius: '4px',
                              boxShadow: isLocked 
                                ? `0 0 0 8px ${colors.bg}, 0 0 30px ${colors.border}, inset 0 0 20px ${colors.bg}` 
                                : (hoveredHighlight === idx ? `0 0 0 4px ${colors.bg}` : 'none'),
                              // Ensure highlights are above the PDF (react-pdf renders at z-index ~1-10)
                              zIndex: isLocked ? 99999 : (hoveredHighlight === idx ? 9999 : (1000 + sortedIdx)),
                              animation: isLocked ? 'pulse 1.5s infinite' : 'none',
                              // Make sure it's visible - locked highlights should be more visible
                              opacity: isLocked ? 1 : (isLargeHighlight ? 0.4 : 0.9),  // Increased opacity for better visibility
                              pointerEvents: isLargeHighlight ? 'none' : 'auto',
                              // Add a glow effect for locked highlights
                              filter: isLocked ? `drop-shadow(0 0 12px ${colors.border}) drop-shadow(0 0 6px ${colors.border})` : 'none',
                              // Ensure it's always visible
                              display: 'block',
                              visibility: 'visible',
                              // Force rendering
                              willChange: 'transform',
                              transform: 'translateZ(0)'  // Force GPU acceleration
                            }}
                            onMouseEnter={() => {
                              if (!isLargeHighlight && !isLocked) {
                                console.log('Mouse entered highlight:', idx)
                                setHoveredHighlight(idx)
                              }
                            }}
                            onMouseLeave={() => {
                              if (!isLargeHighlight && !isLocked) {
                                console.log('Mouse left highlight:', idx)
                                setHoveredHighlight(null)
                              }
                            }}
                            onClick={() => {
                              if (!isLargeHighlight) {
                                // Toggle lock on click
                                setLockedHighlight(isLocked ? null : idx)
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
                    )
                  })()}
                  </div>
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
          <span className="text-xs text-gray-500">
            {lockedHighlight !== null ? '🔒 Highlight locked - Click to unlock' : 'Hover over highlights for details • Click to lock view'}
          </span>
        </div>
      </div>
      
      {/* Add pulse animation for locked highlights */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
      `}</style>
    </div>
  )
}

