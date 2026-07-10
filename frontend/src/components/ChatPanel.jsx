import { useState } from 'react'

const API_BASE = ''

export default function ChatPanel({ collectionName }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/chat/${collectionName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), top_k: 5 }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Search failed')
      }

      const data = await res.json()
      setResults(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-5">
      <h3 className="font-semibold mb-3 flex items-center gap-2">
        <span>🧪</span>
        Test RAG — &quot;{collectionName}&quot;
      </h3>

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about your PDF..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-600 focus:ring-1 focus:ring-purple-600 transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? '...' : 'Search'}
        </button>
      </form>

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 mb-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {results && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500">
            Found {results.total_found} relevant chunks
          </p>
          {results.sources.map((source, i) => (
            <div key={i} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-purple-300 truncate">
                    {source.title || 'Untitled'}
                  </p>
                  {source.section && (
                    <p className="text-xs text-gray-500">{source.section}</p>
                  )}
                </div>
                <span className="text-xs text-gray-600 shrink-0">
                  d={source.distance.toFixed(3)}
                </span>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed line-clamp-4">
                {source.text}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
