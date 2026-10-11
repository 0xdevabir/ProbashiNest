"""The check pipeline: audio -> text -> offer -> verdict -> spoken answer.

Everything stays in memory. Nothing here writes to disk, and document text,
transcripts and file contents are never logged.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Callable, Optional, TypeVar

from backend import errors
from backend.deps import Modules
from probashi.schemas import CheckResponse, Level, Verdict

log = logging.getLogger("probashi.backend.pipeline")

T = TypeVar("T")

_LEVEL_INTRO_BN = {
    Level.red: "লাল সংকেত। এই প্রস্তাবে বড় ঝুঁকি আছে।",
    Level.amber: "হলুদ সংকেত। এই প্রস্তাব এখনো নিশ্চিত নয়।",
    Level.green: "সবুজ সংকেত। বড় কোনো সমস্যা পাওয়া যায়নি। তবুও সাবধান থাকুন।",
}


def build_spoken_summary(verdict: Verdict) -> str:
    """Short Bangla answer: level, first 2 reasons, first next step."""
    parts = [_LEVEL_INTRO_BN[verdict.level]]
    parts += [r.message_bn.strip() for r in verdict.reasons[:2] if r.message_bn.strip()]
    if verdict.next_steps_bn and verdict.next_steps_bn[0].strip():
        parts.append("এখন যা করবেন। " + verdict.next_steps_bn[0].strip())
    return " ".join(parts)


def _run_stage(stage: str, fn: Callable[..., T], *args) -> T:
    try:
        return fn(*args)
    except NotImplementedError:
        log.error("module_not_ready", extra={"stage": stage})
        raise errors.module_not_ready(stage) from None
    except Exception:
        log.exception("stage_failed", extra={"stage": stage})
        raise errors.stage_failed(stage) from None


def _transcribe(modules: Modules, audio: bytes, mime: str, has_other_input: bool) -> Optional[str]:
    try:
        transcript = (modules.transcribe_bn(audio, mime) or "").strip()
    except Exception:
        log.exception("stage_failed", extra={"stage": "transcribe"})
        if has_other_input:
            return None  # carry on with the image/text we do have
        raise errors.voice_unavailable() from None
    if not transcript and not has_other_input:
        raise errors.speech_not_understood()
    return transcript or None


def _synthesize(modules: Modules, verdict: Verdict) -> Optional[str]:
    """Voice output is optional: any failure gives None, never an error."""
    try:
        mp3 = modules.synthesize_bn(build_spoken_summary(verdict))
    except Exception:
        log.exception("stage_failed", extra={"stage": "synthesize", "fallback": "no_audio"})
        return None
    return base64.b64encode(mp3).decode("ascii") if mp3 else None


def run_check(
    modules: Modules,
    *,
    image: Optional[bytes] = None,
    audio: Optional[bytes] = None,
    audio_mime: str = "",
    text: Optional[str] = None,
    save: bool = False,
) -> CheckResponse:
    started = time.monotonic()
    text = (text or "").strip() or None

    transcript = None
    if audio:
        transcript = _transcribe(modules, audio, audio_mime, bool(image or text))
    combined_text = "\n".join(t for t in (text, transcript) if t) or None

    offer = _run_stage("extract", modules.extract_offer, image, combined_text)
    verdict = _run_stage("knowledge", modules.evaluate, offer)
    audio_base64 = _synthesize(modules, verdict)

    # save=true is plumbing only for now: nothing is stored anywhere.
    log.info(
        "check_completed",
        extra={
            "has_image": bool(image),
            "has_audio": bool(audio),
            "has_text": bool(text),
            "verdict_level": verdict.level.value,
            "reason_codes": [r.code for r in verdict.reasons],
            "missing_fields": offer.missing_fields,
            "confidence": offer.confidence,
            "audio_out": audio_base64 is not None,
            "save_requested": save,
            "saved": False,
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return CheckResponse(
        offer=offer, verdict=verdict, transcript_bn=transcript, audio_base64=audio_base64
    )
