import { useState, useCallback, useRef, useEffect } from 'react'
import { startSession, sendMessage, getStreamUrl } from '../lib/api'
import type { UIMessage, StatusEvent, OutlineEvent, ScriptEvent, SessionMeta } from '../types'

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

export interface ArcwrightState {
  sessionId: string | null
  messages: UIMessage[]
  currentNode: string
  statusMessage: string
  isProcessing: boolean
  connectionState: ConnectionState
  error: string | null
  outline: OutlineEvent | null
  script: ScriptEvent | null
}

export interface UseArcwrightReturn extends ArcwrightState {
  start: (params: { userName: string; language: string; platform: string }) => Promise<SessionMeta>
  send: (text: string) => Promise<void>
  reconnect: (sessionId: string) => void
  reset: () => void
}

const INITIAL: ArcwrightState = {
  sessionId:       null,
  messages:        [],
  currentNode:     'idle',
  statusMessage:   '',
  isProcessing:    false,
  connectionState: 'idle',
  error:           null,
  outline:         null,
  script:          null,
}

export function useArcwright(): UseArcwrightReturn {
  const [state, setState] = useState<ArcwrightState>(INITIAL)
  const esRef = useRef<EventSource | null>(null)

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const patch = useCallback((p: Partial<ArcwrightState>) => {
    setState(prev => ({ ...prev, ...p }))
  }, [])

  const pushMessage = useCallback((msg: UIMessage) => {
    setState(prev => ({ ...prev, messages: [...prev.messages, msg] }))
  }, [])

  // ── SSE connect ──────────────────────────────────────────────────────────────

  const connectSSE = useCallback((sessionId: string) => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    patch({ connectionState: 'connecting', sessionId })

    const es = new EventSource(getStreamUrl(sessionId))
    esRef.current = es

    es.onopen = () => patch({ connectionState: 'connected', error: null })

    es.onerror = () => {
      patch({ connectionState: 'disconnected', isProcessing: false })
    }

    es.addEventListener('status', (e: MessageEvent) => {
      const d = JSON.parse(e.data) as StatusEvent
      patch({
        currentNode:   d.node,
        statusMessage: d.message,
        isProcessing:  d.node !== 'idle',
      })
    })

    es.addEventListener('chat', (e: MessageEvent) => {
      const d = JSON.parse(e.data) as { role: 'user' | 'assistant'; content: string }
      pushMessage({
        id:        uid(),
        role:      d.role,
        content:   d.content,
        kind:      'text',
        timestamp: Date.now(),
      })
      patch({ isProcessing: false, error: null })
    })

    es.addEventListener('outline', (e: MessageEvent) => {
      const outline = JSON.parse(e.data) as OutlineEvent
      patch({ outline })
      // Replace last assistant message with an outline card
      setState(prev => {
        // find last assistant text message and upgrade it to outline kind
        const msgs = [...prev.messages]
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === 'assistant' && msgs[i].kind === 'text') {
            msgs[i] = { ...msgs[i], kind: 'outline', outline }
            break
          }
        }
        return { ...prev, messages: msgs, outline }
      })
    })

    es.addEventListener('script', (e: MessageEvent) => {
      const script = JSON.parse(e.data) as ScriptEvent
      patch({ script })
      pushMessage({
        id:        uid(),
        role:      'assistant',
        content:   '',
        kind:      'script',
        script,
        timestamp: Date.now(),
      })
    })

    es.addEventListener('error', (e: MessageEvent) => {
      try {
        const d = JSON.parse(e.data) as { message: string }
        patch({ error: d.message, isProcessing: false })
      } catch {
        patch({ isProcessing: false })
      }
    })
  }, [patch, pushMessage])

  // ── Cleanup on unmount ───────────────────────────────────────────────────────

  useEffect(() => () => { esRef.current?.close() }, [])

  // ── Public API ───────────────────────────────────────────────────────────────

  const start = useCallback(async (params: { userName: string; language: string; platform: string }): Promise<SessionMeta> => {
    patch({ ...INITIAL, isProcessing: true, connectionState: 'connecting' })

    const { session_id } = await startSession({
      user_name: params.userName,
      language:  params.language,
      platform:  params.platform,
    })

    connectSSE(session_id)
    patch({ sessionId: session_id, isProcessing: true })

    return {
      sessionId:    session_id,
      title:        'Nova sesi',
      platform:     params.platform,
      language:     params.language,
      timestamp:    Date.now(),
      messageCount: 0,
    }
  }, [patch, connectSSE])

  const send = useCallback(async (text: string) => {
    if (!state.sessionId) return
    const userMsg: UIMessage = {
      id:        uid(),
      role:      'user',
      content:   text,
      kind:      'text',
      timestamp: Date.now(),
    }
    pushMessage(userMsg)
    patch({ isProcessing: true, error: null })
    await sendMessage({ session_id: state.sessionId, message: text })
  }, [state.sessionId, pushMessage, patch])

  const reconnect = useCallback((sessionId: string) => {
    patch({ ...INITIAL, sessionId, connectionState: 'connecting' })
    connectSSE(sessionId)
  }, [patch, connectSSE])

  const reset = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
    setState(INITIAL)
  }, [])

  return { ...state, start, send, reconnect, reset }
}
