"""Owner: Agent 2 (knowledge base, retrieval and verdict engine).

    from probashi.knowledge import evaluate
    verdict = evaluate(offer)

See README.md in this folder for the level logic and the data sources.
"""

import logging

from probashi.schemas import ExtractedOffer, Verdict

logger = logging.getLogger(__name__)


def evaluate(offer: ExtractedOffer) -> Verdict:
    """Traffic-light verdict for an extracted job offer.

    Deterministic rules decide the level. If the knowledge base cannot be loaded
    the answer is amber ("could not check"), never green.
    """
    from .engine import explain, unavailable_verdict
    from .kb import KnowledgeBaseError

    try:
        return explain(offer)[0]
    except KnowledgeBaseError:
        logger.exception("knowledge base could not be loaded")
        return unavailable_verdict()
