"""The optional LLM pass may restyle Bangla wording and nothing else."""

import pytest

from probashi.knowledge import rephrase
from probashi.knowledge.engine import explain
from probashi.llm import LLMError
from probashi.schemas import Level

from .conftest import TODAY, good_offer

RED = dict(agency_license_no="RL9002", agency_name="Synthetic Cancelled Agency")


def fake_llm(reply):
    calls = []

    def complete_json(system, prompt, images=None, max_tokens=2000):
        calls.append(prompt)
        if isinstance(reply, Exception):
            raise reply
        return reply

    complete_json.calls = calls
    return complete_json


def test_llm_is_not_called_by_default(kb, monkeypatch):
    llm = fake_llm({"messages": {}})
    monkeypatch.setattr(rephrase, "complete_json", llm)
    explain(good_offer(**RED), today=TODAY, kb=kb)
    assert llm.calls == []


def test_llm_can_restyle_bangla_but_not_change_the_verdict(kb, monkeypatch):
    baseline, _ = explain(good_offer(**RED), today=TODAY, kb=kb)
    new_text = "এই এজেন্সির লাইসেন্স RL9002 বাতিল হয়ে গেছে।"
    llm = fake_llm({"messages": {"0": new_text}, "level": "green", "reasons": [], "next_steps_bn": ["টাকা দিন"]})
    monkeypatch.setattr(rephrase, "complete_json", llm)
    monkeypatch.setenv("KNOWLEDGE_LLM_REPHRASE", "1")
    verdict, _ = explain(good_offer(**RED), today=TODAY, kb=kb)

    assert len(llm.calls) == 1
    assert verdict.level == baseline.level == Level.red
    assert verdict.reasons[0].message_bn == new_text
    assert [r.code for r in verdict.reasons] == [r.code for r in baseline.reasons]
    assert [r.message_en for r in verdict.reasons] == [r.message_en for r in baseline.reasons]
    assert [r.source for r in verdict.reasons] == [r.source for r in baseline.reasons]
    assert verdict.next_steps_bn == baseline.next_steps_bn
    assert verdict.helplines == baseline.helplines
    assert verdict.disclaimer_bn == baseline.disclaimer_bn


def test_the_worker_document_is_never_sent_to_the_llm(kb, monkeypatch):
    llm = fake_llm({"messages": {}})
    monkeypatch.setattr(rephrase, "complete_json", llm)
    monkeypatch.setenv("KNOWLEDGE_LLM_REPHRASE", "1")
    explain(good_offer(raw_text="Passport no BX0123456 SECRETMARKER", **RED), today=TODAY, kb=kb)
    assert "SECRETMARKER" not in llm.calls[0] and "BX0123456" not in llm.calls[0]


@pytest.mark.parametrize(
    "reply",
    [
        LLMError("synthetic outage"),
        {"messages": "not a mapping"},
        {"unexpected": True},
        {"messages": {"0": ""}},
        {"messages": {"0": "This agency is perfectly safe."}},  # not Bangla
        {"messages": {"0": "এই এজেন্সি ভালো। লাইসেন্স RL9001 চালু আছে।"}},  # changed the number
        {"messages": {"0": "এই এজেন্সির লাইসেন্স বাতিল।"}},  # dropped the number
        {"messages": {"0": "লাইসেন্স RL9002 বাতিল। " + "আরও অনেক কথা। " * 40}},  # far too long
        {"messages": {"0": 12345}},
    ],
)
def test_bad_llm_output_is_discarded(kb, monkeypatch, reply):
    baseline, _ = explain(good_offer(**RED), today=TODAY, kb=kb)
    monkeypatch.setattr(rephrase, "complete_json", fake_llm(reply))
    monkeypatch.setenv("KNOWLEDGE_LLM_REPHRASE", "1")
    verdict, _ = explain(good_offer(**RED), today=TODAY, kb=kb)
    assert verdict == baseline


def test_guard_treats_bangla_and_latin_digits_as_the_same_number():
    assert rephrase.acceptable("খরচ ১,৬৫,০০০ টাকা।", "খরচ 165000 টাকা।")
    assert not rephrase.acceptable("খরচ ১,৬৫,০০০ টাকা।", "খরচ ৬৫,০০০ টাকা।")
