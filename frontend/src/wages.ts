import { load, save } from './storage'

/** One month of pay, typed in by the worker. Stays on the phone. */
export interface WageEntry {
  /** YYYY-MM */
  month: string
  promised: number
  received: number
}

const KEY = 'wages'

export function loadWages(): WageEntry[] {
  const stored = load<unknown>(KEY, [])
  return Array.isArray(stored) ? (stored as WageEntry[]) : []
}

/** Add or replace the entry for a month; newest month first. */
export function putWage(entries: WageEntry[], entry: WageEntry): WageEntry[] {
  const next = [...entries.filter((e) => e.month !== entry.month), entry].sort((a, b) => b.month.localeCompare(a.month))
  save(KEY, next)
  return next
}

export function removeWage(entries: WageEntry[], month: string): WageEntry[] {
  const next = entries.filter((e) => e.month !== month)
  save(KEY, next)
  return next
}

/** Months paid in full never cancel out months paid short. */
export function wageSummary(entries: WageEntry[]): { promised: number; received: number; shortfall: number } {
  return entries.reduce(
    (sum, e) => ({
      promised: sum.promised + e.promised,
      received: sum.received + e.received,
      shortfall: sum.shortfall + Math.max(0, e.promised - e.received),
    }),
    { promised: 0, received: 0, shortfall: 0 },
  )
}
