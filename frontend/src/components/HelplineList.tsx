import { useI18n } from '../i18n'
import type { Helpline } from '../types'
import { PhoneIcon } from './icons'

/** Strip everything a dialler does not need, so the link cannot carry anything else. */
export const telHref = (phone: string) => `tel:${phone.replace(/[^\d+]/g, '')}`

/** One-tap call buttons. */
export function HelplineList({ helplines }: { helplines: Helpline[] }) {
  const { t } = useI18n()
  return (
    <ul className="flex flex-col gap-2">
      {helplines.map((line) => (
        <li key={line.phone}>
          <a
            href={telHref(line.phone)}
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
  )
}
