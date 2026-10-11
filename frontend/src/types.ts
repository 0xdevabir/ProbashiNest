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
