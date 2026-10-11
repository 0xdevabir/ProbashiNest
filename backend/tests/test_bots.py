"""Telegram and WhatsApp webhooks. All outside HTTP is replaced by a fake: nothing
here talks to the real services, and every token and phone number is SYNTHETIC."""
import dataclasses
import hashlib
import hmac
import json

import pytest

from backend import bots
from backend.config import STUBBABLE, Settings
from backend.tests.conftest import JPG

TG_TOKEN = "SYNTHETIC-TG-TOKEN"
SETTINGS = dataclasses.replace(
    Settings(stubs=frozenset(STUBBABLE)),
    telegram_bot_token=TG_TOKEN, telegram_webhook_secret="tg-secret",
    whatsapp_token="SYNTHETIC-WA-TOKEN", whatsapp_phone_id="1000", whatsapp_verify_token="wa-verify",
    whatsapp_app_secret="wa-app-secret",
)
TG_HEADERS = {"X-Telegram-Bot-Api-Secret-Token": "tg-secret"}


class FakeHttp:
    """Records calls and answers like the two services would."""

    def __init__(self, files: dict):
        self.calls: list[tuple[str, str, dict, bytes | None]] = []
        self.files = files

    def __call__(self, method, url, *, headers=None, body=None, max_bytes=1_000_000):
        self.calls.append((method, url, headers or {}, body))
        if url.endswith("/getFile"):
            return json.dumps({"result": {"file_path": json.loads(body)["file_id"]}}).encode()
        if "/file/bot" in url:
            return self.files[url.rsplit("/", 1)[-1]]
        if url.endswith("/MEDIA1"):
            return json.dumps({"url": "https://lookaside.fbsbx.com/media1"}).encode()
        if url.endswith("/EVIL"):
            return json.dumps({"url": "https://attacker.example/steal"}).encode()
        if url.startswith("https://lookaside.fbsbx.com/"):
            return self.files["media1"]
        if url.endswith("/media"):
            return b'{"id": "UPLOADED"}'
        return b'{"ok": true}'

    def sent(self, suffix: str) -> list[dict]:
        return [json.loads(b) for _, url, h, b in self.calls
                if url.endswith(suffix) and h.get("Content-Type") == "application/json"]


@pytest.fixture
def http(monkeypatch):
    fake = FakeHttp({"photo-big": JPG, "voice-1": b"OggS-synthetic", "media1": JPG, "doc-1": b"not an image"})
    monkeypatch.setattr(bots, "_http", fake)
    return fake


@pytest.fixture
def bot(make_client):
    return make_client(SETTINGS)


def tg(chat_type="private", **message):
    return {"update_id": 1, "message": {"chat": {"id": 42, "type": chat_type}, **message}}


# --- Telegram ---------------------------------------------------------------

def test_telegram_text_gets_a_verdict_and_a_voice_answer(bot, http):
    assert bot.post("/api/bots/telegram", json=tg(text="সৌদি আরবে চাকরি"), headers=TG_HEADERS).json() == {"ok": True}
    (reply,) = http.sent("/sendMessage")
    assert reply["chat_id"] == 42 and reply["text"].startswith("🟡") and "কারণ:" in reply["text"]
    (audio,) = [c for c in http.calls if c[1].endswith("/sendAudio")]
    assert b'name="chat_id"\r\n\r\n42' in audio[3] and b"answer.mp3" in audio[3]


def test_telegram_photo_and_voice_are_fetched_into_memory_and_checked(bot, http, make_client):
    seen = {}

    def extract(image, text):
        seen.update(image=image, text=text)
        from backend.stubs.extract import extract_offer
        return extract_offer(image, text)

    client = make_client(SETTINGS, extract_offer=extract)
    client.post("/api/bots/telegram", headers=TG_HEADERS, json=tg(
        photo=[{"file_id": "photo-small"}, {"file_id": "photo-big"}], caption="এই কাগজ দেখুন"))
    assert seen == {"image": JPG, "text": "এই কাগজ দেখুন"}
    client.post("/api/bots/telegram", headers=TG_HEADERS, json=tg(voice={"file_id": "voice-1", "mime_type": "audio/ogg"}))
    assert seen["image"] is None and seen["text"]  # the stub transcript
    assert len(http.sent("/sendMessage")) == 2


