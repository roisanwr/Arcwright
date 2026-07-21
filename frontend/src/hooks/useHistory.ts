import { useState, useCallback } from 'react'
import type { SessionMeta } from '../types'

const STORAGE_KEY = 'arcwright_sessions'
const MAX_SESSIONS = 30

function load(): SessionMeta[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
  } catch {
    return []
  }
}

function save(sessions: SessionMeta[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
}

export function useHistory() {
  const [sessions, setSessions] = useState<SessionMeta[]>(load)

  const addSession = useCallback((meta: SessionMeta) => {
    setSessions(prev => {
      const filtered = prev.filter(s => s.sessionId !== meta.sessionId)
      const next = [meta, ...filtered].slice(0, MAX_SESSIONS)
      save(next)
      return next
    })
  }, [])

  const updateSession = useCallback((sessionId: string, patch: Partial<SessionMeta>) => {
    setSessions(prev => {
      const next = prev.map(s => s.sessionId === sessionId ? { ...s, ...patch } : s)
      save(next)
      return next
    })
  }, [])

  const removeSession = useCallback((sessionId: string) => {
    setSessions(prev => {
      const next = prev.filter(s => s.sessionId !== sessionId)
      save(next)
      return next
    })
  }, [])

  const clearAll = useCallback(() => {
    save([])
    setSessions([])
  }, [])

  return { sessions, addSession, updateSession, removeSession, clearAll }
}
