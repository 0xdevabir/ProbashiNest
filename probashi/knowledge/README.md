# probashi.knowledge — knowledge base, retrieval and verdict engine (Agent 2)

```python
from probashi.knowledge import evaluate
verdict = evaluate(offer)          # ExtractedOffer -> Verdict (red / amber / green)
```

The verdict has to be trustworthy and explainable, so it is built in three layers:

1. **Rules first.** Deterministic checks (`rules.py`) compare the offer with the files in
   `data/` and raise flags. `engine.decide_level` turns flags into the level. No LLM, no
   embeddings, no randomness: the same offer and data always give the same level.
2. **Retrieval second.** `retrieval.py` finds the rule and fraud-pattern passages that
   support each reason, so the reason can carry a source.
3. **LLM last, optional, wording only.** `rephrase.py` may restyle the Bangla sentences.
   It runs after the level is fixed and cannot change the level, the codes, the sources,
   the next steps or the helplines.

Extra dependency: `PyYAML` (see `requirements.txt`).

## Level logic

| Condition | Level |
| --- | --- |
| Any **high** flag | **red** |
| No high flag, but any **medium** flag or any key fact missing | **amber** |
| Agency verified licensed **and** no high or medium flag **and** every key fact present | **green** |
| Anything else | **amber** |

"Agency verified licensed" means all of: the licence number is in the register copy, its
status is `Active`, its validity date has not passed, the agency name in the offer matches
the registered name, and the register copy is at most 180 days old.

Key facts: employer, job title, destination, salary, agency name, licence number, fee,
contract length, visa type. A field the extractor lists in `missing_fields` counts as
missing even if it has a value.

**Safety rule — unknown is never green.** Every "could not check" outcome is a medium flag:
a missing fact, an unreadable scan, a destination without rules, a stale register, a
licence with an unclear status, a salary in a currency that cannot be compared, and a fee
that can only be compared with an *unverified* ceiling. If the knowledge base cannot be
loaded at all, `evaluate` returns amber with `KNOWLEDGE_UNAVAILABLE`.

### Flags

| Code | Severity | Raised when |
| --- | --- | --- |
| `AGENCY_NOT_FOUND` | high | Licence number is not in the BMET register (and the name is not a registered active agency) |
| `AGENCY_UNLICENSED` | high | Register status is Cancelled, Suspended or Expired (by licence number, or by exact name when no number is given) |
| `FEE_ABOVE_LIMIT` | high | Fee is above a *verified* government ceiling, or at least 3× any ceiling |
| `FEE_ABOVE_LIMIT` | medium | Fee is above an *unverified* ceiling, by less than 3× |
| `SALARY_BELOW_MINIMUM` | high | Salary is below the destination's verified legal minimum wage (same currency) |
| `VISA_JOB_MISMATCH` | high | Tourist, visit, Umrah, Hajj, student or transit visa offered for a job |
| `VISA_JOB_MISMATCH` | medium | Domestic-worker visa with a non-domestic job title |
| `FREE_VISA` | high | "Free visa" in the visa type or in the document / transcript |
| `MISSING_LICENCE_NO` | medium | No readable licence number |
| `MISSING_EMPLOYER` | medium | No employer name |
| `MISSING_KEY_FACTS` | medium | Any other key fact is missing (listed in the message) |
| `AGENCY_NAME_NOT_FOUND` | medium | No licence number and the name is not in the register |
| `AGENCY_NAME_MISMATCH` | medium | Licence number is registered under a different name |
| `AGENCY_LICENCE_MISMATCH` | medium | Name is a registered active agency but the number is not in the register (typo or impostor) |
| `AGENCY_LICENCE_EXPIRED` | medium | Status is Active but the validity date has passed |
| `AGENCY_STATUS_UNCLEAR` | medium | Any other status (e.g. "Server Locked") or no validity date |
| `REGISTER_STALE` | medium | The register copy is older than `register_max_age_days` or undated |
| `FEE_LIMIT_UNVERIFIED` | medium | Fee is within a ceiling that is not verified |
| `FEE_NOT_CHECKABLE` | medium | Non-zero fee and no ceiling on file for the destination (Qatar) |
| `SALARY_NOT_COMPARABLE` | medium | Minimum wage exists but the salary currency is different or unknown |
| `SALARY_UNREALISTIC` | medium | Low-skilled job at more than 4× the destination's minimum wage |
| `UNSUPPORTED_DESTINATION` | medium | No rules file for the destination |
| `LOW_CONFIDENCE` | medium | Extraction confidence below 0.5 |
| `PERSONAL_ACCOUNT_PAYMENT` | medium | Document / transcript mentions paying to a personal account or wallet |
| `PRESSURE_TO_PAY` | medium | Document / transcript shows pressure to pay at once |
| `KNOWLEDGE_UNAVAILABLE` | medium | The knowledge base could not be loaded |
| `AGENCY_LICENSED` | info | The agency was verified as licensed (shown as a positive reason) |

