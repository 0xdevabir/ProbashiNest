"""Chat-app channels: Telegram and WhatsApp (Cloud API) webhooks.

A worker sends a text, a voice note or a photo of the paper and gets the same
verdict as on the web. Files are fetched into memory, checked and dropped. A
channel is switched on only when all of its environment variables are set.

Not tested against the live services: the tests replace `_http`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response

from backend import errors
from backend.config import Settings
from backend.deps import Modules
from backend.pipeline import format_verdict_text, run_check
from backend.ratelimit import RateLimiter
from probashi.voice._http import encode_multipart

log = logging.getLogger("probashi.backend.bots")

TELEGRAM_API = "https://api.telegram.org"
GRAPH_API = "https://graph.facebook.com"
# Hosts WhatsApp media may be downloaded from (our access token is sent with the request).
_META_MEDIA_HOSTS = (".fbsbx.com", ".facebook.com", ".whatsapp.net")
TIMEOUT_SECONDS = 20
MAX_REPLY_CHARS = 4000  # both services cut messages at 4096
IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"%PDF-")  # jpg, png, pdf

WELCOME_BN = (
    "প্রবাসী শিল্ডে স্বাগতম।\n"
    "চাকরির প্রস্তাবের কথা লিখে পাঠান। অথবা ভয়েস পাঠান। অথবা কাগজের ছবি পাঠান।\n"
    "আমরা যাচাই করে লাল, হলুদ বা সবুজ সংকেত দেব।\n"
    "আমরা আপনার ছবি বা ভয়েস জমা রাখি না।"
)
BUSY_BN = "অনেকবার চেষ্টা হয়েছে। এক মিনিট পরে আবার পাঠান।"
BAD_FILE_BN = "এই ফাইল পড়া যাচ্ছে না। পরিষ্কার ছবি দিন, অথবা লিখে পাঠান।"
FAILED_BN = "এখন যাচাই করা যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।"


@dataclass
class Incoming:
    text: Optional[str] = None
    image: Optional[bytes] = None
    audio: Optional[bytes] = None
    audio_mime: str = ""


def _http(method: str, url: str, *, headers: Optional[dict] = None, body: Optional[bytes] = None,
          max_bytes: int = 1_000_000) -> bytes:
    """One HTTPS call. Raises on any failure or on an answer over max_bytes."""
    if not url.startswith("https://"):
        raise ValueError("refusing a non-https URL")
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("answer is too large")
    return data


def _call_json(method: str, url: str, *, headers: Optional[dict] = None, payload: Optional[dict] = None) -> dict:
    headers = dict(headers or {})
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    return json.loads(_http(method, url, headers=headers, body=body) or b"{}")


def _answer(
    incoming: Incoming, *, channel: str, modules: Modules, send_text: Callable[[str], None],
    send_audio: Callable[[bytes], None],
) -> None:
    """Run the check and send the answer. Never raises: a webhook must not be retried
    because of our own failure."""
    try:
        if incoming.image and not incoming.image.startswith(IMAGE_MAGIC):
            return send_text(BAD_FILE_BN)
        try:
            result = run_check(
                modules, image=incoming.image, audio=incoming.audio, audio_mime=incoming.audio_mime,
                text=incoming.text, channel=channel,
            )
        except errors.ApiError as err:
            return send_text(err.detail["message_bn"])
        send_text(format_verdict_text(result)[:MAX_REPLY_CHARS])
        if result.audio_base64:
            send_audio(base64.b64decode(result.audio_base64))
    except Exception as exc:  # noqa: BLE001
        # Only the error type: the message or URL could hold a token or user text.
        log.error("bot_failed", extra={"channel": channel, "error": type(exc).__name__})


def _safe(action: Callable[[], None], channel: str) -> None:
    try:
        action()
    except Exception as exc:  # noqa: BLE001
        log.error("bot_failed", extra={"channel": channel, "error": type(exc).__name__})


# --------------------------------------------------------------------------- Telegram


def _telegram_file(token: str, file_id: str, max_bytes: int) -> bytes:
    info = _call_json("POST", f"{TELEGRAM_API}/bot{token}/getFile", payload={"file_id": file_id})
    path = urllib.parse.quote(str(info["result"]["file_path"]))
    return _http("GET", f"{TELEGRAM_API}/file/bot{token}/{path}", max_bytes=max_bytes)


def handle_telegram(update: dict, settings: Settings, modules: Modules, limiter: RateLimiter) -> None:
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    # Private chats only: a verdict must not be posted into a group.
    if not isinstance(chat_id, int) or chat.get("type") != "private":
        return
    token = settings.telegram_bot_token
    api = f"{TELEGRAM_API}/bot{token}"

    def send_text(text: str) -> None:
        _call_json("POST", f"{api}/sendMessage", payload={"chat_id": chat_id, "text": text})

    def send_audio(mp3: bytes) -> None:
        body, content_type = encode_multipart({"chat_id": str(chat_id)}, {"audio": ("answer.mp3", mp3, "audio/mpeg")})
        _http("POST", f"{api}/sendAudio", headers={"Content-Type": content_type}, body=body)

    def work() -> None:
        text = (message.get("text") or message.get("caption") or "").strip()
        voice = message.get("voice") or message.get("audio")
        photos = message.get("photo") or []
        document = message.get("document") or {}
        if text.startswith("/") or not (text or voice or photos or document):
            return send_text(WELCOME_BN)
        if limiter.check(f"telegram:{chat_id}"):
            return send_text(BUSY_BN)
        incoming = Incoming(text=text or None)
        limit = settings.max_upload_bytes
        if voice:
            incoming.audio = _telegram_file(token, voice["file_id"], limit)
            incoming.audio_mime = str(voice.get("mime_type") or "audio/ogg").split(";")[0]
        if photos:
            incoming.image = _telegram_file(token, photos[-1]["file_id"], limit)  # last = largest
        elif document.get("file_id"):
            incoming.image = _telegram_file(token, document["file_id"], limit)
        _answer(incoming, channel="telegram", modules=modules, send_text=send_text, send_audio=send_audio)

    _safe(work, "telegram")


# --------------------------------------------------------------------------- WhatsApp


def _whatsapp_media(settings: Settings, media_id: str) -> bytes:
    auth = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    version = settings.whatsapp_graph_version
    info = _call_json("GET", f"{GRAPH_API}/{version}/{urllib.parse.quote(media_id, safe='')}", headers=auth)
    url = str(info["url"])
    host = urllib.parse.urlsplit(url).hostname or ""
    if not url.startswith("https://") or not host.endswith(_META_MEDIA_HOSTS):
        raise ValueError("unexpected media host")
    return _http("GET", url, headers=auth, max_bytes=settings.max_upload_bytes)


def handle_whatsapp(payload: dict, settings: Settings, modules: Modules, limiter: RateLimiter) -> None:
    auth = {"Authorization": f"Bearer {settings.whatsapp_token}"}
    base = f"{GRAPH_API}/{settings.whatsapp_graph_version}/{settings.whatsapp_phone_id}"
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            for message in (change.get("value") or {}).get("messages") or []:
                sender = message.get("from")
                if not isinstance(sender, str) or not sender.isdigit():
                    continue

                def send_text(text: str, to: str = sender) -> None:
                    _call_json("POST", f"{base}/messages", headers=auth, payload={
                        "messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}})

                def send_audio(mp3: bytes, to: str = sender) -> None:
                    body, content_type = encode_multipart(
                        {"messaging_product": "whatsapp", "type": "audio/mpeg"},
                        {"file": ("answer.mp3", mp3, "audio/mpeg")})
                    uploaded = json.loads(_http("POST", f"{base}/media",
                                                headers={**auth, "Content-Type": content_type}, body=body))
                    _call_json("POST", f"{base}/messages", headers=auth, payload={
                        "messaging_product": "whatsapp", "to": to, "type": "audio",
                        "audio": {"id": uploaded["id"]}})

                def work(message: dict = message, sender: str = sender, send_text=send_text,
                         send_audio=send_audio) -> None:
                    kind = message.get("type")
                    part = message.get(kind) if isinstance(message.get(kind), dict) else {}
                    incoming = Incoming()
                    if kind == "text":
                        incoming.text = str(part.get("body") or "").strip() or None
                    elif kind == "audio" and part.get("id"):
                        incoming.audio_mime = str(part.get("mime_type") or "audio/ogg").split(";")[0]
                    elif kind in ("image", "document") and part.get("id"):
                        incoming.text = str(part.get("caption") or "").strip() or None
                    else:
                        return send_text(WELCOME_BN)
                    if kind == "text" and not incoming.text:
                        return send_text(WELCOME_BN)
                    if limiter.check(f"whatsapp:{sender}"):
                        return send_text(BUSY_BN)
                    if kind == "audio":
                        incoming.audio = _whatsapp_media(settings, part["id"])
                    elif kind in ("image", "document"):
                        incoming.image = _whatsapp_media(settings, part["id"])
                    _answer(incoming, channel="whatsapp", modules=modules, send_text=send_text,
                            send_audio=send_audio)

                _safe(work, "whatsapp")


# --------------------------------------------------------------------------- routes


def build_router(settings: Settings, limiter: RateLimiter) -> APIRouter:
    router = APIRouter(prefix="/api/bots", tags=["bots"])
    telegram_on = bool(settings.telegram_bot_token and settings.telegram_webhook_secret)
    whatsapp_on = bool(settings.whatsapp_token and settings.whatsapp_phone_id
                       and settings.whatsapp_verify_token and settings.whatsapp_app_secret)

    @router.post("/telegram", include_in_schema=False)
    async def telegram(request: Request, background: BackgroundTasks):
        if not telegram_on:
            raise errors.not_found()
        secret = request.headers.get("x-telegram-bot-api-secret-token", "")
        if not hmac.compare_digest(secret.encode(), settings.telegram_webhook_secret.encode()):
            raise errors.not_found()
        try:
            update = json.loads(await request.body())
        except ValueError:
            raise errors.invalid_request() from None
        if isinstance(update, dict):
            # Answer Telegram at once and do the slow work afterwards, or it sends the update again.
            background.add_task(handle_telegram, update, settings, request.app.state.modules, limiter)
        return {"ok": True}

    @router.get("/whatsapp", include_in_schema=False)
    def whatsapp_verify(
        mode: str = Query("", alias="hub.mode"),
        token: str = Query("", alias="hub.verify_token"),
        challenge: str = Query("", alias="hub.challenge"),
    ):
        if not whatsapp_on or mode != "subscribe" or not hmac.compare_digest(
            token.encode(), settings.whatsapp_verify_token.encode()
        ):
            raise errors.not_found()
        return Response(content=challenge, media_type="text/plain")

    @router.post("/whatsapp", include_in_schema=False)
    async def whatsapp(request: Request, background: BackgroundTasks):
        if not whatsapp_on:
            raise errors.not_found()
        raw = await request.body()
        expected = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(request.headers.get("x-hub-signature-256", "").encode(), expected.encode()):
            raise errors.not_found()
        try:
            payload = json.loads(raw)
        except ValueError:
            raise errors.invalid_request() from None
        if isinstance(payload, dict):
            background.add_task(handle_whatsapp, payload, settings, request.app.state.modules, limiter)
        return {"ok": True}

    return router
