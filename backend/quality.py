"""How the verdict engine does on the labelled cases in data/test_cases/.

The number that matters is `fraud_green`: fraud cases the engine called safe. Target 0.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def evaluation() -> dict:
    """Run the knowledge module's own evaluation once per process. Case ids only, no offer content."""
    from probashi.knowledge.eval import load_cases, run
    from probashi.knowledge.kb import data_dir

    report = run(load_cases(data_dir() / "test_cases"))
    results = report.pop("results")
    if not results:
        raise RuntimeError("no test cases found")
    real = sum(not r["synthetic"] for r in results)
    return {
        **report,
        "as_of": report["as_of"].isoformat(),
        "real": real,
        "synthetic": len(results) - real,
        "misses": [
            {"id": r["id"], "expected": r["expected"], "got": r["got"], "is_fraud": r["is_fraud"]}
            for r in results
            if r["expected"] != r["got"]
        ],
    }
