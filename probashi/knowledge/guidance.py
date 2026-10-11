"""What to do with a verdict: questions, explanations, a complaint draft, a country guide.

Everything here is deterministic and built from the same data files as the verdict.
Nothing in this module can change a verdict's level.

    from probashi.knowledge.guidance import guidance, guide
    extra = guidance(offer, verdict)   # for one checked offer
    page = guide("SA")                 # rights, checklist and contacts for a country
"""

from __future__ import annotations

import logging
from datetime import date

from pydantic import BaseModel, Field

from probashi.schemas import ExtractedOffer, Helpline, Level, Source, Verdict

logger = logging.getLogger(__name__)


class Prompt(BaseModel):
    """One question, in spoken Bangla and in English."""

    key: str  # missing field name (follow-up) or reason code (question for the agent)
    text_bn: str
    text_en: str


class Explainer(BaseModel):
    """The rule or report behind one reason, with where and when it was checked."""

    code: str
    text_bn: str
    text_en: str
    source: Source | None = None
    verified: bool = False
    last_checked: date | None = None


class Guidance(BaseModel):
    follow_up: list[Prompt] = Field(default_factory=list)  # facts still missing, most useful first
    ask_agent: list[Prompt] = Field(default_factory=list)
    explainers: list[Explainer] = Field(default_factory=list)
    complaint_draft_bn: str | None = None  # red verdicts only
    confidence: float = 0.0  # how well the offer was read (0-1), copied from the extractor


class GuideItem(BaseModel):
    id: str
    text_bn: str
    text_en: str
    source: Source | None = None
    verified: bool = False
    last_checked: date | None = None


class Guide(BaseModel):
    country: str
    country_name_bn: str | None = None
    rights: list[GuideItem] = Field(default_factory=list)
    checklist: list[GuideItem] = Field(default_factory=list)
    payment_tips_bn: list[str] = Field(default_factory=list)
    helplines: list[Helpline] = Field(default_factory=list)


# Ordered: the facts that matter most for the verdict are asked first.
_FOLLOW_UP: dict[str, tuple[str, str]] = {
    "agency_license_no": ("এজেন্সির লাইসেন্স নম্বর কত? এটাকে আরএল নম্বর বলে।", "What is the agency's licence (RL) number?"),
    "fees_charged_bdt": ("সব মিলিয়ে কত টাকা চাইছে?", "How much money are they asking for in total?"),
    "visa_type": ("কোন ধরনের ভিসা দিচ্ছে?", "What type of visa are they giving you?"),
    "monthly_salary": ("মাসে বেতন কত? কোন দেশের টাকায়?", "What is the monthly salary, and in which currency?"),
    "destination_country": ("কোন দেশে যাবেন?", "Which country is the job in?"),
    "agency_name": ("এজেন্সির নাম কী?", "What is the agency's name?"),
    "employer_name": ("কোন কোম্পানিতে কাজ করবেন?", "Which company will you work for?"),
    "job_title": ("কী কাজ করতে হবে?", "What job will you do?"),
    "contract_duration_months": ("চুক্তি কত মাসের?", "How many months is the contract for?"),
}
MAX_FOLLOW_UP = 3  # more than three questions at once is too many to answer by voice

_ASK_LICENCE = ("আপনাদের সরকারি লাইসেন্স নম্বর কত? লাইসেন্সের কাগজটা দেখান।",
                "What is your government licence (RL) number? Please show me the licence.")
_ASK_FEE = ("মোট কত টাকা লাগবে? কোন খাতে কত, লিখে দিন।",
            "What is the total cost? Please write down what each part is for.")
_ASK_VISA = ("এটা কি কাজের ভিসা? ভিসার কপি দিন, আমি মিলিয়ে দেখব।",
             "Is this a work visa? Give me a copy so I can check it.")
_ASK_CONTRACT = ("লিখিত চুক্তি দিন। তাতে কোম্পানির নাম, কাজ, বেতন আর মেয়াদ লেখা থাকবে তো?",
                 "Please give me a written contract. Will it name the employer, the job, the salary and the length?")
_ASK_SALARY = ("বেতন কত আর কোন টাকায়, চুক্তিতে লিখে দিন।",
               "Please write the salary and its currency in the contract.")

