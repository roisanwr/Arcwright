import { useState, useEffect, useCallback } from 'react'
import UploadZone from './components/UploadZone'
import JobStatus from './components/JobStatus'
import ChatPanel from './components/ChatPanel'
import CollectionList from './components/CollectionList'

const API_BASE = ''

export default function App() {
  const [jobs, setJobs] = useState([])
  const [activeJob, setActiveJob] = useState(null)
  const [view, setView] = useState('upload')

  const handleUploadComplete = useCallback((job) => {
    setJobs(prev => [job, ...prev])
    setActiveJob(job.job_id)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-3 sm:px-4 py-2 sm:py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-xs sm:text-sm font-bold shrink-0">
              A
            </div>
            <div className="min-w-0">
              <h1 className="text-base sm:text-lg font-semibold truncate">Arwright</h1>
              <p className="text-[10px] sm:text-xs text-gray-500 hidden sm:block">PDF Pipeline</p>
            </div>
          </div>
          <nav className="flex gap-1 sm:gap-2 shrink-0">
            <button
              onClick={() => setView('upload')}
              className={`px-3 sm:px-4 py-2 sm:py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-colors min-h-[36px] sm:min-h-0 ${
                view === 'upload'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              Upload
            </button>
            <button
              onClick={() => setView('collections')}
              className={`px-3 sm:px-4 py-2 sm:py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-colors min-h-[36px] sm:min-h-0 ${
                view === 'collections'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              Collections
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-3 sm:px-4 py-4 sm:py-8">
        {view === 'upload' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6 lg:gap-8">
            {/* Left: Upload + Jobs */}
            <div className="lg:col-span-3 space-y-4 sm:space-y-6">
              <UploadZone onUploadComplete={handleUploadComplete} />
              
              {jobs.length > 0 && (
                <section>
                  <h2 className="text-xs sm:text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2 sm:mb-3">
                    Recent Jobs
                  </h2>
                  <div className="space-y-2 sm:space-y-3">
                    {jobs.map(job => (
                      <JobStatus
                        key={job.job_id}
                        jobId={job.job_id}
                        filename={job.filename}
                        isActive={activeJob === job.job_id}
                        onSelect={() => setActiveJob(job.job_id)}
                      />
                    ))}
                  </div>
                </section>
              )}
            </div>

            {/* Right: Active Job Details */}
            <div className="lg:col-span-2">
              {activeJob ? (
                <JobDetailPanel jobId={activeJob} />
              ) : (
                <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6 sm:p-8 text-center">
                  <div className="text-3xl sm:text-4xl mb-2 sm:mb-3">📄</div>
                  <p className="text-gray-500 text-xs sm:text-sm">
                    Upload a PDF to get started
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {view === 'collections' && <CollectionList />}
      </main>
    </div>
  )
}

function JobDetailPanel({ jobId }) {
  const [jobData, setJobData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/status/${jobId}`)
        if (!res.ok) throw new Error('Job not found')
        const data = await res.json()
        if (cancelled) return
        setJobData(data)
        if (data.status === 'processing') {
          setTimeout(() => { if (!cancelled) fetchStatus() }, 2000)
        }
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    }
    fetchStatus()
    return () => { cancelled = true }
  }, [jobId])

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 sm:p-6">
        <p className="text-red-400 text-xs sm:text-sm">{error}</p>
      </div>
    )
  }

  if (!jobData) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6 sm:p-8 text-center">
        <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-gray-500 text-xs sm:text-sm">Loading...</p>
      </div>
    )
  }

  if (jobData.status === 'processing') {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="animate-spin w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full shrink-0" />
          <div className="min-w-0">
            <p className="font-medium text-sm sm:text-base">Processing...</p>
            <p className="text-xs text-gray-500 truncate">{jobData.filename}</p>
          </div>
        </div>
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full bg-purple-600 rounded-full animate-pulse" style={{ width: '60%' }} />
        </div>
      </div>
    )
  }

  if (jobData.status === 'error') {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 sm:p-6">
        <h3 className="font-semibold text-red-400 mb-2 text-sm sm:text-base">Pipeline Error</h3>
        <p className="text-xs sm:text-sm text-red-300">{jobData.error}</p>
      </div>
    )
  }

  const stats = jobData.stats || {}
  const outputs = jobData.outputs || {}
  const hasMarkdown = !!outputs.markdown
  const hasChunks = !!outputs.chunks

  return (
    <div className="space-y-3 sm:space-y-4">
      {/* Stats */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4 sm:p-5">
        <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm sm:text-base">
          <span className="text-green-400">✅</span>
          Pipeline Complete
        </h3>
        <div className="grid grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
          <div className="bg-gray-800/50 rounded-lg p-2 sm:p-3">
            <p className="text-gray-500 text-[10px] sm:text-xs">Chunks</p>
            <p className="text-base sm:text-lg font-semibold text-purple-400">{stats?.chunk?.count || 0}</p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 sm:p-3">
            <p className="text-gray-500 text-[10px] sm:text-xs">Total Time</p>
            <p className="text-base sm:text-lg font-semibold text-blue-400">{stats?.total_time_s || 0}s</p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 sm:p-3">
            <p className="text-gray-500 text-[10px] sm:text-xs">Extracted</p>
            <p className="text-base sm:text-lg font-semibold text-emerald-400 truncate">{(stats?.extract?.chars || 0).toLocaleString()} chars</p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 sm:p-3">
            <p className="text-gray-500 text-[10px] sm:text-xs">Avg Chunk</p>
            <p className="text-base sm:text-lg font-semibold text-amber-400">{stats?.chunk?.avg_chars || 0} chars</p>
          </div>
        </div>
      </div>

      {/* Downloads */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4 sm:p-5">
        <h3 className="font-semibold mb-3 text-sm sm:text-base">📥 Downloads</h3>
        <div className="space-y-2">
          <a
            href={`${API_BASE}/download/${jobId}/markdown`}
            className={`flex items-center gap-3 p-3 rounded-lg text-sm transition-colors ${
              hasMarkdown
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                : 'bg-gray-800/30 text-gray-600 cursor-not-allowed'
            }`}
          >
            <span className="text-lg sm:text-xl shrink-0">📄</span>
            <div className="min-w-0">
              <p className="font-medium truncate">extracted.md</p>
              <p className="text-xs text-gray-500 hidden sm:block">Full markdown from PDF</p>
            </div>
          </a>
          <a
            href={`${API_BASE}/download/${jobId}/chunks`}
            className={`flex items-center gap-3 p-3 rounded-lg text-sm transition-colors ${
              hasChunks
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                : 'bg-gray-800/30 text-gray-600 cursor-not-allowed'
            }`}
          >
            <span className="text-lg sm:text-xl shrink-0">📦</span>
            <div className="min-w-0">
              <p className="font-medium truncate">chunks.json</p>
              <p className="text-xs text-gray-500 hidden sm:block">Structured chunks for other systems</p>
            </div>
          </a>
        </div>
      </div>

      {/* ChromaDB Info */}
      {outputs.chroma_collection && (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4 sm:p-5">
          <h3 className="font-semibold mb-2 text-sm sm:text-base">🗄️ ChromaDB Collection</h3>
          <div className="bg-gray-800 rounded-lg p-2.5 sm:p-3 font-mono text-xs sm:text-sm text-purple-300 truncate">
            {outputs.chroma_collection}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Access from any Python project: <code className="text-purple-400">chromadb.PersistentClient(path=&quot;...&quot;)</code>
          </p>
        </div>
      )}

      {/* Chat / Test RAG */}
      {outputs.chroma_collection && (
        <ChatPanel collectionName={outputs.chroma_collection} />
      )}
    </div>
  )
}
