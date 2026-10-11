"""Structured (JSON) logging with passport and visa numbers masked.

The API never logs document text or transcripts on purpose. Masking is a
second line of defence for anything that slips in, e.g. through an exception
message raised by another module.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

MASK = "***MASKED***"

_DIGIT = "0-9০-৯"  # ASCII and Bangla digits
_PATTERNS = [
    # A number that follows the word passport/visa, e.g. "Visa No: 6012-345678"
    re.compile(
        rf"((?:passport|visa|পাসপোর্ট|ভিসা)\s*(?:no|number|num|নম্বর|নং)?\.?\s*[:#\-]?\s*)"
        rf"(?=[A-Za-z\-]*[{_DIGIT}])[A-Za-z{_DIGIT}\-]{{5,}}",
        re.IGNORECASE,
    ),
    # Passport shape: 1-2 letters then 7-8 digits, e.g. "A01234567", "BX0123456"
    re.compile(rf"()(?<![A-Za-z0-9])[A-Za-z]{{1,2}}[{_DIGIT}]{{7,8}}(?![A-Za-z0-9])"),
    # Any long run of digits (visa, NID, phone numbers)
    re.compile(rf"()[{_DIGIT}]{{8,}}"),
]

_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
    "color_message",  # uvicorn's ANSI-coloured duplicate of the message
}


def mask_sensitive(text: str) -> str:
    for pattern in _PATTERNS:
        text = pattern.sub(lambda m: m.group(1) + MASK, text)
    return text


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_sensitive(value)
    if isinstance(value, dict):
        return {k: _mask_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_mask_value(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return mask_sensitive(str(value))


class JsonFormatter(logging.Formatter):
    """One JSON object per line; every string value is masked."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": mask_sensitive(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = _mask_value(value)
        if record.exc_info:
            entry["exc"] = mask_sensitive(self.formatException(record.exc_info))
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Route uvicorn's own loggers through the same masked formatter.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
