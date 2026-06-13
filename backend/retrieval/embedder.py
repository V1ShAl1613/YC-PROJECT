"""
Embedder — supports multiple free-tier and local model providers:
1. gemini (text-embedding-004)
2. ollama (nomic-embed-text or custom)
3. simulation (local deterministic mock)
"""

import logging
import os
import hashlib
import json
from typing import List, Optional
import numpy as np
import httpx

logger = logging.getLogger("embedder")

CACHE_FILE = "./data/embed_cache.json"


class Embedder:
    def __init__(self):
        self.provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        
        self._cache: dict = self._load_cache()
        logger.info(f"Embedder initialized: provider={self.provider}, cache={len(self._cache)} entries")

    async def embed(
        self,
        text: str,
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> List[float]:
        """Return embedding vector for a single text."""
        key = hashlib.md5(text.encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]

        text = text[:8000]  # token budget

        active_provider = provider.lower() if provider else self.provider
        active_gemini_key = gemini_key if gemini_key else self.gemini_key

        if active_provider == "gemini" and active_gemini_key:
            vector = await self._embed_gemini(text, active_gemini_key)
        elif active_provider == "ollama":
            vector = await self._embed_ollama(text)
        else:
            # simulation or fallback
            vector = self._embed_simulation(key, 768 if active_provider == "gemini" else 1536)

        if vector:
            self._cache[key] = vector
            self._save_cache()
            return vector
        return self._embed_simulation(key, 768)

    async def embed_batch(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> List[List[float]]:
        """Batch embedding for ingestion pipeline."""
        results = []
        for text in texts:
            vec = await self.embed(text, provider=provider, gemini_key=gemini_key)
            results.append(vec)
        return results

    async def _embed_gemini(self, text: str, gemini_key: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={gemini_key}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url,
                    json={
                        "content": {
                            "parts": [{"text": text}]
                        }
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]["values"]
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            return []

    async def _embed_ollama(self, text: str) -> List[float]:
        url = f"{self.ollama_host}/api/embeddings"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url,
                    json={
                        "model": self.ollama_model,
                        "prompt": text
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            return []

    def _embed_simulation(self, key: str, dim: int) -> List[float]:
        np.random.seed(int(key[:8], 16) % (2**32))
        return np.random.randn(dim).tolist()

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
