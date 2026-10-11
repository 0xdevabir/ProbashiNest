import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { I18nProvider, type Lang } from '../i18n'
import type { Level } from '../types'
import { VerdictCard } from './VerdictCard'

function renderCard(level: Level, lang: Lang = 'bn') {
  return render(
    <I18nProvider initialLang={lang}>
      <VerdictCard level={level} />
    </I18nProvider>,
  )
}

describe('VerdictCard', () => {
  it.each<[Level, string, string]>([
    ['red', 'ঝুঁকি বেশি', 'cross'],
    ['amber', 'আরও যাচাই করুন', 'exclamation'],
    ['green', 'নিরাপদ মনে হচ্ছে', 'check'],
  ])('shows %s as words, a lit lamp and its own icon', (level, words, icon) => {
    const { container } = renderCard(level)

    expect(screen.getByRole('heading', { name: words })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveAttribute('data-level', level)

    // Exactly one lamp is lit, it is the right one, and it carries a shape as well as a colour.
    const lit = container.querySelectorAll('[data-lit="true"]')
    expect(lit).toHaveLength(1)
    expect(lit[0]).toHaveAttribute('data-lamp', level)
    expect(lit[0].querySelector(`[data-icon="${icon}"]`)).not.toBeNull()
  })

  it('tells the worker not to pay on a red verdict', () => {
    renderCard('red')
    expect(screen.getByText('এখনই টাকা দেবেন না।')).toBeInTheDocument()
  })

  it('switches to English', () => {
    renderCard('amber', 'en')
    expect(screen.getByRole('heading', { name: 'Check further' })).toBeInTheDocument()
  })
})
