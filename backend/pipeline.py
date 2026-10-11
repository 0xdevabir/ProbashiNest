"""The check pipeline: audio -> text -> offer -> verdict -> spoken answer.

Everything stays in memory. Nothing here writes to disk, and document text,
transcripts and file contents are never logged.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Callable, Optional, Sequence, TypeVar

from backend import errors
from backend.deps import Modules
from backend.models import CheckResult
from backend.stats import STATS
from probashi.knowledge.consistency import add_mismatch, merge_offers
from probashi.knowledge.guidance import Guidance
from probashi.schemas import ExtractedOffer, Level, Verdict

log = logging.getLogger("probashi.backend.pipeline")

T = TypeVar("T")

MAX_DOCUMENTS = 3  # offer letter, visa, contract. Each one costs an extraction call.

_LEVEL_INTRO_BN = {
    Level.red: "লাল সংকেত। এই প্রস্তাবে বড় ঝুঁকি আছে।",
    Level.amber: "হলুদ সংকেত। এই প্রস্তাব এখনো নিশ্চিত নয়।",
    Level.green: "সবুজ সংকেত। বড় কোনো সমস্যা পাওয়া যায়নি। তবুও সাবধান থাকুন।",
}
_LEVEL_MARK = {Level.red: "🔴", Level.amber: "🟡", Level.green: "🟢"}


def build_spoken_summary(verdict: Verdict) -> str:
    """Short Bangla answer: level, first 2 reasons, first next step."""
    parts = [_LEVEL_INTRO_BN[verdict.level]]
    parts += [r.message_bn.strip() for r in verdict.reasons[:2] if r.message_bn.strip()]
    if verdict.next_steps_bn and verdict.next_steps_bn[0].strip():
        parts.append("এখন যা করবেন। " + verdict.next_steps_bn[0].strip())
    return " ".join(parts)


def format_verdict_text(result: CheckResult) -> str:
    """The whole answer as plain Bangla text, for chat apps and sharing."""
    verdict = result.verdict
    lines = [f"{_LEVEL_MARK[verdict.level]} {_LEVEL_INTRO_BN[verdict.level]}"]
    if verdict.reasons:
        lines += ["", "কারণ:", *[f"• {r.message_bn}" for r in verdict.reasons]]
    if verdict.next_steps_bn:
        lines += ["", "এখন যা করবেন:", *[f"{i}. {s}" for i, s in enumerate(verdict.next_steps_bn, 1)]]
    if result.guidance and result.guidance.follow_up:
        lines += ["", "আরও ভালো উত্তর পেতে এগুলো জানান:", *[f"• {q.text_bn}" for q in result.guidance.follow_up]]
    if verdict.helplines:
        lines += ["", "সাহায্যের নম্বর:", *[f"• {h.name}: {h.phone}" for h in verdict.helplines]]
    if verdict.disclaimer_bn:
        lines += ["", verdict.disclaimer_bn]
    return "\n".join(lines)


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


def _guidance(modules: Modules, offer: ExtractedOffer, verdict: Verdict) -> Optional[Guidance]:
    """Guidance is optional: any failure gives None, never an error."""
    if modules.guidance is None:
        return None
    try:
        return modules.guidance(offer, verdict)
    except Exception:
        log.exception("stage_failed", extra={"stage": "guidance", "fallback": "no_guidance"})
        return None


def run_check(
    modules: Modules,
    *,
    image: Optional[bytes] = None,
    more_images: Sequence[bytes] = (),
    audio: Optional[bytes] = None,
    audio_mime: str = "",
    text: Optional[str] = None,
    save: bool = False,
    voice: bool = True,
    channel: str = "web",
) -> CheckResult:
    started = time.monotonic()
    text = (text or "").strip() or None

    transcript = None
    if audio:
        transcript = _transcribe(modules, audio, audio_mime, bool(image or text))
    combined_text = "\n".join(t for t in (text, transcript) if t) or None

    offers = [_run_stage("extract", modules.extract_offer, image, combined_text)]
    offers += [_run_stage("extract", modules.extract_offer, extra, None) for extra in more_images]
    # Several papers for one job: fill gaps from each other, and warn if they disagree.
    offer, differing = merge_offers(offers)
    verdict = add_mismatch(_run_stage("knowledge", modules.evaluate, offer), differing)
    guidance = _guidance(modules, offer, verdict)
    audio_base64 = _synthesize(modules, verdict) if voice else None

    reason_codes = [r.code for r in verdict.reasons]
    STATS.record_check(
        channel=channel, level=verdict.level.value, codes=reason_codes, country=offer.destination_country
    )
    # save=true is plumbing only for now: nothing is stored anywhere.
    log.info(
        "check_completed",
        extra={
            "channel": channel,
            "has_image": bool(image),
            "documents": len(offers),
            "has_audio": bool(audio),
            "has_text": bool(text),
            "verdict_level": verdict.level.value,
            "reason_codes": reason_codes,
            "missing_fields": offer.missing_fields,
            "confidence": offer.confidence,
            "audio_out": audio_base64 is not None,
            "save_requested": save,
            "saved": False,
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return CheckResult(
        offer=offer, verdict=verdict, transcript_bn=transcript, audio_base64=audio_base64, guidance=guidance
    )
