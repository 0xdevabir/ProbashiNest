"""Fixed Bangla and English wording for every reason code.

Bangla is written the way people speak: short sentences, common words. These
templates are the source of truth; the optional LLM rephrase can only restyle them.
"""

from __future__ import annotations

from datetime import date

from .rules import HIGH, Flag

_TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

DISCLAIMER_BN = "এটা শুধু পরামর্শ, আইনি মতামত নয়। টাকা দেওয়ার আগে নিজে যাচাই করে নিন।"

CURRENCY_BN = {
    "SAR": "রিয়াল", "QAR": "রিয়াল", "OMR": "রিয়াল", "AED": "দিরহাম",
    "KWD": "দিনার", "MYR": "রিঙ্গিত", "BDT": "টাকা", "USD": "ডলার",
}
STATUS_BN = {"cancelled": "বাতিল", "canceled": "বাতিল", "suspended": "স্থগিত", "expired": "মেয়াদ শেষ"}
# Ordered by importance: the Bangla message names only the first three that are missing.
FIELD_BN = {
    "fees_charged_bdt": "কত টাকা লাগবে", "monthly_salary": "বেতন", "visa_type": "ভিসার ধরন",
    "agency_name": "এজেন্সির নাম", "destination_country": "কোন দেশ", "job_title": "কাজের নাম",
    "contract_duration_months": "চুক্তির মেয়াদ", "employer_name": "কোম্পানির নাম",
    "agency_license_no": "লাইসেন্স নম্বর",
}
FIELD_EN = {
    "job_title": "job title", "destination_country": "destination country", "monthly_salary": "salary",
    "agency_name": "agency name", "fees_charged_bdt": "fee charged",
    "contract_duration_months": "contract length", "visa_type": "visa type",
    "employer_name": "employer name", "agency_license_no": "licence number",
}

