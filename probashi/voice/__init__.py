"""Owner: Agent 4 (Bangla voice input and output).

Public API:
    transcribe_bn(audio_bytes, mime_type) -> str
    synthesize_bn(text) -> bytes  # mp3

Both raise a subclass of VoiceError on failure, so callers can catch
VoiceError and still return the verdict without voice. See README.md.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Callable, TypeVar

from .audio import MAX_AUDIO_SECONDS, to_wav_16k_mono
from .errors import (
    AudioError,
    AudioTooLongError,
    NoSpeechError,
    ProviderError,
    VoiceConfigError,
    VoiceError,
)
from .providers import STT_PROVIDERS, TTS_PROVIDERS
from .text_prep import prepare_tts_text

__all__ = [
    "transcribe_bn",
    "synthesize_bn",
    "prepare_tts_text",
    "MAX_AUDIO_SECONDS",
    "VoiceError",
    "VoiceConfigError",
    "AudioError",
    "AudioTooLongError",
    "NoSpeechError",
    "ProviderError",
]

log = logging.getLogger(__name__)

P = TypeVar("P")
R = TypeVar("R")


def _timeout(kind: str, default: float) -> float:
    return float(os.getenv(f"VOICE_{kind}_TIMEOUT_SECONDS", default))


def _provider_chain(registry: dict[str, type[P]], env_var: str) -> list[P]:
    """Chosen provider first, then any other configured provider as fallback."""
    default = next(iter(registry))
    chosen = (os.getenv(env_var) or default).strip().lower()
    if chosen not in registry:
        raise VoiceConfigError(
            f"Unknown {env_var}={chosen!r}. Options: {', '.join(registry)}"
        )
    names = [chosen]
    if os.getenv("VOICE_FALLBACK", "true").lower() != "false":
        names += [n for n in registry if n != chosen]
    chain = [p for p in (registry[n]() for n in names) if p.is_configured()]
    if not chain:
        raise VoiceConfigError(
            f"No voice provider is configured for {env_var} "
            f"(tried: {', '.join(names)}). Set the API keys listed in .env.example."
        )
    return chain


def _call_with_retry(chain: list[P], call: Callable[[P], R]) -> R:
    """Try each provider, retrying once on a retryable error."""
    last: ProviderError | None = None
    for provider in chain:
        for attempt in (1, 2):
            started = time.monotonic()
            try:
                result = call(provider)
                log.info(
                    "voice provider=%s ok attempt=%d seconds=%.1f",
                    provider.name, attempt, time.monotonic() - started,
                )
                return result
            except ProviderError as e:
                last = e
                log.warning(
                    "voice provider=%s failed attempt=%d status=%s retryable=%s",
                    provider.name, attempt, e.status, e.retryable,
                )
                if not e.retryable:
                    break
    assert last is not None
    raise last


def transcribe_bn(audio_bytes: bytes, mime_type: str) -> str:
    """Transcribe a Bangla recording (webm, ogg/opus, wav, mp3, m4a) to text.

    Raises AudioTooLongError above 2 minutes, AudioError for unusable audio,
    NoSpeechError when nothing was heard, ProviderError when the speech
    service fails, VoiceConfigError when keys or ffmpeg are missing.
    """
    chain = _provider_chain(STT_PROVIDERS, "VOICE_STT_PROVIDER")
    wav, seconds = to_wav_16k_mono(audio_bytes, mime_type)
    log.info("voice transcribe audio_seconds=%.1f", seconds)
    timeout = _timeout("STT", 30)
    # Transcripts can contain passport numbers, so they are never logged.
    text = _call_with_retry(chain, lambda p: p.transcribe(wav, timeout)).strip()
    if not text:
        raise NoSpeechError("No speech was recognised in the audio")
    return text


def synthesize_bn(text: str) -> bytes:
    """Return mp3 bytes of `text` spoken in Bangla.

    Numbers and currency codes are expanded to Bangla words and the text is
    trimmed to about 45 seconds. Raises ProviderError or VoiceConfigError.
    """
    prepared = prepare_tts_text(text or "")
    if not prepared:
        raise VoiceError("Nothing to speak: text is empty")
    chain = _provider_chain(TTS_PROVIDERS, "VOICE_TTS_PROVIDER")
    timeout = _timeout("TTS", 20)
    mp3 = _call_with_retry(chain, lambda p: p.synthesize(prepared, timeout))
    if not mp3:
        raise ProviderError("Speech provider returned empty audio")
    return mp3
