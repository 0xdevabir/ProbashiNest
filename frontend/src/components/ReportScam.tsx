import { useState } from 'react'
import { ApiError, sendReport } from '../api'
import { useI18n } from '../i18n'
import type { CheckResult, ScamReport } from '../types'

// The same shapes the server accepts (backend/models.py); anything else is left out, not sent.
const CODE = /^[A-Z][A-Z0-9_]{2,39}$/
const LICENCE = /^[\w \-/]{1,20}$/

export function buildReport(result: CheckResult): ScamReport {
  const { offer, verdict } = result
  const country = offer.destination_country?.trim()
  const licence = offer.agency_license_no?.trim()
  return {
    consent: true,
    level: verdict.level,
    reason_codes: verdict.reasons
      .map((reason) => reason.code)
      .filter((code) => CODE.test(code))
      .slice(0, 20),
    ...(country && /^[A-Za-z]{2}$/.test(country) ? { destination_country: country } : {}),
    ...(offer.agency_name?.trim() ? { agency_name: offer.agency_name.trim().slice(0, 120) } : {}),
    ...(licence && LICENCE.test(licence) ? { agency_license_no: licence } : {}),
  }
}

/** Lets the user tell us about a risky offer. Nothing is sent until they tick the box and press send. */
export function ReportScam({ result }: { result: CheckResult }) {
  const { t } = useI18n()
  const [agreed, setAgreed] = useState(false)
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'failed'>('idle')

  const send = async () => {
    setState('sending')
    try {
      await sendReport(buildReport(result))
      setState('sent')
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
      setState('failed')
    }
  }

  if (state === 'sent') {
    return (
      <p role="status" className="rounded-2xl bg-go-tint p-4 text-lg font-semibold print:hidden">
        {t.guidance.report.sent}
      </p>
    )
  }

  return (
    <section className="flex flex-col gap-3 rounded-2xl border-2 border-line bg-white p-4 print:hidden">
      <div>
        <h2 className="text-xl font-bold">{t.guidance.report.title}</h2>
        <p className="text-muted">{t.guidance.report.help}</p>
      </div>
      <label className="flex cursor-pointer items-start gap-3 text-lg leading-snug">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(event) => setAgreed(event.target.checked)}
          className="mt-1 size-7 shrink-0 accent-stamp"
        />
        {t.guidance.report.consent}
      </label>
      <button
        type="button"
        disabled={!agreed || state === 'sending'}
        onClick={send}
        className="min-h-14 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep disabled:bg-line disabled:text-muted"
      >
        {t.guidance.report.send}
      </button>
      {state === 'failed' && (
        <p role="alert" className="font-semibold text-stop">
          {t.guidance.report.failed}
        </p>
      )}
    </section>
  )
}
