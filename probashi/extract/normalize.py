"""Deterministic normalisation helpers for extracted offer facts.

No LLM and no network here, so everything in this file is unit-testable.

Sources for the code tables:
- Country codes: ISO 3166-1 alpha-2, https://www.iso.org/obp/ui/#search/code/
- Currency codes: ISO 4217, https://www.iso.org/iso-4217-currency-codes.html

Nothing here converts between currencies: that would need an exchange rate,
and we never invent numbers.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, Union

# --------------------------------------------------------------------------
# Text and digits
# --------------------------------------------------------------------------

_DIGIT_MAP = str.maketrans(
    "০১২৩৪৫৬৭৮৯" "٠١٢٣٤٥٦٧٨٩" "۰۱۲۳۴۵۶۷۸۹" "٬٫",
    "0123456789" "0123456789" "0123456789" ",.",
)


def _nfc(s: str) -> str:
    # NFC gives one canonical form for Bangla letters such as য় and ড়,
    # which can be typed either precomposed or as base letter + nukta.
    return unicodedata.normalize("NFC", s)


def to_ascii_digits(s: str) -> str:
    """Convert Bangla, Arabic-Indic and Persian digits to 0-9."""
    return s.translate(_DIGIT_MAP)


def clean_text(s: str) -> str:
    """Canonical form used for all matching: NFC, ASCII digits, lower case,
    no thousands separators, single spaces (newlines are kept)."""
    s = to_ascii_digits(_nfc(s)).lower()
    s = re.sub(r"(?<=\d),(?=\d)", "", s)
    s = re.sub(r"[^\S\n]+", " ", s)
    return s.strip()


# --------------------------------------------------------------------------
# Numbers: digits, Bangla number words, lakh / hazar / crore
# --------------------------------------------------------------------------

_BN_NUMBER_WORDS = {
    "শূন্য": 0, "এক": 1, "দুই": 2, "তিন": 3, "চার": 4, "পাঁচ": 5, "ছয়": 6,
    "সাত": 7, "আট": 8, "নয়": 9, "দশ": 10, "এগারো": 11, "এগার": 11,
    "বারো": 12, "তেরো": 13, "তের": 13, "চৌদ্দ": 14, "পনেরো": 15,
    "পনের": 15, "ষোলো": 16, "ষোল": 16, "সতেরো": 17, "সতের": 17,
    "আঠারো": 18, "আঠার": 18, "ঊনিশ": 19, "বিশ": 20, "কুড়ি": 20,
    "একুশ": 21, "বাইশ": 22, "তেইশ": 23, "চব্বিশ": 24, "পঁচিশ": 25,
    "ছাব্বিশ": 26, "সাতাশ": 27, "আঠাশ": 28, "ঊনত্রিশ": 29, "ত্রিশ": 30,
    "তিরিশ": 30, "একত্রিশ": 31, "বত্রিশ": 32, "তেত্রিশ": 33, "চৌত্রিশ": 34,
    "পঁয়ত্রিশ": 35, "ছত্রিশ": 36, "সাঁইত্রিশ": 37, "আটত্রিশ": 38,
    "ঊনচল্লিশ": 39, "চল্লিশ": 40, "একচল্লিশ": 41, "বিয়াল্লিশ": 42,
    "তেতাল্লিশ": 43, "চুয়াল্লিশ": 44, "পঁয়তাল্লিশ": 45, "ছেচল্লিশ": 46,
    "সাতচল্লিশ": 47, "আটচল্লিশ": 48, "ঊনপঞ্চাশ": 49, "পঞ্চাশ": 50,
    "একান্ন": 51, "বায়ান্ন": 52, "তিপ্পান্ন": 53, "চুয়ান্ন": 54,
    "পঞ্চান্ন": 55, "ছাপ্পান্ন": 56, "সাতান্ন": 57, "আটান্ন": 58,
    "ঊনষাট": 59, "ষাট": 60, "একষট্টি": 61, "বাষট্টি": 62, "তেষট্টি": 63,
    "চৌষট্টি": 64, "পঁয়ষট্টি": 65, "ছেষট্টি": 66, "সাতষট্টি": 67,
    "আটষট্টি": 68, "ঊনসত্তর": 69, "সত্তর": 70, "একাত্তর": 71,
    "বাহাত্তর": 72, "তিয়াত্তর": 73, "চুয়াত্তর": 74, "পঁচাত্তর": 75,
    "ছিয়াত্তর": 76, "সাতাত্তর": 77, "আটাত্তর": 78, "ঊনআশি": 79, "আশি": 80,
    "একাশি": 81, "বিরাশি": 82, "তিরাশি": 83, "চুরাশি": 84, "পঁচাশি": 85,
    "ছিয়াশি": 86, "সাতাশি": 87, "আটাশি": 88, "ঊননব্বই": 89, "নব্বই": 90,
    "একানব্বই": 91, "বিরানব্বই": 92, "তিরানব্বই": 93, "চুরানব্বই": 94,
    "পঁচানব্বই": 95, "ছিয়ানব্বই": 96, "সাতানব্বই": 97, "আটানব্বই": 98,
    "নিরানব্বই": 99,
}
_EN_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}

_NUMBER_WORDS: dict[str, int] = dict(_EN_NUMBER_WORDS)
for _word, _value in _BN_NUMBER_WORDS.items():
    _NUMBER_WORDS[_nfc(_word)] = _value
    if _word.startswith("ঊন"):  # the short-vowel spelling is just as common
        _NUMBER_WORDS[_nfc("উন" + _word[2:])] = _value
_NUMBER_WORDS[_nfc("দু")] = 2  # only as in "দুশ" / "দু লাখ"

_UNITS = {
    "হাজার": 1e3, "thousand": 1e3, "hazar": 1e3, "hajar": 1e3, "k": 1e3,
    "ألف": 1e3, "الف": 1e3, "آلاف": 1e3,
    "লাখ": 1e5, "লক্ষ": 1e5, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5,
    "lacs": 1e5, "lak": 1e5, "lokkho": 1e5,
    "million": 1e6,
    "কোটি": 1e7, "crore": 1e7, "crores": 1e7, "koti": 1e7,
}
_HUNDREDS = {"শ", "শো", "শত", "hundred"}
# "সাড়ে তিন" = 3.5, "সোয়া তিন" = 3.25, "পৌনে তিন" = 2.75
_FRACTION_MODIFIERS = {_nfc("সাড়ে"): 0.5, _nfc("সোয়া"): 0.25, _nfc("পৌনে"): -0.25}
_FRACTION_VALUES = {_nfc("দেড়"): 1.5, _nfc("আড়াই"): 2.5}
_BN_SUFFIXES = ("ের", "টা", "টি", "ে")

# Explicit script ranges: Python's \w does not match Bangla vowel signs.
BN = "%c-%c" % (0x0980, 0x09FF)  # Bengali block
AR = "%c-%c" % (0x0600, 0x06FF)  # Arabic block

_TOKEN_RE = re.compile(
    rf"\d+(?:\.\d+)?|[a-z]+|[{BN}]+|[{AR}]+|[,;।!?\n$]"
)
# "." and ":" are not clause breaks: "Tk. 5000", "বেতন: ১০০০ রিয়াল".
_BREAKS = ",;।!?\n"


@dataclass
class Token:
    text: str
    kind: str  # num | word | frac | mod | hundred | unit | other | break
    value: float = 0.0

    @property
    def is_numeric(self) -> bool:
        return self.kind in ("num", "word", "frac", "mod", "hundred", "unit")


def _classify(text: str) -> Token:
    if text[0].isdigit():
        return Token(text, "num", float(text))
    if text in _BREAKS:
        return Token(text, "break")
    candidates = [text] + [text[: -len(s)] for s in _BN_SUFFIXES if text.endswith(s)]
    for cand in candidates:
        if cand in _NUMBER_WORDS:
            return Token(text, "word", float(_NUMBER_WORDS[cand]))
        if cand in _UNITS:
            return Token(text, "unit", _UNITS[cand])
        if cand in _HUNDREDS:
            return Token(text, "hundred", 100.0)
        if cand in _FRACTION_VALUES:
            return Token(text, "frac", _FRACTION_VALUES[cand])
        if cand in _FRACTION_MODIFIERS:
            return Token(text, "mod", _FRACTION_MODIFIERS[cand])
        for suffix in ("শো", "শত", "শ"):  # "পাঁচশ" = 500, "পনেরোশ" = 1500
            stem = cand[: -len(suffix)]
            if cand.endswith(suffix) and stem in _NUMBER_WORDS:
                return Token(text, "word", _NUMBER_WORDS[stem] * 100.0)
    return Token(text, "other")


def tokenize(cleaned: str) -> list[Token]:
    """Split text that has already been through `clean_text`."""
    return [_classify(t) for t in _TOKEN_RE.findall(cleaned)]


def amount_from_tokens(tokens: list[Token]) -> Optional[float]:
    """Combine number tokens into one amount, or None if there is no single
    clear amount (no number at all, or two separate numbers such as a range)."""
    total = 0.0
    current: Optional[float] = None
    modifier = 0.0
    open_tens = False  # "twenty" waiting for "five"
    seen = False
    for tok in tokens:
        if tok.kind in ("num", "word", "frac"):
            if current is not None:
                if open_tens and tok.kind == "word" and 1 <= tok.value <= 9:
                    current += tok.value
                    open_tens = False
                    continue
                if tok.value == current:  # "Three (3) years"
                    continue
                return None
            current = tok.value + modifier
            modifier = 0.0
            open_tens = tok.kind == "word" and tok.value in range(20, 100, 10)
            seen = True
        elif tok.kind == "mod":
            modifier = tok.value
        elif tok.kind == "hundred":
            if current is not None:
                current *= 100
                open_tens = False
        elif tok.kind == "unit":
            if current is not None:
                total += current * tok.value
                current = None
                open_tens = False
    if not seen:
        return None
    return total + (current or 0.0)


def parse_amount(value: Union[str, int, float, None]) -> Optional[float]:
    """Parse an amount as written: "৫ লাখ", "SR 1,500/-", "সাড়ে তিন লাখ",
    "3 lakh 50 thousand", "পনেরোশ". Returns None when unclear."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value >= 0 else None
    return amount_from_tokens(tokenize(clean_text(value)))


