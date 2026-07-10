import { useState, useEffect } from 'react'

const API_BASE = ''

const STATUS_COLORS = {
  completed: 'text-green-400 bg-green-500/10 border-green-800',
  processing: 'text-yellow-400 bg-yellow-500/10 border-yellow-800',
  error: 'text-red-400 bg-red-500/10 border-red-800',
}

export default function JobStatus({ jobId, filename, isActive, onSelect }) {
  const [status, setStatus] = useState('processing')

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/status/${jobId}`)
        if (res.ok) {
          const data = await res.json()
          setStatus(data.status)
          if (data.status === 'processing') {
            setTimeout(poll, 2000)
          }
        }
      } catch {}
    }
    poll()
  }, [jobId])

  const statusColor = STATUS_COLORS[status] || STATUS_COLORS.processing
  const icons = { completed: '✅', processing: '⏳', error: '❌' }

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 sm:p-4 rounded-xl border transition-all min-h-[52px] ${
        isActive
          ? 'border-purple-600 bg-purple-900/20'
          : 'border-gray-800 bg-gray-900/50 hover:border-gray-700'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <span className="text-base sm:text-lg shrink-0">{icons[status] || '📄'}</span>
          <div className="min-w-0">
            <p className="font-medium text-xs sm:text-sm truncate">{filename}</p>
            <p className="text-[10px] sm:text-xs text-gray-500">Job: {jobId}</p>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium border shrink-0 ${statusColor}`}>
          {status}
        </span>
      </div>
    </button>
  )
}
