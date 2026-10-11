import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { checkOffer } from './api'
import App from './App'
import amber from './fixtures/amber.json'
import red from './fixtures/red.json'
import { withAnswers, withDocument } from './followUp'
import { I18nProvider } from './i18n'
import { verdictText } from './share'
import { bn } from './i18n/translations'
import type { CheckResult, Guide } from './types'
import { putWage, wageSummary } from './wages'

// Everything here is SYNTHETIC: fixtures, agency names and the guide below are made up for tests.
const GUIDE: Guide = {
  country: 'SA',
  country_name_bn: 'সৌদি আরব',
  rights: [
    {
      id: 'SYN_RIGHT',
      text_bn: 'নমুনা অধিকার।',
      text_en: 'Sample right.',
      source: { title: 'Synthetic source', url: 'https://example.test/rule' },
      verified: false,
      last_checked: '2026-01-05',
    },
  ],
  checklist: [
    { id: 'SYN_STEP', text_bn: 'নমুনা ধাপ।', text_en: 'Sample step.', source: null, verified: true, last_checked: null },
  ],
  payment_tips_bn: ['নমুনা পরামর্শ।'],
  helplines: [{ name: 'নমুনা নম্বর', phone: '00000' }],
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status })

function renderApp({ consent = true } = {}) {
  vi.stubEnv('VITE_DEMO_MODE', 'false')
  if (consent) localStorage.setItem('probashi.consent', 'true')
  return render(
    <I18nProvider initialLang="bn">
      <App />
    </I18nProvider>,
  )
}

async function typeAnOffer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /লিখে জানান/ }))
  await user.type(await screen.findByRole('textbox'), 'সৌদি আরবে চাকরি')
  await user.click(screen.getByRole('button', { name: 'যাচাই করুন' }))
}

const calls = (fetchMock: ReturnType<typeof vi.fn>) => fetchMock.mock.calls as unknown as [string, RequestInit][]

describe('consent', () => {
  it('sends nothing until the user agrees, then remembers the answer', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(red))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp({ consent: false })

    await typeAnOffer(user)
    expect(await screen.findByRole('heading', { name: 'শুরু করার আগে' })).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'আমি রাজি, যাচাই করুন' }))
    expect(await screen.findByRole('heading', { name: 'ঝুঁকি বেশি' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(localStorage.getItem('probashi.consent')).toBe('true')
  })

  it('"delete everything" clears what the app kept on the phone, consent included', async () => {
    localStorage.setItem('probashi.wages', '[]')
    localStorage.setItem('someone-else', 'kept')
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole('button', { name: /আপনার তথ্য কীভাবে ব্যবহার হয়/ }))
    await user.click(await screen.findByRole('button', { name: 'এই ফোন থেকে সব মুছে ফেলুন' }))

    expect(screen.getByRole('status')).toHaveTextContent('সব মুছে ফেলা হয়েছে।')
    expect(Object.keys(localStorage).filter((key) => key.startsWith('probashi.'))).toEqual([])
    expect(localStorage.getItem('someone-else')).toBe('kept')
  })
})

describe('slow or missing connection', () => {
  it('sends a failed check again by itself when the phone comes back online', async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce(json(red))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    expect(await screen.findByRole('alert')).toHaveTextContent('ইন্টারনেট ফিরে এলে')
    window.dispatchEvent(new Event('online'))

    expect(await screen.findByRole('heading', { name: 'ঝুঁকি বেশি' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('asks for no spoken answer in low-data mode', async () => {
    localStorage.setItem('probashi.lowData', 'true')
    const fetchMock = vi.fn().mockResolvedValue(json(amber))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    await screen.findByRole('heading', { name: 'আরও যাচাই করুন' })
    expect(calls(fetchMock)[0][0]).toMatch(/\/api\/check\?voice=false$/)
  })

  it('tells the user to wait when the server says there were too many checks', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: {} }, 429)))
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    expect(await screen.findByRole('alert')).toHaveTextContent('একটু অপেক্ষা করুন')
  })
})