def test_telegram_refuses_a_wrong_secret_and_ignores_groups(bot, http):
    assert bot.post("/api/bots/telegram", json=tg(text="x")).status_code == 404
    assert bot.post("/api/bots/telegram", json=tg(text="x"), headers={
        "X-Telegram-Bot-Api-Secret-Token": "guess"}).status_code == 404
    assert bot.post("/api/bots/telegram", json=tg("group", text="x"), headers=TG_HEADERS).status_code == 200
    assert http.calls == []


def test_telegram_start_command_and_bad_file_get_help_not_a_check(bot, http):
    bot.post("/api/bots/telegram", json=tg(text="/start"), headers=TG_HEADERS)
    bot.post("/api/bots/telegram", json=tg(document={"file_id": "doc-1"}), headers=TG_HEADERS)
    assert [m["text"] for m in http.sent("/sendMessage")] == [bots.WELCOME_BN, bots.BAD_FILE_BN]
    assert bot.get("/api/stats").json()["checks"] == 0


def test_telegram_per_chat_limit(make_client, http):
    client = make_client(dataclasses.replace(SETTINGS, rate_limit_per_minute=1))
    for _ in range(2):
        client.post("/api/bots/telegram", json=tg(text="offer"), headers=TG_HEADERS)
    assert http.sent("/sendMessage")[-1]["text"] == bots.BUSY_BN


def test_bot_failure_is_logged_without_the_token_and_still_answers_200(bot, monkeypatch, log_lines):
    def broken(method, url, **kwargs):
        raise RuntimeError(f"cannot reach {url}")

    monkeypatch.setattr(bots, "_http", broken)
    assert bot.post("/api/bots/telegram", json=tg(text="offer"), headers=TG_HEADERS).status_code == 200
    assert TG_TOKEN not in log_lines.raw()
    assert any(line["msg"] == "bot_failed" and line["error"] == "RuntimeError" for line in log_lines())


def test_channels_are_off_without_their_settings(client):
    assert client.post("/api/bots/telegram", json=tg(text="x"), headers=TG_HEADERS).status_code == 404
    assert client.post("/api/bots/whatsapp", json={}).status_code == 404
    assert client.get("/api/bots/whatsapp?hub.mode=subscribe&hub.verify_token=&hub.challenge=1").status_code == 404


# --- WhatsApp ---------------------------------------------------------------

def wa_post(client, payload: dict, secret: str = "wa-app-secret"):
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/api/bots/whatsapp", content=raw,
                       headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})


def wa(message: dict) -> dict:
    return {"entry": [{"changes": [{"value": {"messages": [{"from": "8800000000000", **message}]}}]}]}


def test_whatsapp_verification_handshake(bot):
    ok = bot.get("/api/bots/whatsapp?hub.mode=subscribe&hub.verify_token=wa-verify&hub.challenge=12345")
    assert ok.status_code == 200 and ok.text == "12345"
    assert bot.get("/api/bots/whatsapp?hub.mode=subscribe&hub.verify_token=no&hub.challenge=1").status_code == 404


def test_whatsapp_text_gets_a_verdict_with_the_bearer_token(bot, http):
    assert wa_post(bot, wa({"type": "text", "text": {"body": "মালয়েশিয়ায় চাকরি"}})).status_code == 200
    text, audio = http.sent("/1000/messages")
    assert text["to"] == "8800000000000" and text["text"]["body"].startswith("🟡")
    assert audio["audio"] == {"id": "UPLOADED"}
    assert all(h["Authorization"] == "Bearer SYNTHETIC-WA-TOKEN" for _, _, h, _ in http.calls)


def test_whatsapp_image_is_downloaded_only_from_meta_hosts(bot, http):
    wa_post(bot, wa({"type": "image", "image": {"id": "MEDIA1", "mime_type": "image/jpeg"}}))
    assert http.sent("/1000/messages")[0]["text"]["body"].startswith("🟡")
    http.calls.clear()
    wa_post(bot, wa({"type": "image", "image": {"id": "EVIL"}}))
    assert not any("attacker.example" in url for _, url, _, _ in http.calls)
    assert http.sent("/1000/messages") == []


def test_whatsapp_refuses_an_unsigned_or_wrongly_signed_body(bot, http):
    payload = wa({"type": "text", "text": {"body": "x"}})
    assert bot.post("/api/bots/whatsapp", json=payload).status_code == 404
    assert wa_post(bot, payload, secret="someone-else").status_code == 404
    assert http.calls == []
