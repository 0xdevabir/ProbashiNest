import { load, save } from './storage'
import type { Level } from './types'

export type Tally = Record<Level, number>

const EMPTY: Tally = { red: 0, amber: 0, green: 0 }

export const isHelperMode = () => load('helper', false)
export const setHelperMode = (on: boolean) => save('helper', on)
export const loadTally = (): Tally => ({ ...EMPTY, ...load<Partial<Tally>>('tally', {}) })
export const resetTally = () => save('tally', EMPTY)

/** Helper mode counts verdicts on the phone. Only the three numbers are kept. */
export function recordVerdict(level: Level): void {
  if (!isHelperMode()) return
  const tally = loadTally()
  save('tally', { ...tally, [level]: tally[level] + 1 })
}
