import { useState } from 'react'
import { ChevronIcon } from '../components/icons'
import { ScreenHeader } from '../components/ScreenHeader'
import { useI18n } from '../i18n'
import { isLowData } from '../lowData'
import { save } from '../storage'

export type Tool = 'guide' | 'wages' | 'sos' | 'helper' | 'stats'

const TOOLS: Tool[] = ['guide', 'wages', 'sos', 'helper', 'stats']

export default function More({ onOpen, onBack }: { onOpen: (tool: Tool) => void; onBack: () => void }) {
  const { t } = useI18n()
  const [lowData, setLowData] = useState(isLowData)

  const toggleLowData = (on: boolean) => {
    save('lowData', on)
    setLowData(on)
  }

  return (
    <div className="flex flex-col gap-4 pb-8">
      <ScreenHeader onBack={onBack} />
      <h1 className="text-[1.75rem] leading-[1.3] font-bold">{t.more.title}</h1>
      <ul className="divide-y divide-line overflow-hidden rounded-3xl bg-white shadow-card">
        {TOOLS.map((tool) => (
          <li key={tool}>
            <button
              type="button"
              onClick={() => onOpen(tool)}
              className="flex min-h-18 w-full items-center justify-between gap-3 p-4 text-left active:bg-paper"
            >
              <span>
                <span className="block text-xl leading-tight font-bold">{t.more[tool]}</span>
                <span className="block text-muted">{t.more[`${tool}Help` as const]}</span>
              </span>
              <ChevronIcon className="size-5 shrink-0 -rotate-90 text-muted" />
            </button>
          </li>
        ))}
      </ul>
      <label className="flex cursor-pointer items-center gap-3 rounded-3xl bg-white shadow-card p-4">
        <span className="grow">
          <span className="block text-xl leading-tight font-bold">{t.more.lowData}</span>
          <span className="block text-muted">{t.more.lowDataHelp}</span>
        </span>
        <input
          type="checkbox"
          checked={lowData}
          onChange={(event) => toggleLowData(event.target.checked)}
          role="switch"
          className="switch"
        />
      </label>
    </div>
  )
}
