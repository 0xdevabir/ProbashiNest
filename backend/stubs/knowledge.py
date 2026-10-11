"""STUB for probashi.knowledge (Agent 2). Always amber: nothing is verified.

No sources and no helplines are returned, because a stub must not invent them.
"""
from probashi.schemas import ExtractedOffer, Level, Reason, Verdict


def evaluate(offer: ExtractedOffer) -> Verdict:
    return Verdict(
        level=Level.amber,
        reasons=[
            Reason(
                code="STUB_NOT_VERIFIED",
                message_bn="এটি পরীক্ষামূলক উত্তর। আসল যাচাই এখনো হয়নি।",
                message_en="This is a test answer from a stub. No real check was done.",
            ),
            Reason(
                code="STUB_AGENCY_LICENCE_MISSING",
                message_bn="এজেন্সির লাইসেন্স নম্বর পাওয়া যায়নি।",
                message_en="The agency licence number was not found.",
            ),
            Reason(
                code="STUB_FEES_NOT_CHECKED",
                message_bn="এজেন্টের চাওয়া টাকা ঠিক আছে কি না, জানা যায়নি।",
                message_en="The fee charged by the agent could not be checked.",
            ),
        ],
        next_steps_bn=[
            "এজেন্টের কাছে লাইসেন্স নম্বর চান।",
            "যাচাই না হওয়া পর্যন্ত টাকা দেবেন না।",
        ],
        helplines=[],
        disclaimer_bn="এটি পরীক্ষামূলক তথ্য। এটি আইনি পরামর্শ নয়।",
    )


def guidance(offer: ExtractedOffer, verdict: Verdict):
    """STUB guidance: one fixed follow-up question, no explanations (a stub has no sources)."""
    from probashi.knowledge.guidance import Guidance, Prompt

    ask = [
        Prompt(
            key="agency_license_no",
            text_bn="এজেন্সির লাইসেন্স নম্বর কত? (পরীক্ষামূলক প্রশ্ন)",
            text_en="What is the agency's licence number? (stub question)",
        )
    ]
    return Guidance(
        follow_up=ask if "agency_license_no" in offer.missing_fields else [], confidence=offer.confidence
    )


def guide(country):
    """STUB guide: empty, because a stub must not invent rules or phone numbers."""
    from probashi.knowledge.guidance import Guide

    return Guide(country=(country or "").upper())
