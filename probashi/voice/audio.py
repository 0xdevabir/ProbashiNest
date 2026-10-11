"""Convert uploaded audio to what the speech providers need.

Browsers record webm/ogg (Opus) and WhatsApp voice notes are ogg/opus. We
decode everything with ffmpeg to 16 kHz mono 16-bit WAV. Audio is piped
through ffmpeg in memory and never written to disk (privacy rule).
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import wave

from .errors import AudioError, AudioTooLongError, VoiceConfigError

MAX_AUDIO_SECONDS = 120
MIN_AUDIO_SECONDS = 0.3
MAX_AUDIO_BYTES = 25 * 1024 * 1024
SAMPLE_RATE = 16000
_BYTES_PER_SECOND = SAMPLE_RATE * 2  # mono, 16-bit
_FFMPEG_TIMEOUT_SECONDS = 30

_EXTRA_MIME_TYPES = {
    "video/webm",  # some browsers label MediaRecorder audio this way
    "video/mp4",
    "application/ogg",
    "application/octet-stream",
    "",
}


def normalize_mime(mime_type: str | None) -> str:
    """'Audio/OGG; codecs=opus' -> 'audio/ogg'."""
    return (mime_type or "").split(";")[0].strip().lower()


def ffmpeg_binary() -> str:
    path = os.getenv("FFMPEG_BINARY") or shutil.which("ffmpeg")
    if not path:
        raise VoiceConfigError(
            "ffmpeg not found. Install ffmpeg or set FFMPEG_BINARY to its path."
        )
    return path


def pcm_to_wav(pcm: bytes) -> bytes:
    """Wrap raw 16 kHz mono 16-bit PCM in a WAV header."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def to_wav_16k_mono(audio_bytes: bytes, mime_type: str | None) -> tuple[bytes, float]:
    """Decode any supported audio to WAV. Returns (wav_bytes, duration_seconds).

    Raises AudioTooLongError above MAX_AUDIO_SECONDS, AudioError for empty,
    corrupt or unsupported audio, VoiceConfigError if ffmpeg is missing.
    """
    if not audio_bytes:
        raise AudioError("Audio is empty")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioTooLongError(
            f"Audio is larger than {MAX_AUDIO_BYTES // (1024 * 1024)} MB"
        )
    mime = normalize_mime(mime_type)
    if not mime.startswith("audio/") and mime not in _EXTRA_MIME_TYPES:
        raise AudioError(f"Unsupported audio type: {mime}")

    cmd = [
        ffmpeg_binary(),
        "-hide_banner",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-vn",
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        # Decode one second past the limit so "too long" is detectable
        # without decoding an arbitrarily long file.
        "-t", str(MAX_AUDIO_SECONDS + 1),
        "-f", "s16le",
        "pipe:1",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=audio_bytes,
            capture_output=True,
            timeout=_FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as e:
        raise AudioError("Audio conversion timed out") from e
    except OSError as e:
        raise VoiceConfigError(f"Could not run ffmpeg: {e}") from e

    pcm = proc.stdout
    if proc.returncode != 0 or not pcm:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:]
        raise AudioError(f"Could not decode audio ({mime or 'unknown type'}): {detail}")

    duration = len(pcm) / _BYTES_PER_SECOND
    if duration > MAX_AUDIO_SECONDS:
        raise AudioTooLongError(
            f"Audio is longer than {MAX_AUDIO_SECONDS} seconds"
        )
    if duration < MIN_AUDIO_SECONDS:
        raise AudioError("Audio is too short")
    return pcm_to_wav(pcm), duration
