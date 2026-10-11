import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { ApiError, checkOffer, type ApiErrorKind, type CheckInput } from './api'
import { isDemoBuild, loadFixture, type DemoChoice } from './demo'
import { recordVerdict } from './helper'
import { isLowData } from './lowData'
import { Home } from './screens/Home'
import type { Tool } from './screens/More'
import { CheckFailed, Loading } from './screens/Status'
import { load, save } from './storage'
import type { CheckResult } from './types'

// Home is the only screen in the first download; the rest arrive when needed.
const loadResult = () => import('./screens/Result')
const Result = lazy(loadResult)
const TypeOffer = lazy(() => import('./screens/TypeOffer'))
const Privacy = lazy(() => import('./screens/Privacy'))
const Consent = lazy(() => import('./screens/Consent'))
const More = lazy(() => import('./screens/More'))
const GuideScreen = lazy(() => import('./screens/GuideScreen'))
const Wages = lazy(() => import('./screens/Wages'))
const Sos = lazy(() => import('./screens/Sos'))
const Helper = lazy(() => import('./screens/Helper'))
const StatsScreen = lazy(() => import('./screens/StatsScreen'))
const DemoMenu = lazy(() => import('./components/DemoMenu'))

type Screen = 'home' | 'type' | 'privacy' | 'consent' | 'loading' | 'result' | 'error' | 'more' | Tool

const IN_APP = { inApp: true }

export default function App() {
  const [screen, setScreen] = useState<Screen>('home')
  const [result, setResult] = useState<{ response: CheckResult; isDemo: boolean; input: CheckInput } | null>(null)
  const [errorKind, setErrorKind] = useState<ApiErrorKind>('offline')
  const [demoBuild] = useState(isDemoBuild)
  const [demoChoice, setDemoChoice] = useState<DemoChoice>(demoBuild ? 'red' : 'live')
  const [demoMenuOpen, setDemoMenuOpen] = useState(false)
  // The guide opens from the result (for the offer's country) or from the tools list.
  const [guide, setGuide] = useState<{ country: string | null; from: 'result' | 'more' }>({ country: null, from: 'more' })
  const lastInputRef = useRef<CheckInput | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // The phone's back button returns to home instead of closing the app.
  useEffect(() => {
    if (history.state?.inApp) history.replaceState(null, '')
    const onPop = () => {
      abortRef.current?.abort()
      setScreen('home')
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const open = (next: Screen) => {
    if (!history.state?.inApp) history.pushState(IN_APP, '')
    setScreen(next)
    window.scrollTo(0, 0)
  }

  const goHome = () => {
    abortRef.current?.abort()
    if (history.state?.inApp) history.back()
    else setScreen('home')
  }

  const run = async (input: CheckInput) => {
    lastInputRef.current = input
    abortRef.current?.abort()
    const abort = new AbortController()
    abortRef.current = abort
    open('loading')
    void loadResult()
    const live = demoChoice === 'live'
    try {
      const response = live
        ? await checkOffer(input, abort.signal, { voice: !isLowData() })
        : await loadFixture(demoChoice, abort.signal)
      if (abort.signal.aborted) return
      if (live) recordVerdict(response.verdict.level)
      setResult({ response, isDemo: !live, input })
      setScreen('result')
    } catch (err) {
      if (abort.signal.aborted) return
      setErrorKind(err instanceof ApiError ? err.kind : 'invalid')
      setScreen('error')
    }
  }

  // Nothing leaves the phone until the user has agreed once. Demo answers never leave it at all.
  const submit = (input: CheckInput) => {
    if (demoChoice === 'live' && !load('consent', false)) {
      lastInputRef.current = input
      open('consent')
    } else {
      void run(input)
    }
  }

  const agree = () => {
    save('consent', true)
    if (lastInputRef.current) void run(lastInputRef.current)
  }

  // A check that failed for lack of a connection is sent again as soon as the phone is back online.
  // It waits in memory only, so it is lost if the app is closed: documents are never written to the phone.
  const retryRef = useRef(() => {})
  retryRef.current = () => lastInputRef.current && void run(lastInputRef.current)
  useEffect(() => {
    if (screen !== 'error' || errorKind !== 'offline') return
    const onOnline = () => retryRef.current()
    window.addEventListener('online', onOnline)
    return () => window.removeEventListener('online', onOnline)
  }, [screen, errorKind])

  const toMore = () => setScreen('more')

  return (
    <main className="mx-auto min-h-dvh w-full max-w-md px-4 pt-[max(0.5rem,env(safe-area-inset-top))]">
      <Suspense fallback={null}>
        {screen === 'home' && (
          <Home
            onSubmit={submit}
            onType={() => open('type')}
            onPrivacy={() => open('privacy')}
            onMore={() => open('more')}
            onDemoMenu={demoBuild ? () => setDemoMenuOpen(true) : undefined}
          />
        )}
        {screen === 'type' && <TypeOffer onSubmit={(text) => submit({ text })} onBack={goHome} />}
        {screen === 'privacy' && <Privacy onBack={goHome} />}
        {screen === 'consent' && <Consent onAgree={agree} onBack={goHome} />}
        {screen === 'loading' && <Loading onCancel={goHome} />}
        {screen === 'result' && result && (
          <Result
            {...result}
            onAgain={goHome}
            onResubmit={submit}
            onGuide={(country) => {
              setGuide({ country, from: 'result' })
              open('guide')
            }}
          />
        )}
        {screen === 'error' && (
          <CheckFailed kind={errorKind} onRetry={() => retryRef.current()} onBack={goHome} />
        )}
        {screen === 'more' && (
          <More
            onBack={goHome}
            onOpen={(tool) => {
              setGuide({ country: null, from: 'more' })
              open(tool)
            }}
          />
        )}
        {screen === 'guide' && (
          <GuideScreen
            initialCountry={guide.country}
            onBack={() => (guide.from === 'result' && result ? setScreen('result') : toMore())}
          />
        )}
        {screen === 'wages' && <Wages onBack={toMore} />}
        {screen === 'sos' && <Sos onBack={toMore} />}
        {screen === 'helper' && <Helper onBack={toMore} />}
        {screen === 'stats' && <StatsScreen onBack={toMore} />}
        {demoMenuOpen && (
          <DemoMenu choice={demoChoice} onChoose={setDemoChoice} onClose={() => setDemoMenuOpen(false)} />
        )}
      </Suspense>
    </main>
  )
}