Reasons are returned most serious first. Thresholds (3×, 4×, 0.5, 180 days) and keyword
lists live in `data/engine_config.yaml`; they are design choices, not legal facts.

What the engine deliberately does **not** do:
- No currency conversion (it would need exchange rates nobody sourced).
- No salary-too-high check for Saudi Arabia, the UAE and Oman: they have no minimum wage
  for migrant workers and no sourced market-wage data is on file.
- A zero fee passes; a fee is never called "fine" against an unverified ceiling.

## Messages

Every reason has `message_bn` (short spoken-style Bangla, amounts in Bangla digits) and
`message_en`, from fixed templates in `messages.py`. `next_steps_bn` has 2–4 concrete
actions; a red verdict always starts with "এখন কোনো টাকা দেবেন না।". `disclaimer_bn` says
this is guidance, not legal advice. Helplines are the official Bangladesh numbers plus the
labour wing of the mission in the destination country.

A source from an unverified record has "[not yet verified]" appended to its title.
A reason whose pattern has no source (pressure to pay, personal account) has `source: null`
rather than a borrowed one.

## Retrieval

Passages are every record in `data/rules/*.yaml` and `data/fraud_patterns.yaml` (English
and Bangla text together). Rules of other destinations are never returned.

| `KNOWLEDGE_RETRIEVER` | Backend |
| --- | --- |
| `lexical` (default) | Character n-gram TF-IDF, pure Python, no download, works for Bangla and English |
| `embedding` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; needs `pip install sentence-transformers` and a one-time model download. Falls back to lexical if unavailable |

A reason's source is, in order: the record the check relied on (register, wage or ceiling
record); otherwise the best-ranked passage written for that same reason code. A passage
that is merely similar is never cited. `engine.explain(offer)` returns the verdict plus
the flags and retrieved passages for debugging.

## Optional LLM rephrase

