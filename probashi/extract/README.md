# probashi/extract — reading documents and extracting facts (Agent 3)

```python
from probashi.extract import extract_offer

offer = extract_offer(image_bytes, text)   # -> probashi.schemas.ExtractedOffer
```

- `image_bytes`: a JPEG, PNG or WebP photo/scan, or a PDF. May be `None`.
- `text`: a typed or transcribed description in Bangla, English or romanised Bangla. May be `None`.
- It never raises. If nothing can be read, every field is empty, all nine are in `missing_fields`, and `confidence` is 0.

Extra dependencies: `pip install -r probashi/extract/requirements.txt` (Pillow, pypdfium2). They are not in the root `pyproject.toml` yet.

## How it works

1. **Prepare the image** (`preprocess.py`). Apply the EXIF rotation, flatten transparency, shrink to 1568 px on the long edge, stretch the contrast, re-encode as JPEG. PDFs are rendered page by page (first 3 pages). A sharpness score flags blurry photos. Everything stays in memory.
2. **Ask the vision LLM** (`extractor.py`) through `probashi.llm.complete_json`. The model is asked to transcribe the document and to copy each fact *as written* ("3 lakh 80 thousand taka"), plus its own reading of the number. The answer is validated with Pydantic. If it is not valid JSON or fails validation, the model is asked once more with the error; if that fails too, step 4 runs.
3. **Normalise in code** (`normalize.py`), not in the model:
   - countries → ISO alpha-2 (English, Bangla and Arabic names, plus common cities such as Dubai);
   - currencies → ISO 4217. A bare "riyal", "dinar" or "dirham" is resolved from the destination country, or left empty;
   - Bangla, Arabic-Indic and Persian digits → numbers; "লাখ / lakh / lac", "হাজার", "কোটি", "দেড়", "আড়াই", "সাড়ে চার", "পনেরোশ" → numbers;
   - durations → months; licence numbers → `RL-<digits>`; visa types → a fixed vocabulary.

   When the amount parsed from the text as written and the model's own number disagree, the parsed value is used and the confidence drops.
4. **Fallback without an LLM** (`rules.py`). If the LLM is down or no key is set, typed/spoken text is still read by keyword rules. Confidence is capped at 0.5. Images are not read on this path.

### What the caller can rely on

| Field | Convention |
| --- | --- |
| `missing_fields` | Names from `IMPORTANT_FIELDS`: `employer_name`, `job_title`, `destination_country`, `monthly_salary`, `agency_name`, `agency_license_no`, `fees_charged_bdt`, `contract_duration_months`, `visa_type`. `monthly_salary` is listed when the amount **or** the currency is unknown. |
| `monthly_salary` | Per month. A yearly figure is divided by 12. A daily or weekly figure is not converted: the field stays empty and a note is added. |
| `fees_charged_bdt` | Only taka. A fee stated in another currency is **not** converted (no exchange rates are built in): the field stays empty and a note is added. If no currency is stated the fee is assumed to be taka and the confidence drops. |
| `agency_license_no` | `RL-<digits>` when written in the RL form, otherwise the text as written. Dropped if its digits do not appear in the transcription or in the worker's text. |
| `visa_type` | `free`, `visit`, `tourist`, `umrah`, `hajj`, `student`, `transit` or `work`. If two are mentioned ("visit visa now, work visa later") the riskier one is reported. |
| `document_language` | `en`, `bn`, `ar`, …; may be `None`. |
| `raw_text` | The transcription and/or the worker's own words. Lines starting with `[extract note]` explain anything that was dropped or not converted. |
| `confidence` | `legibility × (0.5 + 0.5 × fields found / 9)`, × 0.75 for a blurry photo, − 0.05 per uncertain field. Never above 0.95 (LLM) or 0.5 (rules). |

Nothing is filled in by guesswork: a value that is not in the input stays `None`.

### Privacy