# --------------------------------------------------------------------------
# Countries
# --------------------------------------------------------------------------

_COUNTRIES: dict[str, tuple[str, ...]] = {
    "SA": ("saudi arabia", "saudi", "ksa", "kingdom of saudi arabia", "soudi",
           "riyadh", "jeddah", "dammam", "makkah", "madinah",
           "সৌদি আরব", "সৌদি", "সউদি", "রিয়াদ", "জেদ্দা", "দাম্মাম",
           "المملكة العربية السعودية", "السعودية"),
    "AE": ("united arab emirates", "uae", "u.a.e", "emirates", "dubai",
           "abu dhabi", "sharjah", "ajman",
           "সংযুক্ত আরব আমিরাত", "আমিরাত", "দুবাই", "আবুধাবি", "আবু ধাবি", "শারজাহ",
           "الإمارات العربية المتحدة", "الإمارات", "الامارات", "دبي", "أبوظبي"),
    "QA": ("qatar", "doha", "কাতার", "দোহা", "قطر", "الدوحة"),
    "KW": ("kuwait", "কুয়েত", "الكويت"),
    "OM": ("oman", "sultanate of oman", "muscat", "ওমান", "মাস্কাট",
           "سلطنة عمان", "عُمان", "مسقط"),
    "BH": ("bahrain", "manama", "বাহরাইন", "বাহরাইন", "البحرين"),
    "MY": ("malaysia", "kuala lumpur", "johor", "মালয়েশিয়া", "মালেশিয়া",
           "কুয়ালালামপুর", "ماليزيا"),
    "SG": ("singapore", "সিঙ্গাপুর", "سنغافورة"),
    "JO": ("jordan", "জর্ডান", "الأردن", "الاردن"),
    "LB": ("lebanon", "লেবানন", "لبنان"),
    "IQ": ("iraq", "ইরাক", "العراق"),
    "LY": ("libya", "লিবিয়া", "ليبيا"),
    "MV": ("maldives", "মালদ্বীপ"),
    "MU": ("mauritius", "মরিশাস"),
    "BN": ("brunei", "brunei darussalam", "ব্রুনাই"),
    "KR": ("south korea", "korea", "republic of korea", "দক্ষিণ কোরিয়া", "কোরিয়া"),
    "JP": ("japan", "জাপান"),
    "IT": ("italy", "ইতালি", "ইটালি"),
    "RO": ("romania", "রোমানিয়া"),
    "PL": ("poland", "পোল্যান্ড"),
    "HR": ("croatia", "ক্রোয়েশিয়া"),
    "RS": ("serbia", "সার্বিয়া"),
    "GR": ("greece", "গ্রিস"),
    "PT": ("portugal", "পর্তুগাল"),
    "ES": ("spain", "স্পেন"),
    "DE": ("germany", "জার্মানি"),
    "FR": ("france", "ফ্রান্স"),
    "MT": ("malta", "মাল্টা"),
    "CY": ("cyprus", "সাইপ্রাস"),
    "HU": ("hungary", "হাঙ্গেরি"),
    "GB": ("united kingdom", "uk", "u.k", "england", "britain", "যুক্তরাজ্য", "ইংল্যান্ড"),
    "US": ("united states", "usa", "u.s.a", "america", "যুক্তরাষ্ট্র", "আমেরিকা"),
    "CA": ("canada", "কানাডা"),
    "AU": ("australia", "অস্ট্রেলিয়া"),
    "RU": ("russia", "রাশিয়া"),
    "TR": ("turkey", "turkiye", "তুরস্ক"),
    "EG": ("egypt", "মিশর", "مصر"),
    "CN": ("china", "চীন"),
    "HK": ("hong kong", "হংকং"),
    "TH": ("thailand", "থাইল্যান্ড"),
    "IN": ("india", "ভারত"),
    "LK": ("sri lanka", "শ্রীলঙ্কা"),
    "NP": ("nepal", "নেপাল"),
    "PK": ("pakistan", "পাকিস্তান"),
    "KH": ("cambodia", "কম্বোডিয়া"),
    "FJ": ("fiji", "ফিজি"),
    "SC": ("seychelles", "সেশেলস"),
    "BD": ("bangladesh", "dhaka", "বাংলাদেশ", "ঢাকা", "بنغلاديش"),
}
_COUNTRY_BY_ALIAS = {
    clean_text(alias): code for code, aliases in _COUNTRIES.items() for alias in aliases
}


