"""Owner: Agent 3 (document reading and fact extraction).

Public API:
    extract_offer(image_bytes, text) -> ExtractedOffer
    mask_pii(text) -> str   # use before logging any document text
See README.md in this folder.
"""
from .extractor import IMPORTANT_FIELDS, extract_offer
from .privacy import mask_pii

__all__ = ["extract_offer", "mask_pii", "IMPORTANT_FIELDS"]
