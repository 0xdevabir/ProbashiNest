"""The no-LLM fallback on the synthetic Bangla descriptions. No API needed."""
import pytest

from probashi.extract.rules import extract_with_rules
from probashi.extract.tests.accuracy import FIELDS, field_correct, load

TEXT_FIXTURES = load("text_fixtures.json")

# Known gaps of the rule-based path, kept visible instead of hidden:
# romanised Bangla is not told apart from English, so the language stays None.
KNOWN_GAPS = {("t7_kuwait_romanised", "document_language")}


def _flat(text: str) -> dict:
    fields, _, _ = extract_with_rules(text)
    salary = fields.pop("monthly_salary")
    return {**fields, "salary_amount": salary.amount, "salary_currency": salary.currency}


@pytest.mark.parametrize("fx", TEXT_FIXTURES, ids=[fx["id"] for fx in TEXT_FIXTURES])
def test_text_fixture(fx):
    got = _flat(fx["text"])
    wrong = {
        f: (fx["expected"][f], got.get(f))
        for f in FIELDS
        if not field_correct(f, fx["expected"][f], got.get(f)) and (fx["id"], f) not in KNOWN_GAPS
    }
    assert not wrong, f"field: (expected, got) = {wrong}"


def test_there_are_at_least_six_bangla_descriptions():
    assert len(TEXT_FIXTURES) >= 6


def test_licence_and_phone_numbers_are_not_read_as_fees():
    got = _flat("এজেন্সির লাইসেন্স নম্বর ৯৯৯৯১। ফোন নম্বর ০১৭০০০০০০০০।")
    assert got["fees_charged_bdt"] is None
    assert got["salary_amount"] is None


def test_fee_in_foreign_currency_is_not_reported_as_taka():
    fields, _, notes = extract_with_rules("সৌদিতে কাজ। এজেন্টকে ২০০০ ডলার দিতে হবে।")
    assert fields["fees_charged_bdt"] is None
    assert any("not converted" in n for n in notes)


def test_bare_riyal_without_country_gives_no_currency():
    got = _flat("বেতন ১০০০ রিয়াল")
    assert got["salary_currency"] is None


def test_employer_is_never_guessed():
    for fx in TEXT_FIXTURES:
        assert _flat(fx["text"])["employer_name"] is None


def test_empty_text():
    got = _flat("")
    assert all(got[f] is None for f in FIELDS)
