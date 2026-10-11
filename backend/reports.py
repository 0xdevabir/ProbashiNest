"""Scam reports that a user chose to send, for a human to review later.

A report is a user's claim, not a finding. It holds the verdict level, the reason
codes, the country and the agency as written on the paper. It never holds the
document, the transcript, the user's name, phone or network address.
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

from backend.logging_utils import mask_sensitive
from backend.models import ReportIn

_lock = threading.Lock()


def build_record(report: ReportIn, today: date | None = None) -> dict:
    return {
        "date": (today or date.today()).isoformat(),  # day only: a timestamp could single out a user
        "level": report.level.value,
        "reason_codes": report.reason_codes,
        "destination_country": (report.destination_country or "").upper() or None,
        "agency_name": mask_sensitive(report.agency_name.strip()) if report.agency_name else None,
        "agency_license_no": mask_sensitive(report.agency_license_no.strip()) if report.agency_license_no else None,
    }


def append_report(path: str, report: ReportIn) -> None:
    line = json.dumps(build_record(report), ensure_ascii=False)
    with _lock, Path(path).open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
