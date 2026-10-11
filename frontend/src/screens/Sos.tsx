import { useState, type FormEvent } from 'react'
import { CountryPicker } from '../components/CountryPicker'
import { HelplineList, telHref } from '../components/HelplineList'
import { PhoneIcon } from '../components/icons'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import { shareText } from '../share'
import { load, save } from '../storage'
import { loadCountry, useGuide } from '../useGuide'

interface Contact {
  name: string
  phone: string
}

const PHONE = /^\+?\d[\d\s-]{5,19}$/
const LOCATE_TIMEOUT_MS = 10_000

/** A map link to where the phone is now, or null if the phone will not say. */
export function locate(): Promise<string | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null)
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve(`https://maps.google.com/?q=${coords.latitude.toFixed(5)},${coords.longitude.toFixed(5)}`),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: LOCATE_TIMEOUT_MS },
    )
  })
}

const field = 'min-h-14 w-full rounded-xl border-2 border-line bg-white px-3 text-xl'
const action = 'flex min-h-16 w-full items-center justify-center gap-3 rounded-full px-5 text-xl font-bold'

/** One place to reach a trusted person and the official numbers. The contact stays on the phone. */
export default function Sos({ onBack }: { onBack: () => void }) {
  const { t } = useI18n()
  const [contact, setContact] = useState(() => load<Contact | null>('contact', null))
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(contact?.name ?? '')
  const [phone, setPhone] = useState(contact?.phone ?? '')
  const [notice, setNotice] = useState<string | null>(null)
  const [country, setCountry] = useState(loadCountry)
  const { guide } = useGuide(country)

  const saveContact = (event: FormEvent) => {
    event.preventDefault()
    if (!PHONE.test(phone.trim())) return
    const next = { name: name.trim().slice(0, 60), phone: phone.trim() }
    save('contact', next)
    setContact(next)
    setEditing(false)
  }

  const message = async () => {
    setNotice(t.sos.locating)
    const link = await locate()
    setNotice(link ? null : t.sos.locationFailed)
    return link ? `${t.sos.message} ${t.sos.here} ${link}` : t.sos.message
  }

  const sendSms = async () => {
    if (!contact) return
    const body = encodeURIComponent(await message())
    // "?&body=" is the form both Android and iOS accept.
    window.location.href = `sms:${contact.phone.replace(/[^\d+]/g, '')}?&body=${body}`
  }

  const share = async () => void shareText(await message())

  return (
    <div className="flex flex-col gap-5 pb-8">
      <ScreenHeader onBack={onBack} />
      <div>
        <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.sos.title}</h1>
        <p className="mt-1 text-lg text-muted">{t.sos.intro}</p>
      </div>

      {contact && !editing ? (
        <section className="flex flex-col gap-3">
          <a href={telHref(contact.phone)} className={`${action} bg-stop text-white`}>
            <PhoneIcon className="size-7" />
            {t.sos.call}: {contact.name || contact.phone}
          </a>
          <button type="button" onClick={sendSms} className={`${action} bg-stamp text-white active:bg-stamp-deep`}>
            {t.sos.sendLocation}
          </button>
          <button type="button" onClick={share} className={`${action} bg-sage-tint text-stamp`}>
            {t.sos.shareLocation}
          </button>
          <button type="button" onClick={() => setEditing(true)} className="min-h-12 font-semibold text-stamp underline">
            {t.sos.change}
          </button>
        </section>
      ) : (
        <form onSubmit={saveContact} className="flex flex-col gap-3 rounded-3xl border border-stamp/20 bg-white shadow-card p-4">
          <div>
            <h2 className="text-xl font-bold">{t.sos.contact}</h2>
            <p className="text-muted">{t.sos.contactHelp}</p>
          </div>
          <label className="flex flex-col gap-1 text-lg font-semibold">
            {t.sos.name}
            <input type="text" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-lg font-semibold">
            {t.sos.phone}
            <input type="tel" required pattern="\+?[0-9][0-9 \-]{5,19}" value={phone} onChange={(e) => setPhone(e.target.value)} className={field} />
          </label>
          <button type="submit" className={`${action} bg-stamp text-white active:bg-stamp-deep`}>
            {t.sos.save}
          </button>
        </form>
      )}

      {notice && (
        <p role="status" className="rounded-3xl bg-wait-tint p-3 font-semibold text-wait-ink">
          {notice}
        </p>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-2xl font-bold">{t.sos.helplines}</h2>
        <CountryPicker value={country} onChange={setCountry} />
        {guide && guide.helplines.length > 0 ? (
          <HelplineList helplines={guide.helplines} />
        ) : (
          !country && <p className="text-muted">{t.sos.helplinesHelp}</p>
        )}
      </section>
    </div>
  )
}
