import type { Level } from '../types'
import { LEVELS } from '../types'
import { CheckIcon, CrossIcon, ExclaimIcon } from './icons'

const lamp: Record<Level, { lit: string; Icon: typeof CrossIcon; icon: string }> = {
  red: { lit: 'bg-stop text-white', Icon: CrossIcon, icon: 'cross' },
  amber: { lit: 'bg-wait text-ink', Icon: ExclaimIcon, icon: 'exclamation' },
  green: { lit: 'bg-go text-white', Icon: CheckIcon, icon: 'check' },
}

interface SignalProps {
  /** The lit lamp. Omit while checking: the lamps then light in turn. */
  active?: Level
  className?: string
}

/**
 * A three-lamp signal head. The verdict is carried by lamp position and by the
 * mark inside the lit lamp as well as by colour, so it reads without colour vision.
 */
export function Signal({ active, className = '' }: SignalProps) {
  return (
    <div aria-hidden="true" className={`flex shrink-0 flex-col gap-2 rounded-full bg-ink p-2 ${className}`}>
      {LEVELS.map((level, i) => {
        const { lit, Icon, icon } = lamp[level]
        const isLit = active === level
        return (
          <div
            key={level}
            data-lamp={level}
            data-lit={isLit}
            className={`grid size-14 place-items-center rounded-full ${
              active ? (isLit ? lit : 'bg-white/10') : `${lit} animate-lamp`
            }`}
            style={active ? undefined : { animationDelay: `${i * 0.6}s` }}
          >
            {isLit && <Icon data-icon={icon} className="size-8" />}
          </div>
        )
      })}
    </div>
  )
}
