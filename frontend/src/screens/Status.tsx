import type { ApiErrorKind } from '../api'
import { RetryIcon } from '../components/icons'
import { Signal } from '../components/Signal'
import { useI18n } from '../i18n'

const quietButton = 'min-h-14 rounded-2xl px-5 text-lg font-semibold text-stamp underline'

export function Loading({ onCancel }: { onCancel: () => void }) {
  const { t } = useI18n()
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-5 pb-6 text-center">
      <Signal />
      <div role="status">
        <h1 className="text-[1.75rem] font-bold">{t.loading.title}</h1>
        <p className="mt-1 text-lg text-muted">{t.loading.help}</p>
      </div>
      <button type="button" onClick={onCancel} className={quietButton}>
        {t.loading.cancel}
      </button>
    </div>
  )
}

interface CheckFailedProps {
  kind: ApiErrorKind
  onRetry: () => void
  onBack: () => void
}

export function CheckFailed({ kind, onRetry, onBack }: CheckFailedProps) {
  const { t } = useI18n()
  const { title, help } = t.errors[kind]
  return (
    <div className="flex min-h-dvh flex-col justify-center gap-5 pb-6">
      <div role="alert" className="rounded-[2rem] border-4 border-ink bg-white p-5">
        <h1 className="text-[1.75rem] leading-[1.3] font-bold">{title}</h1>
        <p className="mt-2 text-xl leading-snug">{help}</p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="flex min-h-16 items-center justify-center gap-3 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep"
      >
        <RetryIcon className="size-7" />
        {t.errors.retry}
      </button>
      <button type="button" onClick={onBack} className={quietButton}>
        {t.back}
      </button>
    </div>
  )
}
