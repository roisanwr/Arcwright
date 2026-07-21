// ── SSE Event types from api_server.py ────────────────────────────────────────

export type SSEEventType = 'status' | 'chat' | 'reasoning' | 'outline' | 'script' | 'error' | 'ping'

export interface StatusEvent {
  node: string
  message: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ReasoningEvent {
  agent: string
  type: string
  content: string
  data?: unknown
}

export interface OutlineEvent {
  title?: string
  hook?: string
  setup?: string
  turning_point?: string
  struggle?: string
  resolution?: string
  punchline?: string
  platform?: string
  duration?: string
  [key: string]: string | undefined
}

export interface ScriptEvent {
  title?: string
  body?: string
  platform_variant?: string
  voice_notes?: string
}

export interface ErrorEvent {
  message: string
}

// ── Chat message in UI (extends ChatMessage with extras) ──────────────────────

export type MessageKind = 'text' | 'outline' | 'script'

export interface UIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  kind: MessageKind
  outline?: OutlineEvent
  script?: ScriptEvent
  timestamp: number
}

// ── Session history stored in localStorage ────────────────────────────────────

export interface SessionMeta {
  sessionId: string
  title: string          // first user message snippet
  platform: string
  language: string
  timestamp: number
  messageCount: number
}

// ── Agent metadata for display ────────────────────────────────────────────────

export interface AgentMeta {
  label: string
  color: string          // CSS color value
  icon: string           // emoji / text icon
}
