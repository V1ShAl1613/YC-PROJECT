"""
ResearchAgent
Responsibility: Convert user query to embeddings, retrieve Top-K relevant
legal documents from the vector store and structured metadata DB.
Sources: Indian Kanoon, CourtListener.
"""

import logging
import hashlib
from typing import Optional, List, Dict, Any

from retrieval.vector_store import VectorStore
from retrieval.embedder import Embedder
from retrieval.metadata_db import MetadataDB

logger = logging.getLogger("research_agent")


class ResearchAgent:
    """
    Stage 1 Agent: Document Retrieval
    - Embeds user query
    - Searches FAISS vector store for Top-K semantic matches
    - Enriches results with structured metadata (court, year, judges)
    - Filters by jurisdiction if specified
    """

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.metadata_db = MetadataDB()
        logger.info("ResearchAgent initialized")

    async def retrieve(
        self,
        query: str,
        jurisdiction: str = "all",
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Main retrieval method.
        Returns list of enriched document dicts with full metadata.
        """
        logger.info(f"Embedding query and searching vector store (top_k={top_k})")

        # 1. Embed the query
        query_vector = await self.embedder.embed(query)

        # 2. Search vector store
        raw_results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k * 2,  # over-fetch to allow jurisdiction filtering
            jurisdiction=jurisdiction if jurisdiction != "all" else None,
        )

        if not raw_results:
            logger.warning("Vector store returned 0 results")
            return []

        # 3. Enrich with metadata
        enriched = []
        for hit in raw_results:
            meta = await self.metadata_db.get(hit["doc_id"])
            if meta:
                enriched.append({**hit, **meta})
            else:
                enriched.append(hit)

        # 4. Apply jurisdiction filter post-fetch if needed
        if jurisdiction and jurisdiction != "all":
            enriched = [
                d for d in enriched
                if d.get("jurisdiction", "").lower() == jurisdiction.lower()
            ]

        # 5. Deduplicate and take top_k
        seen = set()
        unique = []
        for doc in enriched:
            did = doc.get("doc_id") or doc.get("id")
            if did not in seen:
                seen.add(did)
                unique.append(doc)
            if len(unique) >= top_k:
                break

        logger.info(f"Retrieved {len(unique)} unique documents after filtering")
        return unique

    async def search(
        self,
        query: str,
        filters: Optional[Any] = None,
        top_k: int = 10,
    ) -> List[Dict]:
        """Semantic + optional metadata-filtered search."""
        query_vector = await self.embedder.embed(query)
        results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
        )
        if filters:
            results = self._apply_filters(results, filters)
        return results

    async def find_similar(
        self,
        case_id: Optional[str] = None,
        text: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """Find cases similar to a given case or text snippet."""
        if case_id:
            doc = await self.metadata_db.get(case_id)
            if doc:
                text = doc.get("summary") or doc.get("text", "")
        if not text:
            return []
        query_vector = await self.embedder.embed(text)
        results = await self.vector_store.search(query_vector=query_vector, top_k=top_k + 1)
        # Remove the source case itself if it appears
        return [r for r in results if r.get("doc_id") != case_id][:top_k]

    async def get_case(self, case_id: str) -> Optional[Dict]:
        return await self.metadata_db.get(case_id)

    async def get_corpus_stats(self) -> Dict:
        return await self.vector_store.stats()

    def _apply_filters(self, results: List[Dict], filters: Any) -> List[Dict]:
        out = results
        if hasattr(filters, "court") and filters.court:
            out = [r for r in out if filters.court.lower() in r.get("court", "").lower()]
        if hasattr(filters, "year_from") and filters.year_from:
            out = [r for r in out if r.get("year", 0) >= filters.year_from]
        if hasattr(filters, "year_to") and filters.year_to:
            out = [r for r in out if r.get("year", 9999) <= filters.year_to]
        return out