# reason code -> question to put to the agent. Several codes share one question.
_ASK_AGENT: dict[str, tuple[str, str]] = {
    **dict.fromkeys(
        ("MISSING_LICENCE_NO", "AGENCY_NOT_FOUND", "AGENCY_NAME_NOT_FOUND", "AGENCY_LICENCE_MISMATCH",
         "AGENCY_NAME_MISMATCH", "AGENCY_UNLICENSED", "AGENCY_LICENCE_EXPIRED", "AGENCY_STATUS_UNCLEAR"),
        _ASK_LICENCE,
    ),
    **dict.fromkeys(
        ("FEE_ABOVE_LIMIT", "FEE_ABOVE_UNVERIFIED_LIMIT", "FEE_LIMIT_UNVERIFIED", "FEE_NOT_CHECKABLE"), _ASK_FEE
    ),
    **dict.fromkeys(("VISA_JOB_MISMATCH", "FREE_VISA"), _ASK_VISA),
    **dict.fromkeys(("MISSING_EMPLOYER", "MISSING_KEY_FACTS", "JOB_VAGUE"), _ASK_CONTRACT),
    **dict.fromkeys(("SALARY_BELOW_MINIMUM", "SALARY_NOT_COMPARABLE", "SALARY_UNREALISTIC"), _ASK_SALARY),
    "PASSPORT_KEPT": ("পাসপোর্ট কি আমার কাছে থাকবে? এটা চুক্তিতে লিখে দিন।",
                      "Will I keep my own passport? Please write that in the contract."),
    "FEE_DEDUCTED_FROM_SALARY": ("বেতন থেকে কত টাকা কাটবে? কত মাস ধরে কাটবে?",
                                 "How much will be cut from my salary, and for how many months?"),
    "PERSONAL_ACCOUNT_PAYMENT": ("টাকা এজেন্সির নামের অ্যাকাউন্টে দেব। রসিদ দেবেন তো?",
                                 "I will pay only into the agency's own account. Will you give me a receipt?"),
    "PRESSURE_TO_PAY": ("যাচাই করতে আমার কয়েক দিন সময় লাগবে। সময় দেবেন তো?",
                        "I need a few days to check this. Will you give me that time?"),
}

# reason code -> topic of the destination's rule that explains it.
_CODE_TOPIC = {
    "SALARY_BELOW_MINIMUM": "minimum_wage",
    "SALARY_UNREALISTIC": "minimum_wage",
    "FEE_ABOVE_LIMIT": "bd_migration_cost_ceiling",
    "FEE_ABOVE_UNVERIFIED_LIMIT": "bd_migration_cost_ceiling",
    "FEE_LIMIT_UNVERIFIED": "bd_migration_cost_ceiling",
    "PASSPORT_KEPT": "passport_retention",
    "FEE_DEDUCTED_FROM_SALARY": "recruitment_fees",
}
_RIGHTS_TOPICS = ("minimum_wage", "recruitment_fees", "passport_retention", "contract", "complaint_channel")

# Advice, not law: these repeat the engine's own next steps.
PAYMENT_TIPS_BN = [
    "যাচাই শেষ না হলে কোনো টাকা দেবেন না।",
    "টাকা দিলে এজেন্সির রসিদ নিন। রসিদে এজেন্সির নাম আর লাইসেন্স নম্বর থাকতে হবে।",
    "কারও নিজের বিকাশ বা অ্যাকাউন্টে টাকা দেবেন না।",
    "নগদ টাকা দিলে সাক্ষী রাখুন। রসিদের ছবি তুলে পরিবারের কাছে পাঠান।",
]


def _item(rec: dict) -> GuideItem:
    from .kb import source_of

    return GuideItem(id=rec["id"], text_bn=rec["text_bn"], text_en=rec["text_en"], source=source_of(rec),
                     verified=rec["verified"], last_checked=rec["last_checked"])


