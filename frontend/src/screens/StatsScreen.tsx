import { useEffect, useState } from 'react'
import { fetchEvaluation, fetchStats } from '../api'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import { LEVELS, type Evaluation, type Stats } from '../types'

const heading = 'mb-3 text-2xl font-bold'

/** Server-side counts of checks: how many, which verdicts, which destinations, which warning signs. */
export default function StatsScreen({ onBack }: { onBack: () => void }) {
  const { t, lang, num } = useI18n()
  const [stats, setStats] = useState<Stats | null>(null)
  const [failed, setFailed] = useState(false)
  // null = not loaded yet, false = this server has none (for example a stubbed engine).
  const [quality, setQuality] = useState<Evaluation | false | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    fetchStats(abort.signal).then(setStats, () => !abort.signal.aborted && setFailed(true))
    fetchEvaluation(abort.signal).then(setQuality, () => !abort.signal.aborted && setQuality(false))
    return () => abort.abort()
  }, [])

  const countries = Object.entries(stats?.by_country ?? {})
  const since = stats && new Date(stats.since)

  return (
    <div className="flex flex-col gap-6 pb-8">
      <ScreenHeader onBack={onBack} />
      <div>
        <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.stats.title}</h1>
        <p className="mt-1 text-lg text-muted">{t.stats.intro}</p>
      </div>
      {!stats && !failed && <p role="status" className="text-lg text-muted">{t.stats.loading}</p>}
      {failed && (
        <p role="alert" className="rounded-3xl border border-stop/40 bg-stop-tint p-3 text-lg font-semibold">
          {t.stats.failed}
        </p>
      )}
      {quality !== null && (
        <section>
          <h2 className={heading}>{t.stats.quality}</h2>
          {quality === false ? (
            <p className="text-lg text-muted">{t.stats.qualityFailed}</p>
          ) : (
            <>
              <p className="mb-2 text-muted">{t.stats.qualityIntro}</p>
              <dl className="flex flex-col gap-2">
                <div className={`rounded-3xl p-3 ${quality.fraud_green === 0 ? 'bg-go-tint' : 'border border-stop/40 bg-stop-tint'}`}>
                  <dt className="font-semibold">{t.stats.fraudGreen}</dt>
                  <dd className="text-3xl font-bold tabular-nums">
                    {num(quality.fraud_green)} / {num(quality.fraud_total)}
                  </dd>
                </div>
                <div className="rounded-3xl bg-white shadow-card p-3">
                  <dt className="text-muted">{t.stats.fraudRed}</dt>
                  <dd className="text-2xl font-bold tabular-nums">
                    {num(quality.fraud_red)} / {num(quality.fraud_total)}
                  </dd>
                </div>
                <div className="rounded-3xl bg-white shadow-card p-3">
                  <dt className="text-muted">{t.stats.correct}</dt>
                  <dd className="text-2xl font-bold tabular-nums">
                    {num(quality.correct)} / {num(quality.total)}
                  </dd>
                </div>
              </dl>
              <p className="mt-2 text-sm text-muted">
                {t.stats.cases}: {num(quality.real)} {t.stats.realCases}, {num(quality.synthetic)} {t.stats.syntheticCases}.{' '}
                {t.stats.asOf}: {quality.as_of}
              </p>
            </>
          )}
        </section>
      )}
      {stats && (
        <>
          <dl className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded-3xl bg-white shadow-card p-3">
              <dt className="text-muted">{t.stats.checks}</dt>
              <dd className="text-3xl font-bold tabular-nums">{num(stats.checks)}</dd>
            </div>
            <div className="rounded-3xl bg-white shadow-card p-3">
              <dt className="text-muted">{t.stats.reports}</dt>
              <dd className="text-3xl font-bold tabular-nums">{num(stats.reports)}</dd>
            </div>
            {LEVELS.map((level) => (
              <div key={level} className="rounded-3xl bg-white shadow-card p-3 last:col-span-2">
                <dt className="leading-tight text-muted">{t.verdict[level].title}</dt>
                <dd className="text-3xl font-bold tabular-nums">{num(stats.by_level[level] ?? 0)}</dd>
              </div>
            ))}
          </dl>

          {countries.length > 0 && (
            <section>
              <h2 className={heading}>{t.stats.byCountry}</h2>
              <ul className="flex flex-col gap-2">
                {countries.map(([code, count]) => (
                  <li key={code} className="rounded-3xl bg-white shadow-card p-3">
                    <div className="flex justify-between text-lg font-semibold">
                      <span>{t.countries[code] ?? code}</span>
                      <span className="tabular-nums">{num(count)}</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-line">
                      <div className="h-2 rounded-full bg-stamp" style={{ width: `${(count / Math.max(1, stats.checks)) * 100}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {stats.top_reasons.length > 0 && (
            <section>
              <h2 className={heading}>{t.stats.topReasons}</h2>
              <ol className="flex flex-col gap-1 rounded-3xl bg-white shadow-card p-4">
                {stats.top_reasons.map(({ code, count }) => (
                  <li key={code} className="flex justify-between gap-3 border-b border-line py-2 last:border-0">
                    <code className="text-sm break-all">{code}</code>
                    <span className="font-semibold tabular-nums">{num(count)}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {since && !Number.isNaN(since.getTime()) && (
            <p className="text-sm text-muted">
              {t.stats.since}: {since.toLocaleString(lang === 'bn' ? 'bn-BD' : 'en-GB')}
            </p>
          )}
        </>
      )}
    </div>
  )
}
