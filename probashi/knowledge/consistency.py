"""Several papers for one job (offer letter, visa, contract): join them and compare them.

    merged, differing = merge_offers([offer_letter, visa, contract])
    verdict = add_mismatch(evaluate(merged), differing)

A fact missing from one paper is filled from another. A fact that two papers state
differently is a warning: the verdict can no longer be green.
"""

from __future__ import annotations

import re

from probashi.schemas import ExtractedOffer, Level, Reason, Verdict

_COMPARED = (
    "employer_name", "job_title", "destination_country", "monthly_salary", "agency_name",
    "agency_license_no", "fees_charged_bdt", "contract_duration_months", "visa_type",
)


def _value(offer: ExtractedOffer, name: str):
    """Comparable form of a field, or None when the paper does not state it."""
    if name in offer.missing_fields:
        return None
    raw = getattr(offer, name)
    if name == "monthly_salary":
        if raw.amount is None:
            return None
        return (float(raw.amount), (raw.currency or "").upper() or None)
    if isinstance(raw, str):
        # Case, spacing and punctuation differ between papers without meaning anything.
        return re.sub(r"[\W_]+", "", raw).casefold() or None
    return raw


def _differs(name: str, a, b) -> bool:
    if name == "monthly_salary":
        # An unstated currency on one paper is not a contradiction.
        return a[0] != b[0] or (a[1] is not None and b[1] is not None and a[1] != b[1])
    return a != b


def merge_offers(offers: list[ExtractedOffer]) -> tuple[ExtractedOffer, list[str]]:
    """One offer from several papers, plus the fields on which the papers disagree.

    The first paper wins a disagreement in the merged offer (the disagreement is
    reported separately). Confidence is the lowest of the papers.
    """
    if not offers:
        raise ValueError("no offers to merge")
    first, rest = offers[0], offers[1:]
    if not rest:
        return first, []
    data = first.model_dump()
    missing = set(first.missing_fields)
    differing: list[str] = []
    for name in _COMPARED:
        known = _value(first, name)
        for other in rest:
            value = _value(other, name)
            if value is None:
                continue
            if known is None:
                known = value
                data[name] = other.model_dump()[name]
                missing.discard(name)
            elif _differs(name, known, value) and name not in differing:
                differing.append(name)
    data["raw_text"] = "\n".join(o.raw_text for o in offers if o.raw_text)
    data["missing_fields"] = [f for f in first.missing_fields if f in missing]
    data["confidence"] = min(o.confidence for o in offers)
    return ExtractedOffer(**data), differing


def add_mismatch(verdict: Verdict, differing: list[str]) -> Verdict:
    """Add the "papers do not agree" reason. Green becomes amber; red stays red."""
    if not differing:
        return verdict
    from .messages import render
    from .rules import MEDIUM, Flag

    message_bn, message_en = render(Flag("DOCUMENT_MISMATCH", MEDIUM, {"fields": differing}))
    reason = Reason(code="DOCUMENT_MISMATCH", message_bn=message_bn, message_en=message_en)
    level = Level.amber if verdict.level == Level.green else verdict.level
    return verdict.model_copy(update={"level": level, "reasons": [reason, *verdict.reasons]})
