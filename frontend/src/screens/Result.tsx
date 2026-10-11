import { useState } from 'react'
import type { CheckInput } from '../api'
import { AudioAnswer } from '../components/AudioAnswer'
import { FollowUp } from '../components/FollowUp'
import { HelplineList } from '../components/HelplineList'
import { OfferDetails } from '../components/OfferDetails'
import { ReportScam } from '../components/ReportScam'
import { ScreenHeader } from '../components/ScreenHeader'
import { SourceNote } from '../components/SourceNote'
import { VerdictCard } from '../components/VerdictCard'
import { useI18n } from '../i18n'
import { copyText, shareText, verdictText } from '../share'
import type { CheckResult } from '../types'

// How well the extractor says it read the offer. Below CLEAR the user is told to compare.
const CLEAR = 0.8
const PARTLY = 0.5

const quietAction =
  'min-h-14 rounded-3xl border border-stamp/20 bg-white shadow-card px-4 text-lg font-bold text-stamp active:bg-paper print:hidden'

interface ResultProps {
  response: CheckResult
  /** True when the response is a bundled synthetic fixture. */
  isDemo: boolean
  /** What was sent, so a follow-up check can send it again with more facts. */
  input: CheckInput | null
  onAgain: () => void
  onResubmit: (input: CheckInput) => void
  onGuide: (country: string) => void
}

export default function Result({ response, isDemo, input, onAgain, onResubmit, onGuide }: ResultProps) {
  const { t, lang, num } = useI18n()
  const { verdict, offer, guidance } = response
  const heading = 'mb-3 text-2xl font-bold'
  const [notice, setNotice] = useState<string | null>(null)

  const spoken = [
    `${t.verdict[verdict.level].title}।`,
    ...verdict.reasons.map((reason) => reason.message_bn),
    ...verdict.next_steps_bn,
  ].join(' ')

  const confidence = guidance?.confidence ?? offer.confidence
  const readNote =
    confidence >= CLEAR ? t.guidance.readClear : confidence >= PARTLY ? t.guidance.readPartly : t.guidance.readPoor
  const country = /^[A-Za-z]{2}$/.test(offer.destination_country ?? '') ? offer.destination_country!.toUpperCase() : null

  const share = async () => {
    const outcome = await shareText(verdictText(response, t))
    setNotice(outcome === 'copied' ? t.guidance.copied : outcome === 'failed' ? t.guidance.copyFailed : null)
  }

  const copyComplaint = async () => {
    const ok = await copyText(guidance?.complaint_draft_bn ?? '')
    setNotice(ok ? t.guidance.copied : t.guidance.copyFailed)
  }

  const print = () => {
    // Closed sections would print empty, so open them all first.
    document.querySelectorAll('details').forEach((details) => (details.open = true))
    window.print()
  }

  return (
    <div className="flex flex-col gap-6 pb-8">
      <ScreenHeader onBack={onAgain}>
        {isDemo && (
          <span className="rounded-full bg-ink px-3 py-1 text-sm font-semibold text-white">{t.result.demoBadge}</span>
        )}
      </ScreenHeader>

      <div className="flex flex-col gap-3">
        <VerdictCard level={verdict.level} />
        <p className={`text-base ${confidence >= CLEAR ? 'text-muted' : 'font-semibold text-wait-ink'}`}>{readNote}</p>
        <div className="print:hidden">
          <AudioAnswer audioBase64={response.audio_base64} fallbackText={spoken} />
        </div>
        <p className="hidden text-sm print:block">
          {t.guidance.printedOn}: {new Date().toLocaleString(lang === 'bn' ? 'bn-BD' : 'en-GB')}
        </p>
      </div>

      {verdict.reasons.length > 0 && (
        <section>
          <h2 className={heading}>{t.result.reasons}</h2>
          <ul className="flex flex-col gap-2">
            {verdict.reasons.map((reason) => {
              const explainers = guidance?.explainers.filter((e) => e.code === reason.code) ?? []
              return (
                <li key={reason.code} className="rounded-3xl border-l-8 border-stamp bg-white shadow-card p-4">
                  <p className="text-lg leading-snug font-semibold">
                    {lang === 'bn' ? reason.message_bn : reason.message_en || reason.message_bn}
                  </p>
                  <SourceNote source={reason.source} />
                  {explainers.length > 0 && (
                    <details className="mt-2">
                      <summary className="min-h-12 cursor-pointer py-2 font-semibold text-stamp underline">
                        {t.guidance.why}
                      </summary>
                      {explainers.map((e) => (
                        <div key={e.text_bn} className="mt-1 rounded-2xl bg-paper p-3">
                          <p className="text-base leading-snug">{lang === 'bn' ? e.text_bn : e.text_en || e.text_bn}</p>
                          <SourceNote source={e.source} verified={e.verified} lastChecked={e.last_checked} />
                        </div>
                      ))}
                    </details>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {input && <FollowUp input={input} result={response} onResubmit={onResubmit} />}

      {verdict.next_steps_bn.length > 0 && (
        <section>
          <h2 className={heading}>{t.result.steps}</h2>
          <ol className="flex flex-col gap-2">
            {verdict.next_steps_bn.map((step, i) => (
              <li key={step}>
                <label className="flex min-h-16 cursor-pointer items-center gap-3 rounded-3xl bg-white shadow-card p-3 has-checked:bg-go-tint">
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

      {guidance && guidance.ask_agent.length > 0 && (
        <section>
          <h2 className={heading}>{t.guidance.askAgent}</h2>
          <ul className="flex list-disc flex-col gap-2 rounded-3xl bg-white shadow-card p-4 pl-9 text-lg leading-snug">
            {guidance.ask_agent.map((q) => (
              <li key={q.text_bn}>{lang === 'bn' ? q.text_bn : q.text_en || q.text_bn}</li>
            ))}
          </ul>
        </section>
      )}

      {verdict.helplines.length > 0 && (
        <section>
          <h2 className={heading}>{t.result.helplines}</h2>
          <HelplineList helplines={verdict.helplines} />
        </section>
      )}

      {guidance?.complaint_draft_bn && (
        <section>
          <h2 className={heading}>{t.guidance.complaint}</h2>
          <p className="mb-2 text-muted">{t.guidance.complaintHelp}</p>
          <p lang="bn" className="rounded-3xl bg-white shadow-card p-4 text-base break-words whitespace-pre-wrap">
            {guidance.complaint_draft_bn}
          </p>
          <button type="button" onClick={copyComplaint} className={`mt-2 w-full ${quietAction}`}>
            {t.guidance.copy}
          </button>
        </section>
      )}

      <div className="grid grid-cols-2 gap-3 print:hidden">
        <button type="button" onClick={share} className={quietAction}>
          {t.guidance.share}
        </button>
        <button type="button" onClick={print} className={quietAction}>
          {t.guidance.print}
        </button>
      </div>
      {notice && (
        <p role="status" className="-mt-3 text-center font-semibold print:hidden">
          {notice}
        </p>
      )}

      {country && (
        <button type="button" onClick={() => onGuide(country)} className={quietAction}>
          {t.guidance.guideLink}
        </button>
      )}

      {verdict.level !== 'green' && !isDemo && <ReportScam result={response} />}

      <OfferDetails offer={offer} transcript={response.transcript_bn} />

      <p lang="bn" className="text-base text-muted">{verdict.disclaimer_bn}</p>

      <button
        type="button"
        onClick={onAgain}
        className="min-h-16 rounded-full border border-stamp/20 bg-white px-5 text-xl font-bold text-stamp active:bg-paper print:hidden"
      >
        {t.result.again}
      </button>
    </div>
  )
}
