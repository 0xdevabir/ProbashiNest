"""Live provider tests. Each one is skipped unless its API keys are set.

They call the real services and cost a little money (a few seconds of audio).
"""
import os

import pytest

from probashi.voice import audio
from probashi.voice.providers import azure, elevenlabs

PHRASE = "আমি সৌদি আরবে কাজ করতে যাব।"
has_ffmpeg = bool(os.getenv("FFMPEG_BINARY") or audio.shutil.which("ffmpeg"))


def looks_like_mp3(data: bytes) -> bool:
    return data[:3] == b"ID3" or (len(data) > 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0)


TTS = [azure.AzureTTS(), elevenlabs.ElevenLabsTTS()]
STT = [elevenlabs.ElevenLabsSTT(), azure.AzureSTT()]


@pytest.mark.parametrize("provider", TTS, ids=lambda p: p.name)
def test_tts_returns_mp3(provider):
    if not provider.is_configured():
        pytest.skip(f"{provider.name} TTS keys not set")
    assert looks_like_mp3(provider.synthesize(PHRASE, 30))


@pytest.mark.parametrize("stt", STT, ids=lambda p: p.name)
def test_stt_round_trip_of_synthesized_speech(stt):
    """Synthesize a phrase, transcribe it back, expect some Bangla text."""
    tts = next((p for p in TTS if p.is_configured()), None)
    if not stt.is_configured() or tts is None or not has_ffmpeg:
        pytest.skip(f"needs {stt.name} STT keys, any TTS keys, and ffmpeg")
    wav, _ = audio.to_wav_16k_mono(tts.synthesize(PHRASE, 30), "audio/mpeg")
    text = stt.transcribe(wav, 60)
    assert any("ঀ" <= ch <= "৿" for ch in text)