# template -> (Bangla, English)
TEMPLATES: dict[str, tuple[str, str]] = {
    "AGENCY_NOT_FOUND": (
        "লাইসেন্স নম্বর {licence} সরকারি তালিকায় নেই। এটা ভুয়া হতে পারে। নম্বরটা আবার মিলিয়ে দেখুন।",
        "Licence number {licence} is not in the government (BMET) list of recruiting agencies. It may be fake. Check the number again.",
    ),
    "AGENCY_UNLICENSED": (
        "এই এজেন্সির লাইসেন্স ({licence}) এখন চালু নেই। সরকারি তালিকায় লেখা আছে: {status_bn}।",
        "This agency's licence ({licence}, {name}) is not valid now. The government list shows it as: {status}.",
    ),
    "AGENCY_UNLICENSED_BY_NAME": (
        "এই নামের এজেন্সির লাইসেন্স এখন চালু নেই। সরকারি তালিকায় লেখা আছে: {status_bn}।",
        "The agency with this name ({name}) does not have a valid licence now. The government list shows it as: {status}.",
    ),
    "AGENCY_STATUS_UNCLEAR": (
        "সরকারি তালিকায় এই লাইসেন্সের ({licence}) অবস্থা পরিষ্কার নয়। তাই এজেন্সি নিশ্চিত করা গেল না।",
        "The government list does not clearly show licence {licence} as active (listed as: {status}), so the agency could not be confirmed.",
    ),
    "AGENCY_LICENCE_EXPIRED": (
        "সরকারি তালিকা অনুযায়ী এই লাইসেন্সের ({licence}) মেয়াদ {date_bn} তারিখে শেষ হয়েছে।",
        "According to the government list, licence {licence} was valid only until {date}.",
    ),
    "AGENCY_LICENCE_MISMATCH": (
        "এই নামের এজেন্সি সরকারি তালিকায় আছে। কিন্তু লাইসেন্স নম্বর {licence} মিলছে না।",
        "An agency with this name is in the government list, but licence number {licence} does not match it.",
    ),
    "AGENCY_NAME_MISMATCH": (
        "লাইসেন্স নম্বর {licence} সরকারি তালিকায় অন্য নামে আছে। আপনার কাগজের নামের সাথে মিলছে না।",
        "Licence {licence} is registered under a different name ({registered}) than the one in your offer.",
    ),
    "AGENCY_NAME_NOT_FOUND": (
        "এই নামের কোনো এজেন্সি সরকারি তালিকায় পাইনি।",
        "No agency with this name ({name}) was found in the government list.",
    ),
    "MISSING_LICENCE_NO": (
        "এজেন্সির লাইসেন্স নম্বর পাইনি। লাইসেন্স নম্বর ছাড়া এজেন্সি আসল কি না বোঝা যায় না।",
        "No readable recruiting licence (RL) number was found. Without it the agency cannot be verified.",
    ),
    "REGISTER_STALE": (
        "আমাদের কাছে থাকা সরকারি তালিকা পুরোনো হয়ে গেছে। তাই লাইসেন্স নিশ্চিত করা গেল না।",
        "Our copy of the government licence list is too old, so the licence could not be confirmed.",
    ),
    "AGENCY_LICENSED": (
        "এজেন্সির লাইসেন্স ({licence}) সরকারি তালিকায় চালু আছে।",
        "The agency's licence ({licence}, {name}) is listed as active in the government list.",
    ),
    "MISSING_EMPLOYER": (
        "কোন কোম্পানিতে কাজ, সেই নাম পাইনি। কোম্পানির নাম ছাড়া চাকরি যাচাই করা যায় না।",
        "The employer's name is missing. Without it the job cannot be checked.",
    ),
    "MISSING_KEY_FACTS": (
        "কিছু দরকারি তথ্য পাইনি। যেমন: {fields_bn}।",
        "Some key facts are missing: {fields_en}.",
    ),
    "UNSUPPORTED_DESTINATION": (
        "এই দেশের নিয়ম এখনো আমাদের কাছে নেই। তাই পুরো যাচাই করা গেল না।",
        "We do not have rules for this destination ({country}) yet, so the offer could not be fully checked.",
    ),
    "LOW_CONFIDENCE": (
        "কাগজ বা কথা পরিষ্কার বোঝা যায়নি। তাই ফলাফলে ভুল থাকতে পারে।",
        "The document or recording could not be read clearly, so the result may be wrong.",
    ),
    "FEE_ABOVE_LIMIT": (
        "আপনার কাছে {fee_bn} টাকা চাওয়া হয়েছে। সরকারের ঠিক করা খরচ প্রায় {limit_bn} টাকা। এটা অনেক বেশি।",
        "You are being asked for Tk {fee}. The government-fixed cost is about Tk {limit}. This is far too much.",
    ),
    "FEE_ABOVE_UNVERIFIED_LIMIT": (
        "আপনার কাছে {fee_bn} টাকা চাওয়া হয়েছে। খবর অনুযায়ী সরকারের ঠিক করা খরচ প্রায় {limit_bn} টাকা। এখনকার সঠিক খরচ জেনে নিন।",
        "You are being asked for Tk {fee}. Press reports put the government-fixed cost at about Tk {limit}; we could not confirm the current figure.",
    ),
    "FEE_LIMIT_UNVERIFIED": (
        "{fee_bn} টাকা খরচ ঠিক আছে কি না নিশ্চিত হতে পারিনি। সরকারের এখনকার খরচের হার আমাদের যাচাই করা নেই।",
        "We could not confirm that Tk {fee} is within the current government-fixed cost (our figure, Tk {limit}, is not verified).",
    ),
    "FEE_NOT_CHECKABLE": (
        "এই দেশের জন্য সরকারের ঠিক করা খরচ আমাদের জানা নেই। তাই {fee_bn} টাকা ঠিক কি না বলা গেল না।",
        "We have no sourced government-fixed cost for this destination, so Tk {fee} could not be checked.",
    ),
    "SALARY_BELOW_MINIMUM": (
        "বেতন বলা হয়েছে {salary_bn} {currency_bn}। এই দেশের আইনে সর্বনিম্ন বেতন {minimum_bn} {currency_bn}। বেতন আইনের চেয়ে কম।",
        "The salary offered is {salary} {currency}. The legal minimum wage there is {minimum} {currency}. The offer is below the legal minimum.",
    ),
    "SALARY_NOT_COMPARABLE": (
        "বেতন কোন দেশের টাকায়, তা পরিষ্কার নয়। তাই সর্বনিম্ন বেতনের সাথে মেলানো গেল না।",
        "The salary currency is unclear or not the destination's currency, so it could not be compared with the legal minimum wage.",
    ),
    "SALARY_UNREALISTIC": (
        "এই কাজের জন্য {salary_bn} {currency_bn} বেতন অস্বাভাবিক বেশি। বেশি বেতনের লোভ দেখানো প্রতারণার চেনা কৌশল।",
        "A salary of {salary} {currency} is unusually high for this job. Promising a high salary is a known lure.",
    ),
    "VISA_JOB_MISMATCH": (
        "এটা কাজের ভিসা নয়। এই ধরনের ভিসায় বিদেশে কাজ করা যায় না।",
        "The visa ({visa}) is not a work visa. You cannot legally work abroad on it.",
    ),
    "VISA_JOB_MISMATCH_DOMESTIC": (
        "ভিসা গৃহকর্মীর, কিন্তু কাজ বলা হয়েছে অন্য। ভিসা আর কাজ মিলছে না।",
        "The visa ({visa}) is for domestic work but the job offered is different ({job}). The visa does not match the job.",
    ),
    "FREE_VISA": (
        "\"ফ্রি ভিসা\" বলে আসলে কিছু নেই। এই ভিসায় কাজের নিশ্চয়তা থাকে না। ধরা পড়ে দেশে ফেরত আসার ঝুঁকি থাকে।",
        "There is no such thing as a \"free visa\". It gives no guaranteed job and carries a risk of arrest and deportation.",
    ),
    "PERSONAL_ACCOUNT_PAYMENT": (
        "কারও নিজের বিকাশ বা ব্যাংক অ্যাকাউন্টে টাকা পাঠাতে বলা হয়েছে। এটা সন্দেহের বিষয়।",
        "You are asked to pay into a personal account or mobile wallet. This is a warning sign.",
    ),
    "PRESSURE_TO_PAY": (
        "তাড়াতাড়ি টাকা দিতে চাপ দেওয়া হচ্ছে। যাচাই করার সময় না দেওয়া সন্দেহের বিষয়।",
        "You are being pressed to pay quickly. Not giving you time to check is a warning sign.",
    ),
    "PASSPORT_KEPT": (
        "কাগজে পাসপোর্ট মালিকের কাছে রাখার কথা আছে। পাসপোর্ট সব সময় নিজের কাছে রাখবেন।",
        "The document mentions the employer keeping your passport. Your passport should stay with you.",
    ),
    "FEE_DEDUCTED_FROM_SALARY": (
        "কাগজে বেতন থেকে টাকা কাটার কথা আছে। কত টাকা কাটবে আর কেন কাটবে, আগে জেনে নিন।",
        "The document mentions deductions from your salary. Find out how much will be cut, and why, before you agree.",
    ),
    "JOB_VAGUE": (
        "কী কাজ করতে হবে, তা পরিষ্কার বলা নেই। \"যেকোনো কাজ\" বললে পরে অন্য কাজ দিতে পারে।",
        "The job is not clearly named. \"Any work\" can turn into a different job after you arrive.",
    ),
    "DOCUMENT_MISMATCH": (
        "আপনার কাগজগুলো মিলছে না। এক কাগজে এক রকম, আরেক কাগজে অন্য রকম লেখা। যা মিলছে না: {fields_bn}।",
        "Your documents do not agree with each other on: {fields_en}.",
    ),
    "KNOWLEDGE_UNAVAILABLE": (
        "এই মুহূর্তে যাচাই করা যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।",
        "The offer could not be checked right now. Please try again later.",
    ),
}