def _alias_pattern(alias: str) -> str:
    if alias[0].isascii():
        return r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])"
    # Bangla and Arabic take suffixes and prefixes ("সৌদিতে", "بالسعودية"),
    # so only require that the alias starts a Bangla word.
    return rf"(?<![{BN}])" + re.escape(alias)


_COUNTRY_RE = re.compile(
    "|".join(_alias_pattern(a) for a in sorted(_COUNTRY_BY_ALIAS, key=len, reverse=True))
)


def find_countries(text: str) -> list[str]:
    """All country codes mentioned in free text, in order of first mention."""
    found: list[str] = []
    for m in _COUNTRY_RE.finditer(clean_text(text)):
        code = _COUNTRY_BY_ALIAS[m.group(0)]
        if code not in found:
            found.append(code)
    return found


def normalize_country(value: Optional[str]) -> Optional[str]:
    """Country name, city or code -> ISO 3166-1 alpha-2, or None if unknown
    or ambiguous."""
    if not value:
        return None
    raw = value.strip()
    if raw.upper() in _COUNTRIES and len(raw) == 2:
        return raw.upper()
    cleaned = clean_text(raw).strip(" .")
    if cleaned in _COUNTRY_BY_ALIAS:
        return _COUNTRY_BY_ALIAS[cleaned]
    found = find_countries(cleaned)
    if len(found) > 1 and "BD" in found:  # "Dhaka to Riyadh"
        found.remove("BD")
    return found[0] if len(found) == 1 else None


