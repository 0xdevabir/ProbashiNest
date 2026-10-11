import { useState } from 'react'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import { clearAll } from '../storage'

export default function Privacy({ onBack }: { onBack: () => void }) {
  const { t } = useI18n()
  const [deleted, setDeleted] = useState(false)
  const list = 'flex list-disc flex-col gap-3 pl-6 text-xl leading-snug'

  const deleteAll = () => {
    clearAll()
    setDeleted(true)
  }

  return (
    <div className="flex flex-col gap-5 pb-8">
      <ScreenHeader onBack={onBack} />
      <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.privacy.title}</h1>
      <ul className={list}>
        {t.privacy.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
      <section className="rounded-3xl border border-wait/40 bg-wait-tint p-4">
        <h2 className="mb-2 text-2xl font-bold">{t.privacy.adviceTitle}</h2>
        <ul className={list}>
          {t.privacy.advice.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-2xl font-bold">{t.device.title}</h2>
        <ul className={list}>
          {t.device.points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
        <button
          type="button"
          onClick={deleteAll}
          className="min-h-16 rounded-full border border-stop/40 bg-white px-5 text-xl font-bold text-stop active:bg-stop-tint"
        >
          {t.device.deleteAll}
        </button>
        {deleted && (
          <p role="status" className="rounded-3xl bg-go-tint p-3 text-lg font-semibold">
            {t.device.deleted}
          </p>
        )}
      </section>
    </div>
  )
}
