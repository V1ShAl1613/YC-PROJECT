"""
Legal Data Ingestion Pipeline
Ingests case law from:
  - Indian Kanoon (https://indiankanoon.org)
  - CourtListener (https://www.courtlistener.com/api/)

Run: python scripts/ingest.py --source all --limit 100
"""

import asyncio
import argparse
import logging
import sys
import os
import time
import httpx
from typing import List, Dict, Optional, AsyncGenerator
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.vector_store import VectorStore
from retrieval.embedder import Embedder
from retrieval.metadata_db import MetadataDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingestor")

COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v3"
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_API_TOKEN", "")
INDIAN_KANOON_API = "https://api.indiankanoon.org"
INDIAN_KANOON_TOKEN = os.getenv("INDIAN_KANOON_API_TOKEN", "")

BATCH_SIZE = 10
RATE_LIMIT_DELAY = 1.0  # seconds between requests


class CourtListenerIngester:
    """
    Ingests opinions from CourtListener REST API.
    Requires free API token from https://www.courtlistener.com/register/
    """

    def __init__(self):
        self.headers = {"Authorization": f"Token {COURTLISTENER_TOKEN}"} if COURTLISTENER_TOKEN else {}

    async def fetch_opinions(
        self,
        query: str = "civil rights",
        court: str = "scotus",
        limit: int = 50,
    ) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{COURTLISTENER_API}/search/"
            params = {
                "q": query,
                "court": court,
                "type": "o",
                "order_by": "score desc",
                "page_size": min(limit, 20),
            }
            fetched = 0
            while url and fetched < limit:
                try:
                    resp = await client.get(url, params=params, headers=self.headers)
                    resp.raise_for_status()
                    data = resp.json()

                    for result in data.get("results", []):
                        if fetched >= limit:
                            break
                        doc = self._parse_opinion(result)
                        if doc:
                            yield doc
                            fetched += 1

                    url = data.get("next")
                    params = {}  # pagination URL already has params
                    await asyncio.sleep(RATE_LIMIT_DELAY)

                except httpx.HTTPError as e:
                    logger.error(f"CourtListener HTTP error: {e}")
                    break

    def _parse_opinion(self, result: Dict) -> Optional[Dict]:
        try:
            case_name = result.get("caseName", "Unknown v. Unknown")
            year = int(result.get("dateFiled", "1900-01-01")[:4]) if result.get("dateFiled") else 0
            doc_id = f"CL_{result.get('id', '')}"
            return {
                "doc_id": doc_id,
                "case_name": case_name,
                "court": result.get("court", ""),
                "year": year,
                "jurisdiction": "usa",
                "judge": result.get("judge", ""),
                "source": "courtlistener",
                "url": f"https://www.courtlistener.com{result.get('absolute_url', '')}",
                "summary": result.get("snippet", ""),
                "text": result.get("text", result.get("snippet", "")),
                "metadata": {
                    "docket_number": result.get("docketNumber", ""),
                    "citation": result.get("citation", []),
                },
            }
        except Exception as e:
            logger.warning(f"Failed to parse opinion: {e}")
            return None