# --------------------------------------------------------------------------
# Currencies
# --------------------------------------------------------------------------

_CURRENCY_CODES = {
    "SAR", "AED", "QAR", "KWD", "OMR", "BHD", "MYR", "SGD", "JOD", "LBP",
    "IQD", "LYD", "MVR", "MUR", "BND", "KRW", "JPY", "EUR", "RON", "PLN",
    "GBP", "USD", "CAD", "AUD", "RUB", "TRY", "EGP", "CNY", "HKD", "THB",
    "INR", "LKR", "NPR", "PKR", "BDT", "RSD", "HUF", "YER", "MAD",
}
_CURRENCY_ALIASES = {
    "SAR": ("saudi riyal", "saudi riyals", "sr", "s.r", "সৌদি রিয়াল", "ريال سعودي", "ر.س"),
    "QAR": ("qatari riyal", "qatari riyals", "qatari rial", "qr", "q.r",
            "কাতারি রিয়াল", "ريال قطري", "ر.ق"),
    "OMR": ("omani rial", "omani rials", "omani riyal", "ওমানি রিয়াল", "ريال عماني", "ر.ع"),
    "AED": ("uae dirham", "emirati dirham", "dhs", "درهم إماراتي", "د.إ"),
    "KWD": ("kuwaiti dinar", "kuwaiti dinars", "kd", "k.d", "কুয়েতি দিনার", "دينار كويتي", "د.ك"),
    "BHD": ("bahraini dinar", "bahraini dinars", "বাহরাইনি দিনার", "دينار بحريني", "د.ب"),
    "JOD": ("jordanian dinar", "jordanian dinars", "jd", "دينار أردني"),
    "MYR": ("ringgit", "ringgits", "malaysian ringgit", "rm", "রিঙ্গিত", "রিংগিত"),
    "SGD": ("singapore dollar", "singapore dollars", "sgd", "s$", "সিঙ্গাপুর ডলার"),
    "USD": ("us dollar", "us dollars", "u.s. dollar", "u.s. dollars", "us$",
            "american dollar", "মার্কিন ডলার", "ইউএস ডলার", "دولار أمريكي"),
    "EUR": ("euro", "euros", "€", "ইউরো", "يورو"),
    "BDT": ("taka", "tk", "tk.", "টাকা", "৳", "تاكا"),
    "KRW": ("won", "ওন"),
    "JPY": ("yen", "ইয়েন"),
    "RON": ("lei", "leu"),
    "MVR": ("rufiyaa", "রুফিয়া"),
}
_CURRENCY_BY_ALIAS = {
    clean_text(alias): code for code, aliases in _CURRENCY_ALIASES.items() for alias in aliases
}
_CURRENCY_BY_ALIAS.update({code.lower(): code for code in _CURRENCY_CODES})

