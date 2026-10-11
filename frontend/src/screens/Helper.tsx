import { useState } from 'react'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import { isHelperMode, loadTally, resetTally, setHelperMode } from '../helper'
import { LEVELS } from '../types'

/** For people who check offers on behalf of others: a count of results, and nothing else. */
export default function Helper({ onBack }: { onBack: () => void }) {
  const { t, num } = useI18n()
  const [on, setOn] = useState(isHelperMode)
  const [tally, setTally] = useState(loadTally)

  const toggle = (next: boolean) => {
    setHelperMode(next)
    setOn(next)
  }

  const reset = () => {
    resetTally()
    setTally(loadTally())
  }

  return (
    <div className="flex flex-col gap-5 pb-8">
      <ScreenHeader onBack={onBack} />
      <div>
        <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.helper.title}</h1>
        <p className="mt-1 text-lg text-muted">{t.helper.intro}</p>
      </div>
      <label className="flex cursor-pointer items-center gap-3 rounded-2xl bg-white p-4 text-xl font-bold">
        <span className="grow">{t.helper.on}</span>
        <input type="checkbox" checked={on} onChange={(e) => toggle(e.target.checked)} className="size-7 shrink-0 accent-stamp" />
      </label>
      <section>
        <h2 className="mb-3 text-2xl font-bold">{t.helper.counts}</h2>
        <dl className="grid grid-cols-3 gap-2 text-center">
          {LEVELS.map((level) => (
            <div key={level} className="rounded-2xl bg-white p-3">
              <dt className="leading-tight text-muted">{t.verdict[level].title}</dt>
              <dd className="text-3xl font-bold tabular-nums">{num(tally[level])}</dd>
            </div>
          ))}
        </dl>
      </section>
      <button type="button" onClick={reset} className="min-h-12 font-semibold text-stamp underline">
        {t.helper.reset}
      </button>
    </div>
  )
}
