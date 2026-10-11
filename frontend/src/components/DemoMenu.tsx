import type { DemoChoice } from '../demo'
import { useI18n } from '../i18n'
import { LEVELS } from '../types'

interface DemoMenuProps {
  choice: DemoChoice
  onChoose: (choice: DemoChoice) => void
  onClose: () => void
}

/** Hidden presenter menu: pick which synthetic verdict the next check returns. */
export default function DemoMenu({ choice, onChoose, onClose }: DemoMenuProps) {
  const { t } = useI18n()
  const options: { value: DemoChoice; label: string }[] = [
    ...LEVELS.map((level) => ({ value: level, label: t.verdict[level].title })),
    { value: 'live', label: t.demo.live },
  ]
  return (
    <div className="fixed inset-0 z-10 grid place-items-end bg-ink/60 sm:place-items-center" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t.demo.title}
        onClick={(event) => event.stopPropagation()}
        className="flex w-full max-w-md flex-col gap-2 rounded-t-3xl bg-white p-5 sm:rounded-3xl"
      >
        <h2 className="mb-1 text-2xl font-bold">{t.demo.title}</h2>
        {options.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            aria-pressed={choice === value}
            onClick={() => {
              onChoose(value)
              onClose()
            }}
            className="min-h-14 rounded-2xl border-2 border-line px-4 text-left text-xl font-semibold aria-pressed:border-stamp aria-pressed:bg-stamp aria-pressed:text-white"
          >
            {label}
          </button>
        ))}
        <button type="button" onClick={onClose} className="min-h-12 text-lg font-semibold text-stamp underline">
          {t.demo.close}
        </button>
      </div>
    </div>
  )
}
