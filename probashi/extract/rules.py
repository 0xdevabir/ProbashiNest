"""Rule-based fact extraction from free text (no LLM).

Used when the LLM is unavailable, so a Bangla description such as
"সৌদিতে ক্লিনারের কাজ, বেতন ১০০০ রিয়াল, এজেন্টকে ৫ লাখ টাকা দিতে হবে"
still yields the main facts. It is deliberately conservative: when a number
cannot be tied to a salary or a fee it is left out.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from probashi.schemas import Money

from .normalize import (
    AR,
    BN,
    Token,
    amount_from_tokens,
    clean_text,
    currency_term,
    duration_unit_months,
    find_countries,
    normalize_license,
    normalize_visa_type,
    resolve_currency,
    to_ascii_digits,
    tokenize,
)

def _words(*words: str) -> tuple[str, ...]:
    return tuple(clean_text(w) for w in words)


_SALARY_WORDS = _words("বেতন", "মজুরি", "বেসিক", "salary", "wage", "wages", "basic", "beton")
_FEE_WORDS = _words(
    "এজেন্ট", "দালাল", "এজেন্সি", "খরচ", "ফি", "দিতে", "লাগবে", "লাগে", "চায়",
    "চাইছে", "চাচ্ছে", "নিবে", "নেবে", "নিচ্ছে", "জমা", "অগ্রিম",
    "agent", "dalal", "agency", "fee", "fees", "cost", "charge", "charges",
    "pay", "payment", "advance", "khoroch", "chay", "dite", "lagbe",
)
# A number right after one of these is an ID, never money.
_ID_WORDS = _words(
    "rl", "আরএল", "লাইসেন্স", "license", "licence", "নম্বর", "নং", "no", "number",
    "পাসপোর্ট", "passport", "ফোন", "মোবাইল", "phone", "mobile",
)
# A fee with no currency word ("আগে ২ লাখ দিতে হবে") is read as taka only
# from this size up, so small stray numbers are not mistaken for fees.
_MIN_UNLABELLED_FEE = 10_000

# Specific jobs first; "labourer" is the fallback.
_JOBS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cleaner", ("ক্লিনার", "পরিচ্ছন্ন", "cleaner", "cleaning")),
    ("driver", ("ড্রাইভার", "গাড়ি চালক", "driver")),
    ("mason", ("রাজমিস্ত্রি", "mason")),
    ("electrician", ("ইলেকট্রিশিয়ান", "electrician")),
    ("plumber", ("প্লাম্বার", "plumber")),
    ("welder", ("ওয়েল্ডার", "welder")),
    ("carpenter", ("কাঠমিস্ত্রি", "কার্পেন্টার", "carpenter")),
    ("painter", ("রং মিস্ত্রি", "পেইন্টার", "painter")),
    ("tailor", ("দর্জি", "টেইলার", "tailor")),
    ("cook", ("বাবুর্চি", "রান্নার", "cook")),
    ("waiter", ("ওয়েটার", "waiter")),
    ("security guard", ("সিকিউরিটি", "গার্ড", "security guard", "guard")),
    ("domestic worker", ("গৃহকর্মী", "বাসার কাজ", "বাসাবাড়ি", "খাদ্দামা",
                         "housemaid", "domestic worker", "house maid", "basar kaj")),
    ("garment worker", ("গার্মেন্টস", "গার্মেন্ট", "garments", "garment")),
    ("factory worker", ("কারখানা", "ফ্যাক্টরি", "factory")),
    ("construction worker", ("নির্মাণ", "কনস্ট্রাকশন", "construction")),
    ("farm worker", ("কৃষি", "খামার", "বাগান", "farm", "agriculture")),
    ("shop worker", ("সেলসম্যান", "দোকান", "সুপারমার্কেট", "salesman", "shop")),
    ("delivery rider", ("ডেলিভারি", "delivery")),
    ("caregiver", ("কেয়ারগিভার", "caregiver")),
    ("nurse", ("নার্স", "nurse")),
    ("labourer", ("লেবার", "শ্রমিক", "labour", "labor", "labourer", "laborer")),
)

_VISA_WORDS = _words("ভিসা", "visa", "تأشيرة", "فيزا")

_AGENCY_LATIN_RE = re.compile(
    r"((?:[A-Z][A-Za-z&.'-]*\s+){1,4}"
    r"(?:Overseas|International|Recruiting|Manpower|Travels|Enterprise|Agency)"
    r"(?:\s+(?:Agency|Services|Limited|Ltd\.?))*)"
)
_AGENCY_BANGLA_RE = re.compile(
    rf"((?:[{BN}]+\s+){{1,2}}(?:ওভারসিজ|ইন্টারন্যাশনাল|ট্রাভেলস|এন্টারপ্রাইজ|ট্রেডার্স)"
    rf"(?:\s+লিমিটেড)?)"
)
_AGENCY_LEAD_IN = {"নাম", "এজেন্সি", "এজেন্সির", "এজেন্ট", "এজেন্টের", "অফিস",
                   "অফিসের", "আমার", "একটা", "হলো", "হল", "The", "From", "Agency", "Name"}
_LICENSE_RE = re.compile(
    r"(?:licen[cs]e|লাইসেন্স|رخصة|ترخيص)\s*(?:no|নং|নম্বর|number|رقم)?[\s.:#-]*"
    r"((?:rl|আরএল)?[\s-]?\d{1,8})"
)


def _has_word(tokens: list[Token], words: tuple[str, ...]) -> bool:
    for tok in tokens:
        for w in words:
            # Short words must match exactly; longer ones may carry a Bangla
            # ending ("এজেন্টকে", "বেতনের").
            if tok.text == w or (len(w) >= 3 and tok.text.startswith(w)):
                return True
    return False


def _currency_near(clause: list[Token], start: int, end: int) -> Optional[str]:
    """Currency word right after the number phrase, else just before it."""
    after = [t.text for t in clause[end : end + 2]]
    before = [t.text for t in clause[max(0, start - 2) : start]]
    candidates = [" ".join(after[:2]), *after[:1], *reversed(before)]
    for cand in candidates:
        term = currency_term(cand) if cand else None
        if term:
            return term
    return None


def _money_and_duration(tokens: list[Token]):
    """Walk the text clause by clause and classify each number phrase."""
    salaries: list[tuple[float, Optional[str]]] = []
    fees: list[tuple[float, Optional[str]]] = []
    duration: Optional[int] = None

    clauses: list[list[Token]] = [[]]
    for tok in tokens:
        if tok.kind == "break":
            clauses.append([])
        else:
            clauses[-1].append(tok)

    for clause in clauses:
        is_salary = _has_word(clause, _SALARY_WORDS)
        is_fee = _has_word(clause, _FEE_WORDS)
        i = 0
        while i < len(clause):
            if not clause[i].is_numeric:
                i += 1
                continue
            start = i
            while i < len(clause) and clause[i].is_numeric:
                i += 1
            phrase = clause[start:i]
            value = amount_from_tokens(phrase)
            if value is None:
                continue

            unit = duration_unit_months(clause[i].text) if i < len(clause) else None
            if unit:
                if duration is None and 0 < value * unit <= 240:
                    duration = int(round(value * unit))
                continue

            term = _currency_near(clause, start, i)
            has_digit = any(t.kind == "num" for t in phrase)
            if term is None:
                if _has_word(clause[max(0, start - 3) : start], _ID_WORDS):
                    continue
                if is_salary and not is_fee and has_digit:
                    salaries.append((value, None))
                elif is_fee and not is_salary and value >= _MIN_UNLABELLED_FEE:
                    fees.append((value, "BDT"))
            elif is_salary and not is_fee:
                salaries.append((value, term))
            elif is_fee and not is_salary:
                fees.append((value, term))
            elif term != "BDT":
                salaries.append((value, term))  # foreign money is the wage
            elif is_fee:
                fees.append((value, term))
    return salaries, fees, duration


def _job_title(cleaned: str) -> Optional[str]:
    for title, keywords in _JOBS:
        for kw in keywords:
            kw = clean_text(kw)
            pattern = rf"(?<![a-z]){re.escape(kw)}(?![a-z])" if kw[0].isascii() else re.escape(kw)
            if re.search(pattern, cleaned):
                return title
    return None


def _visa_type(tokens: list[Token]) -> Optional[str]:
    contexts = []
    for i, tok in enumerate(tokens):
        if any(tok.text.startswith(w) for w in _VISA_WORDS):
            contexts.append(" ".join(t.text for t in tokens[max(0, i - 2) : i + 2]))
    known = {"free", "visit", "tourist", "umrah", "hajj", "student", "transit", "work"}
    # normalize_visa_type already prefers the riskier type within one string.
    result = normalize_visa_type(" ".join(contexts)) if contexts else None
    return result if result in known else None


def _agency_name(text: str) -> Optional[str]:
    m = _AGENCY_LATIN_RE.search(text) or _AGENCY_BANGLA_RE.search(text)
    if not m:
        return None
    words = m.group(1).split()
    while words and words[0] in _AGENCY_LEAD_IN:
        words.pop(0)
    return " ".join(words) if len(words) >= 2 else None


def _language(text: str) -> Optional[str]:
    bangla = len(re.findall(rf"[{BN}]", text))
    arabic = len(re.findall(rf"[{AR}]", text))
    if bangla > arabic and bangla >= 5:
        return "bn"
    if arabic >= 5:
        return "ar"
    return None  # Latin script could be English or romanised Bangla


def extract_with_rules(text: str) -> tuple[dict[str, Any], set[str], list[str]]:
    """Return (ExtractedOffer field values, uncertain field names, notes)."""
    cleaned = clean_text(text)
    tokens = tokenize(cleaned)
    uncertain: set[str] = set()
    notes: list[str] = []

    countries = [c for c in find_countries(cleaned) if c != "BD"]
    country = countries[0] if len(countries) == 1 else None

    salaries, fees, duration = _money_and_duration(tokens)

    salary = Money()
    if salaries:
        amount, term = salaries[0]
        salary = Money(amount=amount, currency=resolve_currency(term, country))

    fee_bdt: Optional[float] = None
    taka_fees = [amount for amount, term in fees if term == "BDT"]
    if taka_fees:
        fee_bdt = max(taka_fees)  # closest to the total when parts are listed
        if len(taka_fees) > 1:
            uncertain.add("fees_charged_bdt")
    elif fees:
        amount, term = fees[0]
        notes.append(
            f"fee stated as {amount:g} {resolve_currency(term, country) or term}; "
            "not converted to BDT"
        )

    license_no = normalize_license(cleaned) if re.search(r"\brl|আরএল|আর এল", cleaned) else None
    if license_no is None or not license_no.startswith("RL-"):
        m = _LICENSE_RE.search(cleaned)
        license_no = normalize_license(m.group(1)) if m else None

    fields = {
        "employer_name": None,  # not attempted without the LLM
        "job_title": _job_title(cleaned),
        "destination_country": country,
        "monthly_salary": salary,
        "agency_name": _agency_name(to_ascii_digits(text)),
        "agency_license_no": license_no,
        "fees_charged_bdt": fee_bdt,
        "contract_duration_months": duration,
        "visa_type": _visa_type(tokens),
        "document_language": _language(text),
    }
    return fields, uncertain, notes
