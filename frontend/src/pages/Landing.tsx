import { useNavigate } from 'react-router-dom'

// ── Dot grid SVG background ────────────────────────────────────────────────────
function DotGrid() {
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none select-none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <pattern id="dots" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">
          <circle cx="1.5" cy="1.5" r="1.5" fill="#1C1917" fillOpacity="0.07" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots)" />
    </svg>
  )
}

// ── Story nodes illustration (SVG, flat) ──────────────────────────────────────
function StoryGraph() {
  return (
    <svg
      viewBox="0 0 480 320"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full max-w-lg"
      aria-hidden="true"
    >
      {/* Edges */}
      <line x1="80"  y1="160" x2="200" y2="90"  stroke="#4F46E5" strokeWidth="1.5" strokeOpacity="0.25" strokeDasharray="6 4" />
      <line x1="200" y1="90"  x2="320" y2="130" stroke="#4F46E5" strokeWidth="1.5" strokeOpacity="0.25" strokeDasharray="6 4" />
      <line x1="200" y1="90"  x2="260" y2="220" stroke="#4F46E5" strokeWidth="1.5" strokeOpacity="0.25" strokeDasharray="6 4" />
      <line x1="320" y1="130" x2="400" y2="200" stroke="#7C3AED" strokeWidth="1.5" strokeOpacity="0.2"  strokeDasharray="6 4" />
      <line x1="260" y1="220" x2="400" y2="200" stroke="#7C3AED" strokeWidth="1.5" strokeOpacity="0.2"  strokeDasharray="6 4" />

      {/* Node glows */}
      <circle cx="200" cy="90"  r="28" fill="#4F46E5" fillOpacity="0.07" />
      <circle cx="80"  cy="160" r="22" fill="#4F46E5" fillOpacity="0.05" />
      <circle cx="320" cy="130" r="22" fill="#4F46E5" fillOpacity="0.05" />
      <circle cx="260" cy="220" r="18" fill="#7C3AED" fillOpacity="0.06" />
      <circle cx="400" cy="200" r="20" fill="#7C3AED" fillOpacity="0.06" />

      {/* Nodes */}
      <circle cx="200" cy="90"  r="14" fill="#4F46E5" fillOpacity="0.15" stroke="#4F46E5" strokeWidth="1.5" strokeOpacity="0.6" />
      <circle cx="80"  cy="160" r="10" fill="#4F46E5" fillOpacity="0.12" stroke="#4F46E5" strokeWidth="1.5" strokeOpacity="0.45" />
      <circle cx="320" cy="130" r="10" fill="#4F46E5" fillOpacity="0.12" stroke="#4F46E5" strokeWidth="1.5" strokeOpacity="0.45" />
      <circle cx="260" cy="220" r="8"  fill="#7C3AED" fillOpacity="0.15" stroke="#7C3AED" strokeWidth="1.5" strokeOpacity="0.45" />
      <circle cx="400" cy="200" r="10" fill="#7C3AED" fillOpacity="0.12" stroke="#7C3AED" strokeWidth="1.5" strokeOpacity="0.45" />

      {/* Center node label */}
      <circle cx="200" cy="90" r="5" fill="#4F46E5" />

      {/* Node labels */}
      <text x="200" y="74"  textAnchor="middle" fontSize="10" fill="#4F46E5" fillOpacity="0.7" fontFamily="Inter, sans-serif" fontWeight="500">cerita</text>
      <text x="60"  y="155" textAnchor="middle" fontSize="9"  fill="#78716C" fontFamily="Inter, sans-serif">momen</text>
      <text x="320" y="118" textAnchor="middle" fontSize="9"  fill="#78716C" fontFamily="Inter, sans-serif">emosi</text>
      <text x="260" y="243" textAnchor="middle" fontSize="9"  fill="#78716C" fontFamily="Inter, sans-serif">karakter</text>
      <text x="400" y="218" textAnchor="middle" fontSize="9"  fill="#78716C" fontFamily="Inter, sans-serif">konflik</text>
    </svg>
  )
}

// ── Feature pills ─────────────────────────────────────────────────────────────
const FEATURES = [
  { icon: '🎙', label: 'Podcast' },
  { icon: '▶', label: 'YouTube' },
  { icon: '♪', label: 'TikTok'  },
  { icon: '✍', label: 'Blog'    },
]

// ── Social proof avatars (placeholder initials) ────────────────────────────────
const AVATARS = ['R', 'A', 'D', 'M', 'S']
const AVATAR_COLORS = ['#4F46E5', '#7C3AED', '#2563EB', '#0891B2', '#059669']

