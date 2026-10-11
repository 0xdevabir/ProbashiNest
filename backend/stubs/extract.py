"""STUB for probashi.extract (Agent 3). Returns a fixed, synthetic offer."""
from typing import Optional

from probashi.schemas import ExtractedOffer, Money


def extract_offer(image_bytes: Optional[bytes], text: Optional[str]) -> ExtractedOffer:
    return ExtractedOffer(
        employer_name="SYNTHETIC Example Trading Co. (stub)",
        job_title="Cleaner",
        destination_country="SA",
        monthly_salary=Money(amount=1200, currency="SAR"),
        agency_name="SYNTHETIC Example Overseas (stub)",
        agency_license_no=None,
        fees_charged_bdt=450000,
        contract_duration_months=24,
        visa_type="work",
        document_language="bn" if text else None,
        raw_text=text or "[stub: the image was not read]",
        missing_fields=["agency_license_no"],
        confidence=0.5,
    )
