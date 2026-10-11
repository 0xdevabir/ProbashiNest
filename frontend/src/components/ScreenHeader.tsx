import type { ReactNode } from 'react'
import { useI18n } from '../i18n'
import { BackIcon } from './icons'

/** Top bar for every screen except home: one large way back. */
export function ScreenHeader({ onBack, children }: { onBack: () => void; children?: ReactNode }) {
  const { t } = useI18n()
  return (
    <header className="flex min-h-14 items-center justify-between gap-3">
      <button
        type="button"
        onClick={onBack}
        className="-ml-2 flex min-h-12 items-center gap-1 rounded-xl px-2 text-lg font-semibold text-stamp"
      >
        <BackIcon className="size-6" />
        {t.back}
      </button>
      {children}
    </header>
  )
}
