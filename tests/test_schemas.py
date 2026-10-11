"""Guards the shared contract so an accidental change is caught early."""
import pytest
from pydantic import ValidationError

from probashi.schemas import (
    CheckResponse,
    ExtractedOffer,
    Level,
    Money,
    Reason,
    Source,
    Verdict,
)


def _verdict(level: Level = Level.amber) -> Verdict:
    return Verdict(
        level=level,
        reasons=[
            Reason(
                code="MISSING_LICENCE_NO",
                message_bn="এজেন্সির লাইসেন্স নম্বর পাওয়া যায়নি।",
                message_en="Agency licence number not found.",
                source=Source(title="Example source"),
            )
        ],
        next_steps_bn=["এজেন্টের কাছে লাইসেন্স নম্বর চান।"],
        disclaimer_bn="এটি পরামর্শ, আইনি মতামত নয়।",
    )


def test_offer_defaults_are_empty():
    offer = ExtractedOffer()
    assert offer.monthly_salary == Money()
    assert offer.missing_fields == []
    assert offer.confidence == 0.0


def test_confidence_must_be_between_0_and_1():
    with pytest.raises(ValidationError):
        ExtractedOffer(confidence=1.5)


def test_level_values_are_fixed():
    assert {lvl.value for lvl in Level} == {"red", "amber", "green"}


def test_check_response_round_trips_through_json():
    resp = CheckResponse(
        offer=ExtractedOffer(destination_country="SA", fees_charged_bdt=500000),
        verdict=_verdict(Level.red),
    )
    again = CheckResponse.model_validate_json(resp.model_dump_json())
    assert again == resp
    assert again.verdict.level is Level.red
