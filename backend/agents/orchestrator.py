"""
LegalAgentOrchestrator
Coordinates three specialized agents in a sequential pipeline:
  1. ResearchAgent    — retrieves relevant legal documents
  2. LegalAnalystAgent — synthesizes answer from retrieved context ONLY
  3. ValidatorAgent   — verifies citations, checks consistency, scores confidence
"""

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any

from agents.research_agent import ResearchAgent
from agents.analyst_agent import LegalAnalystAgent
from agents.validator_agent import ValidatorAgent
from api.models import QueryResponse, Citation, ValidationResult

logger = logging.getLogger("orchestrator")

FALLBACK_RESPONSE = QueryResponse(
    query="",
    answer="No verified legal information found. The system could not locate any relevant, "
           "verified case law or statutory provisions to answer this query with citations. "
           "Please consult a licensed legal professional.",
    citations=[],
    validation=ValidationResult(
        citation_verified=False,
        cross_consistent=False,
        confidence_score=0.0,
        confidence_label="NONE",
        rejection_reasons=["No relevant documents retrieved from verified sources"],
    ),
    fallback=True,
    latency_ms=0.0,
)


class LegalAgentOrchestrator:
    """
    Strict pipeline: no answer is ever returned without verified citations.
    If any stage fails to produce verifiable output, the fallback is returned.
    """

    def __init__(self):
        self.research_agent = ResearchAgent()
        self.analyst_agent = LegalAnalystAgent()
        self.validator_agent = ValidatorAgent()
        logger.info("LegalAgentOrchestrator initialized with 3-agent pipeline")

    async def run(
        self,
        query: str,
        jurisdiction: str = "all",
        top_k: int = 5,
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> QueryResponse:
        start = time.time()
        trace: List[str] = []

        try:
            # ── Stage 1: Research Agent ───────────────────────────────────
            trace.append("Stage 1: ResearchAgent — retrieving documents")
            logger.info(f"[Stage 1] Retrieving docs for: {query[:60]}...")
            documents = await self.research_agent.retrieve(
                query=query,
                jurisdiction=jurisdiction,
                top_k=top_k,
                provider=provider,
                gemini_key=gemini_key,
            )

            if not documents:
                trace.append("Stage 1 result: NO DOCUMENTS FOUND — returning fallback")
                fallback = FALLBACK_RESPONSE.copy()
                fallback.query = query
                fallback.latency_ms = _ms(start)
                fallback.agent_trace = trace
                return fallback

            trace.append(f"Stage 1 result: {len(documents)} documents retrieved")

            # ── Stage 2: Legal Analyst Agent ──────────────────────────────
            trace.append("Stage 2: LegalAnalystAgent — synthesizing answer from context only")
            analysis = await self.analyst_agent.analyze(
                query=query,
                documents=documents,
                provider=provider,
                gemini_key=gemini_key,
            )

            if not analysis or analysis.get("fallback"):
                trace.append("Stage 2 result: INSUFFICIENT CONTEXT — returning fallback")
                fallback = FALLBACK_RESPONSE.copy()
                fallback.query = query
                fallback.latency_ms = _ms(start)
                fallback.agent_trace = trace
                return fallback

            trace.append(f"Stage 2 result: answer generated with {len(analysis['citations'])} raw citations")

            # ── Stage 3: Validator Agent ──────────────────────────────────
            trace.append("Stage 3: ValidatorAgent — verifying citations and consistency")
            validation_result = await self.validator_agent.validate(
                answer=analysis["answer"],
                citations=analysis["citations"],
                source_documents=documents,
                provider=provider,
                gemini_key=gemini_key,
            )

            if not validation_result.citation_verified or validation_result.confidence_score < 0.4:
                trace.append(
                    f"Stage 3 result: VALIDATION FAILED "
                    f"(confidence={validation_result.confidence_score:.2f}) — returning fallback"
                )
                fallback = FALLBACK_RESPONSE.copy()
                fallback.query = query
                fallback.validation = validation_result
                fallback.latency_ms = _ms(start)
                fallback.agent_trace = trace
                return fallback

            trace.append(
                f"Stage 3 result: VALIDATED (confidence={validation_result.confidence_score:.2f})"
            )

            citations = [Citation(**c) for c in analysis["citations"]]
            response = QueryResponse(
                query=query,
                answer=analysis["answer"],
                citations=citations,
                validation=validation_result,
                fallback=False,
                latency_ms=_ms(start),
                agent_trace=trace,
            )
            logger.info(
                f"Pipeline complete — {len(citations)} citations, "
                f"confidence={validation_result.confidence_score:.2f}, "
                f"latency={response.latency_ms}ms"
            )
            return response

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            fallback = FALLBACK_RESPONSE.copy()
            fallback.query = query
            fallback.latency_ms = _ms(start)
            fallback.agent_trace = trace + [f"PIPELINE ERROR: {str(e)}"]
            return fallback

    async def search(
        self,
        query: str,
        filters: Optional[Any] = None,
        top_k: int = 10,
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> List[Dict]:
        return await self.research_agent.search(
            query=query,
            filters=filters,
            top_k=top_k,
            provider=provider,
            gemini_key=gemini_key,
        )

    async def find_similar(
        self,
        case_id: Optional[str] = None,
        text: Optional[str] = None,
        top_k: int = 5,
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> List[Dict]:
        return await self.research_agent.find_similar(
            case_id=case_id,
            text=text,
            top_k=top_k,
            provider=provider,
            gemini_key=gemini_key,
        )

    async def get_case(self, case_id: str) -> Optional[Dict]:
        return await self.research_agent.get_case(case_id)

    async def get_stats(self) -> Dict:
        return {
            "corpus": await self.research_agent.get_corpus_stats(),
            "agents": {
                "research": "ResearchAgent v1.0",
                "analyst": "LegalAnalystAgent v1.0",
                "validator": "ValidatorAgent v1.0",
            },
            "pipeline": "Sequential 3-Agent RAG with Verification",
            "hallucination_policy": "ZERO TOLERANCE — fallback on any unverified claim",
        }


def _ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)
