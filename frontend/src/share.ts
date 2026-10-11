import type { Translations } from './i18n/translations'
import type { CheckResult } from './types'

/** The verdict as plain Bangla text, short enough for SMS or a chat app. */
export function verdictText(result: CheckResult, t: Translations): string {
  const { verdict } = result
  const helpline = verdict.helplines[0]
  return [
    `${t.appName}: ${t.verdict[verdict.level].title}। ${t.verdict[verdict.level].advice}`,
    ...verdict.reasons.map((reason) => `• ${reason.message_bn}`),
    ...verdict.next_steps_bn.map((step, i) => `${i + 1}. ${step}`),
    helpline ? `${helpline.name}: ${helpline.phone}` : '',
    verdict.disclaimer_bn,
  ]
    .filter(Boolean)
    .join('\n')
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

/** Open the phone's share sheet; fall back to the clipboard where there is none. */
export async function shareText(text: string): Promise<'shared' | 'copied' | 'failed'> {
  if (typeof navigator.share === 'function') {
    try {
      await navigator.share({ text })
      return 'shared'
    } catch (err) {
      // The user closed the sheet: that is not a failure.
      if (err instanceof DOMException && err.name === 'AbortError') return 'shared'
    }
  }
  return (await copyText(text)) ? 'copied' : 'failed'
}
