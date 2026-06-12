"""
ValidatorAgent
Responsibility: The final verification gate.
Checks citations, document completeness, contradiction risk, and confidence score.
Supports Gemini, Ollama, and Simulation.
"""

import logging
import os
import json
from typing import Dict, List, Optional
import httpx

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
    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "simulation").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_LLM_MODEL", "llama3")
        logger.info("ValidatorAgent initialized")

    async def validate(
        self,
        answer: str,
        citations: List[Dict],
        source_documents: List[Dict],
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> ValidationResult:
        audit = audit_citations(
            answer=answer,
            citations=citations,
            source_documents=source_documents,
        )
        rejection_reasons: List[str] = list(audit.rejection_reasons)
        citation_verified = audit.citation_verified

        cross_consistent = True
        try:
            consistency = await self._check_consistency(
                answer,
                citations,
                provider=provider,
                gemini_key=gemini_key,
            )
            if consistency:
                if consistency.get("contradictions_found"):
                    cross_consistent = False
                    rejection_reasons.append("Contradictory claims found across citations")
                if consistency.get("out_of_scope_claims"):
                    cross_consistent = False
                    rejection_reasons.append("Answer contains claims beyond cited documents")
                rejection_reasons.extend(consistency.get("issues", []))
        except Exception as e:
            logger.warning(f"Consistency check failed (non-blocking): {e}")

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
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> Optional[Dict]:
        """Consistency check routed to active provider."""
        active_provider = provider.lower() if provider else self.provider
        active_gemini_key = gemini_key if gemini_key else self.gemini_key

        if active_provider == "simulation" or (active_provider == "gemini" and not active_gemini_key):
            return {
                "all_claims_cited": True,
                "contradictions_found": False,
                "out_of_scope_claims": False,
                "issues": []
            }

        citations_text = "\n".join(
            f"[{c['id']}] {c.get('case_name')} ({c.get('year')}): {c.get('paragraph', '')[:500]}"
            for c in citations
        )
        prompt = CONSISTENCY_PROMPT.format(
            answer=answer[:2000],
            citations=citations_text[:2000],
        )

        if active_provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={active_gemini_key}"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)

        elif active_provider == "ollama":
            url = f"{self.ollama_host}/api/chat"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={
                        "model": self.ollama_model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False,
                        "options": {"temperature": 0.0},
                        "format": "json"
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["message"]["content"]
                return json.loads(raw_text)

        return None

    def _compute_confidence(
        self,
        citations: List[Dict],
        citation_verified: bool,
        cross_consistent: bool,
        rejection_reasons: List[str],
    ) -> float:
        if not citations:
            return 0.0

        scores = [c.get("relevance_score", 0.5) for c in citations]
        avg_relevance = sum(scores) / len(scores)
        base = avg_relevance * 0.4

        base += 0.30 if citation_verified else 0.0
        base += 0.20 if cross_consistent else 0.0

        count_bonus = min(len(citations) * 0.02, 0.10)
        base += count_bonus

        penalty = len(rejection_reasons) * 0.10
        base -= penalty

        return max(0.0, min(1.0, base))
