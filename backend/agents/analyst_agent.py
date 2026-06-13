"""
LegalAnalystAgent
Responsibility: Given retrieved documents, generate a precise legal answer
with inline citations. Supports Gemini (free cloud), Ollama (local), and Simulation.
"""

import json
import logging
import os
from typing import Dict, List, Optional
import httpx

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
    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_LLM_MODEL", "lexverify-legal")
        logger.info(f"LegalAnalystAgent initialized: provider={self.provider}")

    async def analyze(
        self,
        query: str,
        documents: List[Dict],
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> Optional[Dict]:
        if not documents:
            return {"fallback": True}

        active_provider = provider.lower() if provider else self.provider
        active_gemini_key = gemini_key if gemini_key else self.gemini_key

        if active_provider == "gemini" and active_gemini_key:
            return await self._analyze_gemini(query, documents, active_gemini_key)
        elif active_provider == "ollama":
            return await self._analyze_ollama(query, documents)
        else:
            return self._simulate_analysis(query, documents)

    async def _analyze_gemini(self, query: str, documents: List[Dict], gemini_key: str) -> Optional[Dict]:
        context = self._build_context(documents)
        prompt = USER_PROMPT_TEMPLATE.format(query=query, context=context)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_and_validate_llm_response(raw_text, documents)
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return self._simulate_analysis(query, documents)

    async def _analyze_ollama(self, query: str, documents: List[Dict]) -> Optional[Dict]:
        context = self._build_context(documents)
        prompt = USER_PROMPT_TEMPLATE.format(query=query, context=context)
        url = f"{self.ollama_host}/api/chat"
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    url,
                    json={
                        "model": self.ollama_model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
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
                return self._parse_and_validate_llm_response(raw_text, documents)
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return self._simulate_analysis(query, documents)

    def _parse_and_validate_llm_response(self, raw_text: str, documents: List[Dict]) -> Dict:
        try:
            result = json.loads(raw_text)
            if result.get("fallback"):
                return {"fallback": True}

            if not result.get("answer") or not result.get("citations"):
                return {"fallback": True}

            doc_ids = {d["doc_id"] for d in documents if "doc_id" in d}
            validated_citations = []
            for cite in result["citations"]:
                if cite.get("id") in doc_ids:
                    validated_citations.append(cite)
                else:
                    logger.warning(f"Removing unverifiable citation: {cite.get('id')}")

            if not validated_citations:
                return {"fallback": True}

            result["citations"] = validated_citations
            return result
        except Exception as e:
            logger.error(f"Failed to parse LLM json: {e}")
            return {"fallback": True}

    def _simulate_analysis(self, query: str, documents: List[Dict]) -> Dict:
        citations = []
        answer_parts = []
        
        for doc in documents:
            doc_id = doc.get("doc_id", "IK_2023_0001")
            case_name = doc.get("case_name", "Case")
            court = doc.get("court", "Court")
            year = doc.get("year", 2000)
            text = doc.get("text", doc.get("summary", ""))
            
            snippet = text[:200] + "..." if len(text) > 200 else text
            answer_parts.append(
                f"Under the ruling in {case_name} ({court}, {year}), "
                f"it was established that: {snippet.strip()} [CITE:{doc_id}]"
            )
            citations.append({
                "id": doc_id,
                "case_name": case_name,
                "court": court,
                "year": year,
                "paragraph": text[:150],
                "url": doc.get("url", ""),
                "source": doc.get("source", "indian_kanoon"),
                "relevance_score": doc.get("relevance_score", 0.95),
            })
            
        answer = " ".join(answer_parts)
        return {
            "fallback": False,
            "answer": answer,
            "citations": citations,
        }

    def _build_context(self, documents: List[Dict]) -> str:
        parts = []
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get("doc_id", f"doc_{i}")
            case_name = doc.get("case_name", "Unknown v. Unknown")
            court = doc.get("court", "Unknown Court")
            year = doc.get("year", "Unknown Year")
            text = doc.get("text", doc.get("summary", ""))[:3000]
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
