import { useState, useEffect, useCallback } from 'react'
import type { SessionMeta } from '../types'
import { fetchHistory, deleteSession as apiDeleteSession } from '../lib/api'

const DEVICE_KEY = 'arcwright_device_id'
const MAX_LOCAL  = 50

// ── localStorage helpers (cache lokal) ───────────────────────────────────────

function localLoad(): SessionMeta[] {
  try {
    return JSON.parse(localStorage.getItem('arcwright_sessions') ?? '[]')
  } catch {
    return []
  }
}

function localSave(sessions: SessionMeta[]) {
  localStorage.setItem('arcwright_sessions', JSON.stringify(sessions.slice(0, MAX_LOCAL)))
}

// ── Konversi backend format → SessionMeta ────────────────────────────────────

function fromBackend(raw: {
  session_id: string
  title: string
  platform: string
  language: string
  status: string
  created_at: string
  updated_at: string
}): SessionMeta {
  return {
    sessionId:    raw.session_id,
    title:        raw.title || 'Sesi baru',
    platform:     raw.platform,
    language:     raw.language,
    timestamp:    new Date(raw.created_at).getTime(),
    messageCount: 0,
    status:       raw.status,
    updatedAt:    raw.updated_at,
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useHistory() {
  // Mulai dengan data localStorage, langsung tampil sebelum fetch selesai
  const [sessions, setSessions] = useState<SessionMeta[]>(localLoad)
  const [loading,  setLoading]  = useState(false)

  // Pastikan device_id sudah ada
  useEffect(() => {
    if (!localStorage.getItem(DEVICE_KEY)) {
      // Fallback UUID untuk HTTP non-secure context
      const id = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
      })
      localStorage.setItem(DEVICE_KEY, id)
    }
  }, [])

  // Fetch dari backend saat mount — sinkronisasi cache lokal dengan server
  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const backendSessions = await fetchHistory()
      const converted = backendSessions.map(fromBackend)
      setSessions(converted)
      localSave(converted)
    } catch {
      // Jika backend gagal, pakai data lokal yang sudah ada
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  // ── Mutations ──────────────────────────────────────────────────────────────

  const addSession = useCallback((meta: SessionMeta) => {
    setSessions(prev => {
      const filtered = prev.filter(s => s.sessionId !== meta.sessionId)
      const next = [meta, ...filtered]
      localSave(next)
      return next
    })
  }, [])

  const updateSession = useCallback((sessionId: string, patch: Partial<SessionMeta>) => {
    setSessions(prev => {
      const next = prev.map(s => s.sessionId === sessionId ? { ...s, ...patch } : s)
      localSave(next)
      return next
    })
  }, [])

  const removeSession = useCallback(async (sessionId: string) => {
    // Soft-delete ke backend
    try { await apiDeleteSession(sessionId) } catch { /* ignore */ }
    // Hapus dari local state
    setSessions(prev => {
      const next = prev.filter(s => s.sessionId !== sessionId)
      localSave(next)
      return next
    })
  }, [])

  const clearAll = useCallback(() => {
    localSave([])
    setSessions([])
  }, [])

  return { sessions, loading, addSession, updateSession, removeSession, clearAll, refresh }
}
