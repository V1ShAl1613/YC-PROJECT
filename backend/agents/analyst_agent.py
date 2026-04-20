"""
LegalAnalystAgent
Responsibility: Given retrieved documents, generate a precise legal answer
with inline citations. Strict prompt engineering ensures the LLM NEVER
infers facts outside the provided context.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any

import openai

logger = logging.getLogger("analyst_agent")

SYSTEM_PROMPT = """You are a senior legal analyst working for a law firm's research department.

ABSOLUTE RULES — VIOLATION MEANS TERMINATION:
1. Answer ONLY using the provided legal documents. NEVER use external knowledge.
2. Every factual claim MUST be followed by a citation in format: [CITE:doc_id]
3. If the provided documents do not contain sufficient information, respond ONLY with: {"fallback": true}
4. Do NOT infer, assume, extrapolate, or hallucinate ANY legal facts.
5. Do NOT cite a document unless its content directly supports the claim.
6. Use precise legal language. Accuracy > Fluency.

OUTPUT FORMAT (strict JSON only — no markdown, no prose outside JSON):
{
  "fallback": false,
  "answer": "Legal answer with inline [CITE:doc_id] markers...",
  "citations": [
    {
      "id": "doc_id",
      "case_name": "...",
      "court": "...",
      "year": 2020,
      "paragraph": "Exact relevant paragraph or section from the document",
      "url": "...",
      "source": "indian_kanoon or courtlistener",
      "relevance_score": 0.92
    }
  ]
}
"""

USER_PROMPT_TEMPLATE = """LEGAL QUESTION: {query}

RETRIEVED LEGAL DOCUMENTS:
{context}

Using ONLY the documents above, provide a precise legal answer with citations.
If the documents do not contain sufficient information to answer, output: {{"fallback": true}}
"""


class LegalAnalystAgent:
    """
    Stage 2 Agent: Legal Analysis & Answer Synthesis
    - Builds a strict context window from retrieved documents
    - Calls LLM with zero-hallucination prompt
    - Parses and structures the JSON response
    """

    def __init__(self):
        self.client = openai.AsyncOpenAI()
        self.model = "gpt-4o"
        logger.info(f"LegalAnalystAgent initialized with model={self.model}")

    async def analyze(
        self,
        query: str,
        documents: List[Dict],
    ) -> Optional[Dict]:
        """
        Returns dict with keys: answer, citations, fallback
        Returns None on hard failure.
        """
        if not documents:
            return {"fallback": True}

        context = self._build_context(documents)
        prompt = USER_PROMPT_TEMPLATE.format(query=query, context=context)

        logger.info(f"Calling {self.model} with {len(documents)} context documents")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,  # deterministic — zero creativity for legal facts
                max_tokens=2048,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)

            if result.get("fallback"):
                logger.info("LLM returned fallback — insufficient context")
                return {"fallback": True}

            # Validate structure
            if not result.get("answer") or not result.get("citations"):
                logger.warning("LLM response missing required fields")
                return {"fallback": True}

            # Cross-validate: every doc_id in citations must be in retrieved docs
            doc_ids = {d["doc_id"] for d in documents if "doc_id" in d}
            validated_citations = []
            for cite in result["citations"]:
                if cite.get("id") in doc_ids:
                    validated_citations.append(cite)
                else:
                    logger.warning(f"Removing unverifiable citation: {cite.get('id')}")

            if not validated_citations:
                logger.warning("All citations were unverifiable — returning fallback")
                return {"fallback": True}

            result["citations"] = validated_citations
            logger.info(f"Analysis complete: {len(validated_citations)} verified citations")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"LLM returned non-JSON response: {e}")
            return {"fallback": True}
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def _build_context(self, documents: List[Dict]) -> str:
        """
        Builds a structured context string from retrieved documents.
        Each document is clearly labeled with its ID for citation matching.
        """
        parts = []
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get("doc_id", f"doc_{i}")
            case_name = doc.get("case_name", "Unknown v. Unknown")
            court = doc.get("court", "Unknown Court")
            year = doc.get("year", "Unknown Year")
            text = doc.get("text", doc.get("summary", ""))[:3000]  # token budget
            url = doc.get("url", "")
            source = doc.get("source", "unknown")

            parts.append(
                f"[DOCUMENT ID: {doc_id}]\n"
                f"Case: {case_name}\n"
                f"Court: {court} | Year: {year} | Source: {source}\n"
                f"URL: {url}\n"
                f"Content:\n{text}\n"
                f"{'─' * 60}"
            )

        return "\n\n".join(parts)
