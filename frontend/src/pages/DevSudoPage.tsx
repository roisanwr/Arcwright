/**
 * DevSudoPage — Admin panel for Arcwright.
 * Route: /dev/sudo — password protected via admin key.
 *
 * Features:
 * - Sidebar: semua sesi dari semua user (filter, search)
 * - Chat viewer: baca percakapan + inject pesan ke sesi live
 * - Right panel: ⚙️ Proses log, 🧠 Internal Thought, 📄 Skrip (via SSE)
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { MarkdownContent, LoadingDots } from '../components/shared'

const BASE = import.meta.env.VITE_API_BASE ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

interface SessionRow {
  session_id: string
  device_id: string
  title: string
  platform: string
  language: string
  status: string
  created_at: string
  updated_at: string
}

interface AdminStats {
  total_sessions: number
  total_users: number
  active: number
  completed: number
  today: number
}

interface AdminMessage {
  role: string
  content: string
  msg_type: string
  created_at: string
}

interface SessionDetail {
  session_id: string
  meta: SessionRow
  messages: AdminMessage[]
  is_live: boolean
}

interface ProcessEvent {
  node: string
  message: string
  ts: string
}

interface ReasoningEvent {
  agent: string
  type: string
  content: string
  data?: Record<string, unknown>
}

interface ScriptEvent {
  title?: string
  body?: string
  platform_variant?: string
}

interface RagCitation {
  framework?: string
  principle?: string
  content?: string
  source_books?: string[]
  relevance?: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'baru saja'
  if (m < 60) return `${m}m lalu`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}j lalu`
  return `${Math.floor(h / 24)}h lalu`
}

function nowTs() {
  const n = new Date()
  return `${String(n.getHours()).padStart(2,'0')}:${String(n.getMinutes()).padStart(2,'0')}:${String(n.getSeconds()).padStart(2,'0')}`
}

function platformIcon(p: string) {
  return ({ youtube:'▶', tiktok:'♪', podcast:'🎙', blog:'✍', general:'✦' } as Record<string,string>)[p] ?? '✦'
}
function statusColor(s: string) {
  return ({ active:'#2dd4bf', completed:'#818cf8', archived:'#4a5c6b' } as Record<string,string>)[s] ?? '#8899a6'
}
function shortDevice(id: string) { return id ? id.slice(0,8)+'…' : '—' }

const AGENT_META: Record<string,{label:string,color:string,icon:string}> = {
  story_director:  { label:'Story Director',  color:'#60a5fa', icon:'🧠' },
  story_miner:     { label:'Story Miner',     color:'#34d399', icon:'💬' },
  rag_librarian:   { label:'RAG Librarian',   color:'#a78bfa', icon:'📚' },
  web_researcher:  { label:'Web Researcher',  color:'#38bdf8', icon:'🌐' },
  deep_dive:       { label:'Deep Dive',       color:'#f472b6', icon:'🔍' },
  validator:       { label:'Validator',       color:'#facc15', icon:'✅' },
  outline_writer:  { label:'Outline Writer',  color:'#fb923c', icon:'📝' },
  script_writer:   { label:'Script Writer',   color:'#c084fc', icon:'🎬' },
  user_approval:   { label:'User Approval',   color:'#94a3b8', icon:'⏸️' },
  idle:            { label:'Idle',            color:'#475569', icon:'💤' },
}
function getAgent(node: string) {
  return AGENT_META[node] ?? { label: node, color: '#94a3b8', icon: '⚙️' }
}

// ── Login screen ──────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }: { onLogin: (key: string) => void }) {
  const [key, setKey] = useState('')
  const [err, setErr] = useState('')
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => { ref.current?.focus() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr('')
    const res = await fetch(`${BASE}/api/admin/sessions?key=${encodeURIComponent(key)}`)
    if (res.ok) onLogin(key)
    else setErr('Admin key salah.')
  }

  return (
    <div className="flex items-center justify-center h-screen" style={{ background: '#080e18' }}>
      <div className="w-full max-w-sm p-8 rounded-2xl" style={{ background: '#0a1422', border: '1px solid #1a2d47' }}>
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold"
            style={{ background: 'linear-gradient(135deg, #f87171, #818cf8)' }}>⚙</div>
          <h1 className="font-bold text-lg" style={{ color: '#e8e3dc' }}>Arcwright Dev Panel</h1>
          <p className="text-xs" style={{ color: '#4a5c6b' }}>Admin access only</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <input ref={ref} type="password" value={key} onChange={e => setKey(e.target.value)}
            placeholder="Admin key..."
            className="w-full px-4 py-3 rounded-xl text-sm outline-none"
            style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
            onFocus={e => (e.currentTarget.style.borderColor = '#818cf8')}
            onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
          />
          {err && <p className="text-xs text-center" style={{ color: '#f87171' }}>{err}</p>}
          <button type="submit" className="w-full py-3 rounded-xl font-semibold text-sm"
            style={{ background: '#818cf8', color: '#080e18' }}>
            Masuk ⚙
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatsBar({ stats, liveCount }: { stats: AdminStats; liveCount: number }) {
  const items = [
    { label:'Total Sesi',  value: stats.total_sessions, color:'#e8e3dc' },
    { label:'User Unik',   value: stats.total_users,    color:'#2dd4bf' },
    { label:'Active',      value: stats.active,         color:'#2dd4bf' },
    { label:'Completed',   value: stats.completed,      color:'#818cf8' },
    { label:'Hari Ini',    value: stats.today,          color:'#fbbf24' },
    { label:'Live Now',    value: liveCount,            color:'#f87171' },
  ]
  return (
    <div className="grid grid-cols-6 gap-px shrink-0" style={{ background: '#1a2d47', borderBottom: '1px solid #1a2d47' }}>
      {items.map(item => (
        <div key={item.label} className="flex flex-col items-center py-2.5 px-2" style={{ background: '#0a1422' }}>
          <span className="text-base font-bold tabular-nums" style={{ color: item.color }}>{item.value ?? 0}</span>
          <span className="text-[10px] mt-0.5" style={{ color: '#4a5c6b' }}>{item.label}</span>
        </div>
      ))}
    </div>
  )
}

// ── Sidebar item ──────────────────────────────────────────────────────────────

function SessionItem({ session, isActive, isLive, onClick }: {
  session: SessionRow; isActive: boolean; isLive: boolean; onClick: () => void
}) {
  return (
    <div onClick={onClick} className="px-3 py-2.5 cursor-pointer transition-colors"
      style={{ background: isActive ? '#121e30' : 'transparent', borderLeft: isActive ? '2px solid #818cf8' : '2px solid transparent' }}
      onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#0d1827' }}
      onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent' }}
    >
      <div className="flex items-center gap-1.5 mb-0.5">
        <span className="text-xs" style={{ color: '#2dd4bf' }}>{platformIcon(session.platform)}</span>
        <span className="text-[10px] font-mono truncate flex-1" style={{ color: '#4a5c6b' }}>{shortDevice(session.device_id)}</span>
        {isLive && <span className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold animate-pulse"
          style={{ background: 'rgba(248,113,113,0.15)', color: '#f87171' }}>LIVE</span>}
        <span className="text-[9px] px-1 py-0.5 rounded" style={{ color: statusColor(session.status) }}>{session.status}</span>
      </div>
      <p className="text-xs truncate" style={{ color: isActive ? '#e8e3dc' : '#8899a6' }}>{session.title}</p>
      <p className="text-[10px] mt-0.5" style={{ color: '#2d4055' }}>{timeAgo(session.updated_at)}</p>
    </div>
  )
}

// ── Process log tab ───────────────────────────────────────────────────────────

function ProcessLog({ events }: { events: ProcessEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events])
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-1.5 text-xs font-mono">
      {events.length === 0 && (
        <p className="text-center mt-8" style={{ color: '#2d4055' }}>
          Pipeline belum berjalan. Pilih sesi LIVE untuk melihat proses real-time.
        </p>
      )}
      {events.map((ev, i) => {
        const agent = getAgent(ev.node)
        return (
          <div key={i} className="flex items-start gap-2">
            <span className="shrink-0 mt-0.5">{agent.icon}</span>
            <div>
              <span className="font-semibold" style={{ color: agent.color }}>{agent.label}</span>
              <span className="ml-2" style={{ color: '#2d4055' }}>{ev.ts}</span>
              {ev.message && <p style={{ color: '#8899a6' }}>{ev.message}</p>}
            </div>
          </div>
        )
      })}
      <div ref={endRef} />
    </div>
  )
}

// ── Reasoning tab ─────────────────────────────────────────────────────────────

function ReasoningPanel({ reasonings }: { reasonings: ReasoningEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [reasonings])
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {reasonings.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
          <span className="text-3xl opacity-20">🧠</span>
          <p className="text-xs" style={{ color: '#2d4055' }}>Belum ada thought process.<br/>Pilih sesi LIVE untuk monitor secara real-time.</p>
        </div>
      ) : reasonings.map((r, i) => {
        const agent = getAgent(r.agent)
        return (
          <div key={i} className="rounded-lg p-3" style={{ background: '#080e18', border: '1px solid #1a2d47' }}>
            <div className="flex items-center justify-between mb-2 pb-2" style={{ borderBottom: '1px solid #1a2d47' }}>
              <div className="flex items-center gap-2">
                <span>{agent.icon}</span>
                <span className="font-semibold text-xs" style={{ color: agent.color }}>{agent.label}</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-mono"
                style={{ background: '#121e30', color: '#8899a6', border: '1px solid #1a2d47' }}>
                {r.type.replace(/_/g, ' ')}
              </span>
            </div>
            <MarkdownContent content={r.content ?? ''} className="text-xs leading-relaxed" style={{ color: '#c4cdd6', fontFamily: 'monospace' }} />
            {r.data && (
              <pre className="mt-2 text-[10px] overflow-x-auto p-2 rounded"
                style={{ background: '#0a1422', color: '#4a5c6b', border: '1px solid #1a2d47' }}>
                {JSON.stringify(r.data, null, 2)}
              </pre>
            )}
          </div>
        )
      })}
      <div ref={endRef} />
    </div>
  )
}

// ── RAG Citations tab ─────────────────────────────────────────────────────────

function RagPanel({ citations }: { citations: RagCitation[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [citations])
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {citations.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
          <span className="text-3xl opacity-20">📚</span>
          <p className="text-xs" style={{ color: '#2d4055' }}>
            Kutipan dari buku storytelling akan muncul di sini<br/>saat RAG Librarian bekerja.
          </p>
        </div>
      ) : citations.map((c, i) => (
        <div key={i} className="rounded-lg p-3 space-y-2" style={{ background: '#080e18', border: '1px solid #1a2d47' }}>
          {/* Framework badge */}
          {c.framework && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold"
                style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.3)' }}>
                {c.framework}
              </span>
              {c.principle && (
                <span className="text-[10px]" style={{ color: '#8899a6' }}>{c.principle}</span>
              )}
            </div>
          )}
          {/* Content */}
          {c.content && (
            <p className="text-xs leading-relaxed italic" style={{ color: '#c4cdd6', borderLeft: '2px solid #1a2d47', paddingLeft: '8px' }}>
              "{c.content}"
            </p>
          )}
          {/* Relevance */}
          {c.relevance && (
            <p className="text-[10px]" style={{ color: '#2dd4bf' }}>↳ {c.relevance}</p>
          )}
          {/* Source books */}
          {c.source_books && c.source_books.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1" style={{ borderTop: '1px solid #1a2d47' }}>
              {c.source_books.map((b, bi) => (
                <span key={bi} className="text-[10px] px-2 py-0.5 rounded"
                  style={{ background: '#0d1827', color: '#8899a6', border: '1px solid #1a2d47' }}>
                  📖 {b}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}

// ── Script tab ────────────────────────────────────────────────────────────────

function ScriptPanel({ script }: { script: ScriptEvent | null }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    if (!script?.body) return
    navigator.clipboard.writeText(script.body).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }
  if (!script) return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
      <span className="text-3xl opacity-20">📄</span>
      <p className="text-xs" style={{ color: '#2d4055' }}>Skrip belum tersedia.<br/>Akan muncul otomatis saat pipeline selesai.</p>
    </div>
  )
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold text-sm" style={{ color: '#e8e3dc' }}>{script.title ?? 'Script'}</h3>
          {script.platform_variant && (
            <span className="text-[10px] px-2 py-0.5 rounded-full"
              style={{ background: '#1e1a3f', color: '#818cf8', border: '1px solid #2d2a5e' }}>
              {script.platform_variant}
            </span>
          )}
        </div>
        <button onClick={copy} className="text-[10px] px-3 py-1.5 rounded-lg border transition-colors"
          style={{ borderColor: '#1a2d47', color: copied ? '#2dd4bf' : '#8899a6', background: 'transparent' }}>
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <MarkdownContent content={script.body ?? ''} className="text-sm leading-relaxed" style={{ color: '#e8e3dc' }} />
    </div>
  )
}

