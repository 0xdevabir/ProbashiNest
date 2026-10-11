import { useRef, useState, type ChangeEvent } from 'react'
import type { CheckInput } from '../api'
import { CameraIcon, KeyboardIcon, LockIcon, ShieldLogo } from '../components/icons'
import { SpeakButton } from '../components/SpeakButton'
import { compressImage, MAX_IMAGE_BYTES } from '../compress'
import { useI18n } from '../i18n'
import { isLowData, LOW_DATA_IMAGE_BYTES } from '../lowData'

const DEMO_TAPS = 5
const DEMO_TAP_WINDOW_MS = 3000

interface HomeProps {
  onSubmit: (input: CheckInput) => void
  onType: () => void
  onPrivacy: () => void
  onMore: () => void
  /** Present only in demo builds: five quick taps on the logo open the demo menu. */
  onDemoMenu?: () => void
}

export function Home({ onSubmit, onType, onPrivacy, onMore, onDemoMenu }: HomeProps) {
  const { t, toggleLang } = useI18n()
  const fileRef = useRef<HTMLInputElement>(null)
  const tapsRef = useRef<number[]>([])
  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoFailed, setPhotoFailed] = useState(false)

  const onLogoTap = () => {
    const now = Date.now()
    tapsRef.current = [...tapsRef.current.filter((at) => now - at < DEMO_TAP_WINDOW_MS), now]
    if (tapsRef.current.length >= DEMO_TAPS) {
      tapsRef.current = []
      onDemoMenu?.()
    }
  }

  const onPhoto = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    // Allow picking the same file again after a failure.
    event.target.value = ''
    if (!file) return
    setPhotoFailed(false)
    setPhotoBusy(true)
    try {
      onSubmit({ image: await compressImage(file, isLowData() ? LOW_DATA_IMAGE_BYTES : MAX_IMAGE_BYTES) })
    } catch {
      // A format the browser cannot decode: send it untouched if it is already small enough.
      if (file.size <= MAX_IMAGE_BYTES) onSubmit({ image: file })
      else setPhotoFailed(true)
    } finally {
      setPhotoBusy(false)
    }
  }

  const tile =
    'flex min-h-36 flex-col items-center justify-center gap-1 rounded-3xl border-2 border-stamp bg-white px-3 py-4 text-center text-stamp active:bg-paper disabled:opacity-60'

  return (
    <div className="flex min-h-dvh flex-col gap-5 pb-6">
      <header className="flex min-h-14 items-center justify-between">
        {/* Not a button for assistive tech: the logo only hides the demo menu. */}
        <div onClick={onLogoTap} className="flex items-center gap-2 select-none">
          <ShieldLogo className="h-10 w-9" />
          <span className="text-2xl font-bold">{t.appName}</span>
        </div>
        <button
          type="button"
          onClick={toggleLang}
          className="min-h-12 rounded-full border-2 border-line bg-white px-4 text-base font-semibold"
        >
          {t.switchLang}
        </button>
      </header>

      <div>
        <h1 className="text-[1.75rem] leading-[1.3] font-bold text-balance">{t.home.title}</h1>
        <p className="mt-2 text-lg text-muted">{t.home.intro}</p>
      </div>

      <SpeakButton onRecorded={(audio) => onSubmit({ audio })} />

      <div className="grid grid-cols-2 gap-3">
        <button type="button" className={tile} disabled={photoBusy} onClick={() => fileRef.current?.click()}>
          <CameraIcon className="size-10" />
          <span className="text-xl leading-tight font-bold">{photoBusy ? t.home.photoBusy : t.home.photo}</span>
          <span className="text-sm leading-tight text-muted">{t.home.photoHelp}</span>
        </button>
        <button type="button" className={tile} onClick={onType}>
          <KeyboardIcon className="size-10" />
          <span className="text-xl leading-tight font-bold">{t.home.type}</span>
          <span className="text-sm leading-tight text-muted">{t.home.typeHelp}</span>
        </button>
      </div>
      {/* No `capture`: phones then offer the camera and the gallery, where WhatsApp photos live. */}
      <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPhoto} data-testid="photo-input" />

      {photoFailed && (
        <p role="alert" className="rounded-2xl border-2 border-stop bg-stop-tint p-3 text-base font-semibold">
          {t.photoError}
        </p>
      )}

      <button
        type="button"
        onClick={onMore}
        className="min-h-16 rounded-2xl border-2 border-line bg-white px-4 py-2 text-center active:bg-paper"
      >
        <span className="block text-xl leading-tight font-bold text-stamp">{t.home.more}</span>
        <span className="block text-sm leading-tight text-muted">{t.home.moreHelp}</span>
      </button>

      <button
        type="button"
        onClick={onPrivacy}
        className="mt-auto flex min-h-12 items-center justify-center gap-2 text-base font-semibold text-stamp underline"
      >
        <LockIcon className="size-5" />
        {t.home.privacy}
      </button>
    </div>
  )
}