describe('after the verdict', () => {
  it('checks again with the first description plus the answer to a follow-up question', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => json(red))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    await user.type(await screen.findByLabelText('এজেন্সির নাম কী?'), 'নমুনা এজেন্সি')
    await user.click(screen.getByRole('button', { name: 'আবার যাচাই করুন' }))

    await screen.findByRole('heading', { name: 'ঝুঁকি বেশি' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const text = (calls(fetchMock)[1][1].body as FormData).get('text') as string
    expect(text.split('\n')[0]).toBe('সৌদি আরবে চাকরি')
    expect(text).toContain('এজেন্সির নাম কী? নমুনা এজেন্সি')
  })

  it('explains a reason with its source and says when that source is not confirmed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(red)))
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    const why = await screen.findByText('কেন এটা বলছি?')
    const explainer = within(why.closest('details')!)
    expect(explainer.getByText(/সরকারি তালিকায় মিলিয়ে দেখা যায় না/)).toBeInTheDocument()
    expect(explainer.getByText('এই সূত্রটি এখনো সরকারি সূত্র দিয়ে যাচাই হয়নি।')).toBeInTheDocument()
    expect(screen.getByText('আপনাদের এজেন্সির লাইসেন্স নম্বর কত?')).toBeInTheDocument()
    expect(screen.getByText(/অভিযোগ \(নমুনা খসড়া\)/)).toBeInTheDocument()
  })

  it('sends a scam report only after the box is ticked, with no document text in it', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => (url.endsWith('/api/report') ? json({ saved: true }, 201) : json(red)))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    const send = await screen.findByRole('button', { name: 'জানিয়ে দিন' })
    expect(send).toBeDisabled()
    await user.click(screen.getByLabelText(/আমি রাজি। এজেন্সির নাম/))
    await user.click(send)

    expect(await screen.findByText('ধন্যবাদ। আমরা জেনেছি।')).toBeInTheDocument()
    const [url, init] = calls(fetchMock)[1]
    expect(url).toMatch(/\/api\/report$/)
    expect(JSON.parse(init.body as string)).toEqual({
      consent: true,
      level: 'red',
      reason_codes: ['AGENCY_LICENSE_MISSING', 'VISIT_VISA_FOR_WORK', 'CASH_WITHOUT_RECEIPT', 'NO_WRITTEN_CONTRACT'],
      destination_country: 'SA',
    })
  })

  it('opens the guide for the country of the offer and keeps a copy for when there is no connection', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => (url.endsWith('/api/guide/SA') ? json(GUIDE) : json(red)))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)
    await user.click(await screen.findByRole('button', { name: 'এই দেশে আপনার অধিকার দেখুন' }))

    expect(await screen.findByText('নমুনা অধিকার।')).toBeInTheDocument()
    expect(screen.getByText('এই সূত্রটি এখনো সরকারি সূত্র দিয়ে যাচাই হয়নি।')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /নমুনা নম্বর/ })).toHaveAttribute('href', 'tel:00000')
    expect(JSON.parse(localStorage.getItem('probashi.guide.SA')!).rights).toHaveLength(1)
  })
})

describe('helpers', () => {
  const result = red as CheckResult

  it('sends extra papers as more_images', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(amber))
    vi.stubGlobal('fetch', fetchMock)
    const paper = new Blob(['x'], { type: 'image/jpeg' })
    await checkOffer(withDocument({ image: paper }, { ...result, transcript_bn: null }, paper))
    const body = calls(fetchMock)[0][1].body as FormData
    expect(body.getAll('image')).toHaveLength(1)
    expect(body.getAll('more_images')).toHaveLength(1)
  })

  it('a spoken answer replaces audio that is already transcribed, never audio that is not', () => {
    const first = new Blob(['a'], { type: 'audio/webm' })
    const spoken = new Blob(['b'], { type: 'audio/webm' })
    expect(withAnswers({ audio: first }, result, [], spoken)).toMatchObject({ audio: spoken, text: result.transcript_bn })
    expect(withAnswers({ audio: first }, result, []).audio).toBeUndefined()
    expect(withAnswers({ audio: first }, { ...result, transcript_bn: null }, []).audio).toBe(first)
  })

  it('builds a share text with the level, the reasons and a helpline', () => {
    const text = verdictText(result, bn)
    expect(text).toContain('ঝুঁকি বেশি')
    expect(text).toContain(result.verdict.reasons[0].message_bn)
    expect(text).toContain('16135')
  })

  it('adds up underpaid months without letting a full month hide them', () => {
    let entries = putWage([], { month: '2026-01', promised: 1000, received: 700 })
    entries = putWage(entries, { month: '2026-02', promised: 1000, received: 1200 })
    entries = putWage(entries, { month: '2026-01', promised: 1000, received: 800 })
    expect(entries.map((e) => e.month)).toEqual(['2026-02', '2026-01'])
    expect(wageSummary(entries)).toEqual({ promised: 2000, received: 2000, shortfall: 200 })
  })
})

