import type { CheckResponse, Level } from './types'

/** Where a check is answered from: the real API, or a bundled synthetic fixture. */
export type DemoChoice = 'live' | Level

export function isDemoBuild(): boolean {
  return import.meta.env.VITE_DEMO_MODE === 'true'
}

const fixtures: Record<Level, () => Promise<{ default: unknown }>> = {
  red: () => import('./fixtures/red.json'),
  amber: () => import('./fixtures/amber.json'),
  green: () => import('./fixtures/green.json'),
}

// Long enough for the audience to read the loading state during a pitch.
const DEMO_DELAY_MS = 1400

export async function loadFixture(level: Level, signal?: AbortSignal): Promise<CheckResponse> {
  const [mod] = await Promise.all([
    fixtures[level](),
    new Promise((resolve) => setTimeout(resolve, DEMO_DELAY_MS)),
  ])
  signal?.throwIfAborted()
  return mod.default as CheckResponse
}
