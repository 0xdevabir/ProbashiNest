"""Passport and visa numbers must never reach the logs.

All numbers below are synthetic.
"""
import logging

import pytest

from backend.logging_utils import MASK, mask_sensitive
from probashi.schemas import ExtractedOffer

PASSPORT = "BX0123456"
VISA = "6012345678"
BANGLA_VISA = "৬০১২৩৪৫৬৭৮"
SECRETS = (PASSPORT, VISA, BANGLA_VISA, "V-48213")


@pytest.mark.parametrize(
    "text",
    [
        f"Passport No: {PASSPORT}",
        f"holder {PASSPORT} travels",
        f"visa number {VISA}",
        f"Visa: V-48213",
        f"পাসপোর্ট নম্বর {PASSPORT}",
        f"ভিসা নং {BANGLA_VISA}",
        f"ref {VISA}",
    ],
)
def test_numbers_are_masked(text):
    masked = mask_sensitive(text)
    assert MASK in masked
    assert not any(secret in masked for secret in SECRETS)


@pytest.mark.parametrize(
    "text",
    ["fees 450000 BDT", "visa type: employment", "salary 1200 SAR for 24 months", "check_completed"],
)
def test_ordinary_text_is_left_alone(text):
    assert mask_sensitive(text) == text


def test_message_extras_and_tracebacks_are_masked(log_lines):
    log = logging.getLogger("probashi.test")
    log.info("got passport %s", PASSPORT, extra={"note": f"visa {VISA}", "items": [PASSPORT]})
    try:
        raise ValueError(f"cannot parse visa no {BANGLA_VISA}")
    except ValueError:
        log.exception("failed")

    first, second = log_lines()
    assert first["note"] == f"visa {MASK}" and first["items"] == [MASK]
    assert "ValueError" in second["exc"]
    assert not any(secret in log_lines.raw() for secret in SECRETS)


def test_api_logs_never_contain_document_numbers(make_client, log_lines):
    """Numbers in the user's text, and in another module's exception, stay out of logs."""
    text = f"আমার পাসপোর্ট {PASSPORT}, ভিসা নম্বর {VISA}"

    ok = make_client().post("/api/check", data={"text": text})
    assert ok.status_code == 200

    def leaky_extract(image_bytes, text):
        raise ValueError(f"could not parse: {text}")

    failed = make_client(extract_offer=leaky_extract).post("/api/check", data={"text": text})
    assert failed.status_code == 502

    messages = [line["msg"] for line in log_lines()]
    assert "check_completed" in messages and "stage_failed" in messages
    assert not any(secret in log_lines.raw() for secret in SECRETS)
    assert "আমার পাসপোর্ট" in log_lines.raw()  # the traceback was logged, only numbers were masked
    assert MASK in log_lines.raw()


def test_check_completed_log_is_structured_and_has_no_document_text(make_client, log_lines):
    def extract(image_bytes, text):
        return ExtractedOffer(raw_text=text, employer_name="SYNTHETIC Employer", missing_fields=["visa_type"])

    make_client(extract_offer=extract).post("/api/check", data={"text": "গোপন চুক্তির লেখা"})
    (done,) = [line for line in log_lines() if line["msg"] == "check_completed"]
    assert done["verdict_level"] == "amber"
    assert done["missing_fields"] == ["visa_type"]
    assert done["has_text"] is True and done["has_image"] is False
    assert "গোপন চুক্তির লেখা" not in log_lines.raw()
    assert "SYNTHETIC Employer" not in log_lines.raw()
