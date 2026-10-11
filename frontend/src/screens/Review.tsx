import { useState, type FormEvent } from 'react'
import { ApiError, fetchReviewQueue } from '../api'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import type { ReviewQueue } from '../types'

const heading = 'mb-3 text-2xl font-bold'

/** For review staff, opened at #review. The token lives in this screen's memory only. */
export default function Review({ onBack }: { onBack: () => void }) {
  const { t, num } = useI18n()
  const [token, setToken] = useState('')
  const [queue, setQueue] = useState<ReviewQueue | null>(null)
  const [state, setState] = useState<'idle' | 'loading' | 'refused'>('idle')

  const open = async (event: FormEvent) => {
    event.preventDefault()
    setState('loading')
    try {
      setQueue(await fetchReviewQueue(token.trim()))
      setState('idle')
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      setState('refused')
    }
  }

  return (
    <div className="flex flex-col gap-6 pb-8">
      <ScreenHeader onBack={onBack} />
      <div>
        <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.review.title}</h1>
        <p className="mt-1 text-lg text-muted">{t.review.intro}</p>
      </div>

      {!queue && (
        <form onSubmit={open} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-lg font-semibold">
            {t.review.token}
            <input
              type="password"
              autoComplete="off"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              className="min-h-14 rounded-xl border-2 border-line bg-white px-3 text-lg font-normal"
            />
          </label>
          <button
            type="submit"
            disabled={!token.trim() || state === 'loading'}
            className="min-h-14 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep disabled:bg-line disabled:text-muted"
          >
            {t.review.open}
          </button>
          {state === 'refused' && (
            <p role="alert" className="rounded-2xl border-2 border-stop bg-stop-tint p-3 text-lg font-semibold">
              {t.review.refused}
            </p>
          )}
        </form>
      )}

      {queue && (
        <>
          <p className="rounded-2xl bg-white p-4 text-lg">
            {t.review.total}: <strong className="tabular-nums">{num(queue.total)}</strong>
          </p>
          {queue.total === 0 && <p className="text-lg text-muted">{t.review.none}</p>}

          {queue.agencies.length > 0 && (
            <section>
              <h2 className={heading}>{t.review.agencies}</h2>
              <ul className="flex flex-col gap-2">
                {queue.agencies.map((agency) => (
                  <li
                    key={`${agency.agency_license_no}|${agency.agency_name}`}
                    className="flex justify-between gap-3 rounded-2xl bg-white p-3"
                  >
                    <span>
                      <span className="block text-lg font-semibold">{agency.agency_name ?? t.review.noName}</span>
                      <span className="block text-muted">
                        {[agency.agency_license_no, agency.last_date].filter(Boolean).join(' · ')}
                      </span>
                    </span>
                    <span className="shrink-0 font-bold tabular-nums">
                      {num(agency.count)} {t.review.times}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {queue.reports.length > 0 && (
            <section>
              <h2 className={heading}>{t.review.recent}</h2>
              <ul className="flex flex-col gap-2">
                {queue.reports.map((report, i) => (
                  <li key={i} className="rounded-2xl bg-white p-3">
                    <div className="flex justify-between gap-3 font-semibold">
                      <span>{t.verdict[report.level]?.title ?? report.level}</span>
                      <span className="tabular-nums text-muted">{report.date}</span>
                    </div>
                    <p>
                      {[
                        report.agency_name,
                        report.agency_license_no,
                        report.destination_country && (t.countries[report.destination_country] ?? report.destination_country),
                      ]
                        .filter(Boolean)
                        .join(' · ') || t.review.noName}
                    </p>
                    <code className="text-sm break-all text-muted">{report.reason_codes.join(', ')}</code>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}