# Words that name several currencies. They resolve only with the country.
# The second item is used when the country is known but not in the map.
_GENERIC_CURRENCIES: dict[str, tuple[dict[str, str], Optional[str]]] = {
    "riyal": ({"SA": "SAR", "QA": "QAR", "OM": "OMR", "YE": "YER"}, None),
    "dinar": ({"KW": "KWD", "BH": "BHD", "JO": "JOD", "IQ": "IQD", "LY": "LYD",
               "RS": "RSD"}, None),
    "dirham": ({"AE": "AED", "MA": "MAD"}, None),
    "dollar": ({"SG": "SGD", "BN": "BND", "AU": "AUD", "CA": "CAD", "HK": "HKD",
                "FJ": "FJD"}, "USD"),
    "pound": ({"GB": "GBP", "EG": "EGP", "LB": "LBP"}, None),
    "rupee": ({"IN": "INR", "PK": "PKR", "LK": "LKR", "NP": "NPR", "MU": "MUR"}, None),
    "bd": ({"BH": "BHD"}, None),
    "ro": ({"OM": "OMR"}, None),
}
_GENERIC_ALIASES = {
    "riyal": ("riyal", "riyals", "rial", "rials", "riyel", "রিয়াল", "রিয়েল", "ريال", "ريالات"),
    "dinar": ("dinar", "dinars", "দিনার", "دينار"),
    "dirham": ("dirham", "dirhams", "dh", "দিরহাম", "درهم", "دراهم"),
    "dollar": ("dollar", "dollars", "$", "ডলার", "دولار"),
    "pound": ("pound", "pounds", "পাউন্ড"),
    "rupee": ("rupee", "rupees", "rs", "রুপি"),
    "bd": ("bd", "b.d"),
    "ro": ("ro", "r.o"),
}
_GENERIC_BY_ALIAS = {
    clean_text(alias): term for term, aliases in _GENERIC_ALIASES.items() for alias in aliases
}
_CURRENCY_WORD_SUFFIXES = ("ের", "য়ে", "য়", "ে", "র")


