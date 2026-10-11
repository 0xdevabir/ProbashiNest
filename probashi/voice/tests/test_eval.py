import pytest

from probashi.voice.eval import find_clips, normalize, wer


def test_wer_perfect_and_punctuation_insensitive():
    assert wer("আমি সৌদি আরব যাব।", "আমি সৌদি আরব যাব") == 0.0


def test_wer_counts_substitution_deletion_insertion():
    assert wer("আমি সৌদি আরব যাব", "আমি দুবাই আরব যাব") == pytest.approx(0.25)
    assert wer("আমি সৌদি আরব যাব", "আমি সৌদি যাব") == pytest.approx(0.25)
    assert wer("আমি যাব", "আমি আজ যাব") == pytest.approx(0.5)


def test_normalize_keeps_vowel_signs_and_unifies_digits():
    assert normalize("টাকা, ৫০০!") == ["টাকা", "500"]


def test_empty_reference_is_an_error():
    with pytest.raises(ValueError):
        wer("।", "কিছু")


def test_find_clips_pairs_audio_with_txt(tmp_path):
    (tmp_path / "sylheti").mkdir()
    (tmp_path / "sylheti" / "a.ogg").write_bytes(b"x")
    (tmp_path / "sylheti" / "a.txt").write_text("ক", encoding="utf-8")
    (tmp_path / "sylheti" / "no_ref.ogg").write_bytes(b"x")
    assert [a.name for a, _ in find_clips(tmp_path)] == ["a.ogg"]
