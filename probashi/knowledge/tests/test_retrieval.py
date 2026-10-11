from probashi.knowledge.retrieval import Retriever, build_passages


def test_passages_cover_rules_and_patterns(kb):
    passages = build_passages(kb)
    ids = {p.id for p in passages}
    assert {"QA_MIN_WAGE", "SA_PASSPORT", "FP_FREE_VISA"} <= ids
    assert len(ids) == len(passages)


def test_lexical_search_finds_the_matching_passage_in_english_and_bangla(kb):
    r = Retriever(kb, backend="lexical")
    assert r.search("there is no such thing as a free visa, no guaranteed job")[0].passage.id == "FP_FREE_VISA"
    assert r.search("মালিক পাসপোর্ট আটকে রাখতে পারে না", country="KW")[0].passage.id == "KW_PASSPORT"
    assert r.search("minimum wage 1,000 riyals a month", country="QA")[0].passage.id == "QA_MIN_WAGE"


def test_search_never_returns_another_destinations_rule(kb):
    r = Retriever(kb, backend="lexical")
    hits = r.search("employer cannot keep the passport", country="OM", k=50)
    assert hits and all(h.passage.country in (None, "OM") for h in hits)
    assert all(h.passage.country is None for h in r.search("passport", country=None, k=50))


def test_same_code_passage_is_preferred(kb):
    r = Retriever(kb, backend="lexical")
    assert r.search("warning", code="FREE_VISA")[0].passage.code == "FREE_VISA"


def test_unknown_backend_falls_back_to_lexical(kb):
    assert Retriever(kb, backend="does-not-exist").backend == "lexical"
