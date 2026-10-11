"""Shape and wording of the Verdict: messages, sources, next steps, helplines."""

import re
from datetime import date

import pytest

import probashi.knowledge as knowledge
from probashi.knowledge.engine import explain
from probashi.knowledge.messages import DISCLAIMER_BN, TEMPLATES, bn_number, next_steps, render
from probashi.knowledge.rules import HIGH, MEDIUM, Flag
from probashi.schemas import ExtractedOffer, Level, Verdict

from .conftest import TODAY, good_offer

BENGALI = re.compile(r"[ঀ-৿]")
OFFERS = [
    good_offer(),
    ExtractedOffer(),
    good_offer(visa_type="Tourist visa", fees_charged_bdt=900000, destination_country="SA",
               monthly_salary={"amount": 1500, "currency": "SAR"}, raw_text="আজকেই টাকা দিন, বিকাশ করুন"),
    good_offer(agency_license_no="RL9002", agency_name="Synthetic Cancelled Agency"),
    good_offer(agency_license_no="RL9006", agency_name="Synthetic Lapsed Agency", monthly_salary={"amount": 700, "currency": "QAR"}),
    good_offer(destination_country="MY", job_title="Cleaner", monthly_salary={"amount": 9000, "currency": "MYR"}, fees_charged_bdt=90000),
]


@pytest.mark.parametrize("offer", OFFERS)
def test_verdict_is_complete_and_bilingual(kb, offer):
    verdict, _ = explain(offer, today=TODAY, kb=kb)
    assert isinstance(verdict, Verdict)
    assert verdict.reasons, "a verdict always explains itself"
    for reason in verdict.reasons:
        assert reason.code in TEMPLATES
        assert BENGALI.search(reason.message_bn)
        assert reason.message_en and not BENGALI.search(reason.message_en.replace(offer.visa_type or "", ""))
        assert "{" not in reason.message_bn and "{" not in reason.message_en
    assert 2 <= len(verdict.next_steps_bn) <= 4
    assert len(set(verdict.next_steps_bn)) == len(verdict.next_steps_bn)
    assert all(BENGALI.search(s) for s in verdict.next_steps_bn)
    assert verdict.disclaimer_bn == DISCLAIMER_BN


def test_bangla_messages_use_short_sentences(kb):
    for offer in OFFERS:
        for reason in explain(offer, today=TODAY, kb=kb)[0].reasons:
            for sentence in filter(None, (s.strip() for s in reason.message_bn.split("।"))):
                assert len(sentence.split()) <= 16, sentence


def test_every_template_renders():
    params = {"licence": "RL9001", "name": "N", "status": "Cancelled", "date": date(2025, 6, 30), "registered": "R",
              "fields": ["visa_type"], "country": "ZZ", "fee": 100000.0, "limit": 165000, "salary": 1300.5,
              "minimum": 1000, "currency": "QAR", "visa": "Tourist", "job": "Cleaner"}
    for name in TEMPLATES:
        bn, en = render(Flag(name, MEDIUM, params))
        assert bn and en and "{" not in bn + en


def test_amounts_are_spoken_in_bangla_digits():
    assert bn_number(165000) == "১,৬৫,০০০"
    assert bn_number(78990) == "৭৮,৯৯০"
    assert bn_number(1000) == "১,০০০"
    assert bn_number(75) == "৭৫"
    assert bn_number(12345678) == "১,২৩,৪৫,৬৭৮"
    assert bn_number(1300.5) == "১,৩০০.৫"


def test_red_verdict_starts_with_do_not_pay():
    steps = next_steps([Flag("AGENCY_NOT_FOUND", HIGH)])
    assert steps[0] == "এখন কোনো টাকা দেবেন না।"
    assert "এখন কোনো টাকা দেবেন না।" not in next_steps([Flag("MISSING_LICENCE_NO", MEDIUM)])


def test_reasons_carry_sources(kb):
    verdict, _ = explain(
        good_offer(agency_license_no="RL9002", agency_name="Synthetic Cancelled Agency", visa_type="Free visa",
                   monthly_salary={"amount": 700, "currency": "QAR"}),
        today=TODAY, kb=kb,
    )
    by_code = {r.code: r for r in verdict.reasons}
    assert "RAIMS" in by_code["AGENCY_UNLICENSED"].source.title
    assert "ilo.org" in by_code["SALARY_BELOW_MINIMUM"].source.url
    assert "dhakatribune.com" in by_code["FREE_VISA"].source.url  # found by retrieval


def test_unsourced_pattern_has_no_invented_source(kb):
    verdict, _ = explain(good_offer(raw_text="আজকেই টাকা দিতে হবে"), today=TODAY, kb=kb)
    reason = next(r for r in verdict.reasons if r.code == "PRESSURE_TO_PAY")
    assert reason.source is None


def test_helplines_are_home_numbers_plus_destination_wing(kb):
    verdict, _ = explain(good_offer(), today=TODAY, kb=kb)
    phones = [h.phone for h in verdict.helplines]
    assert phones[0] == "16135"
    known = {h["phone"] for h in kb.helplines if h["verified"]}
    assert set(phones) <= known
    qatar = {h["phone"] for h in kb.helplines if h["country"] == "QA"}
    saudi = {h["phone"] for h in kb.helplines if h["country"] == "SA"}
    assert qatar & set(phones) and not saudi & set(phones)


def test_public_evaluate_uses_the_real_data():
    verdict = knowledge.evaluate(ExtractedOffer())
    assert verdict.level == Level.amber
    assert verdict.helplines and verdict.reasons
