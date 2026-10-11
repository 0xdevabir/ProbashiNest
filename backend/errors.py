"""Bilingual API errors.

Every error body has the same shape, so the frontend can always show Bangla:
    {"detail": {"code": "...", "message_bn": "...", "message_en": "..."}}
"""
from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message_bn: str, message_en: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message_bn": message_bn, "message_en": message_en},
        )
        self.code = code


def no_input() -> ApiError:
    return ApiError(
        422,
        "NO_INPUT",
        "কিছু পাওয়া যায়নি। ছবি দিন, কথা বলুন, অথবা লিখে দিন।",
        "Nothing was sent. Provide at least one of: image, audio or text.",
    )


def invalid_request() -> ApiError:
    return ApiError(
        422,
        "INVALID_REQUEST",
        "অনুরোধটি ঠিক নেই। আবার চেষ্টা করুন।",
        "The request is not valid. Send multipart form fields: image, audio, text.",
    )


def too_large(max_mb: float) -> ApiError:
    return ApiError(
        413,
        "TOO_LARGE",
        f"ফাইল অনেক বড়। {max_mb:g} এমবি-র ছোট ফাইল দিন।",
        f"Upload is too large. The limit is {max_mb:g} MB per request.",
    )


def unsupported_image() -> ApiError:
    return ApiError(
        415,
        "UNSUPPORTED_IMAGE",
        "এই ছবি পড়া যাচ্ছে না। JPG, PNG বা PDF দিন।",
        "Unsupported image. Use JPG, PNG or PDF.",
    )


def unsupported_audio() -> ApiError:
    return ApiError(
        415,
        "UNSUPPORTED_AUDIO",
        "এই অডিও চলছে না। আবার রেকর্ড করুন।",
        "Unsupported audio. Use WebM, OGG, MP3 or WAV.",
    )


def speech_not_understood() -> ApiError:
    return ApiError(
        422,
        "SPEECH_NOT_UNDERSTOOD",
        "আপনার কথা বোঝা যায়নি। আবার বলুন, অথবা লিখে দিন।",
        "No speech could be recognised in the audio. Try again or send text.",
    )


def voice_unavailable() -> ApiError:
    return ApiError(
        502,
        "VOICE_UNAVAILABLE",
        "এখন কথা শোনা যাচ্ছে না। লিখে দিন বা ছবি দিন।",
        "Speech-to-text failed. Send text or an image instead.",
    )


def module_not_ready(stage: str) -> ApiError:
    return ApiError(
        503,
        "MODULE_NOT_READY",
        "সেবাটি এখনো তৈরি হয়নি। পরে আবার চেষ্টা করুন।",
        f"The '{stage}' module is not implemented yet. Set USE_STUBS to stub it.",
    )


def stage_failed(stage: str) -> ApiError:
    return ApiError(
        502,
        f"{stage.upper()}_FAILED",
        "এখন যাচাই করা যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।",
        f"The '{stage}' step failed. No verdict was produced. Try again later.",
    )


def rate_limited(retry_after: int) -> ApiError:
    err = ApiError(
        429,
        "RATE_LIMITED",
        "অনেকবার চেষ্টা হয়েছে। এক মিনিট পরে আবার চেষ্টা করুন।",
        f"Too many requests. Try again in {retry_after} seconds.",
    )
    err.headers = {"Retry-After": str(retry_after)}
    return err


def too_many_images(limit: int) -> ApiError:
    return ApiError(
        422,
        "TOO_MANY_IMAGES",
        f"একসাথে {limit}টার বেশি কাগজ দেওয়া যায় না।",
        f"At most {limit} documents can be checked together.",
    )


def consent_required() -> ApiError:
    return ApiError(
        422,
        "CONSENT_REQUIRED",
        "আপনি রাজি না হলে আমরা কিছু জমা রাখি না।",
        "A report is stored only with consent. Send consent: true.",
    )


def reporting_off() -> ApiError:
    return ApiError(
        503,
        "REPORTING_OFF",
        "এখন রিপোর্ট নেওয়া হচ্ছে না। ১৬১৩৫ নম্বরে ফোন করে জানান।",
        "Reporting is not enabled on this server (REPORTS_PATH is not set).",
    )


def guide_unavailable() -> ApiError:
    return ApiError(
        503,
        "GUIDE_UNAVAILABLE",
        "এখন তথ্য দেখানো যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।",
        "The guide could not be loaded. Try again later.",
    )


def not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "এটা পাওয়া যায়নি।", "Not found.")
