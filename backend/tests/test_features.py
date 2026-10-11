"""Guidance, several documents, low-data replies, rate limit, stats, reports and the guide."""
import dataclasses
import json

import pytest

from backend.config import STUBBABLE, Settings
from backend.pipeline import format_verdict_text
from backend.ratelimit import RateLimiter, client_key
from backend.stats import STATS
from backend.tests.conftest import JPG, PDF, PNG
from probashi.knowledge import evaluate as real_evaluate
from probashi.knowledge.guidance import guidance as real_guidance
from probashi.knowledge.guidance import guide as real_guide
from probashi.schemas import ExtractedOffer, Level, Money

ALL_STUBS = frozenset(STUBBABLE)


def _settings(**changes) -> Settings:
    return dataclasses.replace(Settings(stubs=ALL_STUBS), **changes)


def _offer(**changes) -> ExtractedOffer:
    """SYNTHETIC offer used as fake extractor output."""
    data = dict(
        employer_name="SYNTHETIC Employer Co", job_title="Cleaner", destination_country="QA",
        monthly_salary=Money(amount=1300, currency="QAR"), agency_name="SYNTHETIC Agency",
        agency_license_no=None, fees_charged_bdt=0, contract_duration_months=24, visa_type="Work visa",
        raw_text="", missing_fields=["agency_license_no"], confidence=0.9,
    )
    data.update(changes)
    return ExtractedOffer(**data)


def _boom(*args, **kwargs):
    raise RuntimeError("guidance is down")


# --- guidance ---------------------------------------------------------------

def test_check_returns_guidance_next_to_the_shared_contract(client):
    body = client.post("/api/check", data={"text": "চাকরির প্রস্তাব"}).json()
    assert {"offer", "verdict", "transcript_bn", "audio_base64"} <= set(body)
    assert body["guidance"]["follow_up"][0]["key"] == "agency_license_no"


def test_guidance_failure_never_blocks_the_verdict(make_client):
    resp = make_client(guidance=_boom).post("/api/check", data={"text": "চাকরির প্রস্তাব"})
    assert resp.status_code == 200
    assert resp.json()["guidance"] is None and resp.json()["verdict"]["level"] == "amber"


def test_real_knowledge_guidance_explains_and_asks(make_client):
    client = make_client(extract_offer=lambda image, text: _offer(visa_type="Tourist visa"),
                         evaluate=real_evaluate, guidance=real_guidance)
    body = client.post("/api/check", data={"text": "offer"}).json()
    assert body["verdict"]["level"] == "red"
    guidance = body["guidance"]
    assert guidance["follow_up"][0]["key"] == "agency_license_no"
    assert guidance["ask_agent"] and guidance["complaint_draft_bn"].startswith("অভিযোগ")
    assert all(e["last_checked"] for e in guidance["explainers"])


# --- several documents --------------------------------------------------------

def _by_document(offers: dict):
    return lambda image, text: offers[image]


def test_second_document_fills_a_gap(make_client):
    client = make_client(extract_offer=_by_document({
        JPG: _offer(visa_type=None, missing_fields=["agency_license_no", "visa_type"]), PNG: _offer()}))
    body = client.post("/api/check", files=[("image", ("a.jpg", JPG, "image/jpeg")),
                                            ("more_images", ("b.png", PNG, "image/png"))]).json()
    assert body["offer"]["visa_type"] == "Work visa"
    assert body["offer"]["missing_fields"] == ["agency_license_no"]


def test_documents_that_disagree_can_never_be_green(make_client):
    green = lambda offer: real_evaluate(offer).model_copy(update={"level": Level.green})  # noqa: E731
    client = make_client(evaluate=green, extract_offer=_by_document({
        JPG: _offer(), PNG: _offer(monthly_salary=Money(amount=800, currency="QAR"))}))
    one = client.post("/api/check", files={"image": ("a.jpg", JPG, "image/jpeg")}).json()
    assert one["verdict"]["level"] == "green"
    two = client.post("/api/check", files=[("image", ("a.jpg", JPG, "image/jpeg")),
                                           ("more_images", ("b.png", PNG, "image/png"))]).json()
    assert two["verdict"]["level"] == "amber"
    assert two["verdict"]["reasons"][0]["code"] == "DOCUMENT_MISMATCH"


def test_more_images_alone_is_accepted_and_bad_or_extra_files_are_refused(client):
    assert client.post("/api/check", files={"more_images": ("b.png", PNG, "image/png")}).status_code == 200
    bad = client.post("/api/check", files=[("image", ("a.jpg", JPG, "image/jpeg")),
                                           ("more_images", ("x.txt", b"hello", "text/plain"))])
    assert bad.status_code == 415 and bad.json()["detail"]["code"] == "UNSUPPORTED_IMAGE"
    many = client.post("/api/check", files=[("image", ("a.jpg", JPG, "image/jpeg"))]
                       + [("more_images", (f"{i}.pdf", PDF, "application/pdf")) for i in range(3)])
    assert many.status_code == 422 and many.json()["detail"]["code"] == "TOO_MANY_IMAGES"


# --- low-data reply -------------------------------------------------------------

def test_voice_off_skips_speech_synthesis(make_client):
    calls = []
    client = make_client(synthesize_bn=lambda text: calls.append(text) or b"mp3")
    assert client.post("/api/check?voice=false", data={"text": "offer"}).json()["audio_base64"] is None
    assert calls == []
    assert client.post("/api/check", data={"text": "offer"}).json()["audio_base64"]
    assert len(calls) == 1


