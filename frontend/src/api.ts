import { LEVELS, type CheckResult, type Evaluation, type Guide, type ReviewQueue, type ScamReport, type Stats } from './types'

export type ApiErrorKind = 'offline' | 'timeout' | 'server' | 'bad_request' | 'busy' | 'invalid'

export class ApiError extends Error {
  constructor(public readonly kind: ApiErrorKind) {
    super(kind)
    this.name = 'ApiError'
  }
}

/** The server reads at most this many papers in one check (MAX_DOCUMENTS in backend/pipeline.py). */
export const MAX_DOCUMENTS = 3

export interface CheckInput {
  image?: Blob
  /** Other papers for the same job, e.g. the visa next to the offer letter. */
  moreImages?: Blob[]
  audio?: Blob
  text?: string
}

export interface CheckOptions {
  /** false = ask for no spoken answer, to keep the reply small on a slow connection. */
  voice?: boolean
}

// Slow 3G plus OCR, LLM and speech synthesis: give the server a generous window.
const TIMEOUT_MS = 90_000
const SHORT_TIMEOUT_MS = 20_000

function apiBase(): string {
  return (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')
}

function audioFileName(mime: string): string {
  if (mime.includes('mp4')) return 'voice.m4a'
  if (mime.includes('ogg')) return 'voice.ogg'
  return 'voice.webm'
}

// A malformed verdict must surface as an error. Never guess a level for the user.
function isCheckResult(data: unknown): data is CheckResult {
  if (typeof data !== 'object' || data === null) return false
  const { offer, verdict } = data as Partial<CheckResult>
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

async function request(path: string, init: RequestInit, timeoutMs: number, signal?: AbortSignal): Promise<Response> {
  const timeout = new AbortController()
  const timer = setTimeout(() => timeout.abort(), timeoutMs)
  const abort = () => timeout.abort()
  signal?.addEventListener('abort', abort)

  let res: Response
  try {
    res = await fetch(`${apiBase()}${path}`, { ...init, signal: timeout.signal })
  } catch (err) {
    // The caller cancelled: pass the abort through so it is not shown as an error.
    if (signal?.aborted) throw err
    throw new ApiError(timeout.signal.aborted ? 'timeout' : 'offline')
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
  }

  if (res.status >= 500) throw new ApiError('server')
  if (res.status === 429) throw new ApiError('busy')
  if (!res.ok) throw new ApiError('bad_request')
  return res
}

async function json<T>(res: Response, isValid: (data: unknown) => boolean): Promise<T> {
  const data: unknown = await res.json().catch(() => null)
  if (!isValid(data)) throw new ApiError('invalid')
  return data as T
}

const isObject = (data: unknown): data is Record<string, unknown> => typeof data === 'object' && data !== null

export async function checkOffer(
  input: CheckInput,
  signal?: AbortSignal,
  { voice = true }: CheckOptions = {},
): Promise<CheckResult> {
  const body = new FormData()
  if (input.image) body.append('image', input.image, 'document.jpg')
  input.moreImages?.forEach((image, i) => body.append('more_images', image, `document-${i + 2}.jpg`))
  if (input.audio) body.append('audio', input.audio, audioFileName(input.audio.type))
  if (input.text) body.append('text', input.text)

  const res = await request(`/api/check${voice ? '' : '?voice=false'}`, { method: 'POST', body }, TIMEOUT_MS, signal)
  return json<CheckResult>(res, isCheckResult)
}

/** Rights, pre-departure checklist, payment advice and contacts for a destination. */
export async function fetchGuide(country: string, signal?: AbortSignal): Promise<Guide> {
  const res = await request(`/api/guide/${encodeURIComponent(country)}`, { method: 'GET' }, SHORT_TIMEOUT_MS, signal)
  return json<Guide>(
    res,
    (data) => isObject(data) && Array.isArray(data.rights) && Array.isArray(data.checklist) && Array.isArray(data.helplines),
  )
}

export async function fetchStats(signal?: AbortSignal): Promise<Stats> {
  const res = await request('/api/stats', { method: 'GET' }, SHORT_TIMEOUT_MS, signal)
  return json<Stats>(res, (data) => isObject(data) && typeof data.checks === 'number' && isObject(data.by_level))
}

/** Send a scam report the user agreed to share. Carries no document, audio or personal detail. */
export async function sendReport(report: ScamReport): Promise<void> {
  await request(
    '/api/report',
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) },
    SHORT_TIMEOUT_MS,
  )
}

/** The engine's score on the labelled test cases, most importantly how many fraud cases it called safe. */
export async function fetchEvaluation(signal?: AbortSignal): Promise<Evaluation> {
  const res = await request('/api/eval', { method: 'GET' }, SHORT_TIMEOUT_MS, signal)
  return json<Evaluation>(
    res,
    (data) => isObject(data) && typeof data.fraud_green === 'number' && typeof data.total === 'number' && Array.isArray(data.misses),
  )
}

/** Stored scam reports, for review staff. The token is sent once and never kept. */
export async function fetchReviewQueue(token: string, signal?: AbortSignal): Promise<ReviewQueue> {
  const res = await request(
    '/api/admin/reports',
    { method: 'GET', headers: { Authorization: `Bearer ${token}` } },
    SHORT_TIMEOUT_MS,
    signal,
  )
  return json<ReviewQueue>(res, (data) => isObject(data) && Array.isArray(data.agencies) && Array.isArray(data.reports))
}
