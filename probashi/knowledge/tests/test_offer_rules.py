import pytest

from probashi.knowledge.rules import (
    HIGH, MEDIUM, check_fee, check_key_facts, check_salary, check_text_patterns, check_visa, find_keyword, sanitize,
)

from .conftest import good_offer, with_rule


def codes(flags):
    return {f.code: f for f in flags}


# ----------------------------------------------------------------------------- fee

def test_zero_fee_passes(kb):
    assert check_fee(sanitize(good_offer(destination_country="SA", fees_charged_bdt=0)), kb) == []


def test_fee_above_unverified_ceiling_is_medium(kb):
    flags = check_fee(sanitize(good_offer(destination_country="SA", fees_charged_bdt=300000)), kb)
    assert [(f.code, f.severity) for f in flags] == [("FEE_ABOVE_LIMIT", MEDIUM)]
    assert "not yet verified" in flags[0].source.title


def test_fee_grossly_above_ceiling_is_high(kb):
    flags = check_fee(sanitize(good_offer(destination_country="SA", fees_charged_bdt=165000 * 3)), kb)
    assert [(f.code, f.severity) for f in flags] == [("FEE_ABOVE_LIMIT", HIGH)]


def test_fee_above_verified_ceiling_is_high(kb):
    verified = with_rule(kb, "SA", "SA_BD_COST_CEILING", verified=True)
    flags = check_fee(sanitize(good_offer(destination_country="SA", fees_charged_bdt=170000)), verified)
    assert [(f.code, f.severity) for f in flags] == [("FEE_ABOVE_LIMIT", HIGH)]


def test_fee_within_unverified_ceiling_is_not_a_pass(kb):
    flags = check_fee(sanitize(good_offer(destination_country="SA", fees_charged_bdt=100000)), kb)
    assert [(f.code, f.severity) for f in flags] == [("FEE_LIMIT_UNVERIFIED", MEDIUM)]


def test_fee_within_verified_ceiling_passes(kb):
    verified = with_rule(kb, "SA", "SA_BD_COST_CEILING", verified=True)
    assert check_fee(sanitize(good_offer(destination_country="SA", fees_charged_bdt=165000)), verified) == []


def test_fee_not_checkable_without_a_ceiling(kb):
    flags = check_fee(sanitize(good_offer(destination_country="QA", fees_charged_bdt=50000)), kb)
    assert [(f.code, f.severity) for f in flags] == [("FEE_NOT_CHECKABLE", MEDIUM)]


# ----------------------------------------------------------------------------- salary

def test_salary_below_verified_minimum_is_high(kb):
    flags = check_salary(sanitize(good_offer(monthly_salary={"amount": 999, "currency": "QAR"})), kb)
    assert [(f.code, f.severity) for f in flags] == [("SALARY_BELOW_MINIMUM", HIGH)]
    assert flags[0].source.url.startswith("https://www.ilo.org/")


def test_salary_below_unverified_minimum_is_only_medium(kb):
    unverified = with_rule(kb, "QA", "QA_MIN_WAGE", verified=False)
    flags = check_salary(sanitize(good_offer(monthly_salary={"amount": 999, "currency": "QAR"})), unverified)
    assert [(f.code, f.severity) for f in flags] == [("SALARY_BELOW_MINIMUM", MEDIUM)]


def test_salary_at_minimum_passes(kb):
    assert check_salary(sanitize(good_offer(monthly_salary={"amount": 1000, "currency": "QAR"})), kb) == []


@pytest.mark.parametrize("currency", ["BDT", "USD", None])
def test_salary_in_another_currency_is_not_comparable(kb, currency):
    flags = check_salary(sanitize(good_offer(monthly_salary={"amount": 40000, "currency": currency})), kb)
    assert [(f.code, f.severity) for f in flags] == [("SALARY_NOT_COMPARABLE", MEDIUM)]


def test_no_minimum_wage_means_no_salary_flag(kb):
    offer = good_offer(destination_country="SA", monthly_salary={"amount": 300, "currency": "SAR"})
    assert check_salary(sanitize(offer), kb) == []


def test_malaysia_minimum_wage_skips_domestic_jobs(kb):
    maid = good_offer(destination_country="MY", job_title="Housemaid", monthly_salary={"amount": 1200, "currency": "MYR"})
    worker = good_offer(destination_country="MY", job_title="Factory worker", monthly_salary={"amount": 1200, "currency": "MYR"})
    assert check_salary(sanitize(maid), kb) == []
    assert codes(check_salary(sanitize(worker), kb))["SALARY_BELOW_MINIMUM"].severity == HIGH


def test_salary_unrealistic_for_low_skilled_job(kb):
    flags = check_salary(sanitize(good_offer(job_title="Cleaner", monthly_salary={"amount": 4001, "currency": "QAR"})), kb)
    assert [(f.code, f.severity) for f in flags] == [("SALARY_UNREALISTIC", MEDIUM)]


