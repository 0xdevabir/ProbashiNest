"""Per-field extraction accuracy on the synthetic fixtures.

    python -m probashi.extract.tests.accuracy           # LLM if a key is set
    python -m probashi.extract.tests.accuracy --rules   # force the no-LLM path

The --rules run reads only the text fixtures: without an LLM, images are
not read at all.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

from probashi.extract import extract_offer
from probashi.schemas import ExtractedOffer

FIXTURES = Path(__file__).parent / "fixtures"
FIELDS = (
    "employer_name", "job_title", "destination_country", "salary_amount",
    "salary_currency", "agency_name", "agency_license_no", "fees_charged_bdt",
    "contract_duration_months", "visa_type", "document_language",
)
_FREE_TEXT_FIELDS = {"employer_name", "job_title", "agency_name"}


def load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["fixtures"]


def flatten(offer: ExtractedOffer) -> dict[str, Any]:
    flat = offer.model_dump()
    flat["salary_amount"] = offer.monthly_salary.amount
    flat["salary_currency"] = offer.monthly_salary.currency
    return flat


def _loose(s: str) -> str:
    s = re.sub(r"\([^)]*\)", " ", s.lower())  # drop "(FICTIONAL)"
    return " ".join(re.sub(r"[.,&'\"-]", " ", s).split())


def field_correct(field: str, expected: Any, got: Any) -> bool:
    """A list of expected values means any one of them is right. Names and
    job titles match loosely (case, punctuation, one containing the other);
    everything else must match exactly. Expected None means the field must
    be left empty: a value there is an invention."""
    if expected is None or got is None:
        return expected is None and got is None
    options = expected if isinstance(expected, list) else [expected]
    if field in _FREE_TEXT_FIELDS:
        g = _loose(str(got))
        return any(_loose(o) in g or g in _loose(o) for o in options) if g else False
    if isinstance(got, (int, float)) and not isinstance(got, bool):
        return any(abs(float(o) - float(got)) < 0.5 for o in options)
    return got in options


def score(results: list[tuple[dict, dict]]) -> dict[str, tuple[int, int]]:
    """results: (expected, flattened offer) pairs -> field -> (correct, total)."""
    return {
        f: (sum(field_correct(f, exp[f], got.get(f)) for exp, got in results), len(results))
        for f in FIELDS
    }


def format_table(scores: dict[str, tuple[int, int]]) -> str:
    lines = [f"{'field':28s} correct  accuracy"]
    for f, (ok, n) in scores.items():
        lines.append(f"{f:28s} {ok:>3d}/{n:<3d}  {ok / n:6.0%}")
    ok = sum(c for c, _ in scores.values())
    n = sum(t for _, t in scores.values())
    lines.append(f"{'ALL FIELDS':28s} {ok:>3d}/{n:<3d}  {ok / n:6.0%}")
    return "\n".join(lines)


def run(
    extract: Callable[[Optional[bytes], Optional[str]], ExtractedOffer] = extract_offer,
    images: bool = True,
    texts: bool = True,
) -> list[tuple[str, dict, dict]]:
    """Run every fixture; returns (fixture name, expected, flattened offer)."""
    out = []
    if images:
        for fx in load("image_fixtures.json"):
            data = (FIXTURES / fx["file"]).read_bytes()
            out.append((fx["file"], fx["expected"], flatten(extract(data, None))))
    if texts:
        for fx in load("text_fixtures.json"):
            out.append((fx["id"], fx["expected"], flatten(extract(None, fx["text"]))))
    return out


def report(rows: list[tuple[str, dict, dict]]) -> str:
    parts = [format_table(score([(exp, got) for _, exp, got in rows])), "", "Misses:"]
    for name, exp, got in rows:
        for f in FIELDS:
            if not field_correct(f, exp[f], got.get(f)):
                # Expected values are synthetic, so they are safe to print.
                parts.append(f"  {name}: {f}: expected {exp[f]!r}, got {got.get(f)!r}")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rules", action="store_true", help="force the rule-based path")
    args = parser.parse_args()
    if args.rules:
        from probashi.extract import extractor
        from probashi.llm import LLMError

        def no_llm(*a, **k):
            raise LLMError("disabled by --rules")

        extractor.complete_json = no_llm
        print("Path: rules only (text fixtures)\n")
        print(report(run(images=False)))
    else:
        print("Path: as configured by LLM_PROVIDER / LLM_MODEL\n")
        print(report(run()))


if __name__ == "__main__":
    main()
