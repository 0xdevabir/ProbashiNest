"""Tiny stdlib HTTP helper so the voice module needs no extra packages."""
from __future__ import annotations

import socket
import urllib.error
import urllib.request
import uuid

from .errors import ProviderError

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def encode_multipart(
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> tuple[bytes, str]:
    """Return (body, content_type). files maps name -> (filename, data, mime)."""
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    for name, (filename, data, mime) in files.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode()
            + data
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def post(
    url: str,
    *,
    headers: dict[str, str],
    body: bytes,
    timeout: float,
    provider: str,
) -> bytes:
    """POST and return the response body. Raises ProviderError on any failure.

    The error message never includes the request body or headers, so keys,
    audio and transcripts cannot leak into logs.
    """
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read(300).decode("utf-8", "replace")
        raise ProviderError(
            f"{provider} returned HTTP {e.code}: {detail}",
            provider=provider,
            status=e.code,
            retryable=e.code in _RETRYABLE_STATUS,
        ) from e
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        raise ProviderError(
            f"{provider} request failed: {e}", provider=provider, retryable=True
        ) from e
