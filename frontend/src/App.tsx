import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { ApiError, checkOffer, type ApiErrorKind, type CheckInput } from './api'
import { isDemoBuild, loadFixture, type DemoChoice } from './demo'
import { Home } from './screens/Home'
import { CheckFailed, Loading } from './screens/Status'
import type { CheckResponse } from './types'

// Home is the only screen in the first download; the rest arrive when needed.
const loadResult = () => import('./screens/Result')
const Result = lazy(loadResult)
const TypeOffer = lazy(() => import('./screens/TypeOffer'))
const Privacy = lazy(() => import('./screens/Privacy'))
const DemoMenu = lazy(() => import('./components/DemoMenu'))

type Screen = 'home' | 'type' | 'privacy' | 'loading' | 'result' | 'error'

const IN_APP = { inApp: true }

export default function App() {
  const [screen, setScreen] = useState<Screen>('home')
  const [result, setResult] = useState<{ response: CheckResponse; isDemo: boolean } | null>(null)
  const [errorKind, setErrorKind] = useState<ApiErrorKind>('offline')
  const [demoBuild] = useState(isDemoBuild)
  const [demoChoice, setDemoChoice] = useState<DemoChoice>(demoBuild ? 'red' : 'live')
  const [demoMenuOpen, setDemoMenuOpen] = useState(false)
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

  const submit = async (input: CheckInput) => {
    lastInputRef.current = input
    abortRef.current?.abort()
    const abort = new AbortController()
    abortRef.current = abort
    open('loading')
    void loadResult()
    try {
      const response =
        demoChoice === 'live' ? await checkOffer(input, abort.signal) : await loadFixture(demoChoice, abort.signal)
      if (abort.signal.aborted) return
      setResult({ response, isDemo: demoChoice !== 'live' })
      setScreen('result')
    } catch (err) {
      if (abort.signal.aborted) return
      setErrorKind(err instanceof ApiError ? err.kind : 'invalid')
      setScreen('error')
    }
  }

  return (
    <main className="mx-auto min-h-dvh w-full max-w-md px-4 pt-[max(0.5rem,env(safe-area-inset-top))]">
      <Suspense fallback={null}>
        {screen === 'home' && (
          <Home
            onSubmit={submit}
            onType={() => open('type')}
            onPrivacy={() => open('privacy')}
            onDemoMenu={demoBuild ? () => setDemoMenuOpen(true) : undefined}
          />
        )}
        {screen === 'type' && <TypeOffer onSubmit={(text) => submit({ text })} onBack={goHome} />}
        {screen === 'privacy' && <Privacy onBack={goHome} />}
        {screen === 'loading' && <Loading onCancel={goHome} />}
        {screen === 'result' && result && <Result {...result} onAgain={goHome} />}
        {screen === 'error' && (
          <CheckFailed
            kind={errorKind}
            onRetry={() => lastInputRef.current && submit(lastInputRef.current)}
            onBack={goHome}
          />
        )}
        {demoMenuOpen && (
          <DemoMenu choice={demoChoice} onChoose={setDemoChoice} onClose={() => setDemoMenuOpen(false)} />
        )}
      </Suspense>
    </main>
  )
}
