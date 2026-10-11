"""Masking of names and ID numbers before anything is logged. Synthetic values only."""
import pytest

from probashi.extract.privacy import mask_pii


@pytest.mark.parametrize(
    "text, secret",
    [
        ("Passport No: ZZ0000008", "ZZ0000008"),
        ("passport number A01234567 issued in Dhaka", "A01234567"),
        ("Visa No: 0000000008", "0000000008"),
        ("পাসপোর্ট নম্বর: ZZ0000007", "ZZ0000007"),
        ("ভিসা নম্বর ১২৩৪৫৬৭৮৯০", "১২৩৪৫৬৭৮৯০"),
        ("رقم الجواز: ZZ0000004", "ZZ0000004"),
        ("Full name: SAMPLE WORKER EIGHT", "SAMPLE WORKER EIGHT"),
        ("Name of worker: Sample Worker One", "Sample Worker One"),
        ("নাম: নমুনা কর্মী", "নমুনা কর্মী"),
        ("اسم العامل: عامل نموذجي", "عامل نموذجي"),
        ("call 01700000000 today", "01700000000"),
    ],
)
def test_secret_is_masked(text, secret):
    assert secret not in mask_pii(text)


def test_facts_needed_for_debugging_survive():
    text = "Salary: SAR 1,200 per month\nFee: BDT 1,65,000\nLicence: RL-99991\nDuration: 2 years"
    assert mask_pii(text) == text


def test_other_lines_are_kept():
    masked = mask_pii("Country: Qatar\nPassport No: ZZ0000005\nPosition: Driver")
    assert "Country: Qatar" in masked
    assert "Position: Driver" in masked
    assert "ZZ0000005" not in masked


def test_empty():
    assert mask_pii("") == ""
