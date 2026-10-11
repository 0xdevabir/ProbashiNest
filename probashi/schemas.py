"""Shared contract for all Probashi Shield modules.

DO NOT EDIT without agreement from the whole team: every module
(extract, knowledge, voice, backend, frontend) depends on these shapes.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Money(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None  # ISO 4217, e.g. "SAR"


class ExtractedOffer(BaseModel):
    employer_name: Optional[str] = None
    job_title: Optional[str] = None
    destination_country: Optional[str] = None  # ISO 3166 alpha-2, e.g. "SA"
    monthly_salary: Money = Field(default_factory=Money)
    agency_name: Optional[str] = None
    agency_license_no: Optional[str] = None
    fees_charged_bdt: Optional[float] = None
    contract_duration_months: Optional[int] = None
    visa_type: Optional[str] = None
    document_language: Optional[str] = None
    raw_text: str = ""
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Level(str, Enum):
    red = "red"
    amber = "amber"
    green = "green"


class Source(BaseModel):
    title: str
    url: Optional[str] = None


class Reason(BaseModel):
    code: str  # e.g. "AGENCY_UNLICENSED"
    message_bn: str
    message_en: str
    source: Optional[Source] = None


class Helpline(BaseModel):
    name: str
    phone: str


class Verdict(BaseModel):
    level: Level
    reasons: list[Reason]
    next_steps_bn: list[str]
    helplines: list[Helpline] = Field(default_factory=list)
    disclaimer_bn: str


class CheckResponse(BaseModel):
    offer: ExtractedOffer
    verdict: Verdict
    transcript_bn: Optional[str] = None
    audio_base64: Optional[str] = None  # mp3 of the spoken answer
