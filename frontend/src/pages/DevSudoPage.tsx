/**
 * DevSudoPage — Admin panel for Arcwright.
 * Accessible at /dev/sudo — password protected via admin key.
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

function platformIcon(p: string) {
  return { youtube: '▶', tiktok: '♪', podcast: '🎙', blog: '✍', general: '✦' }[p] ?? '✦'
}

function statusColor(s: string) {
  return { active: '#2dd4bf', completed: '#818cf8', archived: '#4a5c6b' }[s] ?? '#8899a6'
}

function shortDevice(id: string) {
  return id ? id.slice(0, 8) + '…' : '—'
}

// ── Login screen ──────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }: { onLogin: (key: string) => void }) {
  const [key, setKey] = useState('')
  const [err, setErr] = useState('')
  const ref = useRef<HTMLInputElement>(null)

  useEffect(() => { ref.current?.focus() }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    const res = await fetch(`${BASE}/api/admin/sessions?key=${encodeURIComponent(key)}`)
    if (res.ok) {
      onLogin(key)
    } else {
      setErr('Admin key salah. Coba lagi.')
    }
  }

  return (
    <div className="flex items-center justify-center h-screen" style={{ background: '#080e18' }}>
      <div className="w-full max-w-sm p-8 rounded-2xl" style={{ background: '#0a1422', border: '1px solid #1a2d47' }}>
        <div className="flex flex-col items-center gap-3 mb-8">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold"
            style={{ background: 'linear-gradient(135deg, #f87171, #818cf8)' }}
          >
            ⚙
          </div>
          <h1 className="font-bold text-lg" style={{ color: '#e8e3dc' }}>Arcwright Dev Panel</h1>
          <p className="text-xs" style={{ color: '#4a5c6b' }}>Admin access only</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <input
            ref={ref}
            type="password"
            value={key}
            onChange={e => setKey(e.target.value)}
            placeholder="Admin key..."
            className="w-full px-4 py-3 rounded-xl text-sm outline-none"
            style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
            onFocus={e => (e.currentTarget.style.borderColor = '#818cf8')}
            onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
          />
          {err && <p className="text-xs text-center" style={{ color: '#f87171' }}>{err}</p>}
          <button
            type="submit"
            className="w-full py-3 rounded-xl font-semibold text-sm"
            style={{ background: '#818cf8', color: '#080e18' }}
          >
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
    { label: 'Total Sesi',  value: stats.total_sessions, color: '#e8e3dc' },
    { label: 'User Unik',   value: stats.total_users,    color: '#2dd4bf' },
    { label: 'Active',      value: stats.active,         color: '#2dd4bf' },
    { label: 'Completed',   value: stats.completed,      color: '#818cf8' },
    { label: 'Hari Ini',    value: stats.today,          color: '#fbbf24' },
    { label: 'Live Now',    value: liveCount,            color: '#f87171' },
  ]
  return (
    <div
      className="grid grid-cols-3 md:grid-cols-6 gap-px shrink-0"
      style={{ background: '#1a2d47', borderBottom: '1px solid #1a2d47' }}
    >
      {items.map(item => (
        <div key={item.label} className="flex flex-col items-center py-3 px-2" style={{ background: '#0a1422' }}>
          <span className="text-lg font-bold tabular-nums" style={{ color: item.color }}>{item.value ?? 0}</span>
          <span className="text-[10px] mt-0.5" style={{ color: '#4a5c6b' }}>{item.label}</span>
        </div>
      ))}
    </div>
  )
}

// ── Sidebar item ──────────────────────────────────────────────────────────────

function SessionItem({
  session, isActive, isLive, onClick,
}: {
  session: SessionRow
  isActive: boolean
  isLive: boolean
  onClick: () => void
}) {
  return (
    <div
      onClick={onClick}
      className="px-3 py-2.5 cursor-pointer transition-colors"
      style={{
        background: isActive ? '#121e30' : 'transparent',
        borderLeft: isActive ? '2px solid #818cf8' : '2px solid transparent',
      }}
      onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = '#0d1827' }}
      onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent' }}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-xs" style={{ color: '#2dd4bf' }}>{platformIcon(session.platform)}</span>
        <span className="text-[10px] font-mono truncate flex-1" style={{ color: '#4a5c6b' }}>
          {shortDevice(session.device_id)}
        </span>
        {isLive && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold" style={{ background: 'rgba(248,113,113,0.15)', color: '#f87171' }}>
            LIVE
          </span>
        )}
        <span className="text-[9px] px-1 py-0.5 rounded" style={{ color: statusColor(session.status) }}>
          {session.status}
        </span>
      </div>
      <p className="text-xs truncate" style={{ color: isActive ? '#e8e3dc' : '#8899a6' }}>{session.title}</p>
      <p className="text-[10px] mt-0.5" style={{ color: '#2d4055' }}>{timeAgo(session.updated_at)}</p>
    </div>
  )
}

// ── Chat viewer ───────────────────────────────────────────────────────────────

function ChatViewer({
  detail, adminKey, onInjectSent,
}: {
  detail: SessionDetail | null
  adminKey: string
  onInjectSent: () => void
}) {
  const [inject, setInject] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [detail?.messages])

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
      setInject('')
      onInjectSent()
    } finally {
      setSending(false)
    }
  }

  if (!detail) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: '#2d4055' }}>
        <span className="text-4xl">⚙</span>
        <p className="text-sm">Pilih sesi dari sidebar untuk melihat detail</p>
      </div>
    )
  }

  const { meta, messages, is_live } = detail

  return (
    <div className="flex flex-col h-full">
      {/* Session header */}
      <div className="px-5 py-3 shrink-0" style={{ borderBottom: '1px solid #1a2d47', background: '#0a1422' }}>
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm" style={{ color: '#e8e3dc' }}>{meta.title}</span>
              {is_live && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold animate-pulse"
                  style={{ background: 'rgba(248,113,113,0.15)', color: '#f87171' }}>
                  ● LIVE
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-[11px]" style={{ color: '#4a5c6b' }}>
                {platformIcon(meta.platform)} {meta.platform}
              </span>
              <span className="text-[11px]" style={{ color: '#4a5c6b' }}>lang: {meta.language}</span>
              <span className="text-[11px] font-mono" style={{ color: '#2d4055' }}>
                device: {shortDevice(meta.device_id)}
              </span>
              <span className="text-[11px]" style={{ color: statusColor(meta.status) }}>{meta.status}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-sm mt-8" style={{ color: '#2d4055' }}>Belum ada pesan di sesi ini.</p>
        )}
        {messages.map((msg, i) => {
          const isUser = msg.role === 'user'
          const isScript = msg.msg_type === 'script'
          return (
            <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div
                className="rounded-xl px-4 py-2.5 text-sm max-w-[80%]"
                style={{
                  background: isScript ? '#0d1827' : isUser ? '#1a2d47' : '#111620',
                  border: isScript ? '1px solid #2d3d52' : isUser ? 'none' : '1px solid #1a2d47',
                  color: '#e8e3dc',
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-semibold" style={{ color: isUser ? '#2dd4bf' : '#818cf8' }}>
                    {isUser ? '👤 User' : isScript ? '🎬 Script' : '🤖 Yui'}
                  </span>
                  <span className="text-[10px]" style={{ color: '#2d4055' }}>{timeAgo(msg.created_at)}</span>
                </div>
                <MarkdownContent content={msg.content} className="text-sm leading-relaxed" />
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Inject message (only if live) */}
      {is_live && (
        <div className="shrink-0 px-5 py-3" style={{ borderTop: '1px solid #1a2d47', background: '#0a1422' }}>
          <form onSubmit={handleInject} className="flex gap-2">
            <input
              type="text"
              value={inject}
              onChange={e => setInject(e.target.value)}
              placeholder="Inject pesan ke sesi ini (admin only)..."
              className="flex-1 px-4 py-2 rounded-xl text-sm outline-none"
              style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
              onFocus={e => (e.currentTarget.style.borderColor = '#f87171')}
              onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
            />
            <button
              type="submit"
              disabled={!inject.trim() || sending}
              className="px-4 py-2 rounded-xl text-xs font-semibold shrink-0"
              style={{ background: '#f87171', color: '#080e18', opacity: inject.trim() ? 1 : 0.4 }}
            >
              {sending ? <LoadingDots size="xs" /> : '⚡ Inject'}
            </button>
          </form>
          <p className="text-[10px] mt-1.5 text-center" style={{ color: '#2d4055' }}>
            ⚠ Inject hanya tersedia saat sesi sedang LIVE
          </p>
        </div>
      )}
    </div>
  )
}

// ── Main DevSudoPage ──────────────────────────────────────────────────────────

export default function DevSudoPage() {
  const [adminKey, setAdminKey]       = useState('')
  const [authed, setAuthed]           = useState(false)
  const [sessions, setSessions]       = useState<SessionRow[]>([])
  const [stats, setStats]             = useState<AdminStats | null>(null)
  const [liveIds, setLiveIds]         = useState<string[]>([])
  const [activeId, setActiveId]       = useState<string | null>(null)
  const [detail, setDetail]           = useState<SessionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [filter, setFilter]           = useState<'all' | 'active' | 'completed' | 'live'>('all')
  const [search, setSearch]           = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchSessions = useCallback(async (key: string) => {
    const res = await fetch(`${BASE}/api/admin/sessions?key=${encodeURIComponent(key)}`)
    if (!res.ok) return
    const data = await res.json()
    setSessions(data.sessions ?? [])
    setStats(data.stats ?? null)
    setLiveIds(data.live_session_ids ?? [])
  }, [])

  const handleLogin = useCallback((key: string) => {
    setAdminKey(key)
    setAuthed(true)
    fetchSessions(key)
  }, [fetchSessions])

  // Auto-refresh tiap 15 detik
  useEffect(() => {
    if (!authed) return
    refreshTimer.current = setInterval(() => fetchSessions(adminKey), 15000)
    return () => { if (refreshTimer.current) clearInterval(refreshTimer.current) }
  }, [authed, adminKey, fetchSessions])

  const handleSelectSession = useCallback(async (sessionId: string) => {
    setActiveId(sessionId)
    setLoadingDetail(true)
    try {
      const res = await fetch(`${BASE}/api/admin/session/${sessionId}?key=${encodeURIComponent(adminKey)}`)
      if (res.ok) setDetail(await res.json())
    } finally {
      setLoadingDetail(false)
    }
  }, [adminKey])

  const handleRefreshDetail = useCallback(() => {
    if (activeId) handleSelectSession(activeId)
    fetchSessions(adminKey)
  }, [activeId, adminKey, handleSelectSession, fetchSessions])

  if (!authed) return <LoginScreen onLogin={handleLogin} />

  // Filter + search
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
      <header
        className="flex items-center justify-between px-4 py-2.5 shrink-0"
        style={{ background: '#0a1422', borderBottom: '1px solid #1a2d47' }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(v => !v)}
            className="p-1.5 rounded-lg"
            style={{ color: '#8899a6' }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
          <div
            className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #f87171, #818cf8)' }}
          >⚙</div>
          <span className="font-semibold text-sm" style={{ color: '#e8e3dc' }}>
            arcwright <span style={{ color: '#818cf8' }}>/ dev sudo</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshDetail}
            className="text-xs px-3 py-1.5 rounded-lg border"
            style={{ borderColor: '#1a2d47', color: '#8899a6' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#e8e3dc')}
            onMouseLeave={e => (e.currentTarget.style.color = '#8899a6')}
          >
            ↻ Refresh
          </button>
          <span className="text-[10px] px-2 py-1 rounded-lg" style={{ background: '#0d1827', color: '#2d4055' }}>
            Auto-refresh 15s
          </span>
        </div>
      </header>

      {/* Stats bar */}
      {stats && <StatsBar stats={stats} liveCount={liveIds.length} />}

      {/* Body */}
      <div className="flex flex-1 min-h-0">

        {/* Sidebar */}
        {sidebarOpen && (
          <aside className="flex flex-col w-72 shrink-0 h-full" style={{ background: '#0a1422', borderRight: '1px solid #1a2d47' }}>

            {/* Search + filter */}
            <div className="px-3 py-3 space-y-2 shrink-0" style={{ borderBottom: '1px solid #1a2d47' }}>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Cari judul / device id / platform..."
                className="w-full px-3 py-2 rounded-lg text-xs outline-none"
                style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
              />
              <div className="flex gap-1">
                {(['all', 'live', 'active', 'completed'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className="flex-1 py-1 rounded-lg text-[10px] font-semibold transition-colors"
                    style={{
                      background: filter === f ? '#1a2d47' : 'transparent',
                      color: filter === f ? '#e8e3dc' : '#4a5c6b',
                      border: filter === f ? '1px solid #2d3d52' : '1px solid transparent',
                    }}
                  >
                    {f === 'live' ? '🔴 live' : f}
                  </button>
                ))}
              </div>
              <p className="text-[10px]" style={{ color: '#2d4055' }}>{filtered.length} sesi ditemukan</p>
            </div>

            {/* Session list */}
            <div className="flex-1 overflow-y-auto divide-y" style={{ borderColor: '#0d1520' }}>
              {filtered.map(s => (
                <SessionItem
                  key={s.session_id}
                  session={s}
                  isActive={s.session_id === activeId}
                  isLive={liveIds.includes(s.session_id)}
                  onClick={() => handleSelectSession(s.session_id)}
                />
              ))}
              {filtered.length === 0 && (
                <p className="text-center text-xs py-8" style={{ color: '#2d4055' }}>
                  Belum ada sesi.
                </p>
              )}
            </div>
          </aside>
        )}

        {/* Chat viewer */}
        <main className="flex-1 min-w-0 h-full overflow-hidden">
          {loadingDetail ? (
            <div className="flex items-center justify-center h-full">
              <LoadingDots />
            </div>
          ) : (
            <ChatViewer
              detail={detail}
              adminKey={adminKey}
              onInjectSent={handleRefreshDetail}
            />
          )}
        </main>
      </div>
    </div>
  )
}