// ── Chat viewer (tengah) ──────────────────────────────────────────────────────

function ChatViewer({ detail, adminKey, onInjectSent }: {
  detail: SessionDetail | null; adminKey: string; onInjectSent: () => void
}) {
  const [inject, setInject] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [detail?.messages])

  const handleInject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detail || !inject.trim() || sending) return
    setSending(true)
    try {
      await fetch(`${BASE}/api/admin/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: detail.session_id, message: inject.trim(), key: adminKey }),
      })
      setInject(''); onInjectSent()
    } finally { setSending(false) }
  }

  if (!detail) return (
    <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: '#2d4055' }}>
      <span className="text-4xl">⚙</span>
      <p className="text-sm">Pilih sesi dari sidebar untuk melihat detail</p>
    </div>
  )

  const { meta, messages, is_live } = detail
  return (
    <div className="flex flex-col h-full">
      {/* Session header */}
      <div className="px-4 py-2.5 shrink-0" style={{ borderBottom: '1px solid #1a2d47', background: '#0a1422' }}>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm" style={{ color: '#e8e3dc' }}>{meta.title}</span>
          {is_live && <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold animate-pulse"
            style={{ background: 'rgba(248,113,113,0.15)', color: '#f87171' }}>● LIVE</span>}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-[11px]" style={{ color: '#4a5c6b' }}>{platformIcon(meta.platform)} {meta.platform}</span>
          <span className="text-[11px]" style={{ color: '#4a5c6b' }}>lang: {meta.language}</span>
          <span className="text-[11px] font-mono" style={{ color: '#2d4055' }}>device: {shortDevice(meta.device_id)}</span>
          <span className="text-[11px]" style={{ color: statusColor(meta.status) }}>{meta.status}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-sm mt-8" style={{ color: '#2d4055' }}>Belum ada pesan.</p>
        )}
        {messages.map((msg, i) => {
          const isUser = msg.role === 'user'
          const isScript = msg.msg_type === 'script'
          return (
            <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className="rounded-xl px-3 py-2 text-sm max-w-[82%]"
                style={{
                  background: isScript ? '#0d1827' : isUser ? '#1a2d47' : '#111620',
                  border: `1px solid ${isScript ? '#2d3d52' : isUser ? '#1a2d47' : '#1a2d47'}`,
                  color: '#e8e3dc',
                }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-semibold" style={{ color: isUser ? '#2dd4bf' : isScript ? '#818cf8' : '#8899a6' }}>
                    {isUser ? '👤 User' : isScript ? '🎬 Script' : '🤖 Yui'}
                  </span>
                  <span className="text-[10px]" style={{ color: '#2d4055' }}>{timeAgo(msg.created_at)}</span>
                </div>
                <MarkdownContent content={msg.content} className="text-xs leading-relaxed" />
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Inject (live only) */}
      {is_live && (
        <div className="shrink-0 px-4 py-2.5" style={{ borderTop: '1px solid #1a2d47', background: '#0a1422' }}>
          <form onSubmit={handleInject} className="flex gap-2">
            <input type="text" value={inject} onChange={e => setInject(e.target.value)}
              placeholder="Inject pesan ke sesi ini (admin)..."
              className="flex-1 px-3 py-2 rounded-xl text-xs outline-none"
              style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
              onFocus={e => (e.currentTarget.style.borderColor = '#f87171')}
              onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
            />
            <button type="submit" disabled={!inject.trim() || sending}
              className="px-3 py-2 rounded-xl text-xs font-semibold shrink-0"
              style={{ background: '#f87171', color: '#080e18', opacity: inject.trim() ? 1 : 0.4 }}>
              {sending ? <LoadingDots size="xs" /> : '⚡ Inject'}
            </button>
          </form>
          <p className="text-[10px] mt-1 text-center" style={{ color: '#2d4055' }}>⚠ Inject hanya tersedia saat sesi LIVE</p>
        </div>
      )}
    </div>
  )
}

// ── Main DevSudoPage ──────────────────────────────────────────────────────────

export default function DevSudoPage() {
  const [adminKey, setAdminKey]   = useState('')
  const [authed, setAuthed]       = useState(false)
  const [sessions, setSessions]   = useState<SessionRow[]>([])
  const [stats, setStats]         = useState<AdminStats | null>(null)
  const [liveIds, setLiveIds]     = useState<string[]>([])
  const [activeId, setActiveId]   = useState<string | null>(null)
  const [detail, setDetail]       = useState<SessionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [filter, setFilter]       = useState<'all'|'live'|'active'|'completed'>('all')
  const [search, setSearch]       = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [rightTab, setRightTab]   = useState<'log'|'reasoning'|'rag'|'script'>('log')

  // Right panel live state (SSE)
  const [processLog, setProcessLog]   = useState<ProcessEvent[]>([])
  const [reasonings, setReasonings]   = useState<ReasoningEvent[]>([])
  const [liveScript, setLiveScript]   = useState<ScriptEvent | null>(null)
  const [ragCitations, setRagCitations] = useState<RagCitation[]>([])
  const esRef = useRef<EventSource | null>(null)
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── SSE connect ke sesi yang dipilih ───────────────────────────────────────

  const connectSSE = useCallback((sessionId: string, key: string) => {
    if (esRef.current) { esRef.current.close(); esRef.current = null }
    setProcessLog([]); setReasonings([]); setLiveScript(null); setRagCitations([])
    setRightTab('log')

    const es = new EventSource(`${BASE}/api/admin/stream/${sessionId}?key=${encodeURIComponent(key)}`)
    esRef.current = es

    es.addEventListener('status', (e: MessageEvent) => {
      const d = JSON.parse(e.data)
      setProcessLog(prev => [...prev.slice(-100), { node: d.node, message: d.message, ts: nowTs() }])
    })
    es.addEventListener('reasoning', (e: MessageEvent) => {
      const r = JSON.parse(e.data) as ReasoningEvent
      setReasonings(prev => [...prev, r])
      setRightTab('reasoning')
    })
    es.addEventListener('script', (e: MessageEvent) => {
      setLiveScript(JSON.parse(e.data))
      setRightTab('script')
    })
    es.addEventListener('rag_citation', (e: MessageEvent) => {
      const c = JSON.parse(e.data) as RagCitation
      setRagCitations(prev => [...prev, c])
      setRightTab('rag')
    })
  }, [])

  useEffect(() => () => { esRef.current?.close() }, [])

  // ── Fetch sessions list ────────────────────────────────────────────────────

  const fetchSessions = useCallback(async (key: string) => {
    const res = await fetch(`${BASE}/api/admin/sessions?key=${encodeURIComponent(key)}`)
    if (!res.ok) return
    const data = await res.json()
    setSessions(data.sessions ?? [])
    setStats(data.stats ?? null)
    setLiveIds(data.live_session_ids ?? [])
  }, [])

  const handleLogin = useCallback((key: string) => {
    setAdminKey(key); setAuthed(true); fetchSessions(key)
  }, [fetchSessions])

  useEffect(() => {
    if (!authed) return
    refreshTimer.current = setInterval(() => fetchSessions(adminKey), 15000)
    return () => { if (refreshTimer.current) clearInterval(refreshTimer.current) }
  }, [authed, adminKey, fetchSessions])

  // ── Select sesi ───────────────────────────────────────────────────────────

  const handleSelectSession = useCallback(async (sessionId: string) => {
    setActiveId(sessionId)
    setLoadingDetail(true)
    // Reset right panel
    setProcessLog([]); setReasonings([]); setLiveScript(null)
    setRightTab('log')
    try {
      const res = await fetch(`${BASE}/api/admin/session/${sessionId}?key=${encodeURIComponent(adminKey)}`)
      if (res.ok) {
        const data: SessionDetail = await res.json()
        setDetail(data)
        // Jika ada script di history, tampilkan
        const scriptMsg = data.messages.findLast(m => m.msg_type === 'script')
        if (scriptMsg) {
          const match = scriptMsg.content.match(/\[SCRIPT:(.+?)\]\n([\s\S]+)/)
          if (match) setLiveScript({ title: match[1], body: match[2] })
        }
        // Connect SSE untuk monitor live events
        connectSSE(sessionId, adminKey)
      }
    } finally { setLoadingDetail(false) }
  }, [adminKey, connectSSE])

  const handleRefresh = useCallback(() => {
    if (activeId) handleSelectSession(activeId)
    fetchSessions(adminKey)
  }, [activeId, adminKey, handleSelectSession, fetchSessions])

  if (!authed) return <LoginScreen onLogin={handleLogin} />

  const filtered = sessions.filter(s => {
    if (filter === 'live'      && !liveIds.includes(s.session_id)) return false
    if (filter === 'active'    && s.status !== 'active')    return false
    if (filter === 'completed' && s.status !== 'completed') return false
    if (search) {
      const q = search.toLowerCase()
      return s.title.toLowerCase().includes(q) || s.device_id.includes(q) || s.platform.includes(q)
    }
    return true
  })

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: '#080e18' }}>

      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 shrink-0"
        style={{ background: '#0a1422', borderBottom: '1px solid #1a2d47' }}>
        <div className="flex items-center gap-3">
          <button onClick={() => setSidebarOpen(v => !v)} className="p-1.5 rounded" style={{ color: '#8899a6' }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
          <div className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #f87171, #818cf8)' }}>⚙</div>
          <span className="font-semibold text-sm" style={{ color: '#e8e3dc' }}>
            arcwright <span style={{ color: '#818cf8' }}>/ dev sudo</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleRefresh}
            className="text-xs px-3 py-1.5 rounded-lg border"
            style={{ borderColor: '#1a2d47', color: '#8899a6' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#e8e3dc')}
            onMouseLeave={e => (e.currentTarget.style.color = '#8899a6')}>
            ↻ Refresh
          </button>
          <span className="text-[10px] px-2 py-1 rounded" style={{ background: '#0d1827', color: '#2d4055' }}>
            auto 15s
          </span>
        </div>
      </header>

      {/* Stats */}
      {stats && <StatsBar stats={stats} liveCount={liveIds.length} />}

      {/* Body — 3 kolom */}
      <div className="flex flex-1 min-h-0">

        {/* Sidebar kiri */}
        {sidebarOpen && (
          <aside className="flex flex-col w-64 shrink-0 h-full" style={{ background: '#0a1422', borderRight: '1px solid #1a2d47' }}>
            <div className="px-3 py-2.5 space-y-2 shrink-0" style={{ borderBottom: '1px solid #1a2d47' }}>
              <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Cari..."
                className="w-full px-3 py-1.5 rounded-lg text-xs outline-none"
                style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
              />
              <div className="flex gap-1">
                {(['all','live','active','completed'] as const).map(f => (
                  <button key={f} onClick={() => setFilter(f)}
                    className="flex-1 py-1 rounded text-[10px] font-semibold"
                    style={{
                      background: filter===f ? '#1a2d47' : 'transparent',
                      color: filter===f ? '#e8e3dc' : '#4a5c6b',
                      border: filter===f ? '1px solid #2d3d52' : '1px solid transparent',
                    }}>
                    {f==='live'?'🔴':''}{f}
                  </button>
                ))}
              </div>
              <p className="text-[10px]" style={{ color: '#2d4055' }}>{filtered.length} sesi</p>
            </div>
            <div className="flex-1 overflow-y-auto divide-y" style={{ borderColor: '#0d1520' }}>
              {filtered.map(s => (
                <SessionItem key={s.session_id} session={s}
                  isActive={s.session_id === activeId}
                  isLive={liveIds.includes(s.session_id)}
                  onClick={() => handleSelectSession(s.session_id)}
                />
              ))}
              {filtered.length === 0 && (
                <p className="text-center text-xs py-8" style={{ color: '#2d4055' }}>Belum ada sesi.</p>
              )}
            </div>
          </aside>
        )}

        {/* Chat viewer — tengah */}
        <main className="flex-1 min-w-0 h-full overflow-hidden border-r" style={{ borderColor: '#1a2d47' }}>
          {loadingDetail
            ? <div className="flex items-center justify-center h-full"><LoadingDots /></div>
            : <ChatViewer detail={detail} adminKey={adminKey} onInjectSent={handleRefresh} />
          }
        </main>

        {/* Right panel — Proses / Internal Thought / Skrip */}
        <div className="flex flex-col w-80 shrink-0 h-full" style={{ background: '#090f1c' }}>
          {/* Tabs */}
          <div className="flex shrink-0" style={{ borderBottom: '1px solid #1a2d47' }}>
            {([
              ['log',       '⚙️ Proses'],
              ['reasoning', '🧠 Thought'],
              ['rag',       '📚 Buku'],
              ['script',    '📄 Skrip'],
            ] as const).map(([tab, label]) => (
              <button key={tab} onClick={() => setRightTab(tab)}
                className="flex-1 py-2.5 text-[10px] font-semibold uppercase tracking-wider transition-colors"
                style={{
                  background: rightTab===tab ? '#0d1827' : 'transparent',
                  color: rightTab===tab ? '#e8e3dc' : '#4a5c6b',
                  borderBottom: rightTab===tab ? '2px solid #818cf8' : '2px solid transparent',
                }}>
                {label}
                {tab==='script' && liveScript && (
                  <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full align-middle" style={{ background: '#2dd4bf' }} />
                )}
                {tab==='reasoning' && reasonings.length > 0 && (
                  <span className="ml-1 text-[9px] px-1 rounded" style={{ background: '#1a2d47', color: '#818cf8' }}>
                    {reasonings.length}
                  </span>
                )}
                {tab==='rag' && ragCitations.length > 0 && (
                  <span className="ml-1 text-[9px] px-1 rounded" style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}>
                    {ragCitations.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 min-h-0 flex flex-col">
            {rightTab === 'log'       && <ProcessLog events={processLog} />}
            {rightTab === 'reasoning' && <ReasoningPanel reasonings={reasonings} />}
            {rightTab === 'rag'       && <RagPanel citations={ragCitations} />}
            {rightTab === 'script'    && <ScriptPanel script={liveScript} />}
          </div>
        </div>

      </div>
    </div>
  )
}
