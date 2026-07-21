import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useArcwright } from '../hooks/useArcwright'
import { useHistory } from '../hooks/useHistory'
import { LoadingDots, StatusBadge, MarkdownContent } from '../components/shared'
import type { UIMessage, OutlineEvent, ScriptEvent } from '../types'

// ── Onboarding steps ──────────────────────────────────────────────────────────

type OnboardStep = 'lang' | 'name' | 'platform'

const PLATFORMS = [
  { id: 'youtube',  label: 'YouTube',  icon: '▶', sub: 'Video naratif' },
  { id: 'tiktok',  label: 'TikTok',   icon: '♪', sub: 'Short-form' },
  { id: 'podcast', label: 'Podcast',  icon: '🎙', sub: 'Audio storytelling' },
  { id: 'blog',    label: 'Blog',     icon: '✍', sub: 'Tulisan panjang' },
  { id: 'general', label: 'General',  icon: '✦', sub: 'Bebas format' },
]

// ── Chat bubbles ──────────────────────────────────────────────────────────────

function OutlineCard({ outline, onDecision, lang }: {
  outline: OutlineEvent
  onDecision: (d: 'approve' | 'revise' | 'reject') => void
  lang: string
}) {
  const rows = Object.entries(outline).filter(([, v]) => v?.trim())
  return (
    <div
      className="rounded-xl border p-4 text-sm space-y-3 max-w-xl w-full"
      style={{ background: '#111620', borderColor: '#1e3a5f' }}
    >
      <div className="flex items-center gap-2 pb-2" style={{ borderBottom: '1px solid #1a2d47' }}>
        <span style={{ color: '#2dd4bf' }}>✦</span>
        <span className="font-semibold text-xs uppercase tracking-wider" style={{ color: '#2dd4bf' }}>
          Story Outline
        </span>
      </div>
      <dl className="space-y-2">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs font-semibold capitalize mb-0.5" style={{ color: '#8899a6' }}>{k.replace(/_/g, ' ')}</dt>
            <dd style={{ color: '#e8e3dc' }}>{v}</dd>
          </div>
        ))}
      </dl>
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onDecision('approve')}
          className="flex-1 py-2 rounded-lg text-xs font-semibold transition-colors"
          style={{ background: '#2dd4bf', color: '#080e18' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#5eead4')}
          onMouseLeave={e => (e.currentTarget.style.background = '#2dd4bf')}
        >
          {lang === 'id' ? '✓ Setuju' : '✓ Approve'}
        </button>
        <button
          onClick={() => onDecision('revise')}
          className="flex-1 py-2 rounded-lg text-xs font-semibold border transition-colors"
          style={{ borderColor: '#1e3a5f', color: '#8899a6', background: 'transparent' }}
          onMouseEnter={e => { e.currentTarget.style.background = '#121e30'; e.currentTarget.style.color = '#e8e3dc' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#8899a6' }}
        >
          {lang === 'id' ? '↺ Revisi' : '↺ Revise'}
        </button>
        <button
          onClick={() => onDecision('reject')}
          className="flex-1 py-2 rounded-lg text-xs font-semibold border transition-colors"
          style={{ borderColor: '#2d1a1a', color: '#f87171', background: 'transparent' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#1a0d0d')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          {lang === 'id' ? '✕ Tolak' : '✕ Reject'}
        </button>
      </div>
    </div>
  )
}

function ScriptCard({ script }: { script: ScriptEvent }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    if (!script.body) return
    navigator.clipboard.writeText(script.body).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <div
      className="rounded-xl border p-4 text-sm space-y-3 max-w-xl w-full"
      style={{ background: '#111620', borderColor: '#2d3d52' }}
    >
      <div className="flex items-center justify-between pb-2" style={{ borderBottom: '1px solid #1a2d47' }}>
        <div className="flex items-center gap-2">
          <span style={{ color: '#818cf8' }}>🎬</span>
          <span className="font-semibold text-xs uppercase tracking-wider" style={{ color: '#818cf8' }}>
            {script.title ?? 'Script'}
          </span>
          {script.platform_variant && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full font-medium"
              style={{ background: '#1e1a3f', color: '#818cf8', border: '1px solid #2d2a5e' }}
            >
              {script.platform_variant}
            </span>
          )}
        </div>
        <button
          onClick={copy}
          className="text-[10px] px-2 py-1 rounded-lg border transition-colors"
          style={{ borderColor: '#1e3a5f', color: copied ? '#2dd4bf' : '#8899a6', background: 'transparent' }}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      {script.body && (
        <div className="max-h-96 overflow-y-auto pr-1">
          <MarkdownContent content={script.body} className="text-sm leading-relaxed" style={{ color: '#e8e3dc' }} />
        </div>
      )}
      {script.voice_notes && (
        <div className="pt-2 text-xs" style={{ color: '#8899a6', borderTop: '1px solid #1a2d47' }}>
          <span className="font-semibold">Voice notes: </span>{script.voice_notes}
        </div>
      )}
    </div>
  )
}

function ChatBubble({ msg, lang, onDecision }: {
  msg: UIMessage
  lang: string
  onDecision: (d: 'approve' | 'revise' | 'reject') => void
}) {
  const isUser = msg.role === 'user'

  if (msg.kind === 'outline' && msg.outline) {
    return (
      <div className="flex justify-start anim-slide-left">
        <div className="flex gap-3 max-w-[88%] md:max-w-[75%] items-start">
          <YuiAvatar />
          <OutlineCard outline={msg.outline} onDecision={onDecision} lang={lang} />
        </div>
      </div>
    )
  }

  if (msg.kind === 'script' && msg.script) {
    return (
      <div className="flex justify-start anim-slide-left">
        <div className="flex gap-3 max-w-[88%] md:max-w-[75%] items-start">
          <YuiAvatar />
          <ScriptCard script={msg.script} />
        </div>
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end anim-slide-right' : 'justify-start anim-slide-left'}`}>
      {!isUser && (
        <div className="flex gap-3 items-end max-w-[88%] md:max-w-[72%]">
          <YuiAvatar />
          <div
            className="rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed"
            style={{ background: '#111620', border: '1px solid #1a2d47', color: '#e8e3dc' }}
          >
            <MarkdownContent content={msg.content} />
          </div>
        </div>
      )}
      {isUser && (
        <div
          className="rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed max-w-[88%] md:max-w-[72%]"
          style={{ background: '#1a2d47', color: '#e8e3dc' }}
        >
          {msg.content}
        </div>
      )}
    </div>
  )
}

function YuiAvatar() {
  return (
    <div
      className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mb-0.5 text-xs font-bold"
      style={{ background: 'linear-gradient(135deg, #2dd4bf, #818cf8)' }}
    >
      Y
    </div>
  )
}

// ── Typing indicator ──────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex justify-start anim-fade-in">
      <div className="flex gap-3 items-end">
        <YuiAvatar />
        <div
          className="rounded-2xl rounded-bl-sm px-4 py-3"
          style={{ background: '#111620', border: '1px solid #1a2d47' }}
        >
          <LoadingDots size="sm" />
        </div>
      </div>
    </div>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

interface SidebarProps {
  sessions: import('../types').SessionMeta[]
  activeId: string | null
  onSelect: (sessionId: string) => void
  onDelete: (sessionId: string) => void
  onNew: () => void
  lang: string
  isOpen: boolean
  onClose: () => void
}

function Sidebar({ sessions, activeId, onSelect, onDelete, onNew, lang, isOpen, onClose }: SidebarProps) {
  const navigate = useNavigate()

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 md:hidden"
          style={{ background: 'rgba(0,0,0,0.6)' }}
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed md:relative z-30 md:z-auto
          flex flex-col h-full
          w-64 shrink-0
          transition-transform duration-300
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
        style={{ background: '#0a1422', borderRight: '1px solid #1a2d47' }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-3 px-4 py-4 shrink-0 cursor-pointer"
          style={{ borderBottom: '1px solid #1a2d47' }}
          onClick={() => navigate('/')}
        >
          <img
            src="/logo-mark.png"
            alt="Arcwright"
            className="w-6 h-6 object-contain shrink-0"
            style={{ filter: 'brightness(0) invert(1) opacity(0.9)' }}
          />
          <span className="font-semibold text-sm tracking-wide" style={{ color: '#e8e3dc' }}>
            arcwright
          </span>
        </div>

        {/* New chat button */}
        <div className="px-3 py-3 shrink-0">
          <button
            onClick={onNew}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
            style={{ background: '#121e30', border: '1px solid #1a2d47', color: '#8899a6' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1a2d47'; e.currentTarget.style.color = '#e8e3dc' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#121e30'; e.currentTarget.style.color = '#8899a6' }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            {lang === 'id' ? 'Chat baru' : 'New chat'}
          </button>
        </div>

        {/* History list */}
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {sessions.length === 0 ? (
            <p className="text-center text-xs px-3 mt-8" style={{ color: '#2d4055' }}>
              {lang === 'id' ? 'Belum ada riwayat.' : 'No history yet.'}
            </p>
          ) : (
            <div className="space-y-0.5">
              {sessions.map(s => (
                <div
                  key={s.sessionId}
                  className="group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors"
                  style={{
                    background: s.sessionId === activeId ? '#1a2d47' : 'transparent',
                    color:      s.sessionId === activeId ? '#e8e3dc' : '#8899a6',
                  }}
                  onClick={() => { onSelect(s.sessionId); onClose() }}
                  onMouseEnter={e => {
                    if (s.sessionId !== activeId) {
                      (e.currentTarget as HTMLDivElement).style.background = '#121e30'
                      ;(e.currentTarget as HTMLDivElement).style.color = '#c4cdd6'
                    }
                  }}
                  onMouseLeave={e => {
                    if (s.sessionId !== activeId) {
                      (e.currentTarget as HTMLDivElement).style.background = 'transparent'
                      ;(e.currentTarget as HTMLDivElement).style.color = '#8899a6'
                    }
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="shrink-0 opacity-50">
                    <path d="M1 10V3a1 1 0 011-1h8a1 1 0 011 1v4.5a1 1 0 01-1 1H4L1 10z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
                  </svg>
                  <span className="text-xs truncate flex-1 leading-tight">{s.title}</span>
                  <button
                    onClick={e => { e.stopPropagation(); onDelete(s.sessionId) }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 rounded transition-opacity text-xs shrink-0"
                    style={{ color: '#4a5c6b' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#f87171')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#4a5c6b')}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom brand */}
        <div
          className="px-4 py-3 shrink-0 text-xs"
          style={{ borderTop: '1px solid #1a2d47', color: '#2d4055' }}
        >
          Powered by 8 AI agents
        </div>
      </aside>
    </>
  )
}

// ── Onboarding ────────────────────────────────────────────────────────────────

interface OnboardingProps {
  onComplete: (name: string, lang: string, platform: string) => void
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
    onComplete(finalName, lang, p)
  }

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
      <div className="w-full max-w-sm space-y-6">

        {/* Avatar */}
        <div className="flex flex-col items-center gap-3 mb-2">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold"
            style={{
              background: 'linear-gradient(135deg, #2dd4bf 0%, #818cf8 100%)',
              boxShadow: '0 0 32px rgba(45,212,191,0.2)',
            }}
          >
            Y
          </div>
          <div className="text-center">
            <h2 className="font-bold text-lg" style={{ color: '#e8e3dc' }}>Halo! Aku Yui.</h2>
            <p className="text-xs mt-1" style={{ color: '#8899a6' }}>
              AI Storytelling Coach · powered by Arcwright
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
                    e.currentTarget.style.borderColor = '#2dd4bf'
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
              onFocus={e => (e.currentTarget.style.borderColor = '#2dd4bf')}
              onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
            />
            <button
              type="submit"
              className="w-full py-3 rounded-xl font-semibold text-sm transition-colors"
              style={{ background: '#2dd4bf', color: '#080e18' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#5eead4')}
              onMouseLeave={e => (e.currentTarget.style.background = '#2dd4bf')}
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
                    e.currentTarget.style.borderColor = '#2dd4bf'
                    e.currentTarget.style.background  = '#111620'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#1a2d47'
                    e.currentTarget.style.background  = '#0d1520'
                  }}
                >
                  <span className="text-lg w-6 text-center shrink-0" style={{ color: '#2dd4bf' }}>{p.icon}</span>
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

// ── Main ChatPage ─────────────────────────────────────────────────────────────

export default function ChatPage() {
  const arcwright = useArcwright()
  const { sessions, addSession, updateSession, removeSession } = useHistory()
  const [onboarded, setOnboarded] = useState(false)
  const [lang, setLang] = useState('id')
  const [userName, setUserName] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [inputValue, setInputValue] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(scrollToBottom, [arcwright.messages, scrollToBottom])

  // ── Onboarding complete ───────────────────────────────────────────────────

  const handleOnboardComplete = useCallback(async (name: string, l: string, platform: string) => {
    setLang(l)
    setUserName(name)
    setOnboarded(true)
    try {
      const meta = await arcwright.start({ userName: name, language: l, platform })
      addSession({ ...meta, title: `${name} · ${platform}` })
    } catch (err) {
      console.error(err)
    }
  }, [arcwright, addSession])

  // ── Send message ──────────────────────────────────────────────────────────

  const handleSend = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    const text = inputValue.trim()
    if (!text || arcwright.isProcessing || !arcwright.sessionId) return
    setInputValue('')

    // Update session title on first user message
    if (arcwright.messages.filter(m => m.role === 'user').length === 0 && arcwright.sessionId) {
      const title = text.slice(0, 50) + (text.length > 50 ? '…' : '')
      updateSession(arcwright.sessionId, { title })
    }

    try {
      await arcwright.send(text)
    } catch (err) {
      console.error(err)
    }
  }, [inputValue, arcwright, updateSession])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e as unknown as React.FormEvent)
    }
  }

  // ── Outline approval ──────────────────────────────────────────────────────

  const handleDecision = useCallback(async (d: 'approve' | 'revise' | 'reject') => {
    if (!arcwright.sessionId) return
    setInputValue('')
    try {
      await arcwright.send(d)
    } catch (err) {
      console.error(err)
    }
  }, [arcwright])

  // ── Resume old session ────────────────────────────────────────────────────

  const handleSelectSession = useCallback((sessionId: string) => {
    const meta = sessions.find(s => s.sessionId === sessionId)
    if (!meta) return
    setLang(meta.language)
    setOnboarded(true)
    arcwright.reconnect(sessionId)
  }, [sessions, arcwright])

  // ── New chat ──────────────────────────────────────────────────────────────

  const handleNewChat = useCallback(() => {
    arcwright.reset()
    setOnboarded(false)
    setInputValue('')
    setSidebarOpen(false)
  }, [arcwright])

  const isId = lang === 'id'

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#080e18' }}>

      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeId={arcwright.sessionId}
        onSelect={handleSelectSession}
        onDelete={removeSession}
        onNew={handleNewChat}
        lang={lang}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0 h-full">

        {/* Header */}
        <header
          className="flex items-center justify-between px-4 py-3 shrink-0"
          style={{ borderBottom: '1px solid #1a2d47', background: '#0a1422' }}
        >
          <div className="flex items-center gap-3">
            {/* Mobile sidebar toggle */}
            <button
              className="md:hidden p-1.5 rounded-lg transition-colors"
              style={{ color: '#8899a6' }}
              onClick={() => setSidebarOpen(v => !v)}
              onMouseEnter={e => (e.currentTarget.style.background = '#121e30')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>

            {/* Logo — hidden on md (shown in sidebar) */}
            <div className="flex items-center gap-2 md:hidden">
              <img
                src="/logo-mark.png"
                alt="Arcwright"
                className="w-5 h-5 object-contain"
                style={{ filter: 'brightness(0) invert(1) opacity(0.85)' }}
              />
              <span className="font-semibold text-sm" style={{ color: '#e8e3dc' }}>arcwright</span>
            </div>

            {/* Desktop title */}
            {onboarded && (
              <span className="hidden md:block text-sm font-medium" style={{ color: '#e8e3dc' }}>
                {isId ? `Sesi ${userName}` : `${userName}'s session`}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {onboarded && (
              <StatusBadge node={arcwright.currentNode} isProcessing={arcwright.isProcessing} />
            )}
          </div>
        </header>

        {/* Content */}
        {!onboarded ? (
          <Onboarding onComplete={handleOnboardComplete} />
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">

              {/* Empty state while connecting */}
              {arcwright.messages.length === 0 && arcwright.isProcessing && (
                <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold"
                    style={{ background: 'linear-gradient(135deg, #2dd4bf, #818cf8)' }}
                  >
                    Y
                  </div>
                  <div>
                    <p className="text-sm font-medium" style={{ color: '#e8e3dc' }}>
                      {isId ? `Hei ${userName}!` : `Hey ${userName}!`}
                    </p>
                    <p className="text-xs mt-1" style={{ color: '#8899a6' }}>
                      {isId ? 'Menghubungkan semua agen AI...' : 'Connecting all AI agents...'}
                    </p>
                  </div>
                  <LoadingDots />
                </div>
              )}

              {/* Chat messages */}
              {arcwright.messages.map(msg => (
                <ChatBubble
                  key={msg.id}
                  msg={msg}
                  lang={lang}
                  onDecision={handleDecision}
                />
              ))}

              {/* Typing indicator */}
              {arcwright.isProcessing && arcwright.messages.length > 0 && (
                <TypingIndicator />
              )}

              {/* Error */}
              {arcwright.error && (
                <div
                  className="mx-auto max-w-md text-center rounded-xl px-4 py-3 text-sm"
                  style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}
                >
                  ⚠ {arcwright.error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div
              className="shrink-0 px-4 py-3"
              style={{ borderTop: '1px solid #1a2d47', background: '#0a1422' }}
            >
              <form onSubmit={handleSend} className="flex gap-2 items-end">
                <textarea
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  disabled={arcwright.isProcessing || arcwright.connectionState === 'disconnected'}
                  placeholder={
                    arcwright.isProcessing
                      ? (isId ? 'Yui sedang berpikir...' : 'Yui is thinking...')
                      : arcwright.connectionState === 'disconnected'
                        ? (isId ? 'Koneksi terputus...' : 'Connection lost...')
                        : (isId ? 'Ketik pesanmu... (Enter untuk kirim)' : 'Type your message... (Enter to send)')
                  }
                  className="flex-1 rounded-xl px-4 py-2.5 text-sm resize-none outline-none transition-all"
                  style={{
                    background:   '#0d1520',
                    border:       '1px solid #1a2d47',
                    color:        '#e8e3dc',
                    minHeight:    '44px',
                    maxHeight:    '120px',
                    lineHeight:   '1.5',
                  }}
                  onFocus={e => (e.currentTarget.style.borderColor = '#2dd4bf')}
                  onBlur={e  => (e.currentTarget.style.borderColor = '#1a2d47')}
                />
                <button
                  type="submit"
                  disabled={arcwright.isProcessing || !inputValue.trim() || arcwright.connectionState === 'disconnected'}
                  className="flex items-center justify-center w-11 h-11 rounded-xl font-medium text-sm transition-all shrink-0"
                  style={{ background: '#2dd4bf', color: '#080e18' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#5eead4')}
                  onMouseLeave={e => (e.currentTarget.style.background = '#2dd4bf')}
                >
                  {arcwright.isProcessing
                    ? <LoadingDots size="xs" />
                    : (
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M14 8H2M9 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )
                  }
                </button>
              </form>

              {/* Connection lost warning */}
              {arcwright.connectionState === 'disconnected' && (
                <p className="text-xs text-center mt-2" style={{ color: '#f87171' }}>
                  {isId ? 'Koneksi ke server terputus.' : 'Connection to server lost.'}
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
