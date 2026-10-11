import { useState } from 'react'
import { CountryPicker } from '../components/CountryPicker'
import { HelplineList } from '../components/HelplineList'
import { ScreenHeader } from '../components/ScreenHeader'
import { SourceNote } from '../components/SourceNote'
import { useI18n } from '../i18n'
import { load, save } from '../storage'
import type { GuideItem } from '../types'
import { loadCountry, useGuide } from '../useGuide'

const heading = 'mb-3 text-2xl font-bold'

function Item({ item }: { item: GuideItem }) {
  const { lang } = useI18n()
  return (
    <>
      <p className="text-lg leading-snug">{lang === 'bn' ? item.text_bn : item.text_en || item.text_bn}</p>
      <SourceNote source={item.source} verified={item.verified} lastChecked={item.last_checked} />
    </>
  )
}

/** Rights at the destination, steps before leaving, payment advice and emergency numbers. */
export default function GuideScreen({ initialCountry, onBack }: { initialCountry?: string | null; onBack: () => void }) {
  const { t } = useI18n()
  const [country, setCountry] = useState<string | null>(() => initialCountry ?? loadCountry())
  const [done, setDone] = useState<string[]>(() => load<string[]>('checklist', []))
  const { guide, status } = useGuide(country)

  const tick = (id: string, checked: boolean) => {
    const next = checked ? [...done, id] : done.filter((d) => d !== id)
    save('checklist', next)
    setDone(next)
  }

  return (
    <div className="flex flex-col gap-6 pb-8">
      <ScreenHeader onBack={onBack} />
      <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.guide.title}</h1>
      <CountryPicker value={country} onChange={setCountry} />

      {status === 'loading' && <p role="status" className="text-lg text-muted">{t.guide.loading}</p>}
      {status === 'failed' && (
        <p role="alert" className="rounded-2xl border-2 border-stop bg-stop-tint p-3 text-lg font-semibold">
          {t.guide.failed}
        </p>
      )}
      {status === 'saved' && <p role="status" className="rounded-2xl bg-wait-tint p-3 font-semibold text-wait-ink">{t.guide.saved}</p>}

      {guide && (
        <>
          <section>
            <h2 className={heading}>{t.guide.rights}</h2>
            {guide.rights.length === 0 ? (
              <p className="rounded-2xl bg-wait-tint p-4 text-lg font-semibold text-wait-ink">{t.guide.noRights}</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {guide.rights.map((item) => (
                  <li key={item.id} className="rounded-2xl border-l-8 border-stamp bg-white p-4">
                    <Item item={item} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {guide.checklist.length > 0 && (
            <section>
              <h2 className={heading}>{t.guide.checklist}</h2>
              <ul className="flex flex-col gap-2">
                {guide.checklist.map((item) => (
                  <li key={item.id}>
                    <label className="flex cursor-pointer items-start gap-3 rounded-2xl bg-white p-4 has-checked:bg-go-tint">
                      <input
                        type="checkbox"
                        checked={done.includes(item.id)}
                        onChange={(event) => tick(item.id, event.target.checked)}
                        className="mt-1 size-7 shrink-0 accent-go"
                      />
                      <span className="min-w-0">
                        <Item item={item} />
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {guide.payment_tips_bn.length > 0 && (
            <section className="rounded-2xl border-2 border-wait bg-wait-tint p-4">
              <h2 className="mb-2 text-2xl font-bold">{t.guide.payment}</h2>
              <ul lang="bn" className="flex list-disc flex-col gap-2 pl-6 text-lg leading-snug">
                {guide.payment_tips_bn.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </section>
          )}

          {guide.helplines.length > 0 && (
            <section>
              <h2 className={heading}>{t.guide.helplines}</h2>
              <HelplineList helplines={guide.helplines} />
            </section>
          )}
        </>
      )}
    </div>
  )
}
