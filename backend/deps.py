"""Dependency injection: the three pipeline modules, real or stubbed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Request

from probashi.schemas import ExtractedOffer, Verdict


@dataclass(frozen=True)
class Modules:
    transcribe_bn: Callable[[bytes, str], str]
    extract_offer: Callable[[Optional[bytes], Optional[str]], ExtractedOffer]
    evaluate: Callable[[ExtractedOffer], Verdict]
    synthesize_bn: Callable[[str], bytes]


def build_modules(stubs: frozenset[str] = frozenset()) -> Modules:
    """Real modules by default; any name in `stubs` is replaced by its stub."""
    if "extract" in stubs:
        from backend.stubs import extract
    else:
        from probashi import extract
    if "knowledge" in stubs:
        from backend.stubs import knowledge
    else:
        from probashi import knowledge
    if "voice" in stubs:
        from backend.stubs import voice
    else:
        from probashi import voice
    return Modules(
        transcribe_bn=voice.transcribe_bn,
        extract_offer=extract.extract_offer,
        evaluate=knowledge.evaluate,
        synthesize_bn=voice.synthesize_bn,
    )


def get_modules(request: Request) -> Modules:
    """FastAPI dependency. Tests may replace it via app.dependency_overrides."""
    return request.app.state.modules
