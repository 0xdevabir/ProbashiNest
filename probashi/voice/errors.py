"""Exceptions raised by probashi.voice.

Everything derives from VoiceError, so the backend can wrap voice calls in
one `except VoiceError` and still return the verdict when voice fails.
"""
from __future__ import annotations

from typing import Optional


class VoiceError(RuntimeError):
    """Base class for every voice failure."""


class VoiceConfigError(VoiceError):
    """Missing API key, unknown provider name, or ffmpeg not installed."""


class AudioError(VoiceError):
    """The uploaded audio is unusable (empty, corrupt, unsupported type)."""


class AudioTooLongError(AudioError):
    """The recording is longer than MAX_AUDIO_SECONDS."""


class NoSpeechError(AudioError):
    """The provider returned an empty transcript. Ask the user to repeat."""


class ProviderError(VoiceError):
    """A speech provider call failed (network, timeout, auth, quota)."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        status: Optional[int] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status = status
        self.retryable = retryable
