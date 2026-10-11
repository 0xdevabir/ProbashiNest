"""Prepare text for Bangla text-to-speech.

TTS engines read "500000 BDT" badly or in English. This module turns
numbers and currency codes into spoken Bangla words and trims the text to
roughly 45 seconds of audio.
"""
from __future__ import annotations

import os
import re
import unicodedata


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# 0-99 are irregular in Bangla, so they are listed in full.
_UNITS = [_nfc(w) for w in (
    "শূন্য এক দুই তিন চার পাঁচ ছয় সাত আট নয় "
    "দশ এগারো বারো তেরো চৌদ্দ পনেরো ষোলো সতেরো আঠারো উনিশ "
    "বিশ একুশ বাইশ তেইশ চব্বিশ পঁচিশ ছাব্বিশ সাতাশ আটাশ ঊনত্রিশ "
    "ত্রিশ একত্রিশ বত্রিশ তেত্রিশ চৌত্রিশ পঁয়ত্রিশ ছত্রিশ সাঁইত্রিশ আটত্রিশ ঊনচল্লিশ "
    "চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চুয়াল্লিশ পঁয়তাল্লিশ ছেচল্লিশ সাতচল্লিশ আটচল্লিশ ঊনপঞ্চাশ "
    "পঞ্চাশ একান্ন বায়ান্ন তিপ্পান্ন চুয়ান্ন পঞ্চান্ন ছাপ্পান্ন সাতান্ন আটান্ন ঊনষাট "
    "ষাট একষট্টি বাষট্টি তেষট্টি চৌষট্টি পঁয়ষট্টি ছেষট্টি সাতষট্টি আটষট্টি ঊনসত্তর "
    "সত্তর একাত্তর বাহাত্তর তিয়াত্তর চুয়াত্তর পঁচাত্তর ছিয়াত্তর সাতাত্তর আটাত্তর ঊনআশি "
    "আশি একাশি বিরাশি তিরাশি চুরাশি পঁচাশি ছিয়াশি সাতাশি আটাশি ঊননব্বই "
    "নব্বই একানব্বই বিরানব্বই তিরানব্বই চুরানব্বই পঁচানব্বই ছিয়ানব্বই সাতানব্বই আটানব্বই নিরানব্বই"
).split()]
assert len(_UNITS) == 100

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# ISO 4217 code -> spoken Bangla name.
CURRENCY_NAMES = {
    "BDT": "টাকা",
    "SAR": "সৌদি রিয়াল",
    "AED": "আমিরাতি দিরহাম",
    "QAR": "কাতারি রিয়াল",
    "KWD": "কুয়েতি দিনার",
    "OMR": "ওমানি রিয়াল",
    "BHD": "বাহরাইনি দিনার",
    "MYR": "মালয়েশিয়ান রিঙ্গিত",
    "SGD": "সিঙ্গাপুর ডলার",
    "USD": "মার্কিন ডলার",
}
CURRENCY_NAMES = {k: _nfc(v) for k, v in CURRENCY_NAMES.items()}
_CURRENCY_ALIASES = {"TK": "BDT", "TK.": "BDT", "৳": "BDT", "RM": "MYR", "$": "USD"}

_NUM = r"\d+(?:\.\d+)?"
_CUR = r"(?:BDT|SAR|AED|QAR|KWD|OMR|BHD|MYR|SGD|USD|Tk\.?|TK|RM|৳|\$)"
_NUM_THEN_CUR = re.compile(rf"({_NUM})\s*({_CUR})(?![A-Za-z])")
_CUR_THEN_NUM = re.compile(rf"(?<![A-Za-z])({_CUR})\s*({_NUM})")
_BARE_CUR = re.compile(r"(?<![A-Za-z])(BDT|SAR|AED|QAR|KWD|OMR|BHD|MYR|SGD|USD)(?![A-Za-z])|৳")
_PERCENT = re.compile(rf"({_NUM})\s*%")
# Phone-like: starts with + or 0, or is a very long digit run (passport, ID).
_PHONE = re.compile(r"(?<![\d.\w])(\+\d[\d-]{6,}\d|0\d[\d-]{2,}\d|\d{9,})(?![\d.]*\d)")
# Codes such as licence numbers: "RL-1234", "A1234567".
_CODE = re.compile(r"\b([A-Za-z]{1,6})([-/]?)(\d{2,})\b")
_NUMBER = re.compile(_NUM)
_SENTENCE_END = re.compile(r"(?<=[।!?\n])\s*")

