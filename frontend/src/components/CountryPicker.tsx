import { useI18n } from '../i18n'

interface CountryPickerProps {
  value: string | null
  onChange: (country: string) => void
}

export function CountryPicker({ value, onChange }: CountryPickerProps) {
  const { t } = useI18n()
  return (
    <label className="flex flex-col gap-1 text-lg font-semibold">
      {t.guide.country}
      <select
        value={value ?? ''}
        onChange={(event) => event.target.value && onChange(event.target.value)}
        className="min-h-14 rounded-2xl border border-stamp/20 bg-white px-3 text-xl"
      >
        <option value="" disabled>
          —
        </option>
        {Object.entries(t.countries).map(([code, name]) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>
    </label>
  )
}
