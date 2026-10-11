import { describe, expect, it, vi } from 'vitest'
import { ApiError, checkOffer } from './api'
import amber from './fixtures/amber.json'

function stubFetch(impl: () => Promise<Response>) {
  const fetchMock = vi.fn(impl)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

describe('checkOffer', () => {
  it('posts multipart data to /api/check on VITE_API_URL', async () => {
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/')
    const fetchMock = stubFetch(async () => json(amber))

    const response = await checkOffer({ text: 'সৌদি আরবে চাকরি', audio: new Blob(['x'], { type: 'audio/webm' }) })

    expect(response.verdict.level).toBe('amber')
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('https://api.example.test/api/check')
    expect(init.method).toBe('POST')
    const body = init.body as FormData
    expect(body.get('text')).toBe('সৌদি আরবে চাকরি')
    expect((body.get('audio') as File).name).toBe('voice.webm')
    expect(body.has('image')).toBe(false)
  })

  it('reports a network failure as offline', async () => {
    stubFetch(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(checkOffer({ text: 'x' })).rejects.toMatchObject({ kind: 'offline' })
  })

  it.each([
    [500, 'server'],
    [503, 'server'],
    [422, 'bad_request'],
  ])('maps HTTP %i to %s', async (status, kind) => {
    stubFetch(async () => json({ detail: 'nope' }, status))
    await expect(checkOffer({ text: 'x' })).rejects.toMatchObject({ kind })
  })

  it('rejects a body that is not JSON', async () => {
    stubFetch(async () => new Response('<html>gateway</html>', { status: 200 }))
    await expect(checkOffer({ text: 'x' })).rejects.toBeInstanceOf(ApiError)
  })

  it('never accepts a verdict with an unknown level', async () => {
    stubFetch(async () => json({ ...amber, verdict: { ...amber.verdict, level: 'ok' } }))
    await expect(checkOffer({ text: 'x' })).rejects.toMatchObject({ kind: 'invalid' })
  })

  it('lets a caller cancel without turning it into an error kind', async () => {
    const abort = new AbortController()
    stubFetch(async () => {
      abort.abort()
      throw new DOMException('Aborted', 'AbortError')
    })
    await expect(checkOffer({ text: 'x' }, abort.signal)).rejects.not.toBeInstanceOf(ApiError)
  })
})