- Uploaded bytes are never written to disk.
- Logs carry field *names* and the confidence only. The transcription is logged at DEBUG, after `mask_pii` has masked names on labelled lines, passport numbers and long digit runs.
- **The returned `raw_text` is not masked.** It can contain the worker's name and passport number. Whoever logs or stores an `ExtractedOffer` should pass it through `probashi.extract.mask_pii` first.

## Tests and fixtures

```bash
pytest probashi/extract                                   # 210 tests, no API key needed
python -m probashi.extract.tests.accuracy --rules         # accuracy of the no-LLM path
ANTHROPIC_API_KEY=... pytest probashi/extract/tests/test_integration.py -s   # real LLM, 17 calls
python probashi/extract/tests/fixtures/generate_fixtures.py   # redraw the sample documents (macOS fonts)
```

`tests/fixtures/` holds 10 synthetic documents drawn with Pillow and 7 Bangla descriptions. Every name, agency and licence number in them is made up and each page is watermarked SAMPLE. They cover: no agency licence, salary in MYR / OMR / KWD / BHD / JOD, an Arabic-only offer, a rotated and skewed photo, handwritten-style amounts, a blurry photo, a Bangla receipt, a visit visa, and a two-page PDF.

### Accuracy

**Rule-based path, 7 Bangla text fixtures** (measured, `accuracy --rules`):

| Field | Correct |
| --- | --- |
| employer_name (must stay empty) | 7/7 |
| job_title | 7/7 |
| destination_country | 7/7 |
| salary_amount | 7/7 |
| salary_currency | 7/7 |
| agency_name | 7/7 |
| agency_license_no | 7/7 |
| fees_charged_bdt | 7/7 |
| contract_duration_months | 7/7 |
| visa_type | 7/7 |
| document_language | 6/7 |
| **All** | **76/77** |

The miss is romanised Bangla, whose language is left empty. The rules were written alongside these seven texts, so this number says the rules work on the phrasings they were built for. It is not an estimate for real speech.

**LLM path, all 17 fixtures: not measured.** No API key was available while this was built. `test_integration.py` prints the same table when a key is set.

## Known weaknesses

- The LLM path has never been run against a real model. The prompt, the retry and the accuracy on images are untested end to end.
- All fixtures are clean synthetic renders. Real photos (creases, stamps, shadows, real handwriting) will be harder; the blur threshold was set on one synthetic blurry image.
- Only the first 3 PDF pages are read.
- Without an LLM, images are not read at all, and the rules only know the phrasings and the roughly 50 countries and 30 job words listed in the code. They never extract the employer.
- Skewed pages are not straightened; only EXIF rotation is applied and the model is left to cope. OpenCV is not used.
- Arabic number words ("سنة واحدة") are not parsed in code; that value comes from the model's own number and is marked uncertain.
- The licence check only confirms the digits appear in the transcription. If the model misreads a digit consistently in both places, the wrong number passes. It does not check that the licence exists; that is the knowledge module's job.
- A fee quoted in a foreign currency is left empty rather than converted.
- `mask_pii` is pattern based. A name on a line without a label ("Mr. …" in running text) is not masked.

## Cost per call (estimate, not measured)

Assumptions: default model `claude-sonnet-5-5` at $2 per million input tokens and $10 per million output tokens; one A4 page at 1568 px costs about 2,300 input tokens (assuming roughly width × height / 750); the instructions are about 1,500 tokens; the answer, with the transcription, about 800 tokens; plus an unknown amount of thinking, billed as output, guessed here at 700 tokens.

| Call | Input | Output | Cost |
| --- | --- | --- | --- |
| One-page photo | ~3,800 | ~1,500 | ~$0.02 |
| Text only | ~1,600 | ~1,000 | ~$0.01 |
| Three-page PDF | ~8,400 | ~2,000 | ~$0.04 |

A retry after an invalid answer doubles the call. None of these token counts were measured; check them against `usage` on real calls before budgeting.
