import { MAX_DOCUMENTS, type CheckInput } from './api'
import type { CheckResult } from './types'

export interface Answer {
  question: string
  answer: string
}

/**
 * The next check: everything from the first one plus the user's answers.
 * Audio the server already transcribed travels as text, so a new spoken answer can take its place.
 */
export function withAnswers(input: CheckInput, result: CheckResult, answers: Answer[], spoken?: Blob): CheckInput {
  const text = [
    input.text,
    result.transcript_bn,
    ...answers.filter(({ answer }) => answer.trim()).map(({ question, answer }) => `${question} ${answer.trim()}`),
  ]
    .filter(Boolean)
    .join('\n')
  return {
    image: input.image,
    moreImages: input.moreImages,
    audio: spoken ?? (result.transcript_bn ? undefined : input.audio),
    text: text || undefined,
  }
}

export function documentCount(input: CheckInput): number {
  return (input.image ? 1 : 0) + (input.moreImages?.length ?? 0)
}

export function canAddDocument(input: CheckInput): boolean {
  return documentCount(input) < MAX_DOCUMENTS
}

/** The same check with one more paper, e.g. the visa next to the offer letter. */
export function withDocument(input: CheckInput, result: CheckResult, image: Blob): CheckInput {
  const base = withAnswers(input, result, [])
  return base.image ? { ...base, moreImages: [...(base.moreImages ?? []), image] } : { ...base, image }
}
