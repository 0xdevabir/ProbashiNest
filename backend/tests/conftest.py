import dataclasses
import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from backend.config import STUBBABLE, Settings
from backend.deps import build_modules
from backend.logging_utils import JsonFormatter
from backend.main import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"\x00" * 64

STUB_SETTINGS = Settings(stubs=frozenset(STUBBABLE))


@pytest.fixture
def stub_modules():
    return build_modules(frozenset(STUBBABLE))


@pytest.fixture
def make_client():
    """Build a client on the stub pipeline, with selected functions replaced."""

    def _make(settings: Settings = STUB_SETTINGS, **overrides) -> TestClient:
        modules = dataclasses.replace(build_modules(frozenset(STUBBABLE)), **overrides)
        return TestClient(create_app(settings, modules))

    return _make


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def log_lines():
    """Capture everything logged, formatted exactly as in production."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.addHandler(handler)

    def _lines() -> list[dict]:
        return [json.loads(line) for line in stream.getvalue().splitlines()]

    _lines.raw = stream.getvalue
    yield _lines
    root.removeHandler(handler)
