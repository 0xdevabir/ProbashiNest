import { useEffect, useState } from 'react'
import { fetchGuide } from './api'
import { load, save } from './storage'
import type { Guide } from './types'

export interface GuideState {
  guide: Guide | null
  status: 'idle' | 'loading' | 'ready' | 'saved' | 'failed'
}

/** The country the user last chose, shared by the guide and the emergency screen. */
export const loadCountry = () => load<string | null>('country', null)

/**
 * Loads a country guide. The last good copy is kept on the phone (it is public
 * information, nothing personal) and shown when there is no connection.
 */
export function useGuide(country: string | null): GuideState {
  const [state, setState] = useState<GuideState>({ guide: null, status: 'idle' })

  useEffect(() => {
    if (!country) {
      setState({ guide: null, status: 'idle' })
      return
    }
    save('country', country)
    const abort = new AbortController()
    setState({ guide: null, status: 'loading' })
    fetchGuide(country, abort.signal).then(
      (guide) => {
        save(`guide.${country}`, guide)
        setState({ guide, status: 'ready' })
      },
      () => {
        if (abort.signal.aborted) return
        const saved = load<Guide | null>(`guide.${country}`, null)
        setState(saved ? { guide: saved, status: 'saved' } : { guide: null, status: 'failed' })
      },
    )
    return () => abort.abort()
  }, [country])

  return state
}
