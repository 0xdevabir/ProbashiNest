import base64
import dataclasses
import tempfile

import pytest
from fastapi.testclient import TestClient
from starlette.formparsers import MultiPartParser

from backend.config import Settings, _parse_stubs
from backend.main import STUBS_HEADER, create_app
from backend.pipeline import build_spoken_summary
from backend.stubs.knowledge import evaluate as stub_evaluate
from backend.tests.conftest import JPG, PDF, PNG, STUB_SETTINGS
from probashi.schemas import CheckResponse, ExtractedOffer, Level


def _boom(*args, **kwargs):
    raise RuntimeError("provider is down")


def _assert_bilingual_error(resp, status: int, code: str):
    assert resp.status_code == status, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == code
    assert any("ঀ" <= ch <= "৿" for ch in detail["message_bn"])  # has Bangla
    assert detail["message_en"].isascii()


# --- health, CORS ---------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["stubs"] == ["extract", "knowledge", "voice"]


def test_cors_allows_the_frontend_origin_only(client):
    ok = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


# --- validation errors ----------------------------------------------------

def test_no_input_is_422_in_bangla_and_english(client):
    _assert_bilingual_error(client.post("/api/check"), 422, "NO_INPUT")


def test_blank_text_and_empty_file_count_as_no_input(client):
    resp = client.post(
        "/api/check", data={"text": "   "}, files={"image": ("offer.png", b"", "image/png")}
    )
    _assert_bilingual_error(resp, 422, "NO_INPUT")


def test_malformed_field_is_422_in_bangla_and_english(client):
    resp = client.post("/api/check?save=maybe", data={"text": "চাকরির প্রস্তাব"})
    _assert_bilingual_error(resp, 422, "INVALID_REQUEST")


def test_unsupported_image_is_415(client):
    resp = client.post("/api/check", files={"image": ("offer.gif", b"GIF89a" + b"\x00" * 32, "image/gif")})
    _assert_bilingual_error(resp, 415, "UNSUPPORTED_IMAGE")


def test_unsupported_audio_is_415(client):
    resp = client.post("/api/check", files={"audio": ("a.flac", b"fLaC" + b"\x00" * 32, "audio/flac")})
    _assert_bilingual_error(resp, 415, "UNSUPPORTED_AUDIO")


def test_request_over_size_limit_is_413(make_client):
    client = make_client(dataclasses.replace(STUB_SETTINGS, max_upload_bytes=1024))
    resp = client.post("/api/check", files={"image": ("offer.png", PNG + b"\x00" * 2048, "image/png")})
    _assert_bilingual_error(resp, 413, "TOO_LARGE")


def test_size_limit_also_applies_without_content_length(make_client):
    client = make_client(dataclasses.replace(STUB_SETTINGS, max_upload_bytes=1024))

    def chunks():  # a generator body is sent chunked, with no Content-Length
        yield b"--b\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\n"
        for _ in range(8):
            yield b"x" * 512
        yield b"\r\n--b--\r\n"

    resp = client.post(
        "/api/check", content=chunks(), headers={"Content-Type": "multipart/form-data; boundary=b"}
    )
    _assert_bilingual_error(resp, 413, "TOO_LARGE")


# --- stub pipeline, end to end -------------------------------------------

@pytest.mark.parametrize("image", [PNG, JPG, PDF])
def test_image_check_end_to_end(client, image):
    resp = client.post("/api/check", files={"image": ("offer", image, "application/octet-stream")})
    assert resp.status_code == 200, resp.text
    body = CheckResponse.model_validate(resp.json())
    assert body.verdict.level is Level.amber  # stubs verify nothing, so never green
    assert body.verdict.reasons and body.verdict.next_steps_bn
    assert body.transcript_bn is None
    assert base64.b64decode(body.audio_base64).startswith(b"\xff\xfb")  # mp3 frame
    assert resp.headers[STUBS_HEADER] == "extract,knowledge,voice"


