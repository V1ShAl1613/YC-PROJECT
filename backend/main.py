"""
Verification-First Legal AI Agent — FastAPI Backend
Production-grade legal research assistant with zero hallucination policy.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Header
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
async def legal_query(
    request: QueryRequest,
    x_model_provider: Optional[str] = Header(None),
    x_gemini_api_key: Optional[str] = Header(None),
):
    """
    Primary endpoint: accepts a legal question, runs multi-agent pipeline,
    returns citation-backed answer or explicit fallback if no verified source found.
    """
    logger.info(f"Legal query received: {request.query[:80]}... provider={x_model_provider}")
    try:
        result = await orchestrator.run(
            query=request.query,
            jurisdiction=request.jurisdiction,
            top_k=request.top_k,
            provider=x_model_provider,
            gemini_key=x_gemini_api_key,
        )
        return result
    except Exception as e:
        logger.error(f"Query pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/search")
async def search_cases(
    request: SearchRequest,
    x_model_provider: Optional[str] = Header(None),
    x_gemini_api_key: Optional[str] = Header(None),
):
    """Full-text + semantic search across the legal corpus."""
    try:
        results = await orchestrator.search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
            provider=x_model_provider,
            gemini_key=x_gemini_api_key,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/similar-cases")
async def similar_cases(
    request: CaseSimilarityRequest,
    x_model_provider: Optional[str] = Header(None),
    x_gemini_api_key: Optional[str] = Header(None),
):
    """Find cases semantically similar to a given case ID or text snippet."""
    try:
        results = await orchestrator.find_similar(
            case_id=request.case_id,
            text=request.text,
            top_k=request.top_k,
            provider=x_model_provider,
            gemini_key=x_gemini_api_key,
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


@app.get("/api/check-ollama")
async def check_ollama():
    """Checks if Ollama is running and lists available models."""
    import httpx
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    custom_model = os.getenv("OLLAMA_LLM_MODEL", "lexverify-legal")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{ollama_host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "status": "connected", 
                    "models": models, 
                    "host": ollama_host,
                    "has_custom_model": custom_model in models or f"{custom_model}:latest" in models
                }
    except Exception as e:
        logger.warning(f"Ollama connection check failed: {e}")
    return {
        "status": "disconnected", 
        "error": "Could not connect to Ollama", 
        "host": ollama_host,
        "has_custom_model": False
    }

@app.get("/api/model-status")
async def model_status():
    """Returns the current active model provider and its status."""
    import httpx
    provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
    
    status_data = {
        "provider": provider,
        "llm_model": None,
        "embed_model": None,
        "status": "unknown"
    }

    if provider == "ollama":
        status_data["llm_model"] = os.getenv("OLLAMA_LLM_MODEL", "lexverify-legal")
        status_data["embed_model"] = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        
        # Check if Ollama is running and has the models
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{ollama_host}/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    if status_data["llm_model"] in models or f"{status_data['llm_model']}:latest" in models:
                        status_data["status"] = "loaded"
                    else:
                        status_data["status"] = "model_not_found"
                else:
                    status_data["status"] = "error"
        except:
            status_data["status"] = "disconnected"

    elif provider == "gemini":
        status_data["llm_model"] = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")
        status_data["embed_model"] = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")
        status_data["status"] = "configured" if os.getenv("GEMINI_API_KEY") else "missing_key"
        
    else:
        status_data["llm_model"] = "simulation (mock)"
        status_data["embed_model"] = "simulation (mock)"
        status_data["status"] = "active"

    return status_data

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "Endpoint not found"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