describe('evaluation and review', () => {
  // SYNTHETIC numbers and names, made up for these tests.
  const STATS = { since: '2026-01-05T00:00:00Z', checks: 4, by_level: { red: 1, amber: 3, green: 0 }, by_channel: {}, by_country: {}, top_reasons: [], reports: 0 }
  const EVALUATION = { as_of: '2026-01-05', total: 10, correct: 9, real: 4, synthetic: 6, fraud_total: 7, fraud_green: 0, fraud_red: 5, misses: [] }

  it('shows how many fraud offers the checker called safe', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => json(url.endsWith('/api/eval') ? EVALUATION : STATS)))
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole('button', { name: /আরও সাহায্য/ }))
    await user.click(await screen.findByRole('button', { name: /মোট হিসাব/ }))

    const safe = (await screen.findByText('প্রতারণার অফারকে নিরাপদ বলেছে')).parentElement!
    expect(within(safe).getByText('০ / ৭')).toBeInTheDocument()
    expect(screen.getByText('৯ / ১০')).toBeInTheDocument()
    expect(screen.getByText(/৪ আসল খবর থেকে, ৬ বানানো নমুনা/)).toBeInTheDocument()
  })

  it('still shows the totals when the server has no evaluation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => (url.endsWith('/api/eval') ? json({}, 503) : json(STATS))))
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole('button', { name: /আরও সাহায্য/ }))
    await user.click(await screen.findByRole('button', { name: /মোট হিসাব/ }))

    expect(await screen.findByText('এই সার্ভারে পরীক্ষার ফল নেই।')).toBeInTheDocument()
    expect(screen.getByText('মোট যাচাই')).toBeInTheDocument()
  })

  it('shows stored reports to a reviewer with the token, and nothing without it', async () => {
    const queue = {
      total: 2,
      agencies: [{ agency_name: 'SYNTHETIC Agency', agency_license_no: 'RL-0000', count: 2, last_date: '2026-01-05' }],
      reports: [{ date: '2026-01-05', level: 'red', reason_codes: ['FREE_VISA'], destination_country: 'SA', agency_name: 'SYNTHETIC Agency', agency_license_no: 'RL-0000' }],
    }
    const fetchMock = vi.fn().mockResolvedValueOnce(json({}, 401)).mockResolvedValueOnce(json(queue))
    vi.stubGlobal('fetch', fetchMock)
    history.replaceState(null, '', '#review') // as when the page is opened at that address
    const user = userEvent.setup()
    renderApp()

    await user.type(await screen.findByLabelText('যাচাইকারীর টোকেন'), 'synthetic-token')
    await user.click(screen.getByRole('button', { name: 'খবর দেখান' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('টোকেন ঠিক আছে কি না দেখুন')

    await user.click(screen.getByRole('button', { name: 'খবর দেখান' }))
    expect(await screen.findByText('২ বার')).toBeInTheDocument()
    expect(screen.getByText('FREE_VISA')).toBeInTheDocument()
    const [url, init] = calls(fetchMock)[1]
    expect(url).toMatch(/\/api\/admin\/reports$/)
    expect(init.headers).toEqual({ Authorization: 'Bearer synthetic-token' })
    expect(JSON.stringify({ ...localStorage })).not.toContain('synthetic-token')
    history.replaceState(null, '', location.pathname)
  })
})
