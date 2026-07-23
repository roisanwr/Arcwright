/**
 * DevPage — Developer UI for Arcwright.
 * Route: /dev
 * 
 * Features:
 * - Terdapat Chat Input
 * - Ditambah right panel 4-tab untuk melihat:
 *   ⚙️ Proses log, 🧠 Internal Thought, 📚 Dari Buku, 📄 Skrip
 * - Connects to current active session SSE
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useArcwright } from '../hooks/useArcwright'
import { useHistory } from '../hooks/useHistory'
import { MarkdownContent, LoadingDots } from '../components/shared'

const BASE = import.meta.env.VITE_API_BASE ?? ''

// ── Types for SSE Events ──────────────────────────────────────────────────────

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

function nowTs() {
  const n = new Date()
  return `${String(n.getHours()).padStart(2,'0')}:${String(n.getMinutes()).padStart(2,'0')}:${String(n.getSeconds()).padStart(2,'0')}`
}

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

// ── Sidebar Item ──────────────────────────────────────────────────────────────
interface SessionRow {
  sessionId: string;
  title: string;
  language?: string;
}

function Sidebar({ sessions, activeId, onSelect, onDelete, onNew }: {
  sessions: SessionRow[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}) {
  return (
    <aside className="w-64 h-full flex flex-col shrink-0" style={{ background: '#0a1422', borderRight: '1px solid #1a2d47' }}>
      <div className="px-4 py-4 shrink-0" style={{ borderBottom: '1px solid #1a2d47' }}>
        <h1 className="font-bold text-sm" style={{ color: '#e8e3dc' }}>Arcwright / Dev</h1>
      </div>
      <div className="p-3 shrink-0">
        <button onClick={onNew} className="w-full flex justify-center py-2 rounded-lg font-medium text-xs transition-colors"
          style={{ background: '#121e30', border: '1px solid #1a2d47', color: '#e8e3dc' }}>
          + Sesi Baru
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
        {sessions.map(s => (
          <div key={s.sessionId} className="group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-xs transition-colors"
            style={{ background: s.sessionId === activeId ? '#1a2d47' : 'transparent', color: s.sessionId === activeId ? '#e8e3dc' : '#8899a6' }}
            onClick={() => onSelect(s.sessionId)}>
            <span className="truncate flex-1">{s.title || 'Sesi Tanpa Nama'}</span>
            <button onClick={(e) => { e.stopPropagation(); onDelete(s.sessionId); }}
              className="opacity-0 group-hover:opacity-100 ml-2 hover:text-red-400">✕</button>
          </div>
        ))}
      </div>
    </aside>
  )
}


// ── Dev Right Panel Components ────────────────────────────────────────────────

function ProcessLog({ events }: { events: ProcessEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events])
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-1.5 text-xs font-mono">
      {events.length === 0 && (
        <p className="text-center mt-8" style={{ color: '#2d4055' }}>Pipeline belum berjalan.</p>
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

function ReasoningPanel({ reasonings }: { reasonings: ReasoningEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [reasonings])
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {reasonings.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
          <span className="text-3xl opacity-20">🧠</span>
          <p className="text-xs" style={{ color: '#2d4055' }}>Belum ada thought process.</p>
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

function RagPanel({ citations }: { citations: RagCitation[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [citations])
  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {citations.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
          <span className="text-3xl opacity-20">📚</span>
          <p className="text-xs" style={{ color: '#2d4055' }}>Kutipan dari buku akan muncul di sini.</p>
        </div>
      ) : citations.map((c, i) => (
        <div key={i} className="rounded-lg p-3 space-y-2" style={{ background: '#080e18', border: '1px solid #1a2d47' }}>
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
          {c.content && (
            <p className="text-xs leading-relaxed italic" style={{ color: '#c4cdd6', borderLeft: '2px solid #1a2d47', paddingLeft: '8px' }}>
              "{c.content}"
            </p>
          )}
          {c.relevance && (
            <p className="text-[10px]" style={{ color: '#2dd4bf' }}>↳ {c.relevance}</p>
          )}
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

function ScriptPanel({ script }: { script: ScriptEvent | null }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    if (!script?.body) return
    navigator.clipboard.writeText(script.body).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }
  if (!script) return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
      <span className="text-3xl opacity-20">📄</span>
      <p className="text-xs" style={{ color: '#2d4055' }}>Skrip belum tersedia.</p>
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


// ── Onboarding steps ──────────────────────────────────────────────────────────

type OnboardStep = 'lang' | 'name' | 'platform'

const PLATFORMS = [
  { id: 'youtube',  label: 'YouTube',  icon: '▶', sub: 'Video naratif' },
  { id: 'tiktok',  label: 'TikTok',   icon: '♪', sub: 'Short-form' },
  { id: 'podcast', label: 'Podcast',  icon: '🎙', sub: 'Audio storytelling' },
  { id: 'blog',    label: 'Blog',     icon: '✍', sub: 'Tulisan panjang' },
  { id: 'general', label: 'General',  icon: '✦', sub: 'Bebas format' },
]

interface OnboardingProps {
  onComplete: (name: string, lang: 'id'|'en', platform: string) => void
}

function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState<OnboardStep>('lang')
  const [lang, setLang] = useState('')
  const [name, setName] = useState('')
  const [_platform, setPlatform] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)
  const isId = lang === 'id'

  useEffect(() => {
    if (step === 'name') nameRef.current?.focus()
  }, [step])

  const handleLang = (l: string) => { setLang(l); setStep('name') }
  const handleName = (e: React.FormEvent) => {
    e.preventDefault()
    setStep('platform')
  }
  const handlePlatform = (p: string) => {
    setPlatform(p)
    const finalName = name.trim() || (lang === 'id' ? 'Kamu' : 'You')
    onComplete(finalName, lang as 'id'|'en', p)
  }

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
      <div className="w-full max-w-sm space-y-6">

        {/* Avatar */}
        <div className="flex flex-col items-center gap-3 mb-2">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold"
            style={{
              background: 'linear-gradient(135deg, #f87171 0%, #818cf8 100%)',
              boxShadow: '0 0 32px rgba(248,113,113,0.2)',
            }}
          >
            DEV
          </div>
          <div className="text-center">
            <h2 className="font-bold text-lg" style={{ color: '#e8e3dc' }}>Arcwright Developer Mode</h2>
            <p className="text-xs mt-1" style={{ color: '#8899a6' }}>
              Setup your dev session
            </p>
          </div>
        </div>

        {/* Step: Language */}
        {step === 'lang' && (
          <div className="space-y-3 anim-fade-up">
            <p className="text-sm text-center" style={{ color: '#8899a6' }}>
              Which language do you prefer?
            </p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: 'id', flag: '🇮🇩', label: 'Bahasa Indonesia', sub: 'Ngobrol pake Indo' },
                { id: 'en', flag: '🇬🇧', label: 'English',          sub: "Let's talk in English" },
              ].map(l => (
                <button
                  key={l.id}
                  onClick={() => handleLang(l.id)}
                  className="flex flex-col items-center gap-1.5 py-4 px-3 rounded-xl border transition-all duration-150"
                  style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = '#f87171'
                    e.currentTarget.style.background  = '#111620'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#1a2d47'
                    e.currentTarget.style.background  = '#0d1520'
                  }}
                >
                  <span className="text-2xl">{l.flag}</span>
                  <span className="font-semibold text-sm">{l.label}</span>
                  <span className="text-[10px]" style={{ color: '#8899a6' }}>{l.sub}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step: Name */}
        {step === 'name' && (
          <form onSubmit={handleName} className="space-y-4 anim-fade-up">
            <p className="text-sm" style={{ color: '#8899a6' }}>
              {isId ? 'Siapa namamu?' : "What's your name?"}
            </p>
            <input
              ref={nameRef}
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={isId ? 'Nama panggilanmu...' : 'Your name...'}
              className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all"
              style={{
                background:  '#0d1520',
                border:      '1px solid #1a2d47',
                color:       '#e8e3dc',
              }}
              onFocus={e => (e.currentTarget.style.borderColor = '#f87171')}
              onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
            />
            <button
              type="submit"
              className="w-full py-3 rounded-xl font-semibold text-sm transition-colors"
              style={{ background: '#f87171', color: '#080e18' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#fca5a5')}
              onMouseLeave={e => (e.currentTarget.style.background = '#f87171')}
            >
              {isId ? 'Lanjut ✦' : 'Continue ✦'}
            </button>
            <button
              type="button"
              onClick={() => setStep('lang')}
              className="w-full text-xs py-1 transition-colors"
              style={{ color: '#4a5c6b' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#8899a6')}
              onMouseLeave={e => (e.currentTarget.style.color = '#4a5c6b')}
            >
              ← {isId ? 'Ganti bahasa' : 'Change language'}
            </button>
          </form>
        )}

        {/* Step: Platform */}
        {step === 'platform' && (
          <div className="space-y-3 anim-fade-up">
            <p className="text-sm" style={{ color: '#8899a6' }}>
              {isId ? 'Mau bikin konten di mana?' : 'Where will you publish?'}
            </p>
            <div className="grid grid-cols-1 gap-2">
              {PLATFORMS.map(p => (
                <button
                  key={p.id}
                  onClick={() => handlePlatform(p.id)}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left"
                  style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = '#f87171'
                    e.currentTarget.style.background  = '#111620'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#1a2d47'
                    e.currentTarget.style.background  = '#0d1520'
                  }}
                >
                  <span className="text-lg w-6 text-center shrink-0" style={{ color: '#f87171' }}>{p.icon}</span>
                  <div>
                    <div className="font-semibold text-sm">{p.label}</div>
                    <div className="text-[10px]" style={{ color: '#8899a6' }}>{p.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Page Component ───────────────────────────────────────────────────────


export default function DevPage() {
  const arc = useArcwright()
  const { sessions, addSession, updateSession, removeSession } = useHistory()
  
  const [hasStarted, setHasStarted] = useState(false)
  const [lang, setLang] = useState<'id'|'en'>('id')
  const [userName, setUserName] = useState('')
  
  const [input, setInput] = useState('')
  
  // Right panel states
  const [rightTab, setRightTab] = useState<'log'|'reasoning'|'rag'|'script'>('log')
  const [processLog, setProcessLog] = useState<ProcessEvent[]>([])
  const [reasonings, setReasonings] = useState<ReasoningEvent[]>([])
  const [liveScript, setLiveScript] = useState<ScriptEvent | null>(null)
  const [ragCitations, setRagCitations] = useState<RagCitation[]>([])
  
  const chatBottomRef = useRef<HTMLDivElement>(null)
  const esRef = useRef<EventSource | null>(null)

  // ── Auto-scroll chat ──
  useEffect(() => { chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [arc.messages])

  // ── Setup SSE untuk current active session ──
  useEffect(() => {
    if (!arc.sessionId) return
    
    // Cleanup previous connection
    if (esRef.current) { esRef.current.close(); esRef.current = null }
    
    // Connect SSE using device_id as "key" to bypass admin key
    const deviceId = localStorage.getItem('arc_device_id') || ''
    const es = new EventSource(`${BASE}/api/stream/${arc.sessionId}?device_id=${deviceId}`)
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

    return () => { esRef.current?.close() }
  }, [arc.sessionId])

  // ── Init session ──
  const handleCompleteSetup = useCallback(async (name: string, pLang: 'id'|'en', platform: string) => {
    setLang(pLang); setUserName(name);
    setHasStarted(true)
    setProcessLog([]); setReasonings([]); setLiveScript(null); setRagCitations([])
    try {
      const newSession = await arc.start({ userName: name, language: pLang, platform })
      addSession({ ...newSession, title: `${name} · ${platform}` })
    } catch (err) { console.error(err) }
  }, [arc, addSession])

  const handleSend = useCallback(async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const text = input.trim()
    if (!text || arc.isProcessing || !arc.sessionId) return
    
    setInput('')
    // Update title kalau baru pertama kali ngobrol
    if (arc.messages.filter(m => m.role === 'user').length === 0 && arc.sessionId) {
      const newTitle = text.slice(0, 50) + (text.length > 50 ? '…' : '')
      updateSession(arc.sessionId, { title: newTitle })
    }
    
    try {
      await arc.send(text)
    } catch (err) { console.error(err) }
  }, [input, arc, updateSession])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleSelectHistory = useCallback(async (sessionId: string) => {
    const sessionInfo = sessions.find((s: SessionRow) => s.sessionId === sessionId)
    if (sessionInfo) {
      setHasStarted(true)
      arc.reconnect(sessionId)
      
      // Clear panel
      setProcessLog([]); setReasonings([]); setLiveScript(null); setRagCitations([])
      setRightTab('log')
      
      try {
        const res = await fetch(`${BASE}/api/history/${sessionId}?device_id=${localStorage.getItem('arc_device_id')}`)
        if (res.ok) {
          const raw = await res.json()
          const msgs = raw.filter((m: any) => m.msg_type === 'chat' && m.content?.trim()).map((m: any, i: number) => ({
            id: `hist-${sessionId}-${i}`,
            role: m.role,
            content: m.content,
            kind: 'text',
            timestamp: new Date(m.created_at).getTime()
          }))
          if (msgs.length > 0) arc.loadMessages(msgs)
          
          // Cek kalau ada script
          const scriptMsg = raw.findLast((m: any) => m.msg_type === 'script')
          if (scriptMsg) {
            const match = scriptMsg.content.match(/\[SCRIPT:(.+?)\]\n([\s\S]+)/)
            if (match) setLiveScript({ title: match[1], body: match[2] })
          }
        }
      } catch (err) { console.error('Failed to load history', err) }
    }
  }, [sessions, arc])

  const handleNewSession = useCallback(() => {
    arc.reset()
    setHasStarted(false)
    setInput('')
    setProcessLog([]); setReasonings([]); setLiveScript(null); setRagCitations([])
  }, [arc])

  // Jika belum set platform dll, tampilkan Onboarding (sama seperti /chat)
  if (!hasStarted) {
    return (
      <div className="flex h-screen overflow-hidden" style={{ background: '#080e18' }}>
        <Sidebar 
          sessions={sessions as SessionRow[]} 
          activeId={arc.sessionId} 
          onSelect={handleSelectHistory}
          onDelete={removeSession}
          onNew={handleNewSession}
        />
        <div className="flex-1 overflow-y-auto">
          <Onboarding onComplete={handleCompleteSetup} />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#080e18' }}>
      <Sidebar 
        sessions={sessions as SessionRow[]} 
        activeId={arc.sessionId} 
        onSelect={handleSelectHistory}
        onDelete={removeSession}
        onNew={handleNewSession}
      />

      {/* Kolom Tengah (Chat) */}
      <div className="flex flex-col flex-1 min-w-0 h-full border-r border-[#1a2d47]">
        {/* Header chat */}
        <header className="flex items-center justify-between px-4 py-3 shrink-0"
                style={{ borderBottom: '1px solid #1a2d47', background: '#0a1422' }}>
          <div className="flex items-center gap-3">
            <span className="font-semibold text-sm" style={{ color: '#e8e3dc' }}>Dev Sesi {userName}</span>
          </div>
        </header>

        {/* Chat area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {arc.messages.map(m => (
            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className="rounded-xl px-4 py-2.5 text-sm max-w-[85%]"
                   style={{
                     background: m.role === 'user' ? '#1a2d47' : '#111620',
                     border: `1px solid ${m.role === 'user' ? '#1a2d47' : '#1a2d47'}`,
                     color: '#e8e3dc',
                   }}>
                <MarkdownContent content={m.content} className="text-sm leading-relaxed" />
              </div>
            </div>
          ))}
          {arc.isProcessing && (
            <div className="flex justify-start">
              <div className="rounded-xl px-4 py-3 text-sm" style={{ background: '#111620', border: '1px solid #1a2d47' }}>
                <LoadingDots />
              </div>
            </div>
          )}
          {arc.error && (
            <div className="mx-auto max-w-md text-center rounded-xl px-4 py-3 text-sm"
                 style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}>
              ⚠ {arc.error}
            </div>
          )}
          <div ref={chatBottomRef} />
        </div>

        {/* Input area */}
        <div className="shrink-0 px-4 py-3" style={{ borderTop: '1px solid #1a2d47', background: '#0a1422' }}>
          <form onSubmit={handleSend} className="flex gap-2 items-end">
            <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
              rows={1}
              disabled={arc.isProcessing || arc.connectionState === 'disconnected'}
              placeholder={lang === 'id' ? 'Ketik pesanmu...' : 'Type your message...'}
              className="flex-1 rounded-xl px-4 py-2.5 text-sm resize-none outline-none transition-all"
              style={{ background: '#0d1520', border: '1px solid #1a2d47', color: '#e8e3dc', minHeight: '44px', maxHeight: '120px' }}
              onFocus={e => (e.currentTarget.style.borderColor = '#f87171')}
              onBlur={e => (e.currentTarget.style.borderColor = '#1a2d47')}
            />
            <button type="submit" disabled={arc.isProcessing || !input.trim() || arc.connectionState === 'disconnected'}
              className="flex items-center justify-center w-11 h-11 rounded-xl font-medium text-sm transition-all shrink-0"
              style={{ background: '#f87171', color: '#080e18' }}>
              {arc.isProcessing ? <LoadingDots size="xs" /> : '►'}
            </button>
          </form>
        </div>
      </div>

      {/* Kolom Kanan (Dev Panel) */}
      <div className="flex flex-col w-80 shrink-0 h-full" style={{ background: '#090f1c' }}>
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
                borderBottom: rightTab===tab ? '2px solid #f87171' : '2px solid transparent',
              }}>
              {label}
              {tab==='script' && liveScript && (
                <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full align-middle" style={{ background: '#2dd4bf' }} />
              )}
              {tab==='reasoning' && reasonings.length > 0 && (
                <span className="ml-1 text-[9px] px-1 rounded" style={{ background: '#1a2d47', color: '#f87171' }}>
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
        <div className="flex-1 min-h-0 flex flex-col">
          {rightTab === 'log'       && <ProcessLog events={processLog} />}
          {rightTab === 'reasoning' && <ReasoningPanel reasonings={reasonings} />}
          {rightTab === 'rag'       && <RagPanel citations={ragCitations} />}
          {rightTab === 'script'    && <ScriptPanel script={liveScript} />}
        </div>
      </div>
    </div>
  )
}