// ── Main component ─────────────────────────────────────────────────────────────
export default function Landing() {
  const navigate = useNavigate()

  return (
    <div
      className="min-h-screen relative overflow-x-hidden"
      style={{ background: '#FAF7F2', color: '#1C1917' }}
    >
      <DotGrid />

      {/* ── Navbar ────────────────────────────────────────────────────────── */}
      <nav
        className="relative z-10 flex items-center justify-between px-6 md:px-12 py-5"
        style={{ borderBottom: '1px solid #E8E2D9' }}
      >
        <div className="flex items-center gap-2.5">
          <img
            src="/logo-mark.png"
            alt="Arcwright"
            className="w-7 h-7 object-contain"
            style={{ filter: 'brightness(0) saturate(0) brightness(0.2)' }}
          />
          <span
            className="font-semibold text-base tracking-tight"
            style={{ color: '#1C1917' }}
          >
            arcwright
          </span>
        </div>

        <button
          onClick={() => navigate('/chat')}
          className="flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold transition-all duration-150"
          style={{ background: '#4F46E5', color: '#fff' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#4338CA')}
          onMouseLeave={e => (e.currentTarget.style.background = '#4F46E5')}
        >
          Start for free
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </nav>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative z-10 px-6 md:px-12 pt-16 pb-12 md:pt-24 md:pb-20">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 items-center">

          {/* Left — copy */}
          <div className="space-y-7">

            {/* Kicker badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold"
              style={{ background: '#EEF2FF', color: '#4F46E5', border: '1px solid #C7D2FE' }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: '#4F46E5' }}
              />
              AI Storytelling Coach — 8 specialized agents
            </div>

            {/* Headline */}
            <div>
              <h1
                className="font-black leading-none tracking-tight"
                style={{ fontSize: 'clamp(2.6rem, 6vw, 4.2rem)', letterSpacing: '-0.03em' }}
              >
                <span style={{ color: '#1C1917' }}>Your story</span>
                <br />
                <span style={{ color: '#1C1917' }}>deserves to be</span>
                <br />
                <span
                  className="relative inline-block"
                  style={{ color: '#4F46E5' }}
                >
                  heard.
                  {/* Underline decoration */}
                  <svg
                    viewBox="0 0 120 12"
                    className="absolute -bottom-2 left-0 w-full"
                    fill="none"
                    preserveAspectRatio="none"
                  >
                    <path d="M2 9 C30 3, 60 3, 118 9" stroke="#4F46E5" strokeWidth="3" strokeLinecap="round" strokeOpacity="0.4" />
                  </svg>
                </span>
              </h1>
            </div>

            {/* Sub */}
            <p
              className="text-base leading-relaxed max-w-md"
              style={{ color: '#78716C' }}
            >
              The moments you think are ordinary are exactly where great stories live. Yui — your AI coach — finds them, shapes them, and writes a script ready for any platform.
            </p>

            {/* CTA group */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <button
                onClick={() => navigate('/chat')}
                className="flex items-center gap-2.5 px-7 py-3.5 rounded-full font-bold text-sm transition-all duration-150 shadow-lg"
                style={{
                  background:   '#4F46E5',
                  color:        '#fff',
                  boxShadow:    '0 8px 24px rgba(79,70,229,0.35)',
                  letterSpacing: '0.01em',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background  = '#4338CA'
                  e.currentTarget.style.boxShadow   = '0 12px 32px rgba(79,70,229,0.45)'
                  e.currentTarget.style.transform   = 'translateY(-1px)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background  = '#4F46E5'
                  e.currentTarget.style.boxShadow   = '0 8px 24px rgba(79,70,229,0.35)'
                  e.currentTarget.style.transform   = 'translateY(0)'
                }}
              >
                Start for free — no account needed
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>

              <p className="text-xs" style={{ color: '#A8A29E' }}>
                No sign-up · Works in English & Indonesian
              </p>
            </div>

            {/* Social proof */}
            <div className="flex items-center gap-3 pt-1">
              <div className="flex -space-x-2">
                {AVATARS.map((a, i) => (
                  <div
                    key={i}
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white ring-2 ring-[#FAF7F2]"
                    style={{ background: AVATAR_COLORS[i] }}
                  >
                    {a}
                  </div>
                ))}
              </div>
              <p className="text-xs" style={{ color: '#78716C' }}>
                Join <strong style={{ color: '#1C1917' }}>creators</strong> already building with Arcwright
              </p>
            </div>
          </div>

          {/* Right — illustration */}
          <div className="relative flex justify-center items-center">
            {/* Card glow */}
            <div
              className="absolute inset-0 rounded-3xl"
              style={{
                background: 'radial-gradient(ellipse at 50% 50%, rgba(79,70,229,0.08) 0%, transparent 70%)',
              }}
            />
            <div
              className="relative w-full rounded-3xl p-8 md:p-10"
              style={{
                background: '#FFFFFF',
                border:     '1px solid #E8E2D9',
                boxShadow:  '0 4px 32px rgba(28,25,23,0.06), 0 1px 3px rgba(28,25,23,0.04)',
              }}
            >
              <StoryGraph />

              {/* Floating label */}
              <div
                className="absolute top-5 right-5 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
                style={{ background: '#EEF2FF', color: '#4F46E5', border: '1px solid #C7D2FE' }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                8 agents running
              </div>

              {/* Bottom agent strip */}
              <div
                className="mt-4 pt-4 flex items-center justify-between"
                style={{ borderTop: '1px solid #F2EEE8' }}
              >
                <span className="text-xs font-medium" style={{ color: '#A8A29E' }}>Last step</span>
                <span
                  className="text-xs px-2.5 py-1 rounded-full font-semibold"
                  style={{ background: '#F5F3FF', color: '#7C3AED' }}
                >
                  ✦ Script Writer done
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Platform tags ─────────────────────────────────────────────────── */}
      <section className="relative z-10 px-6 md:px-12 py-8">
        <div
          className="max-w-6xl mx-auto flex flex-wrap items-center gap-4"
          style={{ borderTop: '1px solid #E8E2D9', paddingTop: '2rem' }}
        >
          <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: '#A8A29E' }}>
              Platforms
            </span>
          {FEATURES.map(f => (
            <div
              key={f.label}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
              style={{ background: '#F2EEE8', color: '#57534E', border: '1px solid #E8E2D9' }}
            >
              <span>{f.icon}</span>
              {f.label}
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────────────────── */}
      <section
        className="relative z-10 px-6 md:px-12 py-16 md:py-24"
        style={{ background: '#FFFFFF', borderTop: '1px solid #E8E2D9', borderBottom: '1px solid #E8E2D9' }}
      >
        <div className="max-w-6xl mx-auto">
          <div className="mb-12">
            <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#4F46E5' }}>
              How it works
            </p>
            <h2
              className="font-black tracking-tight"
              style={{ fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', letterSpacing: '-0.025em', color: '#1C1917' }}
            >
              From a conversation<br />to a finished script.
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                step: '01',
                title: 'Just talk',
                body:  'Yui asks the right questions to surface the hidden tension, emotion, and detail inside your everyday moments.',
                color: '#4F46E5',
                bg:    '#EEF2FF',
              },
              {
                step: '02',
                title: 'Deep analysis',
                body:  '8 AI agents run in parallel — researching trends, stress-testing angles, and scoring your story against a 50-point quality rubric.',
                color: '#7C3AED',
                bg:    '#F5F3FF',
              },
              {
                step: '03',
                title: 'Script, delivered',
                body:  'Review the outline, approve it, and receive a platform-ready script tuned to your voice and target audience.',
                color: '#0891B2',
                bg:    '#ECFEFF',
              },
            ].map(card => (
              <div
                key={card.step}
                className="rounded-2xl p-6 space-y-4"
                style={{ background: card.bg, border: `1px solid ${card.color}22` }}
              >
                <div
                  className="text-xs font-black tracking-widest"
                  style={{ color: card.color, opacity: 0.5 }}
                >
                  {card.step}
                </div>
                <h3
                  className="font-bold text-lg leading-snug"
                  style={{ color: '#1C1917' }}
                >
                  {card.title}
                </h3>
                <p
                  className="text-sm leading-relaxed"
                  style={{ color: '#78716C' }}
                >
                  {card.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA section ───────────────────────────────────────────────────── */}
      <section className="relative z-10 px-6 md:px-12 py-20 md:py-28 text-center">
        <div className="max-w-2xl mx-auto space-y-6">
          <img
            src="/logo-mark.png"
            alt="Arcwright"
            className="w-10 h-10 mx-auto object-contain"
            style={{ filter: 'brightness(0) saturate(0) brightness(0.2)' }}
          />
          <h2
            className="font-black tracking-tight"
            style={{ fontSize: 'clamp(2rem, 5vw, 3.2rem)', letterSpacing: '-0.03em', color: '#1C1917' }}
          >
            Your story is waiting<br />to be written.
          </h2>
          <p className="text-base" style={{ color: '#78716C' }}>
            Start your first conversation with Yui — free, no account required.
          </p>
          <button
            onClick={() => navigate('/chat')}
            className="inline-flex items-center gap-2.5 px-8 py-4 rounded-full font-bold text-sm transition-all duration-150"
            style={{
              background:   '#4F46E5',
              color:        '#fff',
              boxShadow:    '0 8px 24px rgba(79,70,229,0.35)',
              letterSpacing: '0.01em',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#4338CA'
              e.currentTarget.style.boxShadow  = '0 12px 32px rgba(79,70,229,0.45)'
              e.currentTarget.style.transform  = 'translateY(-1px)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = '#4F46E5'
              e.currentTarget.style.boxShadow  = '0 8px 24px rgba(79,70,229,0.35)'
              e.currentTarget.style.transform  = 'translateY(0)'
            }}
          >
            Start for free
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        className="relative z-10 px-6 md:px-12 py-6 flex items-center justify-between text-xs"
        style={{ borderTop: '1px solid #E8E2D9', color: '#A8A29E' }}
      >
        <div className="flex items-center gap-2">
          <img
            src="/logo-mark.png"
            alt=""
            className="w-4 h-4 object-contain"
            style={{ filter: 'brightness(0) saturate(0) brightness(0.6) opacity(0.5)' }}
          />
          <span>arcwright · 2026</span>
        </div>
        <span>AI Storytelling Coach</span>
      </footer>
    </div>
  )
}
