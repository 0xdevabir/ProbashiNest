// Mirrors probashi/schemas.py (the shared contract). Keep in sync; never diverge.

export type Level = 'red' | 'amber' | 'green'

export const LEVELS: readonly Level[] = ['red', 'amber', 'green']

export interface Money {
  amount: number | null
  currency: string | null
}

export interface ExtractedOffer {
  employer_name: string | null
  job_title: string | null
  destination_country: string | null
  monthly_salary: Money
  agency_name: string | null
  agency_license_no: string | null
  fees_charged_bdt: number | null
  contract_duration_months: number | null
  visa_type: string | null
  document_language: string | null
  raw_text: string
  missing_fields: string[]
  confidence: number
}

export interface Source {
  title: string
  url: string | null
}

export interface Reason {
  code: string
  message_bn: string
  message_en: string
  source: Source | null
}

export interface Helpline {
  name: string
  phone: string
}

export interface Verdict {
  level: Level
  reasons: Reason[]
  next_steps_bn: string[]
  helplines: Helpline[]
  disclaimer_bn: string
}

export interface CheckResponse {
  offer: ExtractedOffer
  verdict: Verdict
  transcript_bn: string | null
  audio_base64: string | null
}

// Everything below mirrors probashi/knowledge/guidance.py and backend/models.py.

export interface Prompt {
  /** Missing field name (follow-up) or reason code (question for the agent). */
  key: string
  text_bn: string
  text_en: string
}

export interface Explainer {
  code: string
  text_bn: string
  text_en: string
  source: Source | null
  verified: boolean
  /** ISO date the source was last checked. */
  last_checked: string | null
}

export interface Guidance {
  follow_up: Prompt[]
  ask_agent: Prompt[]
  explainers: Explainer[]
  complaint_draft_bn: string | null
  confidence: number
}

/** `CheckResponse` plus optional guidance. Older servers and fixtures send none. */
export interface CheckResult extends CheckResponse {
  guidance?: Guidance | null
}

export interface GuideItem {
  id: string
  text_bn: string
  text_en: string
  source: Source | null
  verified: boolean
  last_checked: string | null
}

export interface Guide {
  country: string
  country_name_bn: string | null
  rights: GuideItem[]
  checklist: GuideItem[]
  payment_tips_bn: string[]
  helplines: Helpline[]
}

export interface Stats {
  since: string
  checks: number
  by_level: Record<Level, number>
  by_channel: Record<string, number>
  by_country: Record<string, number>
  top_reasons: { code: string; count: number }[]
  reports: number
}

export interface ScamReport {
  consent: boolean
  level: Level
  reason_codes: string[]
  destination_country?: string
  agency_name?: string
  agency_license_no?: string
}

/** How the verdict engine does on the labelled test cases (GET /api/eval). */
export interface Evaluation {
  as_of: string
  total: number
  correct: number
  real: number
  synthetic: number
  fraud_total: number
  /** Fraud cases the engine called safe. The target is 0. */
  fraud_green: number
  fraud_red: number
  misses: { id: string; expected: Level; got: Level; is_fraud: boolean }[]
}

export interface StoredReport {
  date: string
  level: Level
  reason_codes: string[]
  destination_country: string | null
  agency_name: string | null
  agency_license_no: string | null
}

/** Stored scam reports for a human reviewer (GET /api/admin/reports). */
export interface ReviewQueue {
  total: number
  agencies: { agency_name: string | null; agency_license_no: string | null; count: number; last_date: string }[]
  reports: StoredReport[]
}
