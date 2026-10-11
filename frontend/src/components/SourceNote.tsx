import { useI18n } from '../i18n'
import type { Source } from '../types'

interface SourceNoteProps {
  source: Source | null
  /** Pass false to warn that the source is not an official one yet. Omit when unknown. */
  verified?: boolean
  /** ISO date the source was last checked. */
  lastChecked?: string | null
}

/** Where a statement comes from, when it was checked, and whether that source is confirmed. */
export function SourceNote({ source, verified, lastChecked }: SourceNoteProps) {
  const { t, lang } = useI18n()
  // Only http(s) links are rendered as links; anything else from the API stays plain text.
  const safeUrl = source?.url && /^https?:\/\//i.test(source.url) ? source.url : null
  const parsed = lastChecked ? new Date(`${lastChecked}T00:00:00`) : null
  const checked = parsed && !Number.isNaN(parsed.getTime()) ? parsed : null
  if (!source && verified !== false && !checked) return null
  return (
    <div className="mt-1 text-sm text-muted">
      {source && (
        <p>
          {t.result.source}:{' '}
          {safeUrl ? (
            <a href={safeUrl} target="_blank" rel="noopener noreferrer" className="font-semibold text-stamp underline">
              {source.title}
            </a>
          ) : (
            source.title
          )}
        </p>
      )}
      {checked && (
        <p>
          {t.guidance.lastChecked}:{' '}
          {checked.toLocaleDateString(lang === 'bn' ? 'bn-BD' : 'en-GB', { dateStyle: 'medium' })}
        </p>
      )}
      {verified === false && <p className="font-semibold text-wait-ink">{t.guidance.unverified}</p>}
    </div>
  )
}