def _explainers(country: str | None, verdict: Verdict, kb) -> list[Explainer]:
    from .kb import source_of
    from .messages import _TO_BN

    out: list[Explainer] = []
    seen: set[str] = set()
    for reason in verdict.reasons:
        topic = _CODE_TOPIC.get(reason.code)
        rec = kb.rule(country, topic) if topic else None
        if rec is None:
            rec = next((p for p in kb.patterns if p.get("code") == reason.code), None)
        if rec is not None:
            if rec["id"] not in seen:
                seen.add(rec["id"])
                out.append(Explainer(code=reason.code, text_bn=rec["text_bn"], text_en=rec["text_en"],
                                     source=source_of(rec), verified=rec["verified"],
                                     last_checked=rec["last_checked"]))
        elif reason.code.startswith("AGENCY_") or reason.code == "REGISTER_STALE":
            reg = kb.register
            if "register" in seen or not reg.last_checked:
                continue
            seen.add("register")
            day_bn = reg.last_checked.strftime("%d-%m-%Y").translate(_TO_BN)
            out.append(Explainer(
                code=reason.code,
                text_bn=f"আমরা সরকারি এজেন্সি তালিকার সাথে মিলিয়ে দেখেছি। তালিকাটা {day_bn} তারিখে নেওয়া।",
                text_en=f"We compared the offer with the government list of recruiting agencies, copied on {reg.last_checked.isoformat()}.",
                source=Source(title="BMET recruiting agency register (RAIMS)", url=reg.source_url),
                verified=True, last_checked=reg.last_checked,
            ))
    return out


def _complaint_draft(offer: ExtractedOffer, verdict: Verdict, kb) -> str:
    """A plain Bangla note the worker can read out or hand over. Blanks stay blank."""
    from .messages import bn_number

    blank = "__________"
    lines = [
        "অভিযোগ",
        f"আমার নাম: {blank}",
        f"আমার ফোন: {blank}",
        f"এজেন্সি বা দালালের নাম: {offer.agency_name or blank}",
        f"লাইসেন্স নম্বর: {offer.agency_license_no or 'দেয়নি'}",
        f"কোন দেশ: {kb.country_name_bn(offer.destination_country) or offer.destination_country or blank}",
        f"কাজ: {offer.job_title or blank}",
        f"চাওয়া টাকা: {bn_number(offer.fees_charged_bdt) + ' টাকা' if offer.fees_charged_bdt is not None else blank}",
        f"দেওয়া টাকা: {blank}",
        "",
        "যা সমস্যা পাওয়া গেছে:",
        *[f"- {r.message_bn}" for r in verdict.reasons],
        "",
        "আমি এর প্রতিকার চাই।",
        f"তারিখ: {blank}    সই: {blank}",
    ]
    return "\n".join(lines)


def guidance(offer: ExtractedOffer, verdict: Verdict, *, kb=None) -> Guidance:
    """Follow-up questions, questions for the agent, explanations and a complaint draft.

    Never raises for a bad knowledge base: it returns what can be said without one.
    """
    from .kb import KnowledgeBaseError, load_kb
    from .rules import missing_key_fields, sanitize

    clean = sanitize(offer)
    missing = set(missing_key_fields(clean))
    out = Guidance(
        follow_up=[Prompt(key=f, text_bn=bn, text_en=en) for f, (bn, en) in _FOLLOW_UP.items() if f in missing][
            :MAX_FOLLOW_UP
        ],
        confidence=offer.confidence,
    )
    asked: set[tuple[str, str]] = set()
    for reason in verdict.reasons:
        question = _ASK_AGENT.get(reason.code)
        if question and question not in asked:
            asked.add(question)
            out.ask_agent.append(Prompt(key=reason.code, text_bn=question[0], text_en=question[1]))
    try:
        kb = kb or load_kb()
    except KnowledgeBaseError:
        logger.exception("knowledge base could not be loaded")
        return out
    out.explainers = _explainers(clean.destination_country, verdict, kb)
    if verdict.level == Level.red:
        out.complaint_draft_bn = _complaint_draft(clean, verdict, kb)
    return out


def guide(country: str | None, *, kb=None) -> Guide:
    """Rights, pre-departure checklist, payment advice and contacts for a destination.

    An unknown country still gets the checklist, the advice and the Bangladesh numbers.
    Raises KnowledgeBaseError if the data cannot be loaded.
    """
    from .engine import _helplines
    from .kb import load_kb

    kb = kb or load_kb()
    code = (country or "").strip().upper()
    records = kb.rules.get(code, {}).get("records", [])
    return Guide(
        country=code,
        country_name_bn=kb.country_name_bn(code),
        rights=[_item(r) for topic in _RIGHTS_TOPICS for r in records if r["topic"] == topic],
        checklist=[_item(r) for r in kb.checklist],
        payment_tips_bn=PAYMENT_TIPS_BN,
        helplines=_helplines(kb, code),
    )