def test_text_answer_has_level_reasons_steps_and_questions(client):
    from backend.models import CheckResult

    result = CheckResult(**client.post("/api/check?voice=false", data={"text": "offer"}).json())
    text = format_verdict_text(result)
    assert text.startswith("🟡") and result.verdict.reasons[0].message_bn in text
    assert result.verdict.next_steps_bn[0] in text and result.guidance.follow_up[0].text_bn in text


# --- rate limit -------------------------------------------------------------------

def test_rate_limit_answers_429_in_bangla_and_leaves_reads_alone(make_client):
    client = make_client(_settings(rate_limit_per_minute=2))
    assert [client.post("/api/check", data={"text": "x"}).status_code for _ in range(3)] == [200, 200, 429]
    blocked = client.post("/api/check", data={"text": "x"})
    assert blocked.json()["detail"]["code"] == "RATE_LIMITED"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60
    assert client.get("/health").status_code == 200
    assert make_client(_settings(rate_limit_per_minute=0)).post("/api/check", data={"text": "x"}).status_code == 200


def test_rate_limiter_window_and_per_client_counts():
    now = [0.0]
    limiter = RateLimiter(2, clock=lambda: now[0])
    assert [limiter.check("a"), limiter.check("a")] == [0, 0]
    assert limiter.check("a") == 60 and limiter.check("b") == 0
    now[0] = 59.5
    assert limiter.check("a") == 1
    now[0] = 60.0
    assert limiter.check("a") == 0


def test_forwarded_address_is_believed_only_behind_our_proxy():
    scope = {"client": ("10.0.0.1", 1234), "headers": [(b"x-forwarded-for", b"6.6.6.6, 203.0.113.9")]}
    assert client_key(scope, trust_proxy=False) == "10.0.0.1"
    assert client_key(scope, trust_proxy=True) == "203.0.113.9"  # the entry our proxy added
    assert client_key({"headers": []}, trust_proxy=True) == "unknown"


# --- stats ------------------------------------------------------------------------

def test_stats_count_checks_without_any_content(make_client):
    client = make_client(extract_offer=lambda image, text: _offer(destination_country="not a code 01712345678"))
    client.post("/api/check", data={"text": "passport A01234567"})
    client.post("/api/check", data={"text": "again"})
    stats = client.get("/api/stats").json()
    assert stats["checks"] == 2 and stats["by_level"] == {"red": 0, "amber": 2, "green": 0}
    assert stats["by_channel"] == {"web": 2} and stats["by_country"] == {}
    assert stats["top_reasons"][0] == {"code": "STUB_NOT_VERIFIED", "count": 2}
    assert "A01234567" not in json.dumps(stats) and "01712345678" not in json.dumps(stats)


# --- reports ----------------------------------------------------------------------

REPORT = {"consent": True, "level": "red", "reason_codes": ["FREE_VISA"], "destination_country": "sa",
          "agency_name": "SYNTHETIC Agency 01712345678", "agency_license_no": "RL-9001"}


def test_report_is_stored_only_with_consent_and_holds_no_personal_data(make_client, tmp_path):
    path = tmp_path / "reports.jsonl"
    client = make_client(_settings(reports_path=str(path)))
    refused = client.post("/api/report", json={**REPORT, "consent": False})
    assert refused.status_code == 422 and refused.json()["detail"]["code"] == "CONSENT_REQUIRED"
    assert not path.exists()

    assert client.post("/api/report", json=REPORT).status_code == 201
    (record,) = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert set(record) == {"date", "level", "reason_codes", "destination_country", "agency_name",
                           "agency_license_no"}
    assert record["destination_country"] == "SA" and record["agency_license_no"] == "RL-9001"
    assert "01712345678" not in record["agency_name"] and len(record["date"]) == 10
    assert client.get("/api/stats").json()["reports"] == 1


def test_report_is_refused_when_reporting_is_off_or_the_body_is_wrong(make_client, client, tmp_path):
    off = client.post("/api/report", json=REPORT)
    assert off.status_code == 503 and off.json()["detail"]["code"] == "REPORTING_OFF"
    on = make_client(_settings(reports_path=str(tmp_path / "r.jsonl")))
    for bad in ({**REPORT, "raw_text": "the whole letter"}, {**REPORT, "reason_codes": ["drop table"]},
                {**REPORT, "destination_country": "Saudi"}, {**REPORT, "agency_name": "x" * 121}):
        assert on.post("/api/report", json=bad).json()["detail"]["code"] == "INVALID_REQUEST"
    assert not (tmp_path / "r.jsonl").exists()


# --- guide ------------------------------------------------------------------------

def test_guide_with_real_knowledge_has_sourced_rights_and_checklist(make_client):
    page = make_client(guide=real_guide).get("/api/guide/sa").json()
    assert page["country"] == "SA" and page["rights"] and page["checklist"] and page["payment_tips_bn"]
    assert all(item["last_checked"] for item in page["rights"] + page["checklist"])
    assert all(item["verified"] is False for item in page["checklist"])  # secondary source only
    assert any(h["phone"] == "16135" for h in page["helplines"])


def test_guide_stub_invents_nothing_and_bad_codes_are_refused(client, make_client):
    assert client.get("/api/guide/SA").json() == {
        "country": "SA", "country_name_bn": None, "rights": [], "checklist": [], "payment_tips_bn": [],
        "helplines": []}
    assert client.get("/api/guide/saudi").json()["detail"]["code"] == "INVALID_REQUEST"
    down = make_client(guide=_boom).get("/api/guide/SA")
    assert down.status_code == 503 and down.json()["detail"]["code"] == "GUIDE_UNAVAILABLE"
