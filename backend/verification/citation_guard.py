"""
Verification helpers shared by the validator and any future policy checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence


REQUIRED_CITATION_FIELDS = ("case_name", "court", "year", "paragraph")


@dataclass
class CitationAudit:
    citation_verified: bool
    rejection_reasons: List[str]


def audit_citations(
    answer: str,
    citations: Sequence[Dict],
    source_documents: Sequence[Dict],
) -> CitationAudit:
    """
    Enforce the non-negotiable contract:
    - every citation id must exist in the retrieved set
    - every citation must contain the minimum legal reference fields
    - every answer must keep inline [CITE:doc_id] markers
    """
    rejection_reasons: List[str] = []

    source_ids = {doc.get("doc_id") for doc in source_documents if doc.get("doc_id")}
    citation_ids = {cite.get("id") for cite in citations if cite.get("id")}
    unverifiable = sorted(citation_ids - source_ids)

    if unverifiable:
        rejection_reasons.append(
            f"Unverifiable citation IDs: {', '.join(unverifiable)}"
        )

    incomplete: List[str] = []
    for citation in citations:
        missing = [field for field in REQUIRED_CITATION_FIELDS if not citation.get(field)]
        if missing:
            incomplete.append(f"{citation.get('id')}: missing {missing}")

    if incomplete:
        rejection_reasons.extend(incomplete)

    inline_markers = re.findall(r"\[CITE:[^\]]+\]", answer)
    if not inline_markers:
        rejection_reasons.append("Answer contains no inline citation markers")

    citation_verified = not rejection_reasons and bool(citations)
    return CitationAudit(
        citation_verified=citation_verified,
        rejection_reasons=rejection_reasons,
    )
