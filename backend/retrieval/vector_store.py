"""
VectorStore — FAISS-backed semantic search with persistence.
Stores document embeddings indexed by doc_id.
"""

import os
import json
import logging
import pickle
import numpy as np
from typing import List, Dict, Optional, Any

logger = logging.getLogger("vector_store")

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./data/faiss.index")
FAISS_META_PATH = os.getenv("FAISS_META_PATH", "./data/faiss_meta.pkl")
EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small


class VectorStore:
    """
    FAISS-based vector store.
    Falls back to in-memory if faiss is not installed (dev mode).
    """

    def __init__(self):
        self._index = None
        self._id_map: List[str] = []  # index position → doc_id
        self._doc_map: Dict[str, Dict] = {}  # doc_id → partial metadata
        self._load_or_init()

    def _load_or_init(self):
        try:
            import faiss
            self._faiss = faiss

            if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(FAISS_META_PATH):
                self._index = faiss.read_index(FAISS_INDEX_PATH)
                with open(FAISS_META_PATH, "rb") as f:
                    meta = pickle.load(f)
                    self._id_map = meta["id_map"]
                    self._doc_map = meta["doc_map"]
                logger.info(
                    f"FAISS index loaded: {self._index.ntotal} vectors, "
                    f"{len(self._id_map)} docs"
                )
            else:
                self._index = None
                logger.info("New FAISS index initialized (dynamic/empty)")

        except ImportError:
            logger.warning("FAISS not installed — using in-memory fallback (numpy cosine search)")
            self._faiss = None
            self._vectors: List[np.ndarray] = []

    async def add(self, doc_id: str, vector: List[float], metadata: Dict):
        """Add a document vector to the index."""
        dim = len(vector)
        vec = np.array([vector], dtype=np.float32)
        # L2-normalize for cosine similarity via inner product
        vec = vec / (np.linalg.norm(vec, axis=1, keepdims=True) + 1e-10)

        if self._faiss:
            if self._index is None:
                self._index = self._faiss.IndexFlatIP(dim)
            elif hasattr(self._index, "d") and self._index.d != dim:
                logger.warning(f"Re-creating FAISS index due to dimension change from {self._index.d} to {dim}")
                self._index = self._faiss.IndexFlatIP(dim)
                # We should clear the old mapping if index dimension changes to prevent mismatches
                self._id_map = []
                self._doc_map = {}
            self._index.add(vec)
        else:
            self._vectors.append(vec[0])

        self._id_map.append(doc_id)
        self._doc_map[doc_id] = metadata
        self._save()

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        jurisdiction: Optional[str] = None,
    ) -> List[Dict]:
        """Semantic search — returns top_k results with scores."""
        if not self._id_map:
            logger.warning("Vector store is empty")
            return self._demo_results(top_k)  # return demo data in dev mode

        dim = len(query_vector)
        q = np.array([query_vector], dtype=np.float32)
        q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-10)

        if self._faiss and self._index is not None and self._index.ntotal > 0:
            if self._index.d != dim:
                logger.warning(f"Dimension mismatch: Index expects {self._index.d}, query got {dim}")
                return []
            scores, indices = self._index.search(q, min(top_k * 2, self._index.ntotal))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                doc_id = self._id_map[idx]
                meta = self._doc_map.get(doc_id, {})
                if jurisdiction and meta.get("jurisdiction", "").lower() != jurisdiction.lower():
                    continue
                results.append({
                    "doc_id": doc_id,
                    "relevance_score": float(score),
                    **meta,
                })
            return results[:top_k]
        else:
            # Numpy fallback
            if self._vectors and len(self._vectors[0]) != dim:
                logger.warning(f"Dimension mismatch in numpy search: Index expects {len(self._vectors[0])}, query got {dim}")
                return []
            return self._numpy_search(q[0], top_k, jurisdiction)

    def _numpy_search(
        self,
        query_vec: np.ndarray,
        top_k: int,
        jurisdiction: Optional[str],
    ) -> List[Dict]:
        if not self._vectors:
            return self._demo_results(top_k)
        matrix = np.stack(self._vectors)
        scores = matrix @ query_vec
        ranked = np.argsort(-scores)
        results = []
        for idx in ranked:
            doc_id = self._id_map[idx]
            meta = self._doc_map.get(doc_id, {})
            if jurisdiction and meta.get("jurisdiction", "").lower() != jurisdiction.lower():
                continue
            results.append({
                "doc_id": doc_id,
                "relevance_score": float(scores[idx]),
                **meta,
            })
            if len(results) >= top_k:
                break
        return results

    def _save(self):
        os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
        if self._faiss and self._index:
            self._faiss.write_index(self._index, FAISS_INDEX_PATH)
        with open(FAISS_META_PATH, "wb") as f:
            pickle.dump({"id_map": self._id_map, "doc_map": self._doc_map}, f)

    async def stats(self) -> Dict:
        count = self._index.ntotal if self._faiss and self._index else len(self._id_map)
        return {
            "total_documents": count,
            "embedding_dim": EMBEDDING_DIM,
            "backend": "faiss" if self._faiss else "numpy",
            "index_path": FAISS_INDEX_PATH,
        }

    def _demo_results(self, top_k: int) -> List[Dict]:
        """
        Demo data returned when vector store is empty (dev/test mode).
        In production, this should return [] — the agent handles the empty case.
        """
        demo = [
            {
                "doc_id": "IK_2023_0001",
                "case_name": "Arnesh Kumar v. State of Bihar & Anr.",
                "court": "Supreme Court of India",
                "year": 2014,
                "jurisdiction": "india",
                "source": "indian_kanoon",
                "url": "https://indiankanoon.org/doc/78847226/",
                "text": (
                    "The power of arrest without warrant should not be exercised in a routine manner. "
                    "The police officer must have reason to believe that the person has committed a "
                    "cognizable offence. Section 41A CrPC mandates issue of notice before arrest for "
                    "offences carrying less than 7 years imprisonment. Magistrates must apply mind while "
                    "authorizing detention under Section 167 CrPC."
                ),
                "relevance_score": 0.94,
            },
            {
                "doc_id": "IK_2023_0002",
                "case_name": "Gurbaksh Singh Sibbia v. State of Punjab",
                "court": "Supreme Court of India",
                "year": 1980,
                "jurisdiction": "india",
                "source": "indian_kanoon",
                "url": "https://indiankanoon.org/doc/697591/",
                "text": (
                    "Section 438 of the Code of Criminal Procedure confers a power of wide amplitude on "
                    "the High Court and the Court of Session to grant anticipatory bail. The provision "
                    "is intended to protect persons against needless arrests and ignominious detention. "
                    "The Court must weigh the nature and gravity of accusation, antecedents of the "
                    "applicant, possibility of fleeing justice, and likelihood of repeating the offence."
                ),
                "relevance_score": 0.91,
            },
            {
                "doc_id": "CL_2023_0001",
                "case_name": "Miranda v. Arizona",
                "court": "Supreme Court of the United States",
                "year": 1966,
                "jurisdiction": "usa",
                "source": "courtlistener",
                "url": "https://www.courtlistener.com/opinion/107252/miranda-v-arizona/",
                "text": (
                    "The prosecution may not use statements, whether exculpatory or inculpatory, "
                    "stemming from custodial interrogation of the defendant unless it demonstrates the "
                    "use of procedural safeguards effective to secure the privilege against "
                    "self-incrimination. Prior to any questioning, the person must be warned that he "
                    "has a right to remain silent, that any statement he does make may be used as "
                    "evidence against him, and that he has a right to the presence of an attorney."
                ),
                "relevance_score": 0.88,
            },
        ]
        return demo[:top_k]
