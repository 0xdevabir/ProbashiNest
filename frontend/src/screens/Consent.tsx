import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'

/** Shown once, before the first check sends anything off the phone. */
export default function Consent({ onAgree, onBack }: { onAgree: () => void; onBack: () => void }) {
  const { t } = useI18n()
  return (
    <div className="flex min-h-dvh flex-col gap-5 pb-6">
      <ScreenHeader onBack={onBack} />
      <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.consent.title}</h1>
      <ul className="flex list-disc flex-col gap-3 pl-6 text-xl leading-snug">
        {t.consent.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
      <button
        type="button"
        onClick={onAgree}
        className="mt-auto min-h-16 rounded-2xl bg-stamp px-5 text-xl font-bold text-white active:bg-stamp-deep"
      >
        {t.consent.agree}
      </button>
    </div>
  )
}
