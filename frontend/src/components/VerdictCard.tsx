import { useI18n } from '../i18n'
import type { Level } from '../types'
import { Signal } from './Signal'

const tone: Record<Level, string> = {
  red: 'border-stop bg-stop-tint text-stop',
  amber: 'border-wait bg-wait-tint text-wait-ink',
  green: 'border-go bg-go-tint text-go',
}

export function VerdictCard({ level }: { level: Level }) {
  const { t } = useI18n()
  const { title, advice } = t.verdict[level]
  return (
    <section
      role="status"
      data-level={level}
      className={`flex items-center gap-4 rounded-[2rem] border-4 p-4 ${tone[level]}`}
    >
      <Signal active={level} />
      <div className="min-w-0">
        <h1 className="text-[2.25rem] leading-[1.2] font-bold text-balance">{title}</h1>
        <p className="mt-2 text-lg leading-snug font-semibold text-ink">{advice}</p>
      </div>
    </section>
  )
}
