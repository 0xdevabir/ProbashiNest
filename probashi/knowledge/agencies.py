"""Lookup in the copy of the BMET recruiting-agent licence register (data/agencies.csv)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
REQUIRED_COLUMNS = {"licence_no", "name", "status", "valid_until", "source_url", "last_checked"}


@dataclass(frozen=True)
class Agency:
    licence_no: str
    name: str
    status: str
    valid_until: date | None
    source_url: str
    last_checked: date | None


@dataclass
class AgencyRegister:
    by_licence: dict[str, Agency] = field(default_factory=dict)
    by_name: dict[str, list[Agency]] = field(default_factory=dict)

    @property
    def last_checked(self) -> date | None:
        """Oldest check date in the file: the register is only as fresh as its stalest row."""
        dates = [a.last_checked for a in self.by_licence.values()]
        return None if not dates or None in dates else min(dates)

    @property
    def source_url(self) -> str | None:
        return next((a.source_url for a in self.by_licence.values() if a.source_url), None)

    def get(self, licence_no: str | None) -> Agency | None:
        return self.by_licence.get(licence_no or "")

    def find_by_name(self, name: str | None) -> list[Agency]:
        """Agencies whose registered name is the same after normalising."""
        return self.by_name.get(normalize_name(name), []) if name else []


def normalize_licence(raw: str | None) -> str | None:
    """'RL-1428', 'rl 1428', 'আরএল ১৪২৮', '1428' -> 'RL1428'. None if there is no number."""
    if not raw:
        return None
    groups = re.findall(r"\d+", raw.translate(_BN_DIGITS))
    if len(groups) != 1 or len(groups[0]) > 5:
        return None  # no number, or several: not readable as one licence number
    return "RL" + groups[0].zfill(4)


def normalize_name(name: str | None) -> str:
    text = (name or "").lower().replace("&", " and ")
    text = re.sub(r"\bm\s*/\s*s\b\.?", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\blimited\b", "ltd", text)
    text = re.sub(r"\bpvt\b|\bprivate\b|\bthe\b", " ", text)
    return " ".join(text.split())


def names_match(a: str | None, b: str | None, min_ratio: float) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    return na == nb or SequenceMatcher(None, na, nb).ratio() >= min_ratio


def _parse_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def load_register(path: Path) -> AgencyRegister:
    """Read agencies.csv. Raises ValueError if the columns are wrong."""
    reg = AgencyRegister()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        for row in reader:
            licence = normalize_licence(row["licence_no"])
            if not licence:
                raise ValueError(f"bad licence number {row['licence_no']!r}")
            agency = Agency(
                licence_no=licence,
                name=row["name"].strip(),
                status=row["status"].strip(),
                valid_until=_parse_date(row["valid_until"]),
                source_url=row["source_url"].strip(),
                last_checked=_parse_date(row["last_checked"]),
            )
            reg.by_licence[licence] = agency
            reg.by_name.setdefault(normalize_name(agency.name), []).append(agency)
    return reg
