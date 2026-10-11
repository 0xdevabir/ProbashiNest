"""Provider interface. To add a provider, subclass these and register it
in providers/__init__.py."""
from __future__ import annotations

from abc import ABC, abstractmethod


class STTProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the environment variables this provider needs are set."""

    @abstractmethod
    def transcribe(self, wav_bytes: bytes, timeout: float) -> str:
        """Transcribe 16 kHz mono WAV to Bangla text. Raise ProviderError on failure."""


class TTSProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the environment variables this provider needs are set."""

    @abstractmethod
    def synthesize(self, text: str, timeout: float) -> bytes:
        """Return mp3 bytes of prepared Bangla text. Raise ProviderError on failure."""