# Next steps, most urgent first: (step, codes that trigger it; None = always eligible)
_STEPS: list[tuple[str, set[str] | None]] = [
    ("এখন কোনো টাকা দেবেন না।", set()),  # added for every red verdict
    ("এজেন্সির কাছে সরকারি লাইসেন্স নম্বর (আরএল নম্বর) চান।",
     {"MISSING_LICENCE_NO", "AGENCY_NAME_NOT_FOUND", "AGENCY_LICENCE_MISMATCH"}),
    ("কাজের ভিসা ছাড়া যাবেন না। ভিজিট, টুরিস্ট বা ফ্রি ভিসায় রাজি হবেন না।", {"VISA_JOB_MISMATCH", "FREE_VISA"}),
    ("লিখিত চুক্তি চান। তাতে কোম্পানির নাম, কাজ, বেতন আর খরচ লেখা থাকতে হবে।",
     {"MISSING_EMPLOYER", "MISSING_KEY_FACTS", "LOW_CONFIDENCE", "SALARY_BELOW_MINIMUM",
      "SALARY_NOT_COMPARABLE", "SALARY_UNREALISTIC", "PASSPORT_KEPT", "FEE_DEDUCTED_FROM_SALARY",
      "JOB_VAGUE"}),
    ("টাকা দেওয়ার আগে ১৬১৩৫ নম্বরে ফোন করে এজেন্সি আর খরচ যাচাই করুন।", None),
    ("টাকা দিলে এজেন্সির রসিদ নিন। কারও নিজের বিকাশ বা অ্যাকাউন্টে টাকা দেবেন না।", None),
    ("চুক্তি আর সব কাগজের কপি নিজের কাছে আর পরিবারের কাছে রাখুন।", None),
]


