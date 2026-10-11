"""Loads the human-editable knowledge base in data/ and validates its shape.

A malformed file raises KnowledgeBaseError: the engine then answers amber
("could not check") instead of guessing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from probashi.schemas import Source

from .agencies import AgencyRegister, load_register

RULE_TOPICS = {
    "minimum_wage",
    "recruitment_fees",
    "passport_retention",
    "contract",
    "complaint_channel",
    "bd_migration_cost_ceiling",
}
CONFIG_NUMBERS = (
    "register_max_age_days",
    "low_confidence_below",
    "fee_gross_multiple",
    "salary_unrealistic_multiple",
    "agency_name_match_ratio",
)
CONFIG_LISTS = (
    "low_skilled_job_keywords",
    "domestic_job_keywords",
    "non_work_visa_keywords",
    "free_visa_keywords",
    "domestic_visa_keywords",
    "passport_kept_keywords",
    "salary_deduction_keywords",
    "vague_job_keywords",
)


class KnowledgeBaseError(RuntimeError):
    """The knowledge base is missing or malformed."""


def data_dir() -> Path:
    override = os.environ.get("PROBASHI_DATA_DIR")
    return Path(override) if override else Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class KnowledgeBase:
    rules: dict[str, dict[str, Any]]  # country code -> parsed rules file
    patterns: list[dict[str, Any]]
    helplines: list[dict[str, Any]]
    config: dict[str, Any]
    register: AgencyRegister
    checklist: tuple[dict[str, Any], ...] = ()  # pre-departure steps, in order

    def rule(self, country: str | None, topic: str) -> dict[str, Any] | None:
        """First record on a topic for a country, or None."""
        for rec in self.rules.get(country or "", {}).get("records", []):
            if rec["topic"] == topic:
                return rec
        return None

    def country_name_bn(self, country: str | None) -> str | None:
        return self.rules.get(country or "", {}).get("country_name_bn")


def source_of(record: dict[str, Any] | None) -> Source | None:
    """Source of a record. An unverified record says so in the title."""
    src = (record or {}).get("source")
    if not src:
        return None
    title = src["title"]
    if not record.get("verified"):
        title += " [not yet verified]"
    return Source(title=title, url=src.get("url"))


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        raise KnowledgeBaseError(f"cannot read {path.name}: {exc}") from exc


def _check_record(rec: Any, where: str, *, need: tuple[str, ...]) -> None:
    if not isinstance(rec, dict):
        raise KnowledgeBaseError(f"{where}: record is not a mapping")
    rid = rec.get("id", "?")
    for key in ("id", *need, "verified", "last_checked"):
        if key not in rec:
            raise KnowledgeBaseError(f"{where}: record {rid} has no '{key}'")
    if not isinstance(rec["verified"], bool):
        raise KnowledgeBaseError(f"{where}: record {rid}: verified must be true or false")
    if not isinstance(rec["last_checked"], date):
        raise KnowledgeBaseError(f"{where}: record {rid}: last_checked must be a date (YYYY-MM-DD)")
    src = rec.get("source")
    if src is not None and not (isinstance(src, dict) and src.get("title")):
        raise KnowledgeBaseError(f"{where}: record {rid}: source needs a title")
    if src is None and rec["verified"]:
        raise KnowledgeBaseError(f"{where}: record {rid} is verified but has no source")
    if rec["verified"] and not (src.get("url") or "").startswith("http"):
        raise KnowledgeBaseError(f"{where}: record {rid} is verified but has no source URL")


def _load_rules(folder: Path) -> dict[str, dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.yaml")):
        doc = _read_yaml(path)
        if not isinstance(doc, dict) or not isinstance(doc.get("records"), list):
            raise KnowledgeBaseError(f"{path.name}: expected 'country' and a 'records' list")
        for key in ("country", "country_name_bn", "currency"):
            if not doc.get(key):
                raise KnowledgeBaseError(f"{path.name}: missing '{key}'")
        for rec in doc["records"]:
            _check_record(rec, path.name, need=("topic", "text_en", "text_bn", "source"))
            if rec["topic"] not in RULE_TOPICS:
                raise KnowledgeBaseError(f"{path.name}: record {rec['id']}: unknown topic {rec['topic']!r}")
            for num in ("amount", "amount_bdt"):
                val = rec.get(num)
                if val is not None and (isinstance(val, bool) or not isinstance(val, (int, float)) or val <= 0):
                    raise KnowledgeBaseError(f"{path.name}: record {rec['id']}: {num} must be a positive number")
        rules[str(doc["country"]).upper()] = doc
    if not rules:
        raise KnowledgeBaseError(f"no rule files found in {folder}")
    return rules


def _load_config(path: Path) -> dict[str, Any]:
    cfg = _read_yaml(path)
    if not isinstance(cfg, dict):
        raise KnowledgeBaseError(f"{path.name}: expected a mapping")
    for key in CONFIG_NUMBERS:
        val = cfg.get(key)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or val <= 0:
            raise KnowledgeBaseError(f"{path.name}: '{key}' must be a positive number")
    for key in CONFIG_LISTS:
        val = cfg.get(key)
        if not isinstance(val, list) or not all(isinstance(k, str) and k.strip() for k in val):
            raise KnowledgeBaseError(f"{path.name}: '{key}' must be a list of words")
    return cfg


@lru_cache(maxsize=4)
def _load(folder: Path) -> KnowledgeBase:
    patterns = (_read_yaml(folder / "fraud_patterns.yaml") or {}).get("patterns")
    helplines = (_read_yaml(folder / "helplines.yaml") or {}).get("helplines")
    if not isinstance(patterns, list) or not isinstance(helplines, list):
        raise KnowledgeBaseError("fraud_patterns.yaml / helplines.yaml: expected a list of records")
    for rec in patterns:
        _check_record(rec, "fraud_patterns.yaml", need=("code", "text_en", "text_bn", "source"))
        if not isinstance(rec.get("keywords", []), list):
            raise KnowledgeBaseError(f"fraud_patterns.yaml: record {rec['id']}: keywords must be a list")
    for rec in helplines:
        _check_record(rec, "helplines.yaml", need=("country", "name_bn", "phone", "source"))
        if not isinstance(rec["phone"], str):
            raise KnowledgeBaseError(f"helplines.yaml: record {rec['id']}: phone must be quoted text")
    checklist = (_read_yaml(folder / "checklist.yaml") or {}).get("steps")
    if not isinstance(checklist, list):
        raise KnowledgeBaseError("checklist.yaml: expected a list of steps")
    for rec in checklist:
        _check_record(rec, "checklist.yaml", need=("text_en", "text_bn", "source"))
    try:
        register = load_register(folder / "agencies.csv")
    except (OSError, ValueError) as exc:
        raise KnowledgeBaseError(f"agencies.csv: {exc}") from exc
    return KnowledgeBase(
        rules=_load_rules(folder / "rules"),
        patterns=patterns,
        helplines=helplines,
        config=_load_config(folder / "engine_config.yaml"),
        register=register,
        checklist=tuple(checklist),
    )


def load_kb(folder: Path | None = None) -> KnowledgeBase:
    """Load (and cache) the knowledge base from a data folder."""
    return _load(Path(folder) if folder else data_dir())
