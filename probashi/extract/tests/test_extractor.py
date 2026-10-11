"""extract_offer end to end with the LLM replaced by a fake. No API needed.

Every name and number below is synthetic.
"""
import logging

import pytest

from probashi.extract import IMPORTANT_FIELDS, extract_offer
from probashi.extract import extractor
from probashi.extract.tests.accuracy import FIXTURES
from probashi.llm import LLMError
from probashi.schemas import ExtractedOffer

RAW = (
    "OFFER OF EMPLOYMENT (SAMPLE)\n"
    "Employer: Sample Cleaning Co. (FICTIONAL)\n"
    "Full name: SAMPLE WORKER ONE\n"
    "Passport No: ZZ0000001\n"
    "Position: Cleaner\n"
    "Country: Kingdom of Saudi Arabia\n"
    "Salary: SAR 1,200 per month\n"
    "Agency: Namuna Overseas (FICTIONAL), RL-99991\n"
    "Fee: BDT 1,65,000\n"
    "Duration: Two (2) years\n"
    "Visa: Employment Visa"
)
GOOD = {
    "raw_text": RAW,
    "document_language": "en",
    "legibility": 0.9,
    "employer_name": "Sample Cleaning Co. (FICTIONAL)",
    "job_title": "Cleaner",
    "destination_country": "Kingdom of Saudi Arabia",
    "salary_as_written": "SAR 1,200 per month",
    "salary_amount": 1200,
    "salary_currency": "SAR",
    "salary_period": "month",
    "agency_name": "Namuna Overseas (FICTIONAL)",
    "agency_license_no": "RL-99991",
    "fee_as_written": "BDT 1,65,000",
    "fee_amount": 165000,
    "fee_currency": "BDT",
    "duration_as_written": "Two (2) years",
    "duration_months": 24,
    "visa_type": "Employment Visa",
    "uncertain_fields": [],
}
PHOTO = (FIXTURES / "01_en_offer_clean.png").read_bytes()
BLURRY = (FIXTURES / "09_en_offer_blurry.jpg").read_bytes()


