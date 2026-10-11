"""Probashi Shield HTTP API.

Run locally:  uvicorn backend.main:app --reload
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartParser

from backend import errors
from backend.config import Settings, get_settings
from backend.deps import Modules, build_modules, get_modules
from backend.logging_utils import configure_logging
from backend.pipeline import run_check
from probashi.schemas import CheckResponse

log = logging.getLogger("probashi.backend.api")

STUBS_HEADER = "X-Probashi-Stubs"

_AUDIO_TYPES = {
    "audio/webm",
    "video/webm",  # some browsers label MediaRecorder audio this way
    "audio/ogg",
    "application/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
}
_IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"%PDF-")  # jpg, png, pdf


def _error_response(err: errors.ApiError) -> JSONResponse:
    return JSONResponse(status_code=err.status_code, content={"detail": err.detail})


class BodyLimitMiddleware:
    """Reject request bodies over the limit, with or without Content-Length."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        too_large = errors.too_large(self.max_bytes / (1024 * 1024))
        declared = Headers(scope=scope).get("content-length", "")
        if declared.isdigit() and int(declared) > self.max_bytes:
            return await _error_response(too_large)(scope, receive, send)

        seen = 0

        async def limited_receive():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    raise too_large
            return message

        await self.app(scope, limited_receive, send)


async def _read_upload(upload: Optional[UploadFile]) -> Optional[bytes]:
    """Read an upload fully into memory; an empty file counts as not sent."""
    if upload is None:
        return None
    return await upload.read() or None


def create_app(settings: Optional[Settings] = None, modules: Optional[Modules] = None) -> FastAPI:
    settings = settings or get_settings()

    # Privacy: Starlette spools uploads over 1 MB to a temp file on disk.
    # Raise the threshold above the request limit so uploads stay in memory.
    MultiPartParser.spool_max_size = settings.max_upload_bytes + 1

    app = FastAPI(title="Probashi Shield API", version="0.1.0")
    app.state.settings = settings
    app.state.modules = modules or build_modules(settings.stubs)
    if settings.stubs:
        log.warning("running_with_stubs", extra={"stubs": sorted(settings.stubs)})

    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_upload_bytes)
    app.add_middleware(  # added last = outermost, so error responses get CORS headers too
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=[STUBS_HEADER],
    )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        # Log field names and error types only: `input` may hold user text.
        log.info(
            "invalid_request",
            extra={"problems": [f"{'.'.join(map(str, e['loc']))}:{e['type']}" for e in exc.errors()]},
        )
        return _error_response(errors.invalid_request())

    @app.get("/health")
    def health():
        return {"status": "ok", "version": app.version, "stubs": sorted(settings.stubs)}

    @app.post("/api/check", response_model=CheckResponse)
    async def check(
        response: Response,
        image: Optional[UploadFile] = File(None, description="Offer letter, visa or contract: JPG, PNG or PDF"),
        audio: Optional[UploadFile] = File(None, description="Bangla speech: WebM, OGG, MP3 or WAV"),
        text: Optional[str] = Form(None, description="Typed description of the offer"),
        save: bool = Query(False, description="Reserved. Nothing is stored yet, whatever the value."),
        modules: Modules = Depends(get_modules),
    ) -> CheckResponse:
        image_bytes = await _read_upload(image)
        audio_bytes = await _read_upload(audio)
        text = (text or "").strip() or None
        if not (image_bytes or audio_bytes or text):
            raise errors.no_input()

        if image_bytes and not image_bytes.startswith(_IMAGE_MAGIC):
            raise errors.unsupported_image()
        audio_mime = ""
        if audio_bytes:
            audio_mime = (audio.content_type or "").split(";")[0].strip().lower()
            if audio_mime not in _AUDIO_TYPES:
                raise errors.unsupported_audio()

        if settings.stubs:
            response.headers[STUBS_HEADER] = ",".join(sorted(settings.stubs))
        # The modules are blocking (LLM and speech calls), so keep them off the event loop.
        return await run_in_threadpool(
            run_check,
            modules,
            image=image_bytes,
            audio=audio_bytes,
            audio_mime=audio_mime,
            text=text,
            save=save,
        )

    return app


_settings = get_settings()
configure_logging(_settings.log_level)
app = create_app(_settings)
