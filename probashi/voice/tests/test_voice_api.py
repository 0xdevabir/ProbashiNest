"""transcribe_bn / synthesize_bn behaviour with fake providers (no network)."""
import json

import pytest

import probashi.voice as voice
from probashi.voice import _http
from probashi.voice.errors import (
    NoSpeechError,
    ProviderError,
    VoiceConfigError,
    VoiceError,
)
from probashi.voice.providers import azure, elevenlabs
from probashi.voice.providers.base import STTProvider, TTSProvider


class FakeSTT(STTProvider):
    """Test stub, not a real provider."""

    name = "fake"
    configured = True
    outcomes: list = []
    calls = 0

    def is_configured(self):
        return self.configured

    def transcribe(self, wav_bytes, timeout):
        type(self).calls += 1
        outcome = type(self).outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class BackupSTT(FakeSTT):
    name = "backup"
    outcomes: list = []
    calls = 0


class FakeTTS(TTSProvider):
    name = "fake"
    seen: list = []

    def is_configured(self):
        return True

    def synthesize(self, text, timeout):
        type(self).seen.append(text)
        return b"ID3fake-mp3"


@pytest.fixture
def stt(monkeypatch):
    for cls in (FakeSTT, BackupSTT):
        cls.outcomes, cls.calls, cls.configured = [], 0, True
    monkeypatch.setattr(voice, "STT_PROVIDERS", {"fake": FakeSTT, "backup": BackupSTT})
    monkeypatch.setattr(voice, "to_wav_16k_mono", lambda b, m: (b"wav", 1.0))
    monkeypatch.delenv("VOICE_STT_PROVIDER", raising=False)
    monkeypatch.delenv("VOICE_FALLBACK", raising=False)


def retryable():
    return ProviderError("timeout", provider="fake", retryable=True)


def test_transcribe_success(stt):
    FakeSTT.outcomes = ["  আমি সৌদি যাব  "]
    assert voice.transcribe_bn(b"x", "audio/ogg") == "আমি সৌদি যাব"


def test_one_retry_then_success(stt):
    FakeSTT.outcomes = [retryable(), "ঠিক আছে"]
    assert voice.transcribe_bn(b"x", "audio/ogg") == "ঠিক আছে"
    assert FakeSTT.calls == 2 and BackupSTT.calls == 0


def test_falls_back_after_two_failures(stt):
    FakeSTT.outcomes = [retryable(), retryable()]
    BackupSTT.outcomes = ["ব্যাকআপ"]
    assert voice.transcribe_bn(b"x", "audio/ogg") == "ব্যাকআপ"
    assert FakeSTT.calls == 2


def test_non_retryable_error_is_not_retried(stt):
    FakeSTT.outcomes = [ProviderError("bad key", provider="fake", status=401)]
    BackupSTT.outcomes = ["ব্যাকআপ"]
    assert voice.transcribe_bn(b"x", "audio/ogg") == "ব্যাকআপ"
    assert FakeSTT.calls == 1


def test_all_providers_fail_raises_voice_error(stt):
    FakeSTT.outcomes = [retryable(), retryable()]
    BackupSTT.outcomes = [retryable(), retryable()]
    with pytest.raises(VoiceError):
        voice.transcribe_bn(b"x", "audio/ogg")


def test_fallback_can_be_disabled(stt, monkeypatch):
    monkeypatch.setenv("VOICE_FALLBACK", "false")
    FakeSTT.outcomes = [retryable(), retryable()]
    with pytest.raises(ProviderError):
        voice.transcribe_bn(b"x", "audio/ogg")
    assert BackupSTT.calls == 0


def test_env_var_selects_provider(stt, monkeypatch):
    monkeypatch.setenv("VOICE_STT_PROVIDER", "backup")
    BackupSTT.outcomes = ["হ্যাঁ"]
    assert voice.transcribe_bn(b"x", "audio/ogg") == "হ্যাঁ"
    assert FakeSTT.calls == 0


def test_unknown_provider_name(stt, monkeypatch):
    monkeypatch.setenv("VOICE_STT_PROVIDER", "nope")
    with pytest.raises(VoiceConfigError):
        voice.transcribe_bn(b"x", "audio/ogg")


def test_no_provider_configured(stt):
    FakeSTT.configured = BackupSTT.configured = False
    with pytest.raises(VoiceConfigError):
        voice.transcribe_bn(b"x", "audio/ogg")


