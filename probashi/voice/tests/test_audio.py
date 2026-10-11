"""Audio conversion tests. No API keys needed; ffmpeg tests skip without ffmpeg."""
import io
import math
import os
import shutil
import struct
import subprocess
import wave

import pytest

from probashi.voice import audio
from probashi.voice.errors import AudioError, AudioTooLongError, VoiceConfigError

FFMPEG = os.getenv("FFMPEG_BINARY") or shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")


def make_wav(seconds: float, rate: int = 44100, channels: int = 2) -> bytes:
    """Synthetic 440 Hz tone (not a real recording)."""
    frames = bytearray()
    for i in range(int(seconds * rate)):
        sample = int(8000 * math.sin(2 * math.pi * 440 * i / rate))
        frames += struct.pack("<h", sample) * channels
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def encode(wav: bytes, fmt: str, codec: str) -> bytes:
    """Encode with ffmpeg to mimic browser / WhatsApp uploads."""
    proc = subprocess.run(
        [FFMPEG, "-loglevel", "error", "-i", "pipe:0", "-c:a", codec, "-f", fmt, "pipe:1"],
        input=wav, capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        pytest.skip(f"this ffmpeg build cannot encode {codec}/{fmt}")
    return proc.stdout


def assert_wav_16k_mono(wav: bytes) -> None:
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 16000)


def test_normalize_mime():
    assert audio.normalize_mime("Audio/OGG; codecs=opus") == "audio/ogg"
    assert audio.normalize_mime(None) == ""


def test_pcm_to_wav_header():
    wav = audio.pcm_to_wav(b"\x00\x00" * 16000)
    assert_wav_16k_mono(wav)


def test_empty_audio_rejected():
    with pytest.raises(AudioError):
        audio.to_wav_16k_mono(b"", "audio/ogg")


def test_non_audio_mime_rejected():
    with pytest.raises(AudioError):
        audio.to_wav_16k_mono(b"abc", "image/png")


def test_oversized_upload_rejected(monkeypatch):
    monkeypatch.setattr(audio, "MAX_AUDIO_BYTES", 10)
    with pytest.raises(AudioTooLongError):
        audio.to_wav_16k_mono(b"x" * 11, "audio/ogg")


def test_missing_ffmpeg_is_a_config_error(monkeypatch):
    monkeypatch.delenv("FFMPEG_BINARY", raising=False)
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)
    with pytest.raises(VoiceConfigError):
        audio.to_wav_16k_mono(b"abc", "audio/ogg")


@needs_ffmpeg
@pytest.mark.parametrize(
    "mime, fmt, codec",
    [
        ("audio/webm;codecs=opus", "webm", "libopus"),  # Chrome / Android MediaRecorder
        ("audio/ogg; codecs=opus", "ogg", "libopus"),  # Firefox, WhatsApp voice note
        ("audio/mpeg", "mp3", "libmp3lame"),
    ],
)
def test_browser_and_whatsapp_formats_convert(mime, fmt, codec):
    src = encode(make_wav(2.0), fmt, codec)
    wav, seconds = audio.to_wav_16k_mono(src, mime)
    assert_wav_16k_mono(wav)
    assert seconds == pytest.approx(2.0, abs=0.2)


@needs_ffmpeg
def test_stereo_wav_is_downmixed_and_resampled():
    wav, seconds = audio.to_wav_16k_mono(make_wav(1.0), "audio/wav")
    assert_wav_16k_mono(wav)
    assert seconds == pytest.approx(1.0, abs=0.05)


@needs_ffmpeg
def test_longer_than_two_minutes_rejected():
    long_wav = audio.pcm_to_wav(b"\x00\x00" * 16000 * (audio.MAX_AUDIO_SECONDS + 5))
    with pytest.raises(AudioTooLongError):
        audio.to_wav_16k_mono(long_wav, "audio/wav")


@needs_ffmpeg
def test_exactly_at_limit_is_accepted():
    ok_wav = audio.pcm_to_wav(b"\x00\x00" * 16000 * audio.MAX_AUDIO_SECONDS)
    _, seconds = audio.to_wav_16k_mono(ok_wav, "audio/wav")
    assert seconds == pytest.approx(audio.MAX_AUDIO_SECONDS, abs=0.01)


@needs_ffmpeg
def test_too_short_rejected():
    with pytest.raises(AudioError):
        audio.to_wav_16k_mono(make_wav(0.05), "audio/wav")


@needs_ffmpeg
def test_garbage_bytes_rejected():
    with pytest.raises(AudioError):
        audio.to_wav_16k_mono(b"this is not audio" * 100, "audio/ogg")
