"""Provider registry. The first entry of each dict is the default."""
from __future__ import annotations

from .azure import AzureSTT, AzureTTS
from .base import STTProvider, TTSProvider
from .elevenlabs import ElevenLabsSTT, ElevenLabsTTS

STT_PROVIDERS: dict[str, type[STTProvider]] = {
    "elevenlabs": ElevenLabsSTT,
    "azure": AzureSTT,
}
TTS_PROVIDERS: dict[str, type[TTSProvider]] = {
    "azure": AzureTTS,
    "elevenlabs": ElevenLabsTTS,
}

__all__ = ["STTProvider", "TTSProvider", "STT_PROVIDERS", "TTS_PROVIDERS"]
