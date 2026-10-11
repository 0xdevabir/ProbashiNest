"""API models that are not part of the shared contract in probashi/schemas.py."""
from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from probashi.knowledge.guidance import Guidance
from probashi.schemas import CheckResponse, Level

ReasonCode = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{2,39}$")]


class CheckResult(CheckResponse):
    """CheckResponse plus optional guidance. Older clients can ignore the extra field."""

    guidance: Optional[Guidance] = None


class ReportIn(BaseModel):
    """A scam report the user chose to send. No document text, no personal details."""

    model_config = ConfigDict(extra="forbid")

    consent: bool
    level: Level
    reason_codes: list[ReasonCode] = Field(default_factory=list, max_length=20)
    destination_country: Optional[Annotated[str, StringConstraints(pattern=r"^[A-Za-z]{2}$")]] = None
    agency_name: Optional[Annotated[str, StringConstraints(max_length=120)]] = None
    agency_license_no: Optional[Annotated[str, StringConstraints(pattern=r"^[\w \-/]{1,20}$")]] = None
