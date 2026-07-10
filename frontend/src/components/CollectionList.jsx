import { useState, useEffect } from 'react'

const API_BASE = ''

export default function CollectionList() {
  const [collections, setCollections] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchCollections = async () => {
      try {
        const res = await fetch(`${API_BASE}/collections`)
        if (!res.ok) throw new Error('Failed to fetch')
        const data = await res.json()
        setCollections(data.collections || [])
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchCollections()
  }, [])

  if (loading) {
    return (
      <div className="text-center py-20">
        <div className="animate-spin w-8 h-8 border-3 border-purple-500 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-gray-500">Loading collections...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-xl p-6 text-center">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">🗄️ ChromaDB Collections</h2>
          <p className="text-sm text-gray-500 mt-1">
            Reusable RAG collections — accessible from any Python project
          </p>
        </div>
      </div>

      {collections.length === 0 ? (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-12 text-center">
          <div className="text-4xl mb-3">🗄️</div>
          <p className="text-gray-500">No collections yet. Upload a PDF to create one.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {collections.map((col) => (
            <div
              key={col.name}
              className="bg-gray-900/50 rounded-xl border border-gray-800 p-5 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="text-xl">📚</span>
                  <div>
                    <p className="font-medium">{col.name}</p>
                    <p className="text-xs text-gray-500">
                      {col.count} chunks • {col.metadata?.description || 'No description'}
                    </p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-800">
                  {col.count} vectors
                </span>
              </div>
              <div className="mt-2 bg-gray-800 rounded-lg p-2.5 font-mono text-xs text-gray-500">
                <span className="text-purple-400">collection</span> = client.get_collection(&quot;{col.name}&quot;)
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