def test_text_check_end_to_end(client):
    resp = client.post("/api/check", data={"text": "সৌদি আরবে ক্লিনারের চাকরি"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["offer"]["raw_text"] == "সৌদি আরবে ক্লিনারের চাকরি"


def test_audio_is_transcribed_and_used_as_text(make_client):
    seen = {}

    def transcribe(audio_bytes, mime_type):
        seen["mime"] = mime_type
        return "এজেন্ট টাকা চাইছে"

    def extract(image_bytes, text):
        seen["text"] = text
        return ExtractedOffer(raw_text=text or "")

    client = make_client(transcribe_bn=transcribe, extract_offer=extract)
    resp = client.post(
        "/api/check",
        data={"text": "মালয়েশিয়ার চাকরি"},
        files={"audio": ("voice.webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 32, "audio/webm;codecs=opus")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["transcript_bn"] == "এজেন্ট টাকা চাইছে"
    assert seen == {"mime": "audio/webm", "text": "মালয়েশিয়ার চাকরি\nএজেন্ট টাকা চাইছে"}


def test_spoken_summary_has_level_two_reasons_and_first_step(make_client):
    spoken = []
    client = make_client(synthesize_bn=lambda text: spoken.append(text) or b"\xff\xfbmp3")
    assert client.post("/api/check", data={"text": "চাকরি"}).status_code == 200

    verdict = stub_evaluate(ExtractedOffer())
    assert spoken == [build_spoken_summary(verdict)]
    assert spoken[0].startswith("হলুদ সংকেত")
    assert verdict.reasons[0].message_bn in spoken[0]
    assert verdict.reasons[1].message_bn in spoken[0]
    assert verdict.reasons[2].message_bn not in spoken[0]
    assert verdict.next_steps_bn[0] in spoken[0]
    assert verdict.next_steps_bn[1] not in spoken[0]


def test_save_flag_is_accepted_and_stores_nothing(client, log_lines, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert client.post("/api/check", data={"text": "চাকরি"}).status_code == 200
    assert client.post("/api/check?save=true", data={"text": "চাকরি"}).status_code == 200
    done = [line for line in log_lines() if line["msg"] == "check_completed"]
    assert [line["save_requested"] for line in done] == [False, True]
    assert [line["saved"] for line in done] == [False, False]
    assert list(tmp_path.iterdir()) == []


def _post_big_image(client, monkeypatch) -> list[int]:
    """Upload 3 MB (over Starlette's 1 MB default) and report spills to disk."""
    spills = []
    original = tempfile.SpooledTemporaryFile.rollover
    monkeypatch.setattr(
        tempfile.SpooledTemporaryFile,
        "rollover",
        lambda self: spills.append(1) or original(self),
    )
    big = PNG + b"\x00" * (3 * 1024 * 1024)
    resp = client.post("/api/check", files={"image": ("offer.png", big, "image/png")})
    assert resp.status_code == 200, resp.text
    return spills


def test_large_upload_stays_in_memory(client, monkeypatch):
    assert _post_big_image(client, monkeypatch) == []


def test_the_in_memory_test_can_detect_a_spill(client, monkeypatch):
    """Guards the test above: with Starlette's default, the same upload hits disk."""
    monkeypatch.setattr(MultiPartParser, "spool_max_size", 1024 * 1024)
    assert _post_big_image(client, monkeypatch) != []


# --- failures -------------------------------------------------------------

def test_voice_synthesis_failure_still_returns_the_verdict(make_client):
    resp = make_client(synthesize_bn=_boom).post("/api/check", data={"text": "চাকরি"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["audio_base64"] is None
    assert resp.json()["verdict"]["level"] == "amber"


def test_empty_synthesis_output_gives_null_audio(make_client):
    resp = make_client(synthesize_bn=lambda text: b"").post("/api/check", data={"text": "চাকরি"})
    assert resp.status_code == 200
    assert resp.json()["audio_base64"] is None


def test_transcription_failure_with_only_audio_is_502(make_client):
    resp = make_client(transcribe_bn=_boom).post(
        "/api/check", files={"audio": ("v.wav", b"RIFF" + b"\x00" * 32, "audio/wav")}
    )
    _assert_bilingual_error(resp, 502, "VOICE_UNAVAILABLE")


def test_transcription_failure_with_an_image_still_checks_the_image(make_client):
    resp = make_client(transcribe_bn=_boom).post(
        "/api/check",
        files={
            "audio": ("v.wav", b"RIFF" + b"\x00" * 32, "audio/wav"),
            "image": ("offer.png", PNG, "image/png"),
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["transcript_bn"] is None


def test_silent_audio_is_422(make_client):
    resp = make_client(transcribe_bn=lambda a, m: "  ").post(
        "/api/check", files={"audio": ("v.ogg", b"OggS" + b"\x00" * 32, "audio/ogg")}
    )
    _assert_bilingual_error(resp, 422, "SPEECH_NOT_UNDERSTOOD")


@pytest.mark.parametrize("stage, override", [("extract", "extract_offer"), ("knowledge", "evaluate")])
def test_core_stage_failure_is_an_error_not_a_verdict(make_client, stage, override):
    resp = make_client(**{override: _boom}).post("/api/check", data={"text": "চাকরি"})
    _assert_bilingual_error(resp, 502, f"{stage.upper()}_FAILED")
    assert "provider is down" not in resp.text  # internal errors are not leaked


def test_real_placeholder_modules_give_503_not_a_crash():
    client = TestClient(create_app(Settings()))  # no stubs: placeholders raise NotImplementedError
    resp = client.post("/api/check", data={"text": "চাকরি"})
    if resp.status_code == 200:
        pytest.skip("real modules are implemented")
    assert resp.status_code in (502, 503), resp.text
    assert STUBS_HEADER not in resp.headers


# --- settings -------------------------------------------------------------

def test_use_stubs_parsing():
    assert _parse_stubs("false") == frozenset()
    assert _parse_stubs("true") == {"extract", "knowledge", "voice"}
    assert _parse_stubs("voice, knowledge") == {"voice", "knowledge"}
    with pytest.raises(ValueError):
        _parse_stubs("voice,frontend")
