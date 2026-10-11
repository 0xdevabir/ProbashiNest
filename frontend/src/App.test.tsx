import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import red from './fixtures/red.json'
import { I18nProvider } from './i18n'

function renderApp() {
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

describe('App error handling', () => {
  it('explains a network failure in Bangla and recovers on retry', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'false')
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(JSON.stringify(red), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('ইন্টারনেট সংযোগ পাওয়া যাচ্ছে না')
    await user.click(screen.getByRole('button', { name: 'আবার চেষ্টা করুন' }))

    expect(await screen.findByRole('heading', { name: 'ঝুঁকি বেশি' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    // A real answer is never labelled as sample data.
    expect(screen.queryByText('নমুনা তথ্য, আসল নয়')).not.toBeInTheDocument()
  })

  it('shows a server-side message when the API returns 500', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'false')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('boom', { status: 500 })))
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('আমাদের দিকে সমস্যা হয়েছে')
  })

  it('answers from a labelled fixture in demo mode without calling the network', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'true')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    renderApp()

    await typeAnOffer(user)

    expect(await screen.findByRole('heading', { name: 'ঝুঁকি বেশি' }, { timeout: 4000 })).toBeInTheDocument()
    expect(screen.getByText('নমুনা তথ্য, আসল নয়')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