MAX_SPEECH_SECONDS = 45
# ASSUMPTION, not measured: slow, clear Bangla speech is about 12 characters
# per second. Calibrate with real provider output and set VOICE_TTS_MAX_CHARS.
_CHARS_PER_SECOND = 12


def max_tts_chars() -> int:
    return int(os.getenv("VOICE_TTS_MAX_CHARS", MAX_SPEECH_SECONDS * _CHARS_PER_SECOND))


def int_to_bn(n: int) -> str:
    """500000 -> 'পাঁচ লাখ' (Bangladeshi lakh/crore grouping)."""
    if n < 0:
        return "মাইনাস " + int_to_bn(-n)
    if n < 100:
        return _UNITS[n]
    parts = []
    crore, n = divmod(n, 10_000_000)
    if crore:
        parts.append(int_to_bn(crore) + " কোটি")
    lakh, n = divmod(n, 100_000)
    if lakh:
        parts.append(_UNITS[lakh] + " লাখ")
    thousand, n = divmod(n, 1000)
    if thousand:
        parts.append(_UNITS[thousand] + " হাজার")
    hundred, n = divmod(n, 100)
    if hundred:
        parts.append(_UNITS[hundred] + "শ")
    if n:
        parts.append(_UNITS[n])
    return " ".join(parts)


def spell_digits(s: str) -> str:
    """Read digit by digit, for phone and licence numbers: '16135' -> 'এক ছয় এক তিন পাঁচ'."""
    out = []
    for ch in s.translate(_BN_DIGITS):
        if ch.isdigit():
            out.append(_UNITS[int(ch)])
        elif ch == "+":
            out.append("প্লাস")
    return " ".join(out)


def number_to_bn(s: str) -> str:
    """'1500.50' -> 'এক হাজার পাঁচশ দশমিক পাঁচ'. Accepts Bangla digits and commas."""
    s = s.translate(_BN_DIGITS).replace(",", "")
    whole, _, frac = s.partition(".")
    words = int_to_bn(int(whole or "0"))
    frac = frac.rstrip("0")
    if frac:
        words += " দশমিক " + spell_digits(frac)
    return words


def _currency_name(token: str) -> str:
    code = token.upper()
    return CURRENCY_NAMES[_CURRENCY_ALIASES.get(code, code)]


def expand_numbers(text: str) -> str:
    """Replace numbers, currency codes and percentages with Bangla words."""
    text = _nfc(text).translate(_BN_DIGITS)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = _NUM_THEN_CUR.sub(
        lambda m: f"{number_to_bn(m.group(1))} {_currency_name(m.group(2))}", text
    )
    text = _CUR_THEN_NUM.sub(
        lambda m: f"{number_to_bn(m.group(2))} {_currency_name(m.group(1))}", text
    )
    text = _BARE_CUR.sub(lambda m: _currency_name(m.group(0)), text)
    text = _PERCENT.sub(lambda m: f"{number_to_bn(m.group(1))} শতাংশ", text)
    text = _PHONE.sub(lambda m: spell_digits(m.group(1)), text)
    text = _CODE.sub(lambda m: f"{m.group(1)} {spell_digits(m.group(3))}", text)
    text = _NUMBER.sub(lambda m: number_to_bn(m.group(0)), text)
    return text


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def truncate_for_speech(text: str, max_chars: int | None = None) -> str:
    """Keep whole sentences up to max_chars (about 45 seconds of audio)."""
    max_chars = max_chars or max_tts_chars()
    if len(text) <= max_chars:
        return text
    kept: list[str] = []
    total = 0
    for sentence in split_sentences(text):
        if total + len(sentence) + 1 > max_chars:
            break
        kept.append(sentence)
        total += len(sentence) + 1
    if kept:
        return " ".join(kept)
    # A single very long sentence: cut at the last word boundary.
    cut = text[:max_chars].rsplit(None, 1)[0]
    return cut.rstrip(",;:- ") + "।"


def prepare_tts_text(text: str, max_chars: int | None = None) -> str:
    """Full pipeline: expand numbers, strip markup, trim to the length limit."""
    text = expand_numbers(text)
    text = re.sub(r"[*_#`]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text).strip()
    return _nfc(truncate_for_speech(text, max_chars))
