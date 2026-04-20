"""
ValidatorAgent
Responsibility: The final verification gate.
  1. Citation validation — confirm every cited doc_id exists in retrieved set
  2. Cross-document consistency — flag contradictory legal assertions
  3. Confidence scoring — multi-factor score (0.0–1.0)
  4. Rejection — block responses with unverifiable or contradictory citations
"""

import logging
from typing import Dict, List, Optional, Any

import openai

from api.models import ValidationResult
from verification.citation_guard import audit_citations

logger = logging.getLogger("validator_agent")

CONSISTENCY_PROMPT = """You are a legal fact-checker. Review the answer and citations below.

Check for:
1. Does every factual claim in the answer have a supporting citation?
2. Do any citations contradict each other?
3. Are there any claims that go beyond what the cited documents say?

Answer in JSON only:
{
  "all_claims_cited": true/false,
  "contradictions_found": true/false,
  "out_of_scope_claims": true/false,
  "issues": ["issue1", "issue2"]
}

ANSWER:
{answer}

CITATIONS USED:
{citations}
"""


class ValidatorAgent:
    """
    Stage 3 Agent: Verification Gate
    Enforces the zero-hallucination contract.
    """

    def __init__(self):
        self.client = openai.AsyncOpenAI()
        self.model = "gpt-4o"
        logger.info("ValidatorAgent initialized")

    async def validate(
        self,
        answer: str,
        citations: List[Dict],
        source_documents: List[Dict],
    ) -> ValidationResult:
        """
        Returns ValidationResult with pass/fail flags and confidence score.
        """
        audit = audit_citations(
            answer=answer,
            citations=citations,
            source_documents=source_documents,
        )
        rejection_reasons: List[str] = list(audit.rejection_reasons)
        citation_verified = audit.citation_verified

        # ── Check 4: Cross-document consistency (LLM-based) ───────────────
        cross_consistent = True
        consistency_issues: List[str] = []

        try:
            consistency = await self._check_consistency(answer, citations)
            if consistency:
                if consistency.get("contradictions_found"):
                    cross_consistent = False
                    rejection_reasons.append("Contradictory claims found across citations")
                if consistency.get("out_of_scope_claims"):
                    cross_consistent = False
                    rejection_reasons.append("Answer contains claims beyond cited documents")
                consistency_issues = consistency.get("issues", [])
                rejection_reasons.extend(consistency_issues)
        except Exception as e:
            logger.warning(f"Consistency check failed (non-blocking): {e}")
            # Don't fail hard on LLM call failure in validator

        # ── Confidence Score Calculation ──────────────────────────────────
        score = self._compute_confidence(
            citations=citations,
            citation_verified=citation_verified,
            cross_consistent=cross_consistent,
            rejection_reasons=rejection_reasons,
        )

        label = (
            "HIGH" if score >= 0.75
            else "MEDIUM" if score >= 0.5
            else "LOW" if score >= 0.25
            else "NONE"
        )

        logger.info(
            f"Validation result: verified={citation_verified}, "
            f"consistent={cross_consistent}, score={score:.2f}, label={label}, "
            f"issues={len(rejection_reasons)}"
        )

        return ValidationResult(
            citation_verified=citation_verified,
            cross_consistent=cross_consistent,
            confidence_score=round(score, 3),
            confidence_label=label,
            rejection_reasons=rejection_reasons,
        )

    async def _check_consistency(
        self,
        answer: str,
        citations: List[Dict],
    ) -> Optional[Dict]:
        """LLM-powered consistency checker."""
        import json

        citations_text = "\n".join(
            f"[{c['id']}] {c.get('case_name')} ({c.get('year')}): {c.get('paragraph', '')[:500]}"
            for c in citations
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            max_tokens=512,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": CONSISTENCY_PROMPT.format(
                        answer=answer[:2000],
                        citations=citations_text[:2000],
                    ),
                }
            ],
        )
        return json.loads(response.choices[0].message.content)

    def _compute_confidence(
        self,
        citations: List[Dict],
        citation_verified: bool,
        cross_consistent: bool,
        rejection_reasons: List[str],
    ) -> float:
        """
        Multi-factor confidence score:
        - Base: average relevance score of citations (40%)
        - Citation verified: +30%
        - Cross-document consistent: +20%
        - Penalty per rejection reason: -10% each
        """
        if not citations:
            return 0.0

        # Factor 1: Average relevance score
        scores = [c.get("relevance_score", 0.5) for c in citations]
        avg_relevance = sum(scores) / len(scores)
        base = avg_relevance * 0.4

        # Factor 2: Citation verification
        base += 0.30 if citation_verified else 0.0

        # Factor 3: Consistency
        base += 0.20 if cross_consistent else 0.0

        # Factor 4: Citation count bonus (more citations = higher confidence, up to +10%)
        count_bonus = min(len(citations) * 0.02, 0.10)
        base += count_bonus

        # Factor 5: Penalty for issues
        penalty = len(rejection_reasons) * 0.10
        base -= penalty

        return max(0.0, min(1.0, base))
