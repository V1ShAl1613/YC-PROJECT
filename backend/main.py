"""
Verification-First Legal AI Agent — FastAPI Backend
Production-grade legal research assistant with zero hallucination policy.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import time
import logging
import uuid

from agents.orchestrator import LegalAgentOrchestrator
from api.models import QueryRequest, QueryResponse, SearchRequest, CaseSimilarityRequest
from api.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("legal_ai")

app = FastAPI(
    title="Verification-First Legal AI Agent",
    description="High-precision legal intelligence system — Accuracy > Fluency, Proof > Confidence",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = LegalAgentOrchestrator()

app.include_router(health_router, prefix="/api")


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(f"[{request_id}] {response.status_code} — {elapsed}ms")
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed}ms"
    return response


@app.post("/api/query", response_model=QueryResponse)
async def legal_query(request: QueryRequest):
    """
    Primary endpoint: accepts a legal question, runs multi-agent pipeline,
    returns citation-backed answer or explicit fallback if no verified source found.
    """
    logger.info(f"Legal query received: {request.query[:80]}...")
    try:
        result = await orchestrator.run(
            query=request.query,
            jurisdiction=request.jurisdiction,
            top_k=request.top_k,
        )
        return result
    except Exception as e:
        logger.error(f"Query pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/search")
async def search_cases(request: SearchRequest):
    """Full-text + semantic search across the legal corpus."""
    try:
        results = await orchestrator.search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/similar-cases")
async def similar_cases(request: CaseSimilarityRequest):
    """Find cases semantically similar to a given case ID or text snippet."""
    try:
        results = await orchestrator.find_similar(
            case_id=request.case_id,
            text=request.text,
            top_k=request.top_k,
        )
        return {"similar_cases": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/case/{case_id}")
async def get_case(case_id: str):
    """Retrieve full case document by ID."""
    try:
        case = await orchestrator.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def system_stats():
    """Returns corpus stats, model info, and system health metrics."""
    return await orchestrator.get_stats()


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Endpoint not found"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
