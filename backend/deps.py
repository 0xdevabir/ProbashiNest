"""Dependency injection: the three pipeline modules, real or stubbed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from fastapi import Request

from probashi.schemas import ExtractedOffer, Verdict


@dataclass(frozen=True)
class Modules:
    transcribe_bn: Callable[[bytes, str], str]
    extract_offer: Callable[[Optional[bytes], Optional[str]], ExtractedOffer]
    evaluate: Callable[[ExtractedOffer], Verdict]
    synthesize_bn: Callable[[str], bytes]
    # Optional extras from the knowledge module. None = the API answers without them.
    guidance: Optional[Callable[[ExtractedOffer, Verdict], Any]] = None
    guide: Optional[Callable[[Optional[str]], Any]] = None


def build_modules(stubs: frozenset[str] = frozenset()) -> Modules:
    """Real modules by default; any name in `stubs` is replaced by its stub."""
    if "extract" in stubs:
        from backend.stubs import extract
    else:
        from probashi import extract
    if "knowledge" in stubs:
        from backend.stubs import knowledge
        from backend.stubs import knowledge as guidance
    else:
        from probashi import knowledge
        from probashi.knowledge import guidance
    if "voice" in stubs:
        from backend.stubs import voice
    else:
        from probashi import voice
    return Modules(
        transcribe_bn=voice.transcribe_bn,
        extract_offer=extract.extract_offer,
        evaluate=knowledge.evaluate,
        synthesize_bn=voice.synthesize_bn,
        guidance=guidance.guidance,
        guide=guidance.guide,
    )


def get_modules(request: Request) -> Modules:
    """FastAPI dependency. Tests may replace it via app.dependency_overrides."""
    return request.app.state.modules
