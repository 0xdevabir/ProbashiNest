"""The level table, and the safety rule: unknown or unverifiable never becomes green."""

import dataclasses
import itertools

import pytest

import probashi.knowledge as knowledge
from probashi.knowledge.engine import decide_level, explain
from probashi.knowledge.kb import KnowledgeBaseError
from probashi.knowledge.rules import HIGH, INFO, KEY_FIELDS, MEDIUM, Flag
from probashi.schemas import ExtractedOffer, Level

from .conftest import TODAY, good_offer, make_register, with_rule


def level(kb, **changes):
    return explain(good_offer(**changes), today=TODAY, kb=kb)[0].level


# ----------------------------------------------------------------------------- the table

@pytest.mark.parametrize(
    "severities,agency_verified,missing,expected",
    [
        ([HIGH], True, [], Level.red),
        ([HIGH, MEDIUM, INFO], True, [], Level.red),
        ([HIGH], False, ["visa_type"], Level.red),
        ([MEDIUM], True, [], Level.amber),
        ([MEDIUM, INFO], True, [], Level.amber),
        ([INFO], True, ["visa_type"], Level.amber),  # missing fact even if no flag was raised
        ([INFO], False, [], Level.amber),  # nothing wrong found, but agency not verified
        ([], False, [], Level.amber),
        ([INFO], True, [], Level.green),
        ([], True, [], Level.green),
    ],
)
def test_decide_level_table(severities, agency_verified, missing, expected):
    flags = [Flag("X", s) for s in severities]
    assert decide_level(flags, agency_verified, missing) == expected


def test_complete_verified_offer_is_green(kb):
    verdict, why = explain(good_offer(), today=TODAY, kb=kb)
    assert verdict.level == Level.green
    assert why.agency_verified
    assert [r.code for r in verdict.reasons] == ["AGENCY_LICENSED"]


def test_one_high_flag_makes_red_even_with_a_licensed_agency(kb):
    assert level(kb, visa_type="Tourist visa") == Level.red
    assert level(kb, monthly_salary={"amount": 500, "currency": "QAR"}) == Level.red


def test_reasons_are_ordered_most_serious_first(kb):
    verdict, why = explain(good_offer(visa_type="Tourist visa", employer_name=None), today=TODAY, kb=kb)
    assert [f.severity for f in why.flags] == sorted((f.severity for f in why.flags), key=[HIGH, MEDIUM, INFO].index)
    assert verdict.reasons[0].code == "VISA_JOB_MISMATCH"


# ----------------------------------------------------------------------------- unknown never green

def test_empty_offer_is_amber(kb):
    assert explain(ExtractedOffer(), today=TODAY, kb=kb)[0].level == Level.amber


@pytest.mark.parametrize("field", KEY_FIELDS)
def test_each_missing_key_field_blocks_green(kb, field):
    value = {} if field == "monthly_salary" else None
    assert level(kb, **{field: value}) != Level.green


@pytest.mark.parametrize("field", KEY_FIELDS)
def test_field_reported_missing_by_extractor_blocks_green(kb, field):
    assert level(kb, missing_fields=[field]) != Level.green


def test_no_combination_of_missing_fields_is_green(kb):
    for n in (2, 3):
        for combo in itertools.combinations(KEY_FIELDS, n):
            changes = {f: ({} if f == "monthly_salary" else None) for f in combo}
            assert level(kb, **changes) != Level.green, combo


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": 0.0},
        {"confidence": 0.3},
        {"agency_license_no": "RL-1234", "agency_name": "Unknown Synthetic Agency"},  # not in register
        {"agency_license_no": "RL9005", "agency_name": "Synthetic Locked Agency"},  # status unclear
        {"agency_license_no": "RL9007", "agency_name": "Synthetic Undated Agency"},  # no validity date
        {"agency_name": "Some Other Recruiters"},  # name does not match the licence
        {"destination_country": "ZZ"},  # no rules for this destination
        {"monthly_salary": {"amount": 1300, "currency": None}},  # currency unknown
        {"fees_charged_bdt": 50000},  # Qatar: no sourced ceiling to check against
        {"destination_country": "SA", "fees_charged_bdt": 100000},  # ceiling exists but is unverified
    ],
)
def test_unverifiable_evidence_is_never_green(kb, changes):
    assert level(kb, **changes) != Level.green


def test_stale_register_blocks_green(kb):
    stale = dataclasses.replace(kb, register=make_register(last_checked=None))
    assert explain(good_offer(), today=TODAY, kb=stale)[0].level == Level.amber


def test_fee_is_green_only_once_the_ceiling_is_verified(kb):
    offer = dict(destination_country="SA", monthly_salary={"amount": 1500, "currency": "SAR"}, fees_charged_bdt=100000)
    assert level(kb, **offer) == Level.amber
    assert level(with_rule(kb, "SA", "SA_BD_COST_CEILING", verified=True), **offer) == Level.green


def test_broken_knowledge_base_gives_amber_not_green_or_crash(monkeypatch):
    def boom(*args, **kwargs):
        raise KnowledgeBaseError("synthetic failure")

    monkeypatch.setattr("probashi.knowledge.engine.load_kb", boom)
    verdict = knowledge.evaluate(good_offer())
    assert verdict.level == Level.amber
    assert [r.code for r in verdict.reasons] == ["KNOWLEDGE_UNAVAILABLE"]
    assert 2 <= len(verdict.next_steps_bn) <= 4


def test_missing_data_folder_gives_amber(monkeypatch, tmp_path):
    monkeypatch.setenv("PROBASHI_DATA_DIR", str(tmp_path))
    assert knowledge.evaluate(good_offer()).level == Level.amber
