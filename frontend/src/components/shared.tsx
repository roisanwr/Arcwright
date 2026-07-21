// Small shared UI components

// ── Loading dots ──────────────────────────────────────────────────────────────

export function LoadingDots({ size = 'sm' }: { size?: 'xs' | 'sm' }) {
  const sz = size === 'xs' ? 'w-1 h-1' : 'w-1.5 h-1.5'
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className={`dot-blink ${sz} rounded-full bg-current inline-block`}
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </span>
  )
}

// ── Agent metadata ────────────────────────────────────────────────────────────

const AGENT_META: Record<string, { label: string; color: string; dot: string }> = {
  story_director: { label: 'Story Director',  color: '#818cf8', dot: 'bg-indigo-400'  },
  story_miner:    { label: 'Story Miner',     color: '#38bdf8', dot: 'bg-sky-400'     },
  rag_librarian:  { label: 'RAG Librarian',   color: '#4ade80', dot: 'bg-green-400'   },
  web_researcher: { label: 'Web Researcher',  color: '#2dd4bf', dot: 'bg-teal-400'    },
  deep_dive:      { label: 'Deep Dive',       color: '#fbbf24', dot: 'bg-amber-400'   },
  validator:      { label: 'Validator',       color: '#34d399', dot: 'bg-emerald-400' },
  outline_writer: { label: 'Outline Writer',  color: '#fb923c', dot: 'bg-orange-400'  },
  script_writer:  { label: 'Script Writer',   color: '#f87171', dot: 'bg-red-400'     },
  user_approval:  { label: 'Menunggu review', color: '#e879f9', dot: 'bg-fuchsia-400' },
  __interrupt__:  { label: 'Menunggu input',  color: '#e879f9', dot: 'bg-fuchsia-400' },
  idle:           { label: 'Siap',            color: '#475569', dot: 'bg-slate-500'   },
}

export function getAgent(node: string) {
  return AGENT_META[node] ?? { label: node, color: '#475569', dot: 'bg-slate-500' }
}

// ── Status badge ──────────────────────────────────────────────────────────────

interface StatusBadgeProps {
  node: string
  isProcessing: boolean
}

export function StatusBadge({ node, isProcessing }: StatusBadgeProps) {
  const agent = getAgent(node)
  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border"
      style={{
        borderColor: `${agent.color}33`,
        background:  `${agent.color}10`,
        color:       agent.color,
      }}
    >
      {isProcessing ? (
        <span className="relative flex h-2 w-2 shrink-0">
          <span className={`pulse-ring absolute inline-flex h-full w-full rounded-full ${agent.dot} opacity-60`} />
          <span className={`relative inline-flex h-2 w-2 rounded-full ${agent.dot}`} />
        </span>
      ) : (
        <span className={`h-2 w-2 rounded-full ${agent.dot} shrink-0`} />
      )}
      <span>{agent.label}</span>
      {isProcessing && <LoadingDots size="xs" />}
    </div>
  )
}

// ── Markdown renderer ─────────────────────────────────────────────────────────

import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

interface MarkdownContentProps {
  content: string
  className?: string
  style?: React.CSSProperties
}

export function MarkdownContent({ content, className = '', style }: MarkdownContentProps) {
  const html = marked.parse(content) as string
  return (
    <div
      className={`md-content ${className}`}
      style={style}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
