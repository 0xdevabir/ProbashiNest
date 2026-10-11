"""Mask personal data before text goes anywhere near a log.

Over-masking is fine here: this is only for logs, never for the data
returned to the caller.
"""
from __future__ import annotations

import re

_LABELS = (
    r"full\s+name|worker(?:'s)?\s+name|employee\s+name|name\s+of\s+\w+|name"
    r"|passport(?:\s*(?:no|number|#))?\.?|visa\s*(?:no|number|#)\.?"
    r"|নাম|পাসপোর্ট(?:\s*(?:নং|নম্বর))?|ভিসা\s*(?:নং|নম্বর)"
    r"|الاسم(?:\s+\S+)?|اسم\s+\S+|رقم\s+الجواز|رقم\s+جواز\s+السفر|رقم\s+التأشيرة"
)
_LABELLED_RE = re.compile(rf"(?im)^(\s*(?:{_LABELS})\s*[:：-]\s*)(.+)$")
_PASSPORT_RE = re.compile(r"\b([A-Za-z])[A-Za-z]?\d{6,8}\b")
_LONG_NUMBER_RE = re.compile(r"[0-9০-৯٠-٩۰-۹]{8,}")


def mask_pii(text: str) -> str:
    """Hide names on labelled lines, passport numbers and long ID numbers
    (visa numbers, phone numbers)."""
    text = _LABELLED_RE.sub(lambda m: m.group(1) + "***", text)
    text = _PASSPORT_RE.sub(lambda m: m.group(1) + "*******", text)
    return _LONG_NUMBER_RE.sub("********", text)