Off by default. With `KNOWLEDGE_LLM_REPHRASE=1` the engine sends the templated messages and
the retrieved passages (never the worker's document or transcript) through
`probashi.llm.complete_json` and accepts a rewrite of a `message_bn` only if it is Bangla,
not much longer, and contains exactly the same numbers. Anything else, or any LLM error,
keeps the template wording.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `KNOWLEDGE_RETRIEVER` | `lexical` | `lexical` or `embedding` |
| `KNOWLEDGE_LLM_REPHRASE` | off | `1` to let the LLM restyle Bangla messages |
| `PROBASHI_DATA_DIR` | `<repo>/data` | Where the knowledge base files are |

(Agent 1: these are not yet in `.env.example`.)

## Evaluation

```bash
python -m probashi.knowledge.eval        # add -v to list every case
```

Result on 2026-10-11 (30 cases: 8 built from published reports, 22 synthetic):

| Measure | Result |
| --- | --- |
| Accuracy against expected level | 28 / 30 = 93% |
| **Fraud cases rated green** | **0 of 18** |
| Fraud cases rated red | 13 of 18 (the other 5 are amber) |
| Good offers rated green | 4 of 4 |

The two misses are both real cases where a worker paid an unlicensed middleman
(Tk 4 lakh for Saudi Arabia; Tk 2 lakh for Vietnam). The expected level is red; the engine
says amber, because the only hard evidence in the offer is missing information and a fee
above an unverified ceiling by less than 3×. See "Open questions".

## Tests

```bash
pytest probashi/knowledge
```

One test per rule and severity, the level table, "unknown never becomes green" (each key
field, combinations, low confidence, stale register, unverified ceiling, broken knowledge
base), the LLM guard, the data files, the register importer and the evaluation set. Unit
tests use a synthetic agency register (invented names, `RL9001`–`RL9007`).

## Sources

| Used for | Source | Status |
| --- | --- | --- |
| SA, AE, QA, KW, OM: minimum wage, recruitment fees, passport, contract, complaints | ILO factsheets "Regulatory framework governing migrant workers" (Dec 2023; UAE May 2024), ilo.org/publications/… | verified |
| MY minimum wage | Minimum Wages Order 2024, P.U.(A) 376/2024 (gazette text, copy hosted by AmCham Malaysia) | verified, non-government host |
| Agency register | BMET RAIMS, https://raims.oep.gov.bd/agencies | verified (official), copy of 2026-10-11 |
| Helplines 16135, +88 09610 102 030, BMET helpline | https://bmet.gov.bd/ and https://probashi.gov.bd/ | verified |
| Labour-wing office numbers | probashi.gov.bd Labour Welfare Wings contact list | verified |
| Migration cost ceilings SA, AE, KW, OM | The Financial Express, 10 Apr 2019 | **unverified** (news, old) |
| Migration cost ceiling MY | People Matters report of an ACC statement | **unverified** |
| Fraud patterns | The Business Standard (2023, 2025), Prothom Alo (2026), Dhaka Tribune (2020), Khaleej Times (2018), The Daily Star (2021), Bonik Barta | read; pattern "reported" |
| Malaysia fake jobs / fees over 5× | OHCHR press release, Nov 2025 | **unverified** (HTTP 403, seen via search excerpts) |
| Pressure to pay; payment to personal account | none | **no source yet** |

Full URLs are in the data files. `data/README.md` defines "verified" and lists the gaps.

## What is stubbed or missing

- The embedding retriever and the LLM rephrase are implemented but optional and off by default.
- Malaysia: no fee-rule, passport or complaint-channel records (TODO in `MY.yaml`).
- Qatar: no Bangladesh cost ceiling.
- No citation of the Overseas Employment and Migrants Act 2013 (official text not located).
- No sourced market-wage data, so `SALARY_UNREALISTIC` only works for QA, KW and MY.

## Open questions

1. **Cost ceilings.** All are unverified, so today an offer with any non-zero fee cannot be
   green. Someone should confirm the current figures with BMET and set `verified: true`.
2. **Unlicensed middleman with a large fee** (the two eval misses): should "money demanded
   and no licence number" be red instead of amber? It would catch those cases, but it would
   also show red to a worker who simply has not asked for the licence number yet.
3. **`AGENCY_NOT_FOUND` is red.** One misread digit in a scan can cause it. The message asks
   the worker to check the number again; a lower severity for low-confidence scans is possible.
4. **3× and 4× thresholds** are judgement calls. Review with a migration expert.
5. **Register freshness.** Something should run `refresh_agencies` on a schedule; after 180
   days without a refresh no offer can be green.
6. **Agent 1:** add `PyYAML` to `pyproject.toml`, and the three environment variables to `.env.example`.
7. **Voice length.** An offer with many problems yields many reasons. They are ordered most
   serious first, so the voice answer can read only the first two or three.

## Added: clause scanner, guidance, document consistency

- **Contract clause scanner** (`rules.check_contract_clauses`): looks in the document text for three patterns listed in `data/engine_config.yaml`: the employer or agent keeping the passport (`PASSPORT_KEPT`), fees taken out of the salary (`FEE_DEDUCTED_FROM_SALARY`), and a job described too vaguely (`JOB_VAGUE`). Each is a medium flag: it can make a verdict amber, never red on its own, because a keyword match is not proof. `JOB_VAGUE` has no source and says so.
- **Guidance** (`guidance.py`): `guidance(offer, verdict)` returns up to three follow-up questions for missing facts, questions to put to the agent, an explainer per reason (the country rule, the fraud pattern or the licence register, each with source, `verified` and `last_checked`), a complaint draft with blanks for red verdicts, and the extractor's confidence. `guide(country)` returns the rights records for a country, the pre-departure checklist, payment advice and helplines. Both are deterministic, use no LLM, and cannot change a verdict level.
- **Document consistency** (`consistency.py`): `merge_offers(offers)` fills gaps in the first paper from the others and lists the fields on which they disagree. `add_mismatch(verdict, fields)` adds a `DOCUMENT_MISMATCH` reason and lowers green to amber.

Not built, because there is no sourced data for them: an employer blacklist check, typical salary ranges for every country, links to each country's visa-check portal (URLs not verified), remittance and loan advice, and a directory of nearby help offices.
