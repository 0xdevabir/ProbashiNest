import { useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import type { CheckInput } from '../api'
import { compressImage, MAX_IMAGE_BYTES } from '../compress'
import { canAddDocument, withAnswers, withDocument } from '../followUp'
import { useI18n } from '../i18n'
import { isLowData, LOW_DATA_IMAGE_BYTES } from '../lowData'
import type { CheckResult } from '../types'
import { CameraIcon } from './icons'
import { SpeakButton } from './SpeakButton'

interface FollowUpProps {
  input: CheckInput
  result: CheckResult
  onResubmit: (input: CheckInput) => void
}

/** Asks for the facts that were missing and runs the check again with the answers. */
export function FollowUp({ input, result, onResubmit }: FollowUpProps) {
  const { t, lang } = useI18n()
  const questions = result.guidance?.follow_up ?? []
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [photoFailed, setPhotoFailed] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  // The Bangla question travels with its answer, so the extractor knows what the answer is about.
  const typed = () => questions.map((q) => ({ question: q.text_bn, answer: answers[q.key] ?? '' }))
  const hasAnswer = Object.values(answers).some((answer) => answer.trim())

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (hasAnswer) onResubmit(withAnswers(input, result, typed()))
  }

  const onPhoto = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setPhotoFailed(false)
    try {
      const image = await compressImage(file, isLowData() ? LOW_DATA_IMAGE_BYTES : MAX_IMAGE_BYTES)
      onResubmit(withDocument(input, result, image))
    } catch {
      if (file.size <= MAX_IMAGE_BYTES) onResubmit(withDocument(input, result, file))
      else setPhotoFailed(true)
    }
  }

  const addPaper = canAddDocument(input)
  if (questions.length === 0 && !addPaper) return null

  return (
    <section className="flex flex-col gap-3 rounded-2xl border-2 border-stamp bg-white p-4 print:hidden">
      {questions.length > 0 && (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <div>
            <h2 className="text-2xl font-bold">{t.guidance.followUp}</h2>
            <p className="text-muted">{t.guidance.followUpHelp}</p>
          </div>
          {questions.map((q) => (
            <label key={q.key} className="flex flex-col gap-1 text-lg leading-snug font-semibold">
              {lang === 'bn' ? q.text_bn : q.text_en || q.text_bn}
              <input
                type="text"
                maxLength={200}
                value={answers[q.key] ?? ''}
                onChange={(event) => setAnswers({ ...answers, [q.key]: event.target.value })}
                placeholder={t.guidance.answer}
                className="min-h-14 rounded-xl border-2 border-line bg-paper px-3 text-lg font-normal placeholder:text-muted/80"
              />
            </label>
          ))}
          <button
            type="submit"
            disabled={!hasAnswer}
            className="min-h-14 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep disabled:bg-line disabled:text-muted"
          >
            {t.guidance.checkAgain}
          </button>
          <SpeakButton
            help={t.guidance.followUpHelp}
            onRecorded={(audio) => onResubmit(withAnswers(input, result, typed(), audio))}
          />
        </form>
      )}

      {addPaper && (
        <>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex min-h-16 items-center gap-3 rounded-2xl border-2 border-stamp bg-white p-3 text-left text-stamp active:bg-paper"
          >
            <CameraIcon className="size-9 shrink-0" />
            <span>
              <span className="block text-xl leading-tight font-bold">{t.guidance.addPaper}</span>
              <span className="block text-sm leading-tight text-muted">{t.guidance.addPaperHelp}</span>
            </span>
          </button>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPhoto} data-testid="paper-input" />
          {photoFailed && (
            <p role="alert" className="rounded-2xl border-2 border-stop bg-stop-tint p-3 text-base font-semibold">
              {t.photoError}
            </p>
          )}
        </>
      )}
    </section>
  )
}
