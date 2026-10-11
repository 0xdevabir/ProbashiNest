import unicodedata

import pytest

from probashi.voice.text_prep import (
    expand_numbers,
    int_to_bn,
    number_to_bn,
    prepare_tts_text,
    spell_digits,
    truncate_for_speech,
)


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


@pytest.mark.parametrize(
    "n, expected",
    [
        (0, "শূন্য"),
        (7, "সাত"),
        (19, "উনিশ"),
        (45, "পঁয়তাল্লিশ"),
        (99, "নিরানব্বই"),
        (100, "একশ"),
        (250, "দুইশ পঞ্চাশ"),
        (1500, "এক হাজার পাঁচশ"),
        (25000, "পঁচিশ হাজার"),
        (500000, "পাঁচ লাখ"),
        (1250000, "বারো লাখ পঞ্চাশ হাজার"),
        (10000000, "এক কোটি"),
        (1234567890, "একশ তেইশ কোটি পঁয়তাল্লিশ লাখ সাতষট্টি হাজার আটশ নব্বই"),
    ],
)
def test_int_to_bn(n, expected):
    assert int_to_bn(n) == nfc(expected)


def test_number_to_bn_decimals_commas_and_bangla_digits():
    assert number_to_bn("3.5") == nfc("তিন দশমিক পাঁচ")
    assert number_to_bn("1500.00") == nfc("এক হাজার পাঁচশ")
    assert number_to_bn("5,00,000") == nfc("পাঁচ লাখ")
    assert number_to_bn("৫০০") == nfc("পাঁচশ")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("500000 BDT", "পাঁচ লাখ টাকা"),
        ("BDT 500000", "পাঁচ লাখ টাকা"),
        ("৳500", "পাঁচশ টাকা"),
        ("5,00,000 Tk", "পাঁচ লাখ টাকা"),
        ("SAR", "সৌদি রিয়াল"),
        ("1500 SAR", "এক হাজার পাঁচশ সৌদি রিয়াল"),
        ("RM 1500", "এক হাজার পাঁচশ মালয়েশিয়ান রিঙ্গিত"),
        ("বেতন 1200 AED, ফি BDT 450000", "বেতন এক হাজার দুইশ আমিরাতি দিরহাম, ফি চার লাখ পঞ্চাশ হাজার টাকা"),
        ("৫০০০ টাকা", "পাঁচ হাজার টাকা"),
        ("10%", "দশ শতাংশ"),
        ("2 বছর", "দুই বছর"),
    ],
)
def test_expand_currency_and_numbers(text, expected):
    assert expand_numbers(text) == nfc(expected)


def test_currency_code_inside_a_word_is_left_alone():
    assert expand_numbers("USDA SARKAR") == "USDA SARKAR"


def test_phone_and_licence_numbers_are_read_digit_by_digit():
    # Synthetic numbers, not real ones.
    assert expand_numbers("01700000000") == spell_digits("01700000000")
    assert expand_numbers("+8801700000000").startswith(nfc("প্লাস আট আট শূন্য"))
    assert expand_numbers("RL-0123") == nfc("RL শূন্য এক দুই তিন")
    assert spell_digits("16135") == nfc("এক ছয় এক তিন পাঁচ")


def test_no_ascii_or_bangla_digits_survive():
    out = prepare_tts_text("ফি ৪,৫০,০০০ টাকা, বেতন 1500 SAR, মেয়াদ 24 মাস, ফোন 01700000000")
    assert not any(ch.isdigit() for ch in out)


def test_truncate_keeps_whole_sentences():
    text = "প্রথম বাক্য। দ্বিতীয় বাক্য। তৃতীয় বাক্য।"
    out = truncate_for_speech(text, max_chars=30)
    assert out == "প্রথম বাক্য। দ্বিতীয় বাক্য।"
    assert truncate_for_speech(text, max_chars=1000) == text


def test_truncate_single_long_sentence_cuts_at_word_boundary():
    out = truncate_for_speech("শব্দ " * 100, max_chars=50)
    assert len(out) <= 51 and out.endswith("।")


def test_prepare_strips_markdown_and_respects_default_limit(monkeypatch):
    monkeypatch.delenv("VOICE_TTS_MAX_CHARS", raising=False)
    assert prepare_tts_text("**সাবধান!** এই অফার ঝুঁকিপূর্ণ।") == nfc("সাবধান! এই অফার ঝুঁকিপূর্ণ।")
    long = "এটি একটি ছোট বাক্য। " * 200
    assert len(prepare_tts_text(long)) <= 45 * 12
