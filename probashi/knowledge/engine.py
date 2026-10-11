"""Verdict engine: rules first, retrieval second, optional LLM wording last.

The level is fixed by decide_level() before any retrieval or LLM call happens.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from probashi.schemas import ExtractedOffer, Helpline, Level, Reason, Verdict

from . import rephrase
from .kb import KnowledgeBase, load_kb
from .messages import DISCLAIMER_BN, next_steps, render
from .retrieval import Passage, get_retriever
from .rules import HIGH, INFO, MEDIUM, Flag, missing_key_fields, run_checks, sanitize

logger = logging.getLogger(__name__)

_ORDER = {HIGH: 0, MEDIUM: 1, INFO: 2}
MAX_DESTINATION_HELPLINES = 2


@dataclass
class Explanation:
    """Everything behind a verdict, for debugging, the eval script and tests."""

    flags: list[Flag]
    agency_verified: bool
    evidence: list[list[Passage]]  # retrieved passages, one list per reason


def decide_level(flags: list[Flag], agency_verified: bool, missing_fields: list[str]) -> Level:
    """The whole level logic.

    any high flag                                   -> red
    any medium flag, or any key fact missing        -> amber
    agency verified licensed AND nothing else wrong -> green
    anything else (cannot be reached today)         -> amber
    """
    severities = {f.severity for f in flags}
    if HIGH in severities:
        return Level.red
    if MEDIUM in severities or missing_fields:
        return Level.amber
    if agency_verified:
        return Level.green
    return Level.amber


def _helplines(kb: KnowledgeBase, country: str | None) -> list[Helpline]:
    """Bangladesh numbers first, then the destination's labour wing. Verified records only."""
    usable = [h for h in kb.helplines if h["verified"]]
    home = [h for h in usable if h["country"] == "BD"]
    abroad = [h for h in usable if country and h["country"] == country][:MAX_DESTINATION_HELPLINES]
    return [Helpline(name=h["name_bn"], phone=h["phone"]) for h in home + abroad]


def explain(
    offer: ExtractedOffer, *, today: date | None = None, kb: KnowledgeBase | None = None
) -> tuple[Verdict, Explanation]:
    """Evaluate an offer and also return how the verdict was reached."""
    kb = kb or load_kb()
    today = today or date.today()
    clean = sanitize(offer)

    flags, agency_verified = run_checks(clean, kb, today)
    level = decide_level(flags, agency_verified, missing_key_fields(clean))
    flags.sort(key=lambda f: _ORDER[f.severity])

    retriever = get_retriever(kb)
    country = clean.destination_country
    reasons: list[Reason] = []
    evidence: list[list[Passage]] = []
    for flag in flags:
        message_bn, message_en = render(flag)
        hits = retriever.search(f"{message_en}\n{message_bn}", country=country, code=flag.code)
        passages = [h.passage for h in hits]
        relied_on = retriever.by_id(flag.record_id)
        if relied_on and relied_on not in passages:
            passages.insert(0, relied_on)
        source = flag.source
        if source is None:
            # Only a passage written for this very reason code may be cited.
            source = next((p.source for p in passages if p.code == flag.code and p.source), None)
        reasons.append(Reason(code=flag.code, message_bn=message_bn, message_en=message_en, source=source))
        evidence.append(passages)

    if rephrase.enabled():
        reasons = rephrase.rephrase_reasons(reasons, evidence)

    verdict = Verdict(
        level=level,
        reasons=reasons,
        next_steps_bn=next_steps(flags),
        helplines=_helplines(kb, country),
        disclaimer_bn=DISCLAIMER_BN,
    )
    logger.info("verdict level=%s codes=%s", level.value, [f.code for f in flags])
    return verdict, Explanation(flags, agency_verified, evidence)


def unavailable_verdict() -> Verdict:
    """Used when the knowledge base cannot be loaded: never green, never a crash."""
    flag = Flag("KNOWLEDGE_UNAVAILABLE", MEDIUM)
    message_bn, message_en = render(flag)
    return Verdict(
        level=Level.amber,
        reasons=[Reason(code=flag.code, message_bn=message_bn, message_en=message_en)],
        next_steps_bn=next_steps([flag]),
        helplines=[],
        disclaimer_bn=DISCLAIMER_BN,
    )
