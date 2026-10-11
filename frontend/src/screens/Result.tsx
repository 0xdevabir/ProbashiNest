import { AudioAnswer } from '../components/AudioAnswer'
import { PhoneIcon } from '../components/icons'
import { OfferDetails } from '../components/OfferDetails'
import { ScreenHeader } from '../components/ScreenHeader'
import { VerdictCard } from '../components/VerdictCard'
import { useI18n } from '../i18n'
import type { CheckResponse, Source } from '../types'

function SourceLine({ source }: { source: Source }) {
  const { t } = useI18n()
  // Only http(s) links are rendered as links; anything else from the API stays plain text.
  const safeUrl = source.url && /^https?:\/\//i.test(source.url) ? source.url : null
  return (
    <p className="mt-1 text-sm text-muted">
      {t.result.source}:{' '}
      {safeUrl ? (
        <a href={safeUrl} target="_blank" rel="noopener noreferrer" className="font-semibold text-stamp underline">
          {source.title}
        </a>
      ) : (
        source.title
      )}
    </p>
  )
}

interface ResultProps {
  response: CheckResponse
  /** True when the response is a bundled synthetic fixture. */
  isDemo: boolean
  onAgain: () => void
}

export default function Result({ response, isDemo, onAgain }: ResultProps) {
  const { t, lang, num } = useI18n()
  const { verdict, offer } = response
  const heading = 'mb-3 text-2xl font-bold'

  const spoken = [
    `${t.verdict[verdict.level].title}।`,
    ...verdict.reasons.map((reason) => reason.message_bn),
    ...verdict.next_steps_bn,
  ].join(' ')

  return (
    <div className="flex flex-col gap-6 pb-8">
      <ScreenHeader onBack={onAgain}>
        {isDemo && (
          <span className="rounded-full bg-ink px-3 py-1 text-sm font-semibold text-white">{t.result.demoBadge}</span>
        )}
      </ScreenHeader>

      <div className="flex flex-col gap-3">
        <VerdictCard level={verdict.level} />
        <AudioAnswer audioBase64={response.audio_base64} fallbackText={spoken} />
      </div>

      {verdict.reasons.length > 0 && (
        <section>
          <h2 className={heading}>{t.result.reasons}</h2>
          <ul className="flex flex-col gap-2">
            {verdict.reasons.map((reason) => (
              <li key={reason.code} className="rounded-2xl border-l-8 border-stamp bg-white p-4">
                <p className="text-lg leading-snug font-semibold">
                  {lang === 'bn' ? reason.message_bn : reason.message_en || reason.message_bn}
                </p>
                {reason.source && <SourceLine source={reason.source} />}
              </li>
            ))}
          </ul>
        </section>
      )}

      {verdict.next_steps_bn.length > 0 && (
        <section>
          <h2 className={heading}>{t.result.steps}</h2>
          <ol className="flex flex-col gap-2">
            {verdict.next_steps_bn.map((step, i) => (
              <li key={step}>
                <label className="flex min-h-16 cursor-pointer items-center gap-3 rounded-2xl bg-white p-3 has-checked:bg-go-tint">
                  <span className="grid size-10 shrink-0 place-items-center rounded-full bg-ink text-xl font-bold text-white">
                    {num(i + 1)}
                  </span>
                  <span lang="bn" className="grow text-lg leading-snug">{step}</span>
                  <input type="checkbox" className="size-7 shrink-0 accent-go" />
                </label>
              </li>
            ))}
          </ol>
        </section>
      )}

      {verdict.helplines.length > 0 && (
        <section>
          <h2 className={heading}>{t.result.helplines}</h2>
          <ul className="flex flex-col gap-2">
            {verdict.helplines.map((line) => (
              <li key={line.phone}>
                <a
                  href={`tel:${line.phone.replace(/[^\d+]/g, '')}`}
                  aria-label={`${t.result.call}: ${line.name}, ${line.phone}`}
                  className="flex min-h-16 items-center gap-3 rounded-2xl border-2 border-go bg-white p-3 text-ink active:bg-go-tint"
                >
                  <span className="grid size-12 shrink-0 place-items-center rounded-full bg-go text-white">
                    <PhoneIcon className="size-6" />
                  </span>
                  <span className="min-w-0">
                    <span className="block leading-snug">{line.name}</span>
                    <span className="block text-2xl leading-tight font-bold tabular-nums">{line.phone}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <OfferDetails offer={offer} transcript={response.transcript_bn} />

      <p lang="bn" className="text-base text-muted">{verdict.disclaimer_bn}</p>

      <button
        type="button"
        onClick={onAgain}
        className="min-h-16 rounded-2xl border-2 border-stamp bg-white px-5 text-xl font-bold text-stamp active:bg-paper"
      >
        {t.result.again}
      </button>
    </div>
  )
}
