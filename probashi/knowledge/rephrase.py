"""Optional LLM pass that makes the Bangla messages sound more natural.

Off unless KNOWLEDGE_LLM_REPHRASE=1. The LLM sees only our own templated messages
and the retrieved knowledge-base passages (never the worker's document), and its
output can only replace `message_bn`. The level, the reason codes, the sources,
the English text, the next steps and the helplines are never passed through it.
Anything that fails a guard is discarded and the template wording is kept.
"""

from __future__ import annotations

import logging
import os
import re

from probashi.llm import LLMError, complete_json
from probashi.schemas import Reason

from .retrieval import Passage

logger = logging.getLogger(__name__)

_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_BENGALI = re.compile(r"[ঀ-৿]")
MAX_GROWTH = 1.6  # a rewrite may be at most this many times longer than the template
MAX_EXTRA_CHARS = 40

SYSTEM = (
    "You rewrite short Bangla warning messages for Bangladeshi migrant workers with low literacy. "
    "Use simple spoken Bangla, short sentences, everyday words. "
    "Keep the meaning exactly. Keep every number, licence number and amount exactly as given. "
    "Do not add facts, advice, laws, names or numbers. Do not soften or strengthen the warning. "
    "The background passages are only there to help you understand the message."
)


def enabled() -> bool:
    return os.environ.get("KNOWLEDGE_LLM_REPHRASE", "").strip().lower() in ("1", "true", "yes", "on")


def _numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d+", text.translate(_TO_ASCII).replace(",", "")))


def acceptable(original: str, rewrite: object) -> bool:
    """Guard: a rewrite must be Bangla, similar in length, with the same numbers."""
    if not isinstance(rewrite, str):
        return False
    rewrite = rewrite.strip()
    if not rewrite or not _BENGALI.search(rewrite):
        return False
    if len(rewrite) > len(original) * MAX_GROWTH + MAX_EXTRA_CHARS:
        return False
    return _numbers(rewrite) == _numbers(original)


def rephrase_reasons(reasons: list[Reason], evidence: list[list[Passage]]) -> list[Reason]:
    """Return reasons with message_bn restyled where the LLM output passes the guards."""
    if not reasons:
        return reasons
    lines = []
    for i, (reason, passages) in enumerate(zip(reasons, evidence)):
        lines.append(f'{i}: "{reason.message_bn}"  (meaning: {reason.message_en})')
        lines += [f"   background: {p.text_en}" for p in passages[:2]]
    prompt = (
        "Rewrite each numbered Bangla message.\n"
        + "\n".join(lines)
        + '\n\nReturn JSON: {"messages": {"0": "<Bangla>", "1": "<Bangla>", ...}}'
    )
    try:
        reply = complete_json(SYSTEM, prompt, max_tokens=1500)
    except LLMError as exc:
        logger.warning("LLM rephrase failed, keeping template wording: %s", exc)
        return reasons
    rewrites = reply.get("messages") if isinstance(reply, dict) else None
    if not isinstance(rewrites, dict):
        return reasons
    out = []
    for i, reason in enumerate(reasons):
        candidate = rewrites.get(str(i))
        if acceptable(reason.message_bn, candidate):
            out.append(reason.model_copy(update={"message_bn": candidate.strip()}))
        else:
            out.append(reason)
    return out
