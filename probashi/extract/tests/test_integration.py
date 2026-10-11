"""Real LLM run over every fixture. Skipped unless an API key is set.

    ANTHROPIC_API_KEY=... pytest probashi/extract/tests/test_integration.py -s

Use -s to see the per-field accuracy table. This costs real money: one call
per fixture (17 calls).
"""
import os

import pytest

from probashi.extract.tests.accuracy import report, run, score

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY is not set"
)

# Not a quality target, only a tripwire for a broken prompt or wrapper.
MIN_OVERALL_ACCURACY = 0.7


@pytest.fixture(scope="module")
def rows():
    return run()


def test_accuracy_report(rows):
    print("\n" + report(rows))
    scores = score([(exp, got) for _, exp, got in rows])
    correct = sum(c for c, _ in scores.values())
    total = sum(t for _, t in scores.values())
    assert correct / total >= MIN_OVERALL_ACCURACY


def test_nothing_is_invented(rows):
    """Where the document states no value, the field must stay empty. These
    are the fields the verdict engine leans on, so an invention here could
    turn a warning into a pass."""
    critical = ("agency_license_no", "agency_name", "fees_charged_bdt", "salary_amount")
    invented = [
        (name, f, got[f])
        for name, exp, got in rows
        for f in critical
        if exp[f] is None and got[f] is not None
    ]
    assert not invented


def test_every_null_field_is_listed_as_missing(rows):
    for name, _, got in rows:
        for f in ("employer_name", "agency_license_no", "fees_charged_bdt", "visa_type"):
            assert (got[f] is None) == (f in got["missing_fields"]), (name, f)


def test_blurry_photo_is_less_confident_than_the_clean_one(rows):
    by_name = {name: got for name, _, got in rows}
    assert by_name["09_en_offer_blurry.jpg"]["confidence"] < by_name["01_en_offer_clean.png"]["confidence"]
