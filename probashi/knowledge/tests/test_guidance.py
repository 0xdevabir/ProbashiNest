"""Clause scanner and the guidance built on top of a verdict."""

import pytest

from probashi.knowledge.engine import explain
from probashi.knowledge.guidance import MAX_FOLLOW_UP, guidance, guide
from probashi.knowledge.kb import load_kb
from probashi.knowledge.rules import MEDIUM, check_contract_clauses
from probashi.schemas import Level

from .conftest import TODAY, good_offer


def run(kb, **changes):
    offer = good_offer(**changes)
    return offer, explain(offer, today=TODAY, kb=kb)[0]


# ----------------------------------------------------------------------------- clause scanner

@pytest.mark.parametrize("text,code", [
    ("The employer will keep your passport for safe custody.", "PASSPORT_KEPT"),
    ("পাসপোর্ট কোম্পানির কাছে থাকবে।", "PASSPORT_KEPT"),
    ("Visa cost will be deducted from your salary over 10 months.", "FEE_DEDUCTED_FROM_SALARY"),
    ("খরচের টাকা বেতন থেকে কেটে নেওয়া হবে।", "FEE_DEDUCTED_FROM_SALARY"),
    ("You must do any work the sponsor gives.", "JOB_VAGUE"),
    ("যেকোনো কাজ করতে হবে।", "JOB_VAGUE"),
])
def test_risky_clause_is_a_warning_not_red(kb, text, code):
    flags = check_contract_clauses(good_offer(raw_text=text), kb)
    assert [(f.code, f.severity) for f in flags] == [(code, MEDIUM)]
    assert run(kb, raw_text=text)[1].level == Level.amber


def test_clean_text_raises_no_clause_flag(kb):
    assert check_contract_clauses(good_offer(raw_text="Cleaner, 1300 QAR, 24 months."), kb) == []
    assert run(kb)[1].level == Level.green


def test_passport_clause_cites_the_destinations_own_rule(kb):
    (flag,) = check_contract_clauses(good_offer(raw_text="We keep your passport."), kb)
    rule = kb.rule("QA", "passport_retention")
    assert (flag.record_id, flag.source.url) == ((rule["id"], rule["source"]["url"]) if rule else (None, None))


def test_clause_with_no_rule_for_the_country_has_no_source(kb):
    # Malaysia has no passport rule in the data: the warning stays, the citation does not.
    assert kb.rule("MY", "passport_retention") is None
    (flag,) = check_contract_clauses(good_offer(destination_country="MY", raw_text="We keep your passport."), kb)
    assert flag.source is None


# ----------------------------------------------------------------------------- guidance

def test_follow_up_asks_only_for_missing_facts_most_useful_first(kb):
    offer, verdict = run(kb, agency_license_no=None, fees_charged_bdt=None, visa_type=None, job_title=None)
    asked = [p.key for p in guidance(offer, verdict, kb=kb).follow_up]
    assert asked == ["agency_license_no", "fees_charged_bdt", "visa_type"]
    assert len(asked) <= MAX_FOLLOW_UP


def test_complete_green_offer_has_nothing_to_ask(kb):
    offer, verdict = run(kb)
    out = guidance(offer, verdict, kb=kb)
    assert out.follow_up == [] and out.ask_agent == [] and out.complaint_draft_bn is None
    assert out.confidence == offer.confidence


def test_agent_questions_follow_the_reasons_without_repeats(kb):
    offer, verdict = run(kb, agency_license_no=None, employer_name=None, job_title=None, visa_type="Tourist visa")
    questions = guidance(offer, verdict, kb=kb).ask_agent
    assert len({q.text_bn for q in questions}) == len(questions) >= 3
    assert {q.key for q in questions} <= {r.code for r in verdict.reasons}


def test_explainer_carries_source_and_date_and_says_when_unverified(kb):
    offer, verdict = run(kb, destination_country="SA", monthly_salary={"amount": 1500, "currency": "SAR"},
                         fees_charged_bdt=900000)
    by_code = {e.code: e for e in guidance(offer, verdict, kb=kb).explainers}
    ceiling = kb.rule("SA", "bd_migration_cost_ceiling")
    fee = next(e for code, e in by_code.items() if code.startswith("FEE_"))
    assert fee.text_bn == ceiling["text_bn"] and fee.last_checked == ceiling["last_checked"]
    assert fee.verified is False and "not yet verified" in fee.source.title


def test_agency_reason_is_explained_by_the_register_copy(kb):
    offer, verdict = run(kb, agency_license_no="RL-9002")
    explainers = guidance(offer, verdict, kb=kb).explainers
    (agency,) = [e for e in explainers if e.source and e.source.url == kb.register.source_url]
    assert agency.code.startswith("AGENCY_") and agency.last_checked == kb.register.last_checked


def test_complaint_draft_only_for_red_and_never_invents_details(kb):
    offer, verdict = run(kb, visa_type="Tourist visa", agency_license_no=None, fees_charged_bdt=450000)
    assert verdict.level == Level.red
    draft = guidance(offer, verdict, kb=kb).complaint_draft_bn
    assert "৪,৫০,০০০ টাকা" in draft and "Synthetic Active Agency Ltd" in draft and "দেয়নি" in draft
    assert "আমার নাম: __________" in draft
    assert all(r.message_bn in draft for r in verdict.reasons)

    offer, verdict = run(kb, employer_name=None)
    assert verdict.level == Level.amber and guidance(offer, verdict, kb=kb).complaint_draft_bn is None


def test_guidance_survives_a_missing_knowledge_base(kb, monkeypatch, tmp_path):
    offer, verdict = run(kb, agency_license_no=None)
    monkeypatch.setenv("PROBASHI_DATA_DIR", str(tmp_path))
    out = guidance(offer, verdict)
    assert out.follow_up and out.explainers == []


# ----------------------------------------------------------------------------- country guide

def test_guide_lists_only_that_countrys_rights_with_sources(kb):
    page = guide("sa", kb=kb)
    ids = {r["id"] for r in kb.rules["SA"]["records"]}
    assert page.country == "SA" and page.rights and {r.id for r in page.rights} <= ids
    assert all(r.last_checked for r in page.rights)
    assert any(h.phone == "16135" for h in page.helplines)


def test_guide_for_unknown_country_still_gives_checklist_and_home_numbers(kb):
    page = guide("ZZ", kb=kb)
    assert page.rights == [] and page.country_name_bn is None
    assert [c.id for c in page.checklist] == [c["id"] for c in kb.checklist]
    assert page.payment_tips_bn and page.helplines


def test_checklist_steps_are_sourced_and_honest_about_verification():
    steps = load_kb().checklist
    assert len(steps) >= 3
    for step in steps:
        assert step["source"]["url"].startswith("http")
        # Read in a secondary guide only: must stay unverified until checked on a government page.
        assert step["verified"] is (".gov.bd" in step["source"]["url"])
