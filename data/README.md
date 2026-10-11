# data/ — the Probashi Shield knowledge base

Everything the verdict engine knows lives here as files a person can read and edit.
The code in `probashi/knowledge/` only reads them. Owner: Agent 2.

| File | What it holds |
| --- | --- |
| `rules/<CC>.yaml` | Per destination (SA, AE, MY, QA, OM, KW): minimum wage, who pays recruitment fees, passport retention, contract requirements, complaint channel, and the Bangladesh government's migration cost ceiling |
| `agencies.csv` | Copy of the official BMET register of licensed recruiting agencies |
| `fraud_patterns.yaml` | Recruitment fraud red flags, each tied to the reason code the engine raises |
| `helplines.yaml` | Official helplines and labour-wing office numbers of Bangladesh missions |
| `engine_config.yaml` | Thresholds and keyword lists. These are design choices, not facts, and have no source |
| `test_cases/*.json` | Evaluation set for `python -m probashi.knowledge.eval` |

## Every record carries its evidence

```yaml
- id: QA_MIN_WAGE
  topic: minimum_wage
  amount: 1000
  currency: QAR
  text_en: ...            # what the source says, in plain English
  text_bn: ...            # the same in simple spoken Bangla
  source:
    title: "ILO – Qatar: Regulatory framework governing migrant workers (updated December 2023)"
    url: https://www.ilo.org/publications/qatar-regulatory-framework-governing-migrant-workers
  verified: true
  last_checked: 2026-10-11
```

### What `verified` means

- **Rules and helplines — `verified: true`** means: on `last_checked` someone opened the
  cited document and read this exact point there, **and** the document is a primary or
  authoritative source (a government page, an ILO factsheet, a gazette text).
  A figure known only from a news article is `verified: false`, however plausible.
- **Fraud patterns — `verified: true`** means the cited report was opened and the pattern
  was read there. It says the pattern was *reported* by that source, nothing more.
- **`verified: false`** records are still shown to the worker as context, with
  "[not yet verified]" added to the source title, but they are treated as unknown
  by the safety rule: an unverified limit can raise a warning, never clear an offer.
- A record with no source at all has `source: null`, `verified: false` and a `TODO` comment.

**Never add a number, law, name or phone number you have not read in a source.** If you
cannot find it, leave it out and add a `TODO` comment. The loader refuses a record that
says `verified: true` without a source URL.

To verify a record: open the URL, confirm the point, set `verified: true`, update
`last_checked`. The engine picks the change up on the next start; no code change needed.

## `agencies.csv` — where the official list lives

The official list is BMET's Recruiting Agents' Information System (RAIMS):
<https://raims.oep.gov.bd/agencies> (linked from <https://bmet.gov.bd/>). It publishes the
whole table (licence number, name, address, phone, status, validity date) on one page.
`agencies.csv` is a straight copy of that table taken on the `last_checked` date in each
row: 2,858 licences on 2026-10-11 (2,186 Active, 260 Expired, 235 Cancelled,
171 Suspended, 6 "Server Locked"). Phone numbers are not copied.

Columns: `licence_no, name, status, valid_until, address, source_url, last_checked`.

Refresh it regularly — licences are cancelled and suspended all the time:

```bash
python -m probashi.knowledge.refresh_agencies            # fetch and rewrite the CSV
python -m probashi.knowledge.refresh_agencies --html saved-page.html --date 2026-10-11
```

If the copy is older than `register_max_age_days` (see `engine_config.yaml`, 180 days)
the engine stops treating any licence as verified, so no offer can be green until the
file is refreshed. Do not edit rows by hand; re-run the importer.

The importer keeps TLS certificate checking on and refuses a page that does not look like
the register. If the fetch fails, save the page from a browser and use `--html`.

## Test cases

One JSON file per case:

```json
{
  "id": "real_uae_tourist_visa_26",
  "note": "what the case is and why the expected level is right",
  "synthetic": false,
  "source_url": "https://…",
  "is_fraud": true,
  "expected_level": "red",
  "offer": { "destination_country": "AE", "visa_type": "Tourist visa", "confidence": 0.8 }
}
```

- `synthetic: false` — based on a published report (`source_url` required). Only facts stated
  in the report are filled in; nothing is added to make the case easier.
- `synthetic: true` — invented. Invented employers and agencies say "(invented)" or "Synthetic"
  in their names. Where a real, licensed agency's licence number is used (needed to test the
  green path), the note states that the agency did **not** make the offer. Real licensed
  agencies are never used as the wrongdoer in a fraud case.
- `is_fraud` — the scenario is a fraudulent or illegal offer. The key safety number is how
  many of these come out green (target 0).

## Known gaps (do not paper over them)

- **Bangladesh migration cost ceilings** (`*_BD_COST_CEILING`) are all `verified: false`:
  2019 figures from one newspaper report (Malaysia: a trade-press report of an ACC statement).
  No ceiling was found for Qatar. Confirm the current figures with BMET / the ministry.
- **Malaysia**: only the minimum wage was read in a primary text (and from a non-government
  copy of the gazette). Recruitment-fee rules, passport retention and the complaint channel are TODO.
- **Bangladesh law** (Overseas Employment and Migrants Act 2013): the official text was not
  located, so no section of it is cited anywhere.
- **Fraud patterns** "payment to a personal account" and "pressure to pay fast" have no source yet.
- **OHCHR** press releases on Malaysia returned HTTP 403 to automated access; they are cited
  as `verified: false`.
- **UAE hotline 80084** is taken from the ILO factsheet, not re-read on mohre.gov.ae. It is in
  the rules text only, not in `helplines.yaml`.

## Added files and keys

- `checklist.yaml`: pre-departure steps (BMET registration, fingerprint, orientation, clearance card). All four are `verified: false`: they come from one travel-site article, not from bmet.gov.bd. Confirm them there and set `verified: true`.
- `engine_config.yaml`: `passport_kept_keywords`, `salary_deduction_keywords`, `vague_job_keywords` (English and Bangla) for the contract clause scanner. A match gives an amber-level flag only.