def currency_term(word: str) -> Optional[str]:
    """Map one cleaned word or short phrase to an ISO code ("SAR") or to a
    generic term ("riyal") that still needs a country. None if it is not a
    currency word."""
    w = word.strip(" .")
    candidates = [w] + [w[: -len(_nfc(s))] for s in _CURRENCY_WORD_SUFFIXES if w.endswith(_nfc(s))]
    for cand in candidates:
        if cand in _CURRENCY_BY_ALIAS:
            return _CURRENCY_BY_ALIAS[cand]
        if cand in _GENERIC_BY_ALIAS:
            return _GENERIC_BY_ALIAS[cand]
    return None


def resolve_currency(term: Optional[str], country: Optional[str] = None) -> Optional[str]:
    """Turn a `currency_term` result into an ISO 4217 code, using the
    destination country to settle words like "riyal". None if still unclear."""
    if term is None or term in _CURRENCY_CODES:
        return term
    if country is None or term not in _GENERIC_CURRENCIES:
        return None
    by_country, default = _GENERIC_CURRENCIES[term]
    return by_country.get(country, default)


def find_currency_term(text: str) -> Optional[str]:
    """First currency word in a short string such as "SR 1,500 per month"."""
    words = re.findall(rf"[a-z$€.]+|[{BN}]+|[{AR}.]+", clean_text(text))
    for size in (2, 1):
        for i in range(len(words) - size + 1):
            term = currency_term(" ".join(words[i : i + size]))
            if term:
                return term
    return None


def normalize_currency(value: Optional[str], country: Optional[str] = None) -> Optional[str]:
    """Currency as written -> ISO 4217 code, or None when unknown or ambiguous
    ("riyal" with no country stays None rather than being guessed)."""
    if not value:
        return None
    return resolve_currency(find_currency_term(value), country)


# --------------------------------------------------------------------------
# Contract duration
# --------------------------------------------------------------------------

_YEAR_WORDS = ("year", "years", "yr", "yrs", "বছর", "বৎসর", "bochor", "bosor",
               "سنة", "سنوات", "سنه", "عام", "أعوام")
_MONTH_WORDS = ("month", "months", "mo", "mos", "মাস", "mash", "شهر", "أشهر", "اشهر", "شهور", "شهرا")
# Arabic dual forms carry the number 2 inside the word.
_ARABIC_DUALS = {"سنتان": 24, "سنتين": 24, "عامان": 24, "عامين": 24, "شهران": 2, "شهرين": 2}
# "মাসে" / "মাসিক" mean "per month", not a count of months.
_NOT_A_DURATION = {"মাসে", "মাসিক"}


def duration_unit_months(word: str) -> Optional[int]:
    """12 for a word meaning year, 1 for month, else None."""
    if word in _NOT_A_DURATION:
        return None
    for cand in [word] + [word[: -len(s)] for s in _BN_SUFFIXES if word.endswith(s)]:
        if cand in _YEAR_WORDS:
            return 12
        if cand in _MONTH_WORDS:
            return 1
    return None


