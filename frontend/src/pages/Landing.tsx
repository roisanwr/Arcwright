import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import IntroScene from '../components/IntroScene'

export default function Landing() {
  const [heroVisible, setHeroVisible] = useState(false)
  const navigate = useNavigate()

  const handleReady = useCallback(() => setHeroVisible(true), [])

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#080e18]">

      {/* Three.js backdrop — full screen */}
      <div className="absolute inset-0">
        <IntroScene onReady={handleReady} />
      </div>

      {/* Gradient fade at bottom so text is readable */}
      <div
        className="absolute inset-x-0 bottom-0 h-3/5 pointer-events-none"
        style={{ background: 'linear-gradient(to top, #080e18 30%, transparent)' }}
      />

      {/* Hero overlay — fades in after animation */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-end pb-16 px-6 text-center"
        style={{
          opacity:    heroVisible ? 1 : 0,
          transition: 'opacity 1s ease',
        }}
      >
        {/* Logo mark */}
        <img
          src="/logo-mark.png"
          alt="Arcwright"
          className="w-12 h-12 mb-6 object-contain"
          style={{ filter: 'brightness(0) invert(1) opacity(0.85)' }}
        />

        {/* Kicker */}
        <p
          className="text-xs font-semibold tracking-[0.25em] uppercase mb-4"
          style={{ color: '#2dd4bf', opacity: 0.9 }}
        >
          Storytelling AI
        </p>

        {/* Headline */}
        <h1
          className="font-extrabold leading-tight mb-4 max-w-lg"
          style={{
            fontSize:      'clamp(2rem, 6vw, 3.5rem)',
            letterSpacing: '-0.02em',
            color:         '#e8e3dc',
          }}
        >
          Ceritamu layak<br />untuk didengar.
        </h1>

        {/* Sub */}
        <p
          className="text-sm leading-relaxed mb-8 max-w-sm"
          style={{ color: '#8899a6' }}
        >
          Dari momen sehari-hari yang kamu anggap biasa — Yui bantu kamu temukan kisah yang berkesan dan siap tampil di platform apapun.
        </p>

        {/* CTA */}
        <button
          onClick={() => navigate('/chat')}
          className="group relative flex items-center gap-2 font-semibold text-sm px-7 py-3.5 rounded-full transition-all duration-200"
          style={{
            background:   '#2dd4bf',
            color:        '#080e18',
            letterSpacing: '0.01em',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#5eead4')}
          onMouseLeave={e => (e.currentTarget.style.background = '#2dd4bf')}
        >
          Mulai Ngobrol
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="transition-transform group-hover:translate-x-0.5">
            <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        {/* Trust line */}
        <p className="mt-4 text-xs" style={{ color: '#2d4055' }}>
          Gratis · Tanpa akun · Langsung mulai
        </p>
      </div>
    </div>
  )
}
