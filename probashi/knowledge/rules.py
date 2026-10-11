"""Deterministic checks. Each check returns Flags; no LLM is involved.

Severity decides the traffic light (see engine.decide_level):
  high   -> red
  medium -> amber (also used for every "could not check" outcome)
  info   -> no effect on the level
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from probashi.schemas import ExtractedOffer, Money, Source

from .agencies import names_match, normalize_licence
from .kb import KnowledgeBase, source_of

HIGH, MEDIUM, INFO = "high", "medium", "info"

BAD_STATUSES = {"cancelled", "canceled", "suspended", "expired"}
# Facts the engine needs. Any of them missing keeps the verdict away from green.
KEY_FIELDS = (
    "employer_name",
    "job_title",
    "destination_country",
    "monthly_salary",
    "agency_name",
    "agency_license_no",
    "fees_charged_bdt",
    "contract_duration_months",
    "visa_type",
)


@dataclass
class Flag:
    code: str
    severity: str
    params: dict[str, Any] = field(default_factory=dict)
    source: Source | None = None
    template: str | None = None  # message variant; defaults to the code
    record_id: str | None = None  # knowledge-base record the check relied on


def find_keyword(text: str | None, keywords: list[str]) -> str | None:
    """First keyword found in text. A keyword must start at the start of a word
    (so "porter" is not found in "supporter", nor "হজ ভিসা" in "সহজ ভিসা")."""
    low = (text or "").lower()
    if not low:
        return None
    for kw in keywords:
        k = kw.lower().strip()
        boundary = r"\b" if k.isascii() else r"(?<![\u0980-\u09FF])"
        if re.search(boundary + re.escape(k), low):
            return kw
    return None


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


def sanitize(offer: ExtractedOffer) -> ExtractedOffer:
    """Copy of the offer where blank values and fields the extractor reported as
    missing are None, so every check sees one meaning of "unknown"."""
    data = offer.model_dump()
    for name in ("employer_name", "job_title", "destination_country", "agency_name", "agency_license_no", "visa_type"):
        data[name] = _clean(data[name])
    if data["destination_country"]:
        data["destination_country"] = data["destination_country"].upper()
    salary = data["monthly_salary"]
    if salary["amount"] is not None and salary["amount"] <= 0:
        salary["amount"] = None
    salary["currency"] = (_clean(salary["currency"]) or "").upper() or None
    if data["fees_charged_bdt"] is not None and data["fees_charged_bdt"] < 0:
        data["fees_charged_bdt"] = None
    if data["contract_duration_months"] is not None and data["contract_duration_months"] <= 0:
        data["contract_duration_months"] = None
    for name in offer.missing_fields:
        if name == "monthly_salary":
            data["monthly_salary"] = Money().model_dump()
        elif name in KEY_FIELDS:
            data[name] = None
    return ExtractedOffer(**data)


def missing_key_fields(offer: ExtractedOffer) -> list[str]:
    """Names of key fields with no value (expects a sanitized offer)."""
    missing = [n for n in KEY_FIELDS if n != "monthly_salary" and getattr(offer, n) is None]
    if offer.monthly_salary.amount is None:
        missing.append("monthly_salary")
    return missing


# --------------------------------------------------------------------------- agency


def _register_source(kb: KnowledgeBase) -> Source:
    checked = kb.register.last_checked
    suffix = f" (copy of {checked.isoformat()})" if checked else ""
    return Source(
        title="BMET Recruiting Agents' Information System (RAIMS) – recruiting licence list" + suffix,
        url=kb.register.source_url,
    )


def check_agency(offer: ExtractedOffer, kb: KnowledgeBase, today: date) -> tuple[list[Flag], bool]:
    """Returns (flags, agency_verified). agency_verified is True only when the
    licence is in a fresh register copy, Active, in date, and under the same name."""
    src = _register_source(kb)
    reg = kb.register
    ratio = kb.config["agency_name_match_ratio"]
    flags: list[Flag] = []

    checked = reg.last_checked
    fresh = checked is not None and 0 <= (today - checked).days <= kb.config["register_max_age_days"]
    if not fresh:
        flags.append(Flag("REGISTER_STALE", MEDIUM, source=src))

    name = offer.agency_name
    licence = normalize_licence(offer.agency_license_no)

    if not licence:
        flags.append(Flag("MISSING_LICENCE_NO", MEDIUM))
        if name:
            same_name = reg.find_by_name(name)
            if not same_name:
                flags.append(Flag("AGENCY_NAME_NOT_FOUND", MEDIUM, {"name": name}, src))
            elif all(a.status.lower() in BAD_STATUSES for a in same_name):
                flags.append(
                    Flag("AGENCY_UNLICENSED", HIGH, {"name": name, "status": same_name[0].status}, src,
                         template="AGENCY_UNLICENSED_BY_NAME")
                )
        return flags, False

    agency = reg.get(licence)
    if agency is None:
        if any(a.status.lower() == "active" for a in reg.find_by_name(name)):
            # A real agency's name with a number that is not theirs: could be a typo
            # or an impostor. Cannot tell, so warn rather than accuse.
            flags.append(Flag("AGENCY_LICENCE_MISMATCH", MEDIUM, {"licence": licence, "name": name}, src))
        else:
            flags.append(Flag("AGENCY_NOT_FOUND", HIGH, {"licence": licence}, src))
        return flags, False

    params = {"licence": licence, "name": agency.name, "status": agency.status}
    status = agency.status.lower()
    licence_ok = False
    if status in BAD_STATUSES:
        flags.append(Flag("AGENCY_UNLICENSED", HIGH, params, src))
    elif status != "active" or agency.valid_until is None:
        flags.append(Flag("AGENCY_STATUS_UNCLEAR", MEDIUM, params, src))
    elif agency.valid_until < today:
        flags.append(Flag("AGENCY_LICENCE_EXPIRED", MEDIUM, {**params, "date": agency.valid_until}, src))
    else:
        licence_ok = True

    name_ok = False
    if name and not names_match(name, agency.name, ratio):
        flags.append(Flag("AGENCY_NAME_MISMATCH", MEDIUM, {"licence": licence, "registered": agency.name}, src))
    elif name:
        name_ok = True
    # A missing agency name is reported by check_key_facts.

    verified = fresh and licence_ok and name_ok
    if verified:
        flags.append(Flag("AGENCY_LICENSED", INFO, params, src))
    return flags, verified


# --------------------------------------------------------------------------- fee


def check_fee(offer: ExtractedOffer, kb: KnowledgeBase) -> list[Flag]:
    fee = offer.fees_charged_bdt
    if fee is None or fee == 0 or offer.destination_country not in kb.rules:
        return []  # missing fee / unsupported country are reported by check_key_facts
    ceiling = kb.rule(offer.destination_country, "bd_migration_cost_ceiling")
    if ceiling is None or not ceiling.get("amount_bdt"):
        return [Flag("FEE_NOT_CHECKABLE", MEDIUM, {"fee": fee})]
    limit = ceiling["amount_bdt"]
    params = {"fee": fee, "limit": limit}
    src, rid, verified = source_of(ceiling), ceiling["id"], ceiling["verified"]
    if fee > limit:
        if verified or fee >= kb.config["fee_gross_multiple"] * limit:
            return [Flag("FEE_ABOVE_LIMIT", HIGH, params, src, record_id=rid)]
        return [Flag("FEE_ABOVE_LIMIT", MEDIUM, params, src, template="FEE_ABOVE_UNVERIFIED_LIMIT", record_id=rid)]
    if not verified:
        # Within a ceiling we could not verify: not a pass, only "not confirmed".
        return [Flag("FEE_LIMIT_UNVERIFIED", MEDIUM, params, src, record_id=rid)]
    return []


# --------------------------------------------------------------------------- salary


def check_salary(offer: ExtractedOffer, kb: KnowledgeBase) -> list[Flag]:
    amount, currency = offer.monthly_salary.amount, offer.monthly_salary.currency
    wage = kb.rule(offer.destination_country, "minimum_wage")
    if amount is None or wage is None or not wage.get("amount"):
        return []  # no legal minimum for this destination: nothing to compare with
    cfg = kb.config
    if wage.get("excludes_domestic") and find_keyword(offer.job_title, cfg["domestic_job_keywords"]):
        return []
    src, rid = source_of(wage), wage["id"]
    if currency != wage.get("currency", kb.rules[offer.destination_country]["currency"]):
        # No exchange rates are stored (they would be invented numbers), so no conversion.
        return [Flag("SALARY_NOT_COMPARABLE", MEDIUM, {"salary": amount, "currency": currency}, src, record_id=rid)]
    params = {"salary": amount, "minimum": wage["amount"], "currency": currency}
    if amount < wage["amount"]:
        return [Flag("SALARY_BELOW_MINIMUM", HIGH if wage["verified"] else MEDIUM, params, src, record_id=rid)]
    if amount > cfg["salary_unrealistic_multiple"] * wage["amount"] and find_keyword(
        offer.job_title, cfg["low_skilled_job_keywords"]
    ):
        return [Flag("SALARY_UNREALISTIC", MEDIUM, {**params, "job": offer.job_title})]
    return []


# --------------------------------------------------------------------------- visa


def check_visa(offer: ExtractedOffer, kb: KnowledgeBase) -> list[Flag]:
    cfg = kb.config
    visa = offer.visa_type
    if find_keyword(visa, cfg["free_visa_keywords"]) or find_keyword(offer.raw_text, cfg["free_visa_keywords"]):
        return [Flag("FREE_VISA", HIGH, {"visa": visa})]
    if not visa:
        return []
    if find_keyword(visa, cfg["non_work_visa_keywords"]):
        return [Flag("VISA_JOB_MISMATCH", HIGH, {"visa": visa, "job": offer.job_title})]
    if (
        offer.job_title
        and find_keyword(visa, cfg["domestic_visa_keywords"])
        and not find_keyword(offer.job_title, cfg["domestic_job_keywords"])
    ):
        return [Flag("VISA_JOB_MISMATCH", MEDIUM, {"visa": visa, "job": offer.job_title},
                     template="VISA_JOB_MISMATCH_DOMESTIC")]
    return []


# --------------------------------------------------------------------------- key facts, text


def check_key_facts(offer: ExtractedOffer, kb: KnowledgeBase) -> list[Flag]:
    flags: list[Flag] = []
    missing = missing_key_fields(offer)
    if "employer_name" in missing:
        flags.append(Flag("MISSING_EMPLOYER", MEDIUM))
    # The licence number has its own flag from check_agency.
    others = [m for m in missing if m not in ("employer_name", "agency_license_no")]
    if others:
        flags.append(Flag("MISSING_KEY_FACTS", MEDIUM, {"fields": others}))
    country = offer.destination_country
    if country and country not in kb.rules:
        flags.append(Flag("UNSUPPORTED_DESTINATION", MEDIUM, {"country": country}))
    if offer.confidence < kb.config["low_confidence_below"]:
        flags.append(Flag("LOW_CONFIDENCE", MEDIUM))
    return flags


def check_text_patterns(offer: ExtractedOffer, kb: KnowledgeBase) -> list[Flag]:
    """Fraud patterns that are recognised by words in the document or transcript."""
    flags: list[Flag] = []
    for pattern in kb.patterns:
        if pattern.get("code") and pattern.get("keywords") and find_keyword(offer.raw_text, pattern["keywords"]):
            flags.append(Flag(pattern["code"], MEDIUM, source=source_of(pattern), record_id=pattern["id"]))
    return flags


# Clauses recognised by words in the document: (code, keyword list, rule topic cited).
_CLAUSES = (
    ("PASSPORT_KEPT", "passport_kept_keywords", "passport_retention"),
    ("FEE_DEDUCTED_FROM_SALARY", "salary_deduction_keywords", "recruitment_fees"),
    ("JOB_VAGUE", "vague_job_keywords", None),
)


def check_contract_clauses(offer: ExtractedOffer, kb: KnowledgeBase) -> list[Flag]:
    """Risky clauses found by keyword. Always a warning, never high: a keyword
    cannot tell "the employer will keep" from "the employer will not keep"."""
    flags: list[Flag] = []
    text = f"{offer.raw_text}\n{offer.job_title or ''}"
    for code, keywords, topic in _CLAUSES:
        if not find_keyword(text, kb.config[keywords]):
            continue
        rule = kb.rule(offer.destination_country, topic) if topic else None
        flags.append(Flag(code, MEDIUM, source=source_of(rule), record_id=rule["id"] if rule else None))
    return flags


def run_checks(offer: ExtractedOffer, kb: KnowledgeBase, today: date) -> tuple[list[Flag], bool]:
    """All checks on a sanitized offer. Returns (flags, agency_verified)."""
    flags, agency_verified = check_agency(offer, kb, today)
    flags += check_fee(offer, kb)
    flags += check_salary(offer, kb)
    flags += check_visa(offer, kb)
    flags += check_key_facts(offer, kb)
    flags += check_text_patterns(offer, kb)
    flags += check_contract_clauses(offer, kb)
    return flags, agency_verified
