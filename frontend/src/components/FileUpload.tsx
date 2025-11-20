'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Loader2, CheckCircle, XCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FileUploadProps {
  onUploadSuccess: (resumeId: number) => void
}

export function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState(false)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    setUploading(true)
    setError('')
    setSuccess(false)
    setUploadProgress('Uploading resume...')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post(`${API_URL}/api/parse`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setUploadProgress('Parsing resume...')
      
      // Wait a bit for parsing to complete
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      setSuccess(true)
      setUploadProgress('Resume uploaded successfully!')
      
      // Call success callback
      onUploadSuccess(response.data.id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload resume')
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }, [onUploadSuccess])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    disabled: uploading,
  })

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200 ease-in-out
          ${isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 bg-white hover:border-primary-400 hover:bg-gray-50'
          }
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
          ${success ? 'border-green-500 bg-green-50' : ''}
          ${error ? 'border-red-500 bg-red-50' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-4">
          {uploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="h-16 w-16 text-primary-600 animate-spin" />
              <p className="mt-4 text-lg font-medium text-gray-900">{uploadProgress}</p>
            </div>
          ) : success ? (
            <div className="flex flex-col items-center">
              <CheckCircle className="h-16 w-16 text-green-600" />
              <p className="mt-4 text-lg font-medium text-green-900">{uploadProgress}</p>
              <p className="text-sm text-gray-600 mt-2">
                Click the "Analyze" button to view your results
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center">
              <XCircle className="h-16 w-16 text-red-600" />
              <p className="mt-4 text-lg font-medium text-red-900">Upload Failed</p>
              <p className="text-sm text-red-700 mt-2">{error}</p>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setError('')
                }}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Try Again
              </button>
            </div>
          ) : (
            <>
              <div className="flex justify-center">
                {isDragActive ? (
                  <FileText className="h-16 w-16 text-primary-600" />
                ) : (
                  <Upload className="h-16 w-16 text-gray-400" />
                )}
              </div>
              
              <div>
                <p className="text-xl font-semibold text-gray-900">
                  {isDragActive ? 'Drop your resume here' : 'Upload your resume'}
                </p>
                <p className="text-sm text-gray-600 mt-2">
                  Drag and drop or click to browse
                </p>
              </div>

              <div className="flex items-center justify-center space-x-2 text-sm text-gray-500">
                <span>Supported formats:</span>
                <span className="font-medium text-gray-700">PDF, DOCX</span>
              </div>

              <button
                type="button"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
              >
                Select File
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tips */}
      <div className="mt-6 bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h3 className="font-semibold text-gray-900 mb-3">Tips for best results:</h3>
        <ul className="space-y-2 text-sm text-gray-600">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Use a clean, well-formatted resume without images or complex layouts</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Include clear section headers (Experience, Education, Skills)</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>List your skills explicitly in a dedicated section</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Keep file size under 10MB</span>
          </li>
        </ul>
      </div>
    </div>
  )
}