def test_high_salary_for_skilled_job_is_not_flagged(kb):
    offer = good_offer(job_title="Civil engineer", monthly_salary={"amount": 9000, "currency": "QAR"})
    assert check_salary(sanitize(offer), kb) == []


# ----------------------------------------------------------------------------- visa

@pytest.mark.parametrize("visa", ["Tourist visa", "visit visa", "VISITOR", "Umrah visa", "Student visa", "ভিজিট ভিসা", "ট্যুরিস্ট ভিসা", "ওমরাহ ভিসা"])
def test_non_work_visa_is_high(kb, visa):
    flags = check_visa(sanitize(good_offer(visa_type=visa)), kb)
    assert [(f.code, f.severity) for f in flags] == [("VISA_JOB_MISMATCH", HIGH)]


@pytest.mark.parametrize("change", [{"visa_type": "Free visa"}, {"visa_type": "ফ্রি ভিসা"}, {"raw_text": "দালাল বলছে ফ্রি ভিসা আছে"}])
def test_free_visa_is_high(kb, change):
    flags = check_visa(sanitize(good_offer(**change)), kb)
    assert [(f.code, f.severity) for f in flags] == [("FREE_VISA", HIGH)]


def test_domestic_visa_for_other_job_is_medium(kb):
    flags = check_visa(sanitize(good_offer(visa_type="Domestic worker visa", job_title="Electrician")), kb)
    assert [(f.code, f.severity) for f in flags] == [("VISA_JOB_MISMATCH", MEDIUM)]
    assert check_visa(sanitize(good_offer(visa_type="Domestic worker visa", job_title="Housemaid")), kb) == []


@pytest.mark.parametrize("visa", ["Work visa", "Employment visa", "কাজের ভিসা", "সহজ ভিসা"])
def test_work_visa_passes(kb, visa):
    assert check_visa(sanitize(good_offer(visa_type=visa)), kb) == []


def test_keyword_needs_a_word_start_for_latin_words():
    assert find_keyword("IT supporter", ["porter"]) is None
    assert find_keyword("Porter", ["porter"]) == "porter"
    assert find_keyword("labourer", ["labour"]) == "labour"


# ----------------------------------------------------------------------------- key facts, text

def test_missing_employer(kb):
    flags = codes(check_key_facts(sanitize(good_offer(employer_name="  ")), kb))
    assert flags["MISSING_EMPLOYER"].severity == MEDIUM


@pytest.mark.parametrize(
    "change,field",
    [({"job_title": None}, "job_title"), ({"destination_country": None}, "destination_country"),
     ({"monthly_salary": {}}, "monthly_salary"), ({"monthly_salary": {"amount": 0, "currency": "QAR"}}, "monthly_salary"),
     ({"agency_name": None}, "agency_name"), ({"fees_charged_bdt": None}, "fees_charged_bdt"),
     ({"fees_charged_bdt": -5}, "fees_charged_bdt"), ({"contract_duration_months": None}, "contract_duration_months"),
     ({"visa_type": ""}, "visa_type"), ({"missing_fields": ["visa_type"]}, "visa_type")],
)
def test_missing_key_fact(kb, change, field):
    flags = codes(check_key_facts(sanitize(good_offer(**change)), kb))
    assert flags["MISSING_KEY_FACTS"].severity == MEDIUM
    assert flags["MISSING_KEY_FACTS"].params["fields"] == [field]


def test_complete_offer_has_no_key_fact_flags(kb):
    assert check_key_facts(sanitize(good_offer()), kb) == []


def test_unsupported_destination(kb):
    flags = codes(check_key_facts(sanitize(good_offer(destination_country="sg")), kb))
    assert flags["UNSUPPORTED_DESTINATION"].severity == MEDIUM


def test_low_confidence(kb):
    assert codes(check_key_facts(sanitize(good_offer(confidence=0.49)), kb))["LOW_CONFIDENCE"].severity == MEDIUM
    assert check_key_facts(sanitize(good_offer(confidence=0.5)), kb) == []


@pytest.mark.parametrize(
    "text,code",
    [("আজকেই টাকা দিতে হবে", "PRESSURE_TO_PAY"), ("You must pay today or lose the seat", "PRESSURE_TO_PAY"),
     ("তার পার্সোনাল বিকাশ নম্বরে পাঠান", "PERSONAL_ACCOUNT_PAYMENT"), ("send to my personal account", "PERSONAL_ACCOUNT_PAYMENT")],
)
def test_text_patterns(kb, text, code):
    flags = check_text_patterns(sanitize(good_offer(raw_text=text)), kb)
    assert [(f.code, f.severity) for f in flags] == [(code, MEDIUM)]


def test_plain_text_raises_no_pattern(kb):
    assert check_text_patterns(sanitize(good_offer(raw_text="Employment contract for cleaner, 24 months.")), kb) == []
