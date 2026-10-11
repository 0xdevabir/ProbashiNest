import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'

export default function Privacy({ onBack }: { onBack: () => void }) {
  const { t } = useI18n()
  const list = 'flex list-disc flex-col gap-3 pl-6 text-xl leading-snug'
  return (
    <div className="flex flex-col gap-5 pb-8">
      <ScreenHeader onBack={onBack} />
      <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.privacy.title}</h1>
      <ul className={list}>
        {t.privacy.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
      <section className="rounded-2xl border-2 border-wait bg-wait-tint p-4">
        <h2 className="mb-2 text-2xl font-bold">{t.privacy.adviceTitle}</h2>
        <ul className={list}>
          {t.privacy.advice.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
