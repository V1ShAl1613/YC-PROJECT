"""
Embedder — wraps OpenAI text-embedding-3-small for query and document embedding.
"""

import logging
import os
import hashlib
import json
from typing import List
import openai

logger = logging.getLogger("embedder")

MODEL = "text-embedding-3-small"
CACHE_FILE = "./data/embed_cache.json"


class Embedder:
    """
    Embedding generator with in-memory + disk cache.
    In production, replace disk cache with Redis.
    """

    def __init__(self):
        self.client = openai.AsyncOpenAI()
        self.model = MODEL
        self._cache: dict = self._load_cache()
        logger.info(f"Embedder initialized: model={MODEL}, cache={len(self._cache)} entries")

    async def embed(self, text: str) -> List[float]:
        """Return embedding vector for a single text."""
        key = hashlib.md5(text.encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]

        text = text[:8000]  # token budget
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float",
            )
            vector = response.data[0].embedding
            self._cache[key] = vector
            self._save_cache()
            return vector
        except openai.APIError as e:
            logger.error(f"Embedding API error: {e}")
            # Return zero vector as fallback (retrieval will return no results)
            return [0.0] * 1536

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding for ingestion pipeline."""
        texts = [t[:8000] for t in texts]
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]
        except openai.APIError as e:
            logger.error(f"Batch embedding error: {e}")
            return [[0.0] * 1536] * len(texts)

    def _load_cache(self) -> dict:
        os.makedirs("./data", exist_ok=True)
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")
