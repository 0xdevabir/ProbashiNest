import dataclasses
from datetime import date, timedelta

import pytest

from probashi.knowledge.agencies import names_match, normalize_licence
from probashi.knowledge.rules import HIGH, INFO, MEDIUM, check_agency, sanitize

from .conftest import REGISTER_DATE, TODAY, good_offer, make_register


def agency_flags(kb, today=TODAY, **changes):
    flags, verified = check_agency(sanitize(good_offer(**changes)), kb, today)
    return {f.code: f for f in flags}, verified


@pytest.mark.parametrize(
    "raw,expected",
    [("RL-9001", "RL9001"), ("rl 9001", "RL9001"), ("আরএল-৯০০১", "RL9001"), ("RL No. 45", "RL0045"),
     ("9001", "RL9001"), ("", None), (None, None), ("applied", None), ("RL-12/2019", None), ("123456", None)],
)
def test_normalize_licence(raw, expected):
    assert normalize_licence(raw) == expected


def test_names_match_ignores_case_and_company_suffix():
    assert names_match("synthetic active agency limited", "Synthetic Active Agency Ltd", 0.85)
    assert names_match("M/S Synthetic Active Agency Ltd.", "Synthetic Active Agency Ltd", 0.85)
    assert not names_match("Completely Different Recruiting", "Synthetic Active Agency Ltd", 0.85)
    assert not names_match(None, "Synthetic Active Agency Ltd", 0.85)


def test_active_licence_with_matching_name_is_verified(kb):
    flags, verified = agency_flags(kb)
    assert verified
    assert set(flags) == {"AGENCY_LICENSED"}
    assert flags["AGENCY_LICENSED"].severity == INFO


def test_agency_not_found(kb):
    flags, verified = agency_flags(kb, agency_license_no="RL-1234", agency_name="Unknown Synthetic Agency")
    assert not verified
    assert flags["AGENCY_NOT_FOUND"].severity == HIGH


@pytest.mark.parametrize("licence", ["RL9002", "RL9003", "RL9004"])
def test_agency_unlicensed_for_cancelled_suspended_expired(kb, licence):
    name = kb.register.get(licence).name
    flags, verified = agency_flags(kb, agency_license_no=licence, agency_name=name)
    assert not verified
    assert flags["AGENCY_UNLICENSED"].severity == HIGH


def test_agency_unlicensed_by_name_when_no_licence_given(kb):
    flags, verified = agency_flags(kb, agency_license_no=None, agency_name="Synthetic Cancelled Agency")
    assert not verified
    assert flags["AGENCY_UNLICENSED"].severity == HIGH
    assert flags["MISSING_LICENCE_NO"].severity == MEDIUM


def test_unknown_status_is_unclear_not_licensed(kb):
    flags, verified = agency_flags(kb, agency_license_no="RL9005", agency_name="Synthetic Locked Agency")
    assert not verified
    assert flags["AGENCY_STATUS_UNCLEAR"].severity == MEDIUM


def test_active_without_validity_date_is_unclear(kb):
    flags, verified = agency_flags(kb, agency_license_no="RL9007", agency_name="Synthetic Undated Agency")
    assert not verified
    assert "AGENCY_STATUS_UNCLEAR" in flags


def test_active_but_past_validity_date(kb):
    flags, verified = agency_flags(kb, agency_license_no="RL9006", agency_name="Synthetic Lapsed Agency")
    assert not verified
    assert flags["AGENCY_LICENCE_EXPIRED"].severity == MEDIUM


def test_licence_valid_until_today_still_counts(kb):
    flags, verified = agency_flags(kb, today=date(2030, 1, 1))
    assert "AGENCY_LICENCE_EXPIRED" not in flags  # (register is stale by then, checked elsewhere)


def test_name_mismatch(kb):
    flags, verified = agency_flags(kb, agency_name="Some Other Recruiters")
    assert not verified
    assert flags["AGENCY_NAME_MISMATCH"].severity == MEDIUM
    assert "AGENCY_LICENSED" not in flags


def test_licence_without_agency_name_is_not_verified(kb):
    flags, verified = agency_flags(kb, agency_name=None)
    assert not verified
    assert "AGENCY_LICENSED" not in flags


def test_wrong_number_for_a_registered_name_is_mismatch_not_accusation(kb):
    flags, verified = agency_flags(kb, agency_license_no="RL-1234")
    assert not verified
    assert flags["AGENCY_LICENCE_MISMATCH"].severity == MEDIUM
    assert "AGENCY_NOT_FOUND" not in flags


def test_missing_licence_number(kb):
    flags, verified = agency_flags(kb, agency_license_no=None)
    assert not verified
    assert flags["MISSING_LICENCE_NO"].severity == MEDIUM
    assert "AGENCY_NAME_NOT_FOUND" not in flags  # the name is in the register


def test_unreadable_licence_number_counts_as_missing(kb):
    flags, verified = agency_flags(kb, agency_license_no="pending")
    assert not verified
    assert "MISSING_LICENCE_NO" in flags


def test_missing_licence_and_unknown_name(kb):
    flags, _ = agency_flags(kb, agency_license_no=None, agency_name="Nobody Knows Manpower")
    assert flags["AGENCY_NAME_NOT_FOUND"].severity == MEDIUM


@pytest.mark.parametrize("last_checked", [None, REGISTER_DATE - timedelta(days=400), TODAY + timedelta(days=5)])
def test_stale_or_undated_register_never_verifies(kb, last_checked):
    stale = dataclasses.replace(kb, register=make_register(last_checked))
    flags, verified = agency_flags(stale)
    assert not verified
    assert flags["REGISTER_STALE"].severity == MEDIUM
    assert "AGENCY_LICENSED" not in flags
