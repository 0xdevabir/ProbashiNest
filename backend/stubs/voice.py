"""STUB for probashi.voice (Agent 4). Fixed transcript, silent mp3."""

# One silent MPEG-1 Layer III frame (128 kbps, 44.1 kHz, 417 bytes), repeated.
_SILENT_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413
_SILENT_MP3 = _SILENT_FRAME * 20  # about half a second


def transcribe_bn(audio_bytes: bytes, mime_type: str) -> str:
    # Synthetic sentence: "They offered me a cleaner job in Saudi Arabia.
    # The agent is asking for four and a half lakh taka."
    return "আমাকে সৌদি আরবে ক্লিনারের চাকরি দেবে বলেছে। এজেন্ট সাড়ে চার লাখ টাকা চাইছে।"


def synthesize_bn(text: str) -> bytes:
    return _SILENT_MP3
