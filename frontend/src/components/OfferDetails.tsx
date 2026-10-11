import { useI18n } from '../i18n'
import type { Translations } from '../i18n/translations'
import type { ExtractedOffer } from '../types'
import { ChevronIcon } from './icons'

type FieldKey = keyof Translations['fields']

// Below this the extractor itself is unsure, so the reader is told to double-check.
const LOW_CONFIDENCE = 0.5

interface OfferDetailsProps {
  offer: ExtractedOffer
  transcript: string | null
}

export function OfferDetails({ offer, transcript }: OfferDetailsProps) {
  const { t, num } = useI18n()

  const values: Record<FieldKey, string | null> = {
    employer_name: offer.employer_name,
    job_title: offer.job_title,
    destination_country:
      offer.destination_country && (t.countries[offer.destination_country] ?? offer.destination_country),
    monthly_salary:
      offer.monthly_salary?.amount != null
        ? `${num(offer.monthly_salary.amount)} ${offer.monthly_salary.currency ?? ''}`.trim()
        : null,
    agency_name: offer.agency_name,
    agency_license_no: offer.agency_license_no,
    fees_charged_bdt: offer.fees_charged_bdt != null ? `${num(offer.fees_charged_bdt)} BDT` : null,
    contract_duration_months:
      offer.contract_duration_months != null
        ? `${num(offer.contract_duration_months)} ${t.result.months}`
        : null,
    visa_type: offer.visa_type,
  }

  return (
    <details className="group rounded-3xl bg-white shadow-card">
      <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-3 px-4 text-lg font-bold [&::-webkit-details-marker]:hidden">
        {t.result.read}
        <ChevronIcon className="size-6 shrink-0 transition-transform group-open:rotate-180" />
      </summary>
      <div className="border-t border-line px-4 pb-4">
        {offer.confidence < LOW_CONFIDENCE && (
          <p className="mt-3 rounded-2xl bg-wait-tint p-3 font-semibold text-wait-ink">{t.result.lowConfidence}</p>
        )}
        {transcript && (
          <div className="border-b border-line py-3">
            <p className="text-muted">{t.result.heard}</p>
            <p lang="bn" className="text-lg">{transcript}</p>
          </div>
        )}
        <dl>
          {(Object.keys(values) as FieldKey[]).map((key) => (
            <div key={key} className="flex items-baseline justify-between gap-4 border-b border-line py-3 last:border-0">
              <dt className="shrink-0 text-muted">{t.fields[key]}</dt>
              <dd className={`text-right text-lg font-semibold ${values[key] ? '' : 'text-wait-ink'}`}>
                {values[key] || t.result.notFound}
              </dd>
            </div>
          ))}
        </dl>
        {offer.raw_text && (
          <details className="mt-2">
            <summary className="min-h-12 cursor-pointer py-3 font-semibold text-stamp underline">{t.result.rawText}</summary>
            <p className="rounded-2xl bg-paper p-3 text-base break-words whitespace-pre-wrap">{offer.raw_text}</p>
          </details>
        )}
      </div>
    </details>
  )
}
