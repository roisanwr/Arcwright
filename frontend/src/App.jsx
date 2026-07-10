import { useState, useEffect, useCallback } from 'react'
import UploadZone from './components/UploadZone'
import JobStatus from './components/JobStatus'
import ChatPanel from './components/ChatPanel'
import CollectionList from './components/CollectionList'

const API_BASE = ''

export default function App() {
  const [jobs, setJobs] = useState([])
  const [activeJob, setActiveJob] = useState(null)
  const [view, setView] = useState('upload') // upload | collections

  const handleUploadComplete = useCallback((job) => {
    setJobs(prev => [job, ...prev])
    setActiveJob(job.job_id)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-sm font-bold">
              A
            </div>
            <div>
              <h1 className="text-lg font-semibold">Arwright</h1>
              <p className="text-xs text-gray-500">PDF Pipeline</p>
            </div>
          </div>
          <nav className="flex gap-2">
            <button
              onClick={() => setView('upload')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                view === 'upload'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              Upload
            </button>
            <button
              onClick={() => setView('collections')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
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
      <main className="max-w-6xl mx-auto px-4 py-8">
        {view === 'upload' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
            {/* Left: Upload + Jobs */}
            <div className="lg:col-span-3 space-y-6">
              <UploadZone onUploadComplete={handleUploadComplete} />
              
              {jobs.length > 0 && (
                <section>
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    Recent Jobs
                  </h2>
                  <div className="space-y-3">
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
                <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-8 text-center">
                  <div className="text-4xl mb-3">📄</div>
                  <p className="text-gray-500 text-sm">
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

  // Poll job status
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
      <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    )
  }

  if (!jobData) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-8 text-center">
        <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-gray-500 text-sm">Loading...</p>
      </div>
    )
  }

  if (jobData.status === 'processing') {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="animate-spin w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full" />
          <div>
            <p className="font-medium">Processing...</p>
            <p className="text-xs text-gray-500">{jobData.filename}</p>
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
      <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
        <h3 className="font-semibold text-red-400 mb-2">Pipeline Error</h3>
        <p className="text-sm text-red-300">{jobData.error}</p>
      </div>
    )
  }

  // Completed
  const stats = jobData.stats || {}
  const outputs = jobData.outputs || {}
  const hasMarkdown = !!outputs.markdown
  const hasChunks = !!outputs.chunks

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <span className="text-green-400">✅</span>
          Pipeline Complete
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-500 text-xs">Chunks</p>
            <p className="text-lg font-semibold text-purple-400">{stats?.chunk?.count || 0}</p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-500 text-xs">Total Time</p>
            <p className="text-lg font-semibold text-blue-400">{stats?.total_time_s || 0}s</p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-500 text-xs">Extracted</p>
            <p className="text-lg font-semibold text-emerald-400">{(stats?.extract?.chars || 0).toLocaleString()} chars</p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <p className="text-gray-500 text-xs">Avg Chunk</p>
            <p className="text-lg font-semibold text-amber-400">{stats?.chunk?.avg_chars || 0} chars</p>
          </div>
        </div>
      </div>

      {/* Downloads */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
        <h3 className="font-semibold mb-3">📥 Downloads</h3>
        <div className="space-y-2">
          <a
            href={`${API_BASE}/download/${jobId}/markdown`}
            className={`flex items-center gap-3 p-3 rounded-lg text-sm transition-colors ${
              hasMarkdown
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                : 'bg-gray-800/30 text-gray-600 cursor-not-allowed'
            }`}
          >
            <span className="text-xl">📄</span>
            <div>
              <p className="font-medium">extracted.md</p>
              <p className="text-xs text-gray-500">Full markdown from PDF</p>
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
            <span className="text-xl">📦</span>
            <div>
              <p className="font-medium">chunks.json</p>
              <p className="text-xs text-gray-500">Structured chunks for other systems</p>
            </div>
          </a>
        </div>
      </div>

      {/* ChromaDB Info */}
      {outputs.chroma_collection && (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
          <h3 className="font-semibold mb-2">🗄️ ChromaDB Collection</h3>
          <div className="bg-gray-800 rounded-lg p-3 font-mono text-sm text-purple-300">
            {outputs.chroma_collection}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Access from any Python project: <code className="text-purple-400">chromadb.PersistentClient(path="...")</code>
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