def bn_number(value: float) -> str:
    """165000 -> '১,৬৫,০০০' (Bangla digits, lakh grouping)."""
    n = round(value, 2)
    whole, frac = divmod(abs(n), 1)
    digits = str(int(whole))
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join(groups + [tail])
    if frac:
        text += f"{frac:.2f}"[1:].rstrip("0")
    return ("-" if n < 0 else "") + text.translate(_TO_BN)


def _en_number(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _format_params(params: dict) -> dict:
    out: dict[str, object] = {}
    for key, val in params.items():
        if isinstance(val, bool) or val is None:
            out[key] = "" if val is None else val
        elif isinstance(val, (int, float)):
            out[key] = _en_number(val)
            out[key + "_bn"] = bn_number(val)
        elif isinstance(val, date):
            out[key] = val.isoformat()
            out[key + "_bn"] = val.strftime("%d-%m-%Y").translate(_TO_BN)
        elif key == "fields":
            # Spoken Bangla names the three most important ones; English lists all.
            ranked = sorted(val, key=lambda f: list(FIELD_BN).index(f) if f in FIELD_BN else 99)
            out["fields_bn"] = ", ".join(FIELD_BN.get(f, f) for f in ranked[:3])
            out["fields_en"] = ", ".join(FIELD_EN.get(f, f) for f in val)
        else:
            out[key] = val
    if "status" in out:
        out["status_bn"] = STATUS_BN.get(str(out["status"]).lower(), str(out["status"]))
    if "currency" in out:
        out["currency_bn"] = CURRENCY_BN.get(str(out["currency"]), str(out["currency"]))
    return out


def render(flag: Flag) -> tuple[str, str]:
    """(message_bn, message_en) for a flag."""
    bn, en = TEMPLATES[flag.template or flag.code]
    params = _format_params(flag.params)
    return bn.format(**params), en.format(**params)


def next_steps(flags: list[Flag]) -> list[str]:
    """2-4 concrete actions, most urgent first."""
    codes = {f.code for f in flags}
    steps: list[str] = []
    if any(f.severity == HIGH for f in flags):
        steps.append(_STEPS[0][0])
    steps += [step for step, trigger in _STEPS[1:] if trigger and trigger & codes]
    for step, trigger in _STEPS:
        if len(steps) >= 3:
            break
        if trigger is None and step not in steps:
            steps.append(step)
    return steps[:4]
