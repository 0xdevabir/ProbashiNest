"""Checks on the real files in data/: every record is sourced or marked unverified,
and the evaluation set never rates a fraud case green."""

import json
from datetime import date

import pytest

from probashi.knowledge import eval as kb_eval
from probashi.knowledge.kb import KnowledgeBaseError, data_dir, load_kb, source_of
from probashi.knowledge.refresh_agencies import parse_register

COUNTRIES = {"SA", "AE", "MY", "QA", "OM", "KW"}


def all_records(kb):
    for doc in kb.rules.values():
        yield from doc["records"]
    yield from kb.patterns
    yield from kb.helplines


def test_all_six_destinations_have_rules():
    assert set(load_kb().rules) == COUNTRIES


def test_every_record_is_sourced_or_marked_unverified():
    for rec in all_records(load_kb()):
        assert isinstance(rec["verified"], bool) and isinstance(rec["last_checked"], date), rec["id"]
        if rec["verified"]:
            assert rec["source"]["title"] and rec["source"]["url"].startswith("http"), rec["id"]


def test_every_helpline_shown_to_users_has_an_official_source():
    for rec in load_kb().helplines:
        assert rec["verified"] and ".gov.bd" in rec["source"]["url"], rec["id"]


def test_unverified_source_is_labelled():
    kb = load_kb()
    ceiling = kb.rule("SA", "bd_migration_cost_ceiling")
    assert not ceiling["verified"] and "not yet verified" in source_of(ceiling).title
    assert "not yet verified" not in source_of(kb.rule("QA", "minimum_wage")).title


def test_agency_register_copy_is_loaded_with_source_and_date():
    reg = load_kb().register
    assert len(reg.by_licence) > 1000
    assert reg.source_url.startswith("https://raims.oep.gov.bd")
    assert isinstance(reg.last_checked, date)


def test_malformed_knowledge_base_is_rejected(tmp_path):
    with pytest.raises(KnowledgeBaseError):
        load_kb(tmp_path)


def _register_html(rows: int) -> str:
    body = "".join(
        f"<tr><td></td><td>RL{i:04d}</td><td> Synthetic &amp; Co {i} </td><td>Addr, Dhaka</td><td>+880</td>"
        f"<td>{'Active' if i % 2 else 'Cancelled'}</td><td>{'01/Mar/2027' if i % 3 else ''}</td></tr>"
        for i in range(rows)
    )
    return f"<table><thead><tr><th>#</th></tr></thead><tbody>{body}</tbody></table>"


def test_register_importer_copies_rows_without_guessing():
    rows = parse_register(_register_html(1200), date(2026, 10, 11))
    assert len(rows) == 1200
    assert rows[1] == {
        "licence_no": "RL0001", "name": "Synthetic & Co 1", "status": "Active", "valid_until": "2027-03-01",
        "address": "Addr, Dhaka", "source_url": "https://raims.oep.gov.bd/agencies", "last_checked": "2026-10-11",
    }
    assert rows[0]["valid_until"] == ""  # unknown date stays empty
    assert "phone" not in rows[0]


def test_register_importer_rejects_a_page_that_is_not_the_register():
    with pytest.raises(ValueError):
        parse_register("<html><body>Sign in</body></html>", date(2026, 10, 11))
    with pytest.raises(ValueError):
        parse_register(_register_html(20), date(2026, 10, 11))


# ----------------------------------------------------------------------------- evaluation set

def test_evaluation_set_is_big_enough_and_labelled():
    cases = kb_eval.load_cases(data_dir() / "test_cases")
    assert len(cases) >= 20
    for case in cases:
        assert isinstance(case["synthetic"], bool) and case["note"]
        if not case["synthetic"]:
            assert case["source_url"].startswith("http"), case["id"]
    assert {c["expected_level"] for c in cases} == {"red", "amber", "green"}


def test_no_fraud_case_is_rated_green():
    report = kb_eval.run(kb_eval.load_cases(data_dir() / "test_cases"))
    assert report["fraud_total"] >= 10
    assert report["fraud_green"] == 0
    assert report["correct"] / report["total"] >= 0.9


def test_eval_cli_prints_the_two_headline_numbers(capsys):
    assert kb_eval.main([]) == 0
    out = capsys.readouterr().out
    assert "accuracy:" in out and "fraud cases rated green: 0" in out


def test_case_files_are_valid_offers():
    from probashi.schemas import ExtractedOffer

    for path in sorted((data_dir() / "test_cases").glob("*.json")):
        ExtractedOffer(**json.loads(path.read_text(encoding="utf-8"))["offer"])
