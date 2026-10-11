"""Joining and comparing several papers for one job."""

import pytest

from probashi.knowledge.consistency import add_mismatch, merge_offers
from probashi.knowledge.engine import explain
from probashi.schemas import Level

from .conftest import TODAY, good_offer


def test_single_paper_is_returned_unchanged():
    offer = good_offer()
    assert merge_offers([offer]) == (offer, [])
    with pytest.raises(ValueError):
        merge_offers([])


def test_missing_fact_is_filled_from_another_paper():
    letter = good_offer(visa_type=None, monthly_salary={"amount": None, "currency": None},
                        missing_fields=["visa_type", "monthly_salary", "employer_name"], employer_name=None)
    visa = good_offer(employer_name=None, missing_fields=["employer_name"], confidence=0.6, raw_text="visa page")
    merged, differing = merge_offers([letter, visa])
    assert differing == []
    assert merged.visa_type == "Work visa" and merged.monthly_salary.amount == 1300
    assert merged.missing_fields == ["employer_name"]
    assert merged.confidence == 0.6 and "visa page" in merged.raw_text


def test_spelling_and_spacing_are_not_a_disagreement():
    a = good_offer(agency_license_no="RL-9001", employer_name="Synthetic Employer Co")
    b = good_offer(agency_license_no="rl 9001", employer_name="SYNTHETIC EMPLOYER CO.",
                   monthly_salary={"amount": 1300, "currency": None})
    assert merge_offers([a, b])[1] == []


def test_papers_that_disagree_are_reported_and_first_paper_wins():
    letter = good_offer()
    contract = good_offer(monthly_salary={"amount": 900, "currency": "QAR"}, job_title="Farm labour")
    merged, differing = merge_offers([letter, contract, contract])
    assert differing == ["job_title", "monthly_salary"]
    assert merged.monthly_salary.amount == 1300 and merged.job_title == "Cleaner"


def test_a_value_marked_missing_is_ignored_even_if_filled():
    other = good_offer(job_title="Driver", missing_fields=["job_title"])
    assert merge_offers([good_offer(), other])[1] == []


def test_mismatch_turns_green_into_amber_and_keeps_red_red(kb):
    green = explain(good_offer(), today=TODAY, kb=kb)[0]
    assert green.level == Level.green and add_mismatch(green, []) is green
    warned = add_mismatch(green, ["monthly_salary", "job_title"])
    assert warned.level == Level.amber and warned.reasons[0].code == "DOCUMENT_MISMATCH"
    assert "বেতন" in warned.reasons[0].message_bn and "salary" in warned.reasons[0].message_en

    red = explain(good_offer(visa_type="Tourist visa"), today=TODAY, kb=kb)[0]
    assert add_mismatch(red, ["job_title"]).level == Level.red
