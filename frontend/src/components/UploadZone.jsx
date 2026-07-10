import { useState, useRef, useCallback } from 'react'

const API_BASE = ''

export default function UploadZone({ onUploadComplete }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleFile = useCallback(async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('force_ocr', 'true')

      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }

      const job = await res.json()
      onUploadComplete(job)
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }, [onUploadComplete])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }, [handleFile])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragging(false)
  }, [])

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
          ${dragging
            ? 'border-purple-500 bg-purple-500/10'
            : 'border-gray-700 hover:border-gray-600 bg-gray-900/30 hover:bg-gray-900/50'
          }
          ${uploading ? 'pointer-events-none opacity-50' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {uploading ? (
          <div>
            <div className="animate-spin w-10 h-10 border-3 border-purple-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">Uploading & processing PDF...</p>
          </div>
        ) : (
          <div>
            <div className="text-5xl mb-4">📄</div>
            <p className="text-lg font-medium text-gray-300 mb-1">
              Drop your PDF here
            </p>
            <p className="text-sm text-gray-500">
              or click to browse — any PDF, any language
            </p>
            <div className="flex items-center justify-center gap-4 mt-4 text-xs text-gray-600">
              <span>🔍 OCR for scanned docs</span>
              <span>✂️ Auto-chunking</span>
              <span>🧠 Vector embeddings</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 bg-red-900/20 border border-red-800 rounded-lg p-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}
    </div>
  )
}