class IndianKanoonIngester:
    """
    Ingests judgments from Indian Kanoon.
    Uses their API or falls back to structured scraping.
    """

    def __init__(self):
        self.headers = {
            "Authorization": f"Token {INDIAN_KANOON_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def fetch_judgments(
        self,
        query: str = "anticipatory bail",
        pagenum: int = 0,
        limit: int = 50,
    ) -> AsyncGenerator[Dict, None]:
        async with httpx.AsyncClient(timeout=30) as client:
            fetched = 0
            page = pagenum

            while fetched < limit:
                try:
                    resp = await client.post(
                        f"{INDIAN_KANOON_API}/search/",
                        data={"formInput": query, "pagenum": page},
                        headers=self.headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    docs = data.get("docs", [])

                    if not docs:
                        break

                    for doc_meta in docs:
                        if fetched >= limit:
                            break
                        tid = doc_meta.get("tid")
                        if tid:
                            full_doc = await self._fetch_full_doc(client, tid)
                            if full_doc:
                                yield full_doc
                                fetched += 1
                            await asyncio.sleep(RATE_LIMIT_DELAY)

                    page += 1
                    await asyncio.sleep(RATE_LIMIT_DELAY)

                except (httpx.HTTPError, KeyError) as e:
                    logger.error(f"Indian Kanoon error: {e}")
                    break

    async def _fetch_full_doc(self, client: httpx.AsyncClient, tid: str) -> Optional[Dict]:
        try:
            resp = await client.post(
                f"{INDIAN_KANOON_API}/doc/{tid}/",
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

            title = data.get("title", "")
            doc_id = f"IK_{tid}"
            year = self._extract_year(data)

            # Extract clean text from HTML
            html = data.get("doc", "")
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)[:10000]

            return {
                "doc_id": doc_id,
                "case_name": title,
                "court": data.get("docsource", ""),
                "year": year,
                "jurisdiction": "india",
                "judge": "",
                "source": "indian_kanoon",
                "url": f"https://indiankanoon.org/doc/{tid}/",
                "summary": text[:500],
                "text": text,
                "metadata": {"tid": tid},
            }
        except Exception as e:
            logger.warning(f"Failed to fetch doc {tid}: {e}")
            return None

    @staticmethod
    def _extract_year(data: Dict) -> int:
        for field in ["publishdate", "reportcite"]:
            val = str(data.get(field, ""))
            import re
            match = re.search(r"\b(19|20)\d{2}\b", val)
            if match:
                return int(match.group())
        return 0


class Ingestor:
    """Main ingestion coordinator."""

    def __init__(self):
        self.vector_store = VectorStore()
        self.embedder = Embedder()
        self.metadata_db = MetadataDB()
        self.cl_ingester = CourtListenerIngester()
        self.ik_ingester = IndianKanoonIngester()

    async def ingest_batch(self, documents: List[Dict]) -> int:
        """Embed and store a batch of documents."""
        texts = [d.get("text", d.get("summary", ""))[:8000] for d in documents]
        vectors = await self.embedder.embed_batch(texts)

        count = 0
        for doc, vector in zip(documents, vectors):
            # Store in metadata DB
            await self.metadata_db.insert(doc)

            # Store in vector index
            await self.vector_store.add(
                doc_id=doc["doc_id"],
                vector=vector,
                metadata={
                    k: v for k, v in doc.items()
                    if k not in ("text", "metadata")
                },
            )
            count += 1

        return count

    async def run(
        self,
        source: str = "all",
        limit: int = 100,
        query: str = "fundamental rights",
    ):
        total = 0
        batch: List[Dict] = []

        async def flush():
            nonlocal total
            if batch:
                n = await self.ingest_batch(batch)
                total += n
                logger.info(f"Ingested batch: {n} docs (total={total})")
                batch.clear()

        if source in ("courtlistener", "all"):
            logger.info(f"Ingesting from CourtListener (limit={limit // 2})...")
            async for doc in self.cl_ingester.fetch_opinions(query=query, limit=limit // 2):
                batch.append(doc)
                if len(batch) >= BATCH_SIZE:
                    await flush()
            await flush()

        if source in ("indian_kanoon", "all"):
            logger.info(f"Ingesting from Indian Kanoon (limit={limit // 2})...")
            async for doc in self.ik_ingester.fetch_judgments(query=query, limit=limit // 2):
                batch.append(doc)
                if len(batch) >= BATCH_SIZE:
                    await flush()
            await flush()

        logger.info(f"✅ Ingestion complete. Total documents: {total}")
        return total


async def main():
    parser = argparse.ArgumentParser(description="Legal data ingestion pipeline")
    parser.add_argument("--source", choices=["all", "courtlistener", "indian_kanoon"], default="all")
    parser.add_argument("--limit", type=int, default=100, help="Max documents to ingest")
    parser.add_argument("--query", type=str, default="fundamental rights bail arrest", help="Search query")
    args = parser.parse_args()

    ingestor = Ingestor()
    await ingestor.run(source=args.source, limit=args.limit, query=args.query)


if __name__ == "__main__":
    asyncio.run(main())
