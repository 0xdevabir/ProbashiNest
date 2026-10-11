import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { bn, en, type Translations } from './translations'

export type Lang = 'bn' | 'en'

interface I18n {
  lang: Lang
  t: Translations
  toggleLang: () => void
  /** Format a number in the digits of the current language. */
  num: (value: number) => string
}

const STORAGE_KEY = 'probashi.lang'
const tables: Record<Lang, Translations> = { bn, en }
const formats: Record<Lang, Intl.NumberFormat> = {
  bn: new Intl.NumberFormat('bn-BD'),
  en: new Intl.NumberFormat('en-US'),
}

const I18nContext = createContext<I18n | null>(null)

function storedLang(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'bn'
  } catch {
    return 'bn'
  }
}

export function I18nProvider({ children, initialLang }: { children: ReactNode; initialLang?: Lang }) {
  const [lang, setLang] = useState<Lang>(() => initialLang ?? storedLang())

  useEffect(() => {
    document.documentElement.lang = lang
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      // private mode: the choice just will not persist
    }
  }, [lang])

  const value = useMemo<I18n>(
    () => ({
      lang,
      t: tables[lang],
      toggleLang: () => setLang((l) => (l === 'bn' ? 'en' : 'bn')),
      num: (n) => formats[lang].format(n),
    }),
    [lang],
  )
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}