def test_empty_transcript_raises_no_speech(stt):
    FakeSTT.outcomes = ["   "]
    with pytest.raises(NoSpeechError):
        voice.transcribe_bn(b"x", "audio/ogg")


def test_synthesize_expands_numbers_before_calling_provider(monkeypatch):
    FakeTTS.seen = []
    monkeypatch.setattr(voice, "TTS_PROVIDERS", {"fake": FakeTTS})
    monkeypatch.delenv("VOICE_TTS_PROVIDER", raising=False)
    assert voice.synthesize_bn("ফি 500000 BDT") == b"ID3fake-mp3"
    assert FakeTTS.seen == ["ফি পাঁচ লাখ টাকা"]


def test_synthesize_empty_text(monkeypatch):
    monkeypatch.setattr(voice, "TTS_PROVIDERS", {"fake": FakeTTS})
    with pytest.raises(VoiceError):
        voice.synthesize_bn("   ")


# --- request shapes of the real providers, with HTTP mocked -----------------


@pytest.fixture
def captured(monkeypatch):
    box = {}

    def fake_post(url, *, headers, body, timeout, provider):
        box.update(url=url, headers=headers, body=body, timeout=timeout)
        return box["response"]

    monkeypatch.setattr(_http, "post", fake_post)
    return box


def test_azure_tts_request(captured, monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "southeastasia")
    monkeypatch.delenv("AZURE_TTS_VOICE", raising=False)
    monkeypatch.delenv("AZURE_TTS_RATE", raising=False)
    captured["response"] = b"mp3"
    assert azure.AzureTTS().synthesize("ক < খ", 5) == b"mp3"
    assert captured["url"] == "https://southeastasia.tts.speech.microsoft.com/cognitiveservices/v1"
    assert "mp3" in captured["headers"]["X-Microsoft-OutputFormat"]
    ssml = captured["body"].decode("utf-8")
    assert "bn-BD-NabanitaNeural" in ssml and "rate='-15%'" in ssml
    assert "ক &lt; খ" in ssml  # text is XML-escaped


def test_azure_stt_request_and_response(captured, monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "southeastasia")
    monkeypatch.delenv("AZURE_SPEECH_ENDPOINT", raising=False)
    captured["response"] = json.dumps({"combinedPhrases": [{"text": "আমি যাব"}]}).encode()
    assert azure.AzureSTT().transcribe(b"RIFFwav", 5) == "আমি যাব"
    assert "/speechtotext/transcriptions:transcribe?api-version=" in captured["url"]
    assert b'"bn-IN"' in captured["body"] and b"RIFFwav" in captured["body"]


def test_elevenlabs_stt_request_and_bad_response(captured, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    captured["response"] = json.dumps({"text": "আমি যাব"}).encode()
    assert elevenlabs.ElevenLabsSTT().transcribe(b"RIFFwav", 5) == "আমি যাব"
    assert captured["url"].endswith("/v1/speech-to-text")
    assert b"scribe_v2" in captured["body"] and b"ben" in captured["body"]
    captured["response"] = b"<html>oops</html>"
    with pytest.raises(ProviderError):
        elevenlabs.ElevenLabsSTT().transcribe(b"RIFFwav", 5)


def test_elevenlabs_tts_needs_a_voice_id(captured, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    assert not elevenlabs.ElevenLabsTTS().is_configured()
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice123")
    captured["response"] = b"mp3"
    assert elevenlabs.ElevenLabsTTS().synthesize("হ্যালো", 5) == b"mp3"
    assert "/text-to-speech/voice123?output_format=mp3" in captured["url"]
    assert json.loads(captured["body"])["model_id"] == "eleven_v3"


def test_multipart_encoding():
    body, content_type = _http.encode_multipart(
        {"a": "1"}, {"file": ("x.wav", b"\x00\x01", "audio/wav")}
    )
    boundary = content_type.split("boundary=")[1].encode()
    assert body.count(b"--" + boundary) == 3
    assert b'name="a"\r\n\r\n1\r\n' in body
    assert b'filename="x.wav"\r\nContent-Type: audio/wav\r\n\r\n\x00\x01\r\n' in body


def test_http_connection_failure_is_retryable_provider_error():
    with pytest.raises(ProviderError) as info:
        _http.post("http://127.0.0.1:9/", headers={}, body=b"", timeout=1, provider="t")
    assert info.value.retryable
