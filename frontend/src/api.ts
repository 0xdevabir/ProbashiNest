import { LEVELS, type CheckResponse } from './types'

export type ApiErrorKind = 'offline' | 'timeout' | 'server' | 'bad_request' | 'invalid'

export class ApiError extends Error {
  constructor(public readonly kind: ApiErrorKind) {
    super(kind)
    this.name = 'ApiError'
  }
}

export interface CheckInput {
  image?: Blob
  audio?: Blob
  text?: string
}

// Slow 3G plus OCR, LLM and speech synthesis: give the server a generous window.
const TIMEOUT_MS = 90_000

function apiBase(): string {
  return (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')
}

function audioFileName(mime: string): string {
  if (mime.includes('mp4')) return 'voice.m4a'
  if (mime.includes('ogg')) return 'voice.ogg'
  return 'voice.webm'
}

// A malformed verdict must surface as an error. Never guess a level for the user.
function isCheckResponse(data: unknown): data is CheckResponse {
  if (typeof data !== 'object' || data === null) return false
  const { offer, verdict } = data as Partial<CheckResponse>
  return (
    typeof offer === 'object' &&
    offer !== null &&
    typeof verdict === 'object' &&
    verdict !== null &&
    LEVELS.includes(verdict.level) &&
    Array.isArray(verdict.reasons) &&
    Array.isArray(verdict.next_steps_bn)
  )
}

export async function checkOffer(input: CheckInput, signal?: AbortSignal): Promise<CheckResponse> {
  const body = new FormData()
  if (input.image) body.append('image', input.image, 'document.jpg')
  if (input.audio) body.append('audio', input.audio, audioFileName(input.audio.type))
  if (input.text) body.append('text', input.text)

  const timeout = new AbortController()
  const timer = setTimeout(() => timeout.abort(), TIMEOUT_MS)
  const abort = () => timeout.abort()
  signal?.addEventListener('abort', abort)

  let res: Response
  try {
    res = await fetch(`${apiBase()}/api/check`, { method: 'POST', body, signal: timeout.signal })
  } catch (err) {
    // The caller cancelled: pass the abort through so it is not shown as an error.
    if (signal?.aborted) throw err
    throw new ApiError(timeout.signal.aborted ? 'timeout' : 'offline')
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
  }

  if (res.status >= 500) throw new ApiError('server')
  if (!res.ok) throw new ApiError('bad_request')

  const data: unknown = await res.json().catch(() => null)
  if (!isCheckResponse(data)) throw new ApiError('invalid')
  return data
}
