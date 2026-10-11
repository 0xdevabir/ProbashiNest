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


def read_reports(path: str) -> list[dict]:
    """Every stored report, oldest first. A missing file means none yet; a damaged line is skipped."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    records = []
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def review_queue(records: list[dict], limit: int = 200) -> dict:
    """What a reviewer needs: the newest reports, and which agencies are named again and again.

    Several reports about one agency are still claims, not proof. A person must check them.
    """
    groups: dict[tuple[str, str], dict] = {}
    for record in records:
        name = record.get("agency_name") or ""
        licence = record.get("agency_license_no") or ""
        if not (name or licence):
            continue
        # Group by licence number when there is one: names are spelled many ways.
        key = ("licence", licence.upper()) if licence else ("name", name.casefold())
        group = groups.setdefault(
            key, {"agency_name": name or None, "agency_license_no": licence or None, "count": 0, "last_date": ""}
        )
        group["count"] += 1
        group["agency_name"] = group["agency_name"] or name or None
        group["last_date"] = max(group["last_date"], str(record.get("date") or ""))
    agencies = sorted(groups.values(), key=lambda g: (-g["count"], g["last_date"]))
    return {"total": len(records), "agencies": agencies[:limit], "reports": records[::-1][:limit]}
