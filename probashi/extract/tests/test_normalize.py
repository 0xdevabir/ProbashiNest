"""Normalisation: digits, amounts, countries, currencies, durations. No API needed."""
import pytest

from probashi.extract.normalize import (
    normalize_country,
    normalize_currency,
    normalize_license,
    normalize_visa_type,
    parse_amount,
    parse_duration_months,
    to_ascii_digits,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("১০০০", "1000"),
        ("০১২৩৪৫৬৭৮৯", "0123456789"),
        ("١٥٠٠", "1500"),  # Arabic-Indic
        ("۱۵۰۰", "1500"),  # Persian
        ("RL-৯৯৯৯১", "RL-99991"),
    ],
)
def test_to_ascii_digits(raw, expected):
    assert to_ascii_digits(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("5 lakh", 500_000),
        ("৫ লাখ", 500_000),
        ("৫ লাখ টাকা", 500_000),
        ("পাঁচ লক্ষ", 500_000),
        ("5 lac", 500_000),
        ("1.5 lakh", 150_000),
        ("দেড় লাখ", 150_000),
        ("আড়াই লাখ", 250_000),
        ("সাড়ে চার লাখ", 450_000),
        ("সোয়া দুই লাখ", 225_000),
        ("পৌনে তিন লাখ", 275_000),
        ("৩ লাখ ৫০ হাজার", 350_000),
        ("Taka 3 lakh 80 thousand", 380_000),
        ("১ কোটি", 10_000_000),
        ("পনেরোশ", 1500),
        ("বারোশো রিয়াল", 1200),
        ("দুই হাজার পাঁচশ", 2500),
        ("1,65,000", 165_000),  # South Asian digit grouping
        ("BDT 1,65,000/-", 165_000),
        ("SAR 1,200.00", 1200),
        ("50k", 50_000),
        ("fifty thousand", 50_000),
        ("১০০০", 1000),
        (1200, 1200),
        (1200.5, 1200.5),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", [None, "", "   ", "অনেক টাকা", "n/a", "লাখ"])
def test_parse_amount_refuses_to_guess(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Saudi Arabia", "SA"),
        ("Kingdom of Saudi Arabia", "SA"),
        ("KSA", "SA"),
        ("সৌদি", "SA"),
        ("সৌদি আরব", "SA"),
        ("المملكة العربية السعودية", "SA"),
        ("UAE", "AE"),
        ("Dubai", "AE"),
        ("দুবাই", "AE"),
        ("الإمارات العربية المتحدة", "AE"),
        ("Malaysia", "MY"),
        ("মালয়েশিয়া", "MY"),
        ("Qatar", "QA"),
        ("কাতার", "QA"),
        ("Kuwait", "KW"),
        ("Oman", "OM"),
        ("Bahrain", "BH"),
        ("Jordan", "JO"),
        ("Singapore", "SG"),
        ("sa", "SA"),  # already a code
    ],
)
def test_normalize_country(raw, expected):
    assert normalize_country(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "বিদেশ", "abroad", "Middle East", "Atlantis"])
def test_normalize_country_unknown_is_none(raw):
    assert normalize_country(raw) is None


def test_normalize_country_two_countries_is_ambiguous():
    assert normalize_country("Saudi Arabia or Qatar") is None


@pytest.mark.parametrize(
    "raw, country, expected",
    [
        ("SAR", None, "SAR"),
        ("Saudi Riyal", None, "SAR"),
        ("ريال سعودي", None, "SAR"),
        ("RM", None, "MYR"),
        ("ringgit", None, "MYR"),
        ("রিঙ্গিত", None, "MYR"),
        ("AED", None, "AED"),
        ("Dhs", None, "AED"),
        ("QR", None, "QAR"),
        ("Omani Rial", None, "OMR"),
        ("কুয়েতি দিনার", None, "KWD"),
        ("taka", None, "BDT"),
        ("টাকা", None, "BDT"),
        ("Tk.", None, "BDT"),
        ("USD", None, "USD"),
        # A bare "riyal" or "dinar" means different money in different countries.
        ("riyal", "SA", "SAR"),
        ("রিয়াল", "QA", "QAR"),
        ("রিয়াল", "OM", "OMR"),
        ("dinar", "KW", "KWD"),
        ("dinar", "BH", "BHD"),
        ("dinar", "JO", "JOD"),
        ("দিরহাম", "AE", "AED"),
        ("BD", "BH", "BHD"),
    ],
)
def test_normalize_currency(raw, country, expected):
    assert normalize_currency(raw, country) == expected


@pytest.mark.parametrize(
    "raw, country",
    [("riyal", None), ("রিয়াল", None), ("dinar", None), ("riyal", "MY"), ("", "SA"), (None, "SA"), ("gold", "SA")],
)
def test_normalize_currency_does_not_guess(raw, country):
    assert normalize_currency(raw, country) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2 years", 24),
        ("Two (2) years", 24),
        ("Three (3) years", 36),
        ("24 months", 24),
        ("২ বছর", 24),
        ("দুই বছর", 24),
        ("তিন বছরের চুক্তি", 36),
        ("৬ মাস", 6),
        ("দেড় বছর", 18),
        ("1 year 6 months", 18),
        ("2 bochor", 24),
        ("سنتان", 24),
        ("٣ سنوات", 36),
        (24, 24),
    ],
)
def test_parse_duration_months(raw, expected):
    assert parse_duration_months(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "long term", "years", "বছর"])
def test_parse_duration_months_refuses_to_guess(raw):
    assert parse_duration_months(raw) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("RL-99991", "RL-99991"),
        ("RL 99991", "RL-99991"),
        ("rl no. 99992", "RL-99992"),
        ("R.L. No: 99991", "RL-99991"),
        ("আরএল-৯৯৯৯৪", "RL-99994"),
        ("আরএল ৯৯৯৯১", "RL-99991"),
        ("99991", "99991"),  # no prefix is added that the source did not have
    ],
)
def test_normalize_license(raw, expected):
    assert normalize_license(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "RL", "pending", "__________"])
def test_normalize_license_without_digits_is_none(raw):
    assert normalize_license(raw) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Employment Visa", "work"),
        ("work visa", "work"),
        ("কাজের ভিসা", "work"),
        ("تأشيرة عمل", "work"),
        ("Visit Pass (Temporary Employment)", "work"),
        ("VISIT", "visit"),
        ("ভিজিট ভিসা", "visit"),
        ("زيارة", "visit"),
        ("tourist visa", "tourist"),
        ("free visa", "free"),
        ("ফ্রি ভিসা", "free"),
        ("Umrah", "umrah"),
        ("student visa", "student"),
        # When a risky type is mixed with "work", the risky one is reported.
        ("visit visa, work visa later", "visit"),
    ],
)
def test_normalize_visa_type(raw, expected):
    assert normalize_visa_type(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "visa", "ভিসা"])
def test_normalize_visa_type_unknown_is_none(raw):
    assert normalize_visa_type(raw) is None
