"""Shared, swappable LLM wrapper used by the extract and knowledge modules.

Provider and model come from environment variables:
    LLM_PROVIDER  (default "anthropic")
    LLM_MODEL     (default "claude-sonnet-5-5")
    ANTHROPIC_API_KEY  (when LLM_PROVIDER=anthropic)

Owners of other modules should call these functions rather than an SDK
directly, so the provider can be changed in one place. To add a provider,
add a branch in `_client_call`.
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Optional


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns unusable output."""


@dataclass
class ImageInput:
    data: bytes
    media_type: str  # e.g. "image/jpeg", "image/png"


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "anthropic").lower()


def _model() -> str:
    return os.getenv("LLM_MODEL", "claude-sonnet-5-5")


def _client_call(
    system: str,
    prompt: str,
    images: Optional[list[ImageInput]] = None,
    max_tokens: int = 2000,
) -> str:
    provider = _provider()
    if provider == "anthropic":
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise LLMError("Install the 'anthropic' package") from e
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY is not set")
        content: list[dict] = []
        for img in images or []:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.media_type,
                        "data": base64.b64encode(img.data).decode(),
                    },
                }
            )
        content.append({"type": "text", "text": prompt})
        client = anthropic.Anthropic()
        try:
            resp = client.messages.create(
                model=_model(),
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as e:  # network, auth, rate limit
            raise LLMError(f"LLM call failed: {e}") from e
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    raise LLMError(f"Unknown LLM_PROVIDER: {provider}")


def complete_text(
    system: str,
    prompt: str,
    images: Optional[list[ImageInput]] = None,
    max_tokens: int = 2000,
) -> str:
    """Return the model's plain-text answer."""
    return _client_call(system, prompt, images, max_tokens)


def complete_json(
    system: str,
    prompt: str,
    images: Optional[list[ImageInput]] = None,
    max_tokens: int = 2000,
) -> dict:
    """Return the model's answer parsed as a JSON object.

    The prompt should describe the exact JSON shape wanted. Code fences
    around the JSON are tolerated. Raises LLMError if no valid JSON object
    comes back; callers decide whether to retry.
    """
    text = _client_call(
        system + "\nRespond with a single JSON object only, no other text.",
        prompt,
        images,
        max_tokens,
    ).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("No JSON object in LLM response")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"Invalid JSON from LLM: {e}") from e