def parse_duration_months(value: Union[str, int, float, None]) -> Optional[int]:
    """"2 years", "২ বছর", "দুই বছরের চুক্তি", "24 months", "سنتان" -> months."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if math.isfinite(value) and 0 < value <= 240 else None
    tokens = tokenize(clean_text(value))
    months = 0.0
    found = False
    pending: list[Token] = []
    for tok in tokens:
        if tok.text in _ARABIC_DUALS:
            months += _ARABIC_DUALS[tok.text]
            found = True
            pending = []
            continue
        unit = duration_unit_months(tok.text) if tok.kind == "other" else None
        if unit:
            # No number before the unit, or a number word we cannot parse:
            # give up rather than guess.
            count = amount_from_tokens(pending) if pending else None
            if count is None:
                return None
            months += count * unit
            found = True
            pending = []
        elif tok.is_numeric:
            pending.append(tok)
        else:
            pending = []
    if not found or not 0 < months <= 240:
        return None
    return int(round(months))


# --------------------------------------------------------------------------
# Licence numbers and visa types
# --------------------------------------------------------------------------

_RL_RE = re.compile(r"(?:\br\.?\s?l\b\.?|আরএল|আর এল)\W{0,3}(?:no|নং|নম্বর|number)?\W{0,3}(\d{1,6})\b")


def normalize_license(value: Optional[str]) -> Optional[str]:
    """Recruiting licence number as written -> "RL-1234" when it follows the
    RL pattern, else the trimmed upper-case original. A value with no digits
    is not a licence number and becomes None."""
    if not value:
        return None
    cleaned = clean_text(value)
    if not re.search(r"\d", cleaned):
        return None
    m = _RL_RE.search(cleaned)
    if m:
        return f"RL-{m.group(1)}"
    return re.sub(r"\s+", " ", to_ascii_digits(value)).strip(" .:#").upper()


# Checked in this order, so the riskier reading wins when a text mentions
# two types ("ভিজিট ভিসায় নিবে, পরে কাজের ভিসা করে দিবে" -> "visit").
_VISA_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("free", ("free", "freelance", "azad", "ফ্রি", "আজাদ", "حرة", "آزاد")),
    ("visit", ("visit", "ভিজিট", "زيارة")),
    ("tourist", ("tourist", "tourism", "ট্যুরিস্ট", "টুরিস্ট", "ভ্রমণ", "سياحة", "سياحية")),
    ("umrah", ("umrah", "umra", "ওমরাহ", "ওমরা", "উমরাহ", "عمرة")),
    ("hajj", ("hajj", "haj", "হজ", "حج")),
    ("student", ("student", "study", "স্টুডেন্ট", "ছাত্র", "دراسة", "طالب")),
    ("transit", ("transit", "ট্রানজিট", "عبور")),
    ("work", ("work", "working", "employment", "labour", "labor", "worker", "ওয়ার্ক",
              "কাজের", "কর্ম", "চাকরি", "عمل")),
)


def normalize_visa_type(value: Optional[str]) -> Optional[str]:
    """Visa type as written -> one of free, visit, tourist, umrah, hajj,
    student, transit, work; or the cleaned original if none matches."""
    if not value:
        return None
    cleaned = clean_text(value)
    # Malaysia's foreign-worker permit is literally called a "Visit Pass
    # (Temporary Employment)", VP(TE) / PLKS. It is a work permit.
    if re.search(r"temporary employment|vp\s*\(?te\)?|\bplks\b", cleaned):
        return "work"
    for canonical, keywords in _VISA_TYPES:
        for kw in keywords:
            kw = clean_text(kw)
            pattern = _alias_pattern(kw) if kw[0].isascii() else re.escape(kw)
            if re.search(pattern, cleaned):
                return canonical
    leftover = re.sub(r"visa|ভিসা|تأشيرة|فيزا", "", cleaned).strip(" .:-")
    return leftover or None
