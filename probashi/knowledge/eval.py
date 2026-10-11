"""Run the verdict engine over data/test_cases/ and report how it did.

    python -m probashi.knowledge.eval            # summary + every miss
    python -m probashi.knowledge.eval -v         # one line per case

Prints accuracy against the expected level and, most importantly, the number of
fraud cases rated green (target: 0). Exit code is 1 if any fraud case is green.

The register lookup depends on the date, so by default the cases are evaluated
"as of" the day data/agencies.csv was last refreshed; use --as-of to change that.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from probashi.schemas import ExtractedOffer

from .engine import explain
from .kb import data_dir, load_kb

REQUIRED = ("id", "note", "synthetic", "is_fraud", "expected_level", "offer")


def load_cases(folder: Path) -> list[dict]:
    cases = []
    for path in sorted(folder.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED if k not in case]
        if missing:
            raise ValueError(f"{path.name}: missing {missing}")
        if case["expected_level"] not in ("red", "amber", "green"):
            raise ValueError(f"{path.name}: bad expected_level {case['expected_level']!r}")
        cases.append(case)
    return cases


def run(cases: list[dict], as_of: date | None = None) -> dict:
    """Evaluate every case. Returns counts and per-case results."""
    kb = load_kb()
    as_of = as_of or kb.register.last_checked or date.today()
    results = []
    for case in cases:
        verdict, _ = explain(ExtractedOffer(**case["offer"]), today=as_of, kb=kb)
        results.append(
            {
                "id": case["id"],
                "expected": case["expected_level"],
                "got": verdict.level.value,
                "is_fraud": bool(case["is_fraud"]),
                "synthetic": bool(case["synthetic"]),
                "codes": [r.code for r in verdict.reasons],
            }
        )
    fraud = [r for r in results if r["is_fraud"]]
    return {
        "as_of": as_of,
        "results": results,
        "total": len(results),
        "correct": sum(r["expected"] == r["got"] for r in results),
        "fraud_total": len(fraud),
        "fraud_green": sum(r["got"] == "green" for r in fraud),
        "fraud_red": sum(r["got"] == "red" for r in fraud),
        "safe_green_expected": sum(r["expected"] == "green" for r in results),
        "safe_green_got": sum(r["expected"] == "green" and r["got"] == "green" for r in results),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate the verdict engine on data/test_cases/")
    ap.add_argument("--cases", type=Path, default=data_dir() / "test_cases")
    ap.add_argument("--as-of", type=date.fromisoformat, default=None, help="evaluation date (YYYY-MM-DD)")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every case")
    args = ap.parse_args(argv)

    report = run(load_cases(args.cases), args.as_of)
    total = report["total"]
    if not total:
        print(f"no test cases found in {args.cases}")
        return 1
    for r in report["results"]:
        ok = r["expected"] == r["got"]
        if args.verbose or not ok:
            mark = "ok  " if ok else "MISS"
            print(f"{mark} {r['id']:<42} expected={r['expected']:<5} got={r['got']:<5} {','.join(r['codes'])}")
    real = sum(not r["synthetic"] for r in report["results"])
    print(f"\ncases: {total} ({real} from real reports, {total - real} synthetic), evaluated as of {report['as_of']}")
    print(f"accuracy: {report['correct']}/{total} = {report['correct'] / total:.0%}")
    print(f"fraud cases rated green: {report['fraud_green']} of {report['fraud_total']} (target 0)")
    print(f"fraud cases rated red: {report['fraud_red']} of {report['fraud_total']} (the rest are amber)")
    print(f"good offers rated green: {report['safe_green_got']} of {report['safe_green_expected']}")
    return 1 if report["fraud_green"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
