/**
 * Arcwright API client.
 * All endpoint paths live here — change once if backend routes change.
 */

const BASE = import.meta.env.VITE_API_BASE ?? ''

export interface StartSessionParams {
  user_name: string
  language: string
  platform: string
}

export interface StartSessionResponse {
  session_id: string
}

export async function startSession(params: StartSessionParams): Promise<StartSessionResponse> {
  const qs = new URLSearchParams({
    user_name: params.user_name,
    language:  params.language,
    platform:  params.platform,
  })
  const res = await fetch(`${BASE}/api/start?${qs}`)
  if (!res.ok) throw new Error(`Failed to start session: ${res.status}`)
  return res.json()
}

export interface SendMessageParams {
  session_id: string
  message: string
}

export async function sendMessage(params: SendMessageParams): Promise<void> {
  const res = await fetch(`${BASE}/api/chat`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
}

export function getStreamUrl(sessionId: string): string {
  return `${BASE}/api/stream?session_id=${sessionId}`
}
