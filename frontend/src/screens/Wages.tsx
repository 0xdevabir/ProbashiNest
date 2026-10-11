import { useState, type FormEvent } from 'react'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import { loadWages, putWage, removeWage, wageSummary } from '../wages'

const field = 'min-h-14 w-full rounded-xl border-2 border-line bg-white px-3 text-xl'

/** A pay diary that never leaves the phone, so a shortfall can be shown to a helpline later. */
export default function Wages({ onBack }: { onBack: () => void }) {
  const { t, num } = useI18n()
  const [entries, setEntries] = useState(loadWages)
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7))
  const [promised, setPromised] = useState(() => (loadWages()[0]?.promised ?? '').toString())
  const [received, setReceived] = useState('')
  const summary = wageSummary(entries)

  const add = (event: FormEvent) => {
    event.preventDefault()
    const entry = { month, promised: Number(promised), received: Number(received) }
    const valid = /^\d{4}-\d{2}$/.test(month) && [entry.promised, entry.received].every((n) => Number.isFinite(n) && n >= 0)
    if (!valid || promised === '' || received === '') return
    setEntries(putWage(entries, entry))
    setReceived('')
  }

  return (
    <div className="flex flex-col gap-5 pb-8">
      <ScreenHeader onBack={onBack} />
      <div>
        <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.wages.title}</h1>
        <p className="mt-1 text-lg text-muted">{t.wages.intro}</p>
      </div>

      <form onSubmit={add} className="flex flex-col gap-3 rounded-2xl border-2 border-stamp bg-white p-4">
        <label className="flex flex-col gap-1 text-lg font-semibold">
          {t.wages.month}
          <input type="month" required value={month} onChange={(e) => setMonth(e.target.value)} className={field} />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-lg font-semibold">
            {t.wages.promised}
            <input type="number" inputMode="decimal" min="0" required value={promised} onChange={(e) => setPromised(e.target.value)} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-lg font-semibold">
            {t.wages.received}
            <input type="number" inputMode="decimal" min="0" required value={received} onChange={(e) => setReceived(e.target.value)} className={field} />
          </label>
        </div>
        <button type="submit" className="min-h-14 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep">
          {t.wages.add}
        </button>
      </form>

      {entries.length === 0 ? (
        <p className="text-lg text-muted">{t.wages.none}</p>
      ) : (
        <>
          <div
            role="status"
            className={`rounded-2xl p-4 text-xl font-bold ${summary.shortfall > 0 ? 'bg-stop-tint text-stop' : 'bg-go-tint text-go'}`}
          >
            {summary.shortfall > 0 ? `${t.wages.shortfall}: ${num(summary.shortfall)}` : t.wages.allPaid}
            {summary.shortfall > 0 && <p className="mt-1 text-base font-semibold text-ink">{t.wages.advice}</p>}
          </div>
          <ul className="flex flex-col gap-2">
            {entries.map((entry) => (
              <li key={entry.month} className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4">
                <span>
                  <span className="block text-lg font-bold tabular-nums">{entry.month}</span>
                  <span className="block text-muted">
                    {t.wages.promised}: {num(entry.promised)} · {t.wages.received}: {num(entry.received)}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => setEntries(removeWage(entries, entry.month))}
                  aria-label={`${t.wages.remove}: ${entry.month}`}
                  className="min-h-12 px-2 font-semibold text-stop underline"
                >
                  {t.wages.remove}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
