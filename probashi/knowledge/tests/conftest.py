"""Shared fixtures. The agency register used in unit tests is SYNTHETIC (invented
names and licence numbers) so tests do not depend on the live register copy."""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from probashi.knowledge.agencies import Agency, AgencyRegister, normalize_name
from probashi.knowledge.kb import load_kb
from probashi.schemas import ExtractedOffer

TODAY = date(2026, 1, 15)
REGISTER_DATE = date(2026, 1, 10)

# licence, name, status, valid_until  -- all synthetic
SYNTHETIC_AGENCIES = [
    ("RL9001", "Synthetic Active Agency Ltd", "Active", date(2030, 1, 1)),
    ("RL9002", "Synthetic Cancelled Agency", "Cancelled", date(2030, 1, 1)),
    ("RL9003", "Synthetic Suspended Agency", "Suspended", date(2030, 1, 1)),
    ("RL9004", "Synthetic Expired Agency", "Expired", date(2025, 1, 1)),
    ("RL9005", "Synthetic Locked Agency", "Server Locked", date(2030, 1, 1)),
    ("RL9006", "Synthetic Lapsed Agency", "Active", date(2025, 6, 30)),
    ("RL9007", "Synthetic Undated Agency", "Active", None),
]


def make_register(last_checked: date | None = REGISTER_DATE) -> AgencyRegister:
    reg = AgencyRegister()
    for licence, name, status, valid in SYNTHETIC_AGENCIES:
        agency = Agency(licence, name, status, valid, "https://example.invalid/synthetic-register", last_checked)
        reg.by_licence[licence] = agency
        reg.by_name.setdefault(normalize_name(name), []).append(agency)
    return reg


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    for var in ("KNOWLEDGE_LLM_REPHRASE", "KNOWLEDGE_RETRIEVER", "PROBASHI_DATA_DIR"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def kb():
    """Real rules, patterns, helplines and thresholds with the synthetic register."""
    return dataclasses.replace(load_kb(), register=make_register())


def good_offer(**changes) -> ExtractedOffer:
    """A complete Qatar offer that should be green with the synthetic register."""
    data = dict(
        employer_name="Synthetic Employer Co",
        job_title="Cleaner",
        destination_country="QA",
        monthly_salary={"amount": 1300, "currency": "QAR"},
        agency_name="Synthetic Active Agency Ltd",
        agency_license_no="RL-9001",
        fees_charged_bdt=0,
        contract_duration_months=24,
        visa_type="Work visa",
        raw_text="",
        confidence=0.9,
    )
    data.update(changes)
    return ExtractedOffer(**data)


def with_rule(kb, country: str, record_id: str, **changes):
    """Copy of kb with one rule record changed (e.g. to pretend a ceiling is verified)."""
    doc = dict(kb.rules[country])
    doc["records"] = [dict(r, **changes) if r["id"] == record_id else r for r in doc["records"]]
    return dataclasses.replace(kb, rules={**kb.rules, country: doc})
