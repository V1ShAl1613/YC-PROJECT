"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum


class JurisdictionEnum(str, Enum):
    INDIA = "india"
    USA = "usa"
    UK = "uk"
    ALL = "all"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=2000, description="Legal question")
    jurisdiction: JurisdictionEnum = Field(JurisdictionEnum.ALL, description="Jurisdiction filter")
    top_k: int = Field(5, ge=1, le=20, description="Number of documents to retrieve")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What are the grounds for anticipatory bail under Indian law?",
                "jurisdiction": "india",
                "top_k": 5,
            }
        }
    }


class Citation(BaseModel):
    id: str
    case_name: str
    court: str
    year: int
    paragraph: str = Field(..., description="Exact paragraph, extract, or pinpoint reference supporting the claim")
    url: Optional[str] = None
    source: str  # "indian_kanoon" | "courtlistener"
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class ValidationResult(BaseModel):
    citation_verified: bool
    cross_consistent: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_label: str  # HIGH / MEDIUM / LOW
    rejection_reasons: List[str] = []


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    validation: ValidationResult
    fallback: bool = False  # True when "No verified legal information found"
    latency_ms: float
    agent_trace: Optional[List[str]] = None  # debug trace

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "...",
                "answer": "Under Section 438 CrPC...",
                "citations": [],
                "validation": {"confidence_score": 0.92},
                "fallback": False,
                "latency_ms": 1240.5,
            }
        }
    }


class SearchFilters(BaseModel):
    court: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    jurisdiction: Optional[JurisdictionEnum] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    filters: Optional[SearchFilters] = None
    top_k: int = Field(10, ge=1, le=50)


class CaseSimilarityRequest(BaseModel):
    case_id: Optional[str] = None
    text: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)

    @validator("case_id", always=True)
    def at_least_one(cls, v, values):
        if not v and not values.get("text"):
            raise ValueError("Provide either case_id or text")
        return v
