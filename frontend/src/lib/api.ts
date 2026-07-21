/**
 * Arcwright API client.
 * All endpoint paths live here — change once if backend routes change.
 */

const BASE = import.meta.env.VITE_API_BASE ?? ''

// ── UUID helper — works on HTTP (non-secure context) ────────────────────────
function generateUUID(): string {
  // crypto.randomUUID() hanya tersedia di HTTPS/localhost
  // Fallback manual agar tetap bekerja di plain HTTP
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    try { return crypto.randomUUID() } catch { /* fallthrough */ }
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

// ── Device ID ─────────────────────────────────────────────────────────────────
// UUID persisten di localStorage — pengganti login tanpa autentikasi.
// Hanya hilang jika user manual clear browser storage.

const DEVICE_ID_KEY = 'arcwright_device_id'

export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id = generateUUID()
    localStorage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}

// ── Session API ───────────────────────────────────────────────────────────────

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
    device_id: getDeviceId(),
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
    body:    JSON.stringify({ ...params, device_id: getDeviceId() }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
}

export function getStreamUrl(sessionId: string): string {
  return `${BASE}/api/stream?session_id=${sessionId}`
}

// ── History API ───────────────────────────────────────────────────────────────

export interface BackendSessionMeta {
  session_id: string
  title: string
  platform: string
  language: string
  status: string
  created_at: string
  updated_at: string
}

export interface BackendMessage {
  role: string
  content: string
  msg_type: string
  created_at: string
}

export async function fetchHistory(): Promise<BackendSessionMeta[]> {
  const deviceId = getDeviceId()
  const res = await fetch(`${BASE}/api/history?device_id=${deviceId}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.sessions ?? []
}

export async function fetchSession(sessionId: string): Promise<BackendMessage[]> {
  const deviceId = getDeviceId()
  const res = await fetch(`${BASE}/api/session/${sessionId}?device_id=${deviceId}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.messages ?? []
}

export async function deleteSession(sessionId: string): Promise<void> {
  const deviceId = getDeviceId()
  await fetch(`${BASE}/api/session/${sessionId}?device_id=${deviceId}`, {
    method: 'DELETE',
  })
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<void> {
  await fetch(`${BASE}/api/session/${sessionId}`, {
    method:  'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ device_id: getDeviceId(), title }),
  })
}
