import { load } from './storage'

interface Connection {
  saveData?: boolean
  effectiveType?: string
}

/** True when the phone asks to save data or reports a 2G link. Unknown counts as false. */
export function detectLowData(): boolean {
  const connection = (navigator as Navigator & { connection?: Connection }).connection
  return Boolean(connection?.saveData) || /(^|-)2g$/.test(connection?.effectiveType ?? '')
}

/** The user's own choice wins over what the phone reports. */
export function isLowData(): boolean {
  return load<boolean | null>('lowData', null) ?? detectLowData()
}

// Smaller photos in low-data mode: still readable for OCR at the 1600 px long edge.
export const LOW_DATA_IMAGE_BYTES = 600 * 1024
