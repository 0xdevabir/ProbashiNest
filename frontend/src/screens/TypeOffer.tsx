import { useState, type FormEvent } from 'react'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'

const MAX_CHARS = 4000

export default function TypeOffer({ onSubmit, onBack }: { onSubmit: (text: string) => void; onBack: () => void }) {
  const { t } = useI18n()
  const [text, setText] = useState('')
  const trimmed = text.trim()

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <form onSubmit={submit} className="flex min-h-dvh flex-col gap-4 pb-6">
      <ScreenHeader onBack={onBack} />
      <label htmlFor="offer-text" className="text-2xl font-bold">
        {t.typeScreen.title}
      </label>
      <textarea
        id="offer-text"
        autoFocus
        rows={7}
        maxLength={MAX_CHARS}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={t.typeScreen.placeholder}
        className="w-full rounded-2xl border-2 border-stamp bg-white p-4 text-xl placeholder:text-muted/80"
      />
      <button
        type="submit"
        disabled={!trimmed}
        className="min-h-16 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep disabled:bg-line disabled:text-muted"
      >
        {t.typeScreen.submit}
      </button>
    </form>
  )
}
