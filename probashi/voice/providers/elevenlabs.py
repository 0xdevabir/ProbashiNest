"""ElevenLabs: Scribe v2 speech-to-text and Eleven v3 text-to-speech.

API reference:
  https://elevenlabs.io/docs/api-reference/speech-to-text/convert
  https://elevenlabs.io/docs/api-reference/text-to-speech/convert
"""
from __future__ import annotations

import json
import os

from .. import _http
from ..errors import ProviderError
from .base import STTProvider, TTSProvider

_BASE_URL = "https://api.elevenlabs.io/v1"


def _key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "")


class ElevenLabsSTT(STTProvider):
    name = "elevenlabs"

    def is_configured(self) -> bool:
        return bool(_key())

    def transcribe(self, wav_bytes: bytes, timeout: float) -> str:
        body, content_type = _http.encode_multipart(
            {
                "model_id": os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2"),
                "language_code": "ben",
                "tag_audio_events": "false",
            },
            {"file": ("audio.wav", wav_bytes, "audio/wav")},
        )
        raw = _http.post(
            f"{_BASE_URL}/speech-to-text",
            headers={"xi-api-key": _key(), "Content-Type": content_type},
            body=body,
            timeout=timeout,
            provider=self.name,
        )
        try:
            return json.loads(raw)["text"]
        except (ValueError, KeyError, TypeError) as e:
            raise ProviderError(
                "elevenlabs returned an unexpected response", provider=self.name
            ) from e


class ElevenLabsTTS(TTSProvider):
    name = "elevenlabs"

    def is_configured(self) -> bool:
        # No default voice: a voice ID must be picked by the team, not invented.
        return bool(_key() and os.getenv("ELEVENLABS_VOICE_ID"))

    def synthesize(self, text: str, timeout: float) -> bytes:
        payload = {
            "text": text,
            "model_id": os.getenv("ELEVENLABS_TTS_MODEL", "eleven_v3"),
            "language_code": "bn",
            # Below 1.0 is slower. UNVERIFIED whether eleven_v3 honours it.
            "voice_settings": {"speed": float(os.getenv("ELEVENLABS_TTS_SPEED", "0.9"))},
        }
        return _http.post(
            f"{_BASE_URL}/text-to-speech/{os.environ['ELEVENLABS_VOICE_ID']}"
            "?output_format=mp3_44100_128",
            headers={"xi-api-key": _key(), "Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
            timeout=timeout,
            provider=self.name,
        )