class FakeLLM:
    """Stands in for probashi.llm.complete_json; answers are served in order."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, system, prompt, images=None, max_tokens=0):
        self.calls.append({"prompt": prompt, "images": images})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def llm(monkeypatch):
    def install(*answers):
        fake = FakeLLM(*answers)
        monkeypatch.setattr(extractor, "complete_json", fake)
        return fake

    return install


def test_happy_path_normalises_everything(llm):
    fake = llm(GOOD)
    offer = extract_offer(PHOTO, None)
    assert isinstance(offer, ExtractedOffer)
    assert offer.employer_name == "Sample Cleaning Co. (FICTIONAL)"
    assert offer.job_title == "cleaner"
    assert offer.destination_country == "SA"
    assert offer.monthly_salary.amount == 1200
    assert offer.monthly_salary.currency == "SAR"
    assert offer.agency_license_no == "RL-99991"
    assert offer.fees_charged_bdt == 165000
    assert offer.contract_duration_months == 24
    assert offer.visa_type == "work"
    assert offer.document_language == "en"
    assert offer.missing_fields == []
    assert 0.8 <= offer.confidence <= 0.95
    assert len(fake.calls) == 1
    assert fake.calls[0]["images"][0].media_type == "image/jpeg"


def test_missing_fields_lists_every_important_null(llm):
    llm({"raw_text": "something about a job abroad", "legibility": 0.8, "job_title": "driver"})
    offer = extract_offer(None, "বিদেশে ড্রাইভারের কাজ")
    assert offer.job_title == "driver"
    assert set(offer.missing_fields) == set(IMPORTANT_FIELDS) - {"job_title"}
    assert offer.confidence < 0.6


def test_salary_without_currency_counts_as_missing(llm):
    llm({**GOOD, "destination_country": None, "salary_as_written": "1200 riyal", "salary_currency": "riyal"})
    offer = extract_offer(PHOTO, None)
    assert offer.monthly_salary.amount == 1200
    assert offer.monthly_salary.currency is None  # riyal of which country?
    assert "monthly_salary" in offer.missing_fields


def test_yearly_salary_becomes_monthly(llm):
    llm({**GOOD, "salary_as_written": "SAR 14,400 per year", "salary_amount": 14400, "salary_period": "year"})
    assert extract_offer(PHOTO, None).monthly_salary.amount == 1200


def test_daily_salary_is_not_converted(llm):
    llm({**GOOD, "salary_as_written": "SAR 50 per day", "salary_amount": 50, "salary_period": "day"})
    offer = extract_offer(PHOTO, None)
    assert offer.monthly_salary.amount is None
    assert "[extract note] salary stated per day" in offer.raw_text


def test_invented_licence_number_is_dropped(llm):
    llm({**GOOD, "agency_license_no": "RL-12345"})  # not in the transcription
    offer = extract_offer(PHOTO, None)
    assert offer.agency_license_no is None
    assert "agency_license_no" in offer.missing_fields
    assert "licence number from the model was not found" in offer.raw_text


def test_fee_in_foreign_currency_is_not_reported_as_taka(llm):
    llm({**GOOD, "fee_as_written": "USD 2,000", "fee_amount": 2000, "fee_currency": "USD"})
    offer = extract_offer(PHOTO, None)
    assert offer.fees_charged_bdt is None
    assert "fees_charged_bdt" in offer.missing_fields
    assert "not converted to BDT" in offer.raw_text


def test_number_disagreement_lowers_confidence(llm):
    llm(GOOD)
    agreed = extract_offer(PHOTO, None)
    llm({**GOOD, "fee_amount": 16500})  # model's number contradicts the text as written
    disputed = extract_offer(PHOTO, None)
    assert disputed.fees_charged_bdt == 165000  # the text as written wins
    assert disputed.confidence < agreed.confidence


def test_blurry_photo_lowers_confidence(llm):
    llm(GOOD)
    sharp = extract_offer(PHOTO, None)
    llm(GOOD)
    blurry = extract_offer(BLURRY, None)
    assert blurry.confidence < sharp.confidence


def test_retries_once_when_the_answer_is_not_json(llm):
    fake = llm(LLMError("No JSON object in LLM response"), GOOD)
    offer = extract_offer(PHOTO, None)
    assert offer.destination_country == "SA"
    assert len(fake.calls) == 2
    assert "previous answer was rejected" in fake.calls[1]["prompt"]


def test_retries_once_with_the_validation_error(llm):
    fake = llm({**GOOD, "legibility": 7, "uncertain_fields": "fee"}, GOOD)
    offer = extract_offer(PHOTO, None)
    assert offer.fees_charged_bdt == 165000
    assert len(fake.calls) == 2
    retry = fake.calls[1]["prompt"]
    assert "legibility" in retry and "uncertain_fields" in retry
    assert "ZZ0000001" not in retry.split("previous answer was rejected")[1]


def test_two_bad_answers_fall_back_to_rules(llm):
    fake = llm({"legibility": "very"}, {"legibility": "very"})
    offer = extract_offer(None, "সৌদিতে ক্লিনারের কাজ, বেতন ১০০০ রিয়াল, এজেন্টকে ৫ লাখ টাকা দিতে হবে")
    assert len(fake.calls) == 2
    assert offer.destination_country == "SA"
    assert offer.fees_charged_bdt == 500000
    assert offer.confidence <= 0.5


def test_llm_outage_falls_back_to_rules_without_retry(llm):
    fake = llm(LLMError("ANTHROPIC_API_KEY is not set"))
    offer = extract_offer(None, "সৌদিতে ক্লিনারের কাজ, বেতন ১০০০ রিয়াল, এজেন্টকে ৫ লাখ টাকা দিতে হবে")
    assert len(fake.calls) == 1
    assert offer.monthly_salary.amount == 1000
    assert offer.monthly_salary.currency == "SAR"
    assert offer.job_title == "cleaner"
    assert "agency_license_no" in offer.missing_fields
    assert 0 < offer.confidence <= 0.5


def test_llm_outage_with_only_a_photo_returns_nothing(llm):
    llm(LLMError("LLM call failed: timeout"))
    offer = extract_offer(PHOTO, None)
    assert set(offer.missing_fields) == set(IMPORTANT_FIELDS)
    assert offer.confidence == 0
    assert "not read" in offer.raw_text


@pytest.mark.parametrize("image, text", [(None, None), (None, ""), (b"", "   ")])
def test_no_input_returns_nothing_and_never_calls_the_llm(llm, image, text):
    fake = llm()
    offer = extract_offer(image, text)
    assert set(offer.missing_fields) == set(IMPORTANT_FIELDS)
    assert offer.confidence == 0
    assert fake.calls == []


def test_unreadable_image_with_text_still_uses_the_text(llm):
    fake = llm({"raw_text": "", "legibility": 0.8, "destination_country": "Qatar"})
    offer = extract_offer(b"not an image", "কাতারে কাজ")
    assert offer.destination_country == "QA"
    assert fake.calls[0]["images"] is None
    assert "could not be opened" in offer.raw_text


def test_unreadable_image_alone_returns_nothing(llm):
    fake = llm()
    offer = extract_offer(b"not an image", None)
    assert offer.confidence == 0
    assert fake.calls == []


def test_photo_and_description_are_both_kept_in_raw_text(llm):
    llm(GOOD)
    offer = extract_offer(PHOTO, "এজেন্ট বলছে বেতন ভালো")
    assert "OFFER OF EMPLOYMENT" in offer.raw_text
    assert "এজেন্ট বলছে বেতন ভালো" in offer.raw_text


def test_nullish_strings_from_the_model_become_none(llm):
    llm({**GOOD, "employer_name": "N/A", "agency_name": "null", "visa_type": "  "})
    offer = extract_offer(PHOTO, None)
    assert offer.employer_name is None
    assert offer.agency_name is None
    assert offer.visa_type is None
    assert {"employer_name", "agency_name", "visa_type"} <= set(offer.missing_fields)


def test_logs_never_contain_names_or_passport_numbers(llm, caplog):
    caplog.set_level(logging.DEBUG, logger="probashi")
    llm(GOOD)
    extract_offer(PHOTO, None)
    llm(LLMError("LLM call failed: echo of Passport No: ZZ0000001"))
    extract_offer(None, "Full name: SAMPLE WORKER ONE\nPassport No: ZZ0000001\nসৌদিতে কাজ")
    assert caplog.records
    assert "ZZ0000001" not in caplog.text
    assert "SAMPLE WORKER ONE" not in caplog.text
