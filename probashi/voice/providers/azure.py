"""Azure AI Speech: neural text-to-speech (bn-BD voices) and fast transcription.

API reference:
  https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech
  https://learn.microsoft.com/en-us/azure/ai-services/speech-service/fast-transcription-create
"""
from __future__ import annotations

import json
import os
from xml.sax.saxutils import escape

from .. import _http
from ..errors import ProviderError
from .base import STTProvider, TTSProvider

_STT_API_VERSION = "2025-10-15"


def _key() -> str:
    return os.getenv("AZURE_SPEECH_KEY", "")


def _region() -> str:
    return os.getenv("AZURE_SPEECH_REGION", "")


def build_ssml(text: str) -> str:
    voice = os.getenv("AZURE_TTS_VOICE", "bn-BD-NabanitaNeural")
    rate = os.getenv("AZURE_TTS_RATE", "-15%")
    return (
        "<speak version='1.0' xml:lang='bn-BD'>"
        f"<voice name='{escape(voice)}'><prosody rate='{escape(rate)}'>"
        f"{escape(text)}</prosody></voice></speak>"
    )


class AzureTTS(TTSProvider):
    name = "azure"

    def is_configured(self) -> bool:
        return bool(_key() and _region())

    def synthesize(self, text: str, timeout: float) -> bytes:
        return _http.post(
            f"https://{_region()}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers={
                "Ocp-Apim-Subscription-Key": _key(),
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "probashi-shield",
            },
            body=build_ssml(text).encode("utf-8"),
            timeout=timeout,
            provider=self.name,
        )


class AzureSTT(STTProvider):
    """Azure has no bn-BD speech-to-text locale; bn-IN is the only Bangla one."""

    name = "azure"

    def is_configured(self) -> bool:
        return bool(_key() and (_region() or os.getenv("AZURE_SPEECH_ENDPOINT")))

    def transcribe(self, wav_bytes: bytes, timeout: float) -> str:
        # The docs show the resource endpoint (AZURE_SPEECH_ENDPOINT). The
        # regional host below is the fallback when only a region is set.
        base = os.getenv("AZURE_SPEECH_ENDPOINT", "").rstrip("/") or (
            f"https://{_region()}.api.cognitive.microsoft.com"
        )
        body, content_type = _http.encode_multipart(
            {"definition": json.dumps({"locales": ["bn-IN"], "profanityFilterMode": "None"})},
            {"audio": ("audio.wav", wav_bytes, "audio/wav")},
        )
        raw = _http.post(
            f"{base}/speechtotext/transcriptions:transcribe?api-version={_STT_API_VERSION}",
            headers={"Ocp-Apim-Subscription-Key": _key(), "Content-Type": content_type},
            body=body,
            timeout=timeout,
            provider=self.name,
        )
        try:
            phrases = json.loads(raw)["combinedPhrases"]
            return " ".join(p["text"] for p in phrases)
        except (ValueError, KeyError, TypeError) as e:
            raise ProviderError(
                "azure returned an unexpected response", provider=self.name
            ) from e
