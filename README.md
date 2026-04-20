# LexVerify — Verification-First Legal AI Agent

> **Accuracy > Fluency · Proof > Confidence · Truth > Speed**

A production-grade legal research assistant that provides citation-backed answers with **zero hallucination tolerance**. Every answer must cite a real, retrieved legal document. If no verified source exists, the system returns a clean fallback instead of fabricating information.

## Non-Negotiable Rules

1. Never generate an answer without citations.
2. If no relevant verified source is found, return: `No verified legal information found`.
3. Every answer must include case name, court, year, and an exact paragraph or pinpoint reference.
4. Do not infer, assume, or fabricate legal facts.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Research Agent                                 │
│  • Embed query via OpenAI text-embedding-3-small         │
│  • FAISS vector search → Top-K semantic matches          │
│  • Enrich with PostgreSQL metadata                       │
│  • Filter by jurisdiction                                │
└─────────────────────┬───────────────────────────────────┘
                      │ Retrieved documents
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 2: Legal Analyst Agent                            │
│  • GPT-4o, temperature=0.0, JSON mode                    │
│  • Answer ONLY from provided context                     │
│  • Inline [CITE:doc_id] markers required                 │
│  • Returns {"fallback": true} if context insufficient    │
└─────────────────────┬───────────────────────────────────┘
                      │ Draft answer + citations
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 3: Validator Agent  ◄── CRITICAL GATE            │
│  • Check all doc_ids exist in retrieved set              │
│  • Verify field completeness (name, court, year, para)   │
│  • LLM cross-document consistency check                  │
│  • Multi-factor confidence score (0.0 – 1.0)            │
│  • REJECT if score < 0.4 or any unverifiable citation    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
            Verified Answer with Citations
            OR "No verified legal information found"
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.12 + FastAPI |
| LLM | GPT-4o (temperature=0) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | FAISS (CPU) with persistence |
| Metadata DB | PostgreSQL / SQLite (dev) |
| Frontend | Next.js 14 + TypeScript |
| Orchestration | Custom 3-agent sequential pipeline |
| Data Sources | Indian Kanoon, CourtListener |
| Container | Docker Compose |

---

## Project Structure

```
legal-ai/
├── backend/
│   ├── main.py                    # FastAPI application
│   ├── agents/
│   │   ├── orchestrator.py        # 3-agent pipeline coordinator
│   │   ├── research_agent.py      # Stage 1: document retrieval
│   │   ├── analyst_agent.py       # Stage 2: LLM synthesis
│   │   └── validator_agent.py     # Stage 3: verification gate
│   ├── retrieval/
│   │   ├── vector_store.py        # FAISS index with persistence
│   │   ├── embedder.py            # OpenAI embedding wrapper
│   │   └── metadata_db.py         # PostgreSQL/SQLite metadata
│   ├── verification/
│   │   └── citation_guard.py      # Shared citation and policy checks
│   ├── api/
│   │   ├── models.py              # Pydantic request/response models
│   │   └── health.py              # Health check endpoint
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Main application shell
│   │   │   ├── layout.tsx         # Root layout
│   │   │   └── globals.css        # Production CSS
│   │   ├── components/
│   │   │   ├── QueryInterface.tsx  # Main query UI
│   │   │   ├── Sidebar.tsx        # Navigation
│   │   │   ├── CitationCard.tsx   # Citation display
│   │   │   └── index.tsx          # Other components
│   │   └── types/api.ts           # TypeScript API types
│   ├── package.json
│   └── Dockerfile
├── database/
│   └── migrations/
│       └── 001_init.sql           # PostgreSQL schema
├── scripts/
│   └── ingest.py                  # Data ingestion pipeline
└── docker-compose.yml
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- (Optional) CourtListener API token
- (Optional) Indian Kanoon API token

### 1. Clone and configure

```bash
git clone https://github.com/yourorg/legal-ai
cd legal-ai

# Create environment file
cat > .env << EOF
OPENAI_API_KEY=sk-...
COURTLISTENER_API_TOKEN=your_token_here
INDIAN_KANOON_API_TOKEN=your_token_here
EOF
```

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

Services:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **PostgreSQL**: localhost:5432

### 3. Run without Docker (development)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env .env                # ensure OPENAI_API_KEY is set
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### 4. Ingest legal data

```bash
cd backend
# Ingest from both sources (requires API tokens)
python ../scripts/ingest.py --source all --limit 200 --query "fundamental rights bail arrest"

# Ingest only from CourtListener
python ../scripts/ingest.py --source courtlistener --limit 100 --query "civil rights"

# Ingest only from Indian Kanoon
python ../scripts/ingest.py --source indian_kanoon --limit 100 --query "section 438 CrPC"
```

> **Note**: The system ships with 4 seeded demo cases for immediate testing without API tokens.

---

## API Reference

### POST `/api/query`
Primary endpoint — legal question answering with citations.

```json
{
  "query": "What are the grounds for anticipatory bail under Indian law?",
  "jurisdiction": "india",
  "top_k": 5
}
```

Response:
```json
{
  "query": "...",
  "answer": "Under Section 438 CrPC... [CITE:IK_2023_0002]",
  "citations": [
    {
      "id": "IK_2023_0002",
      "case_name": "Gurbaksh Singh Sibbia v. State of Punjab",
      "court": "Supreme Court of India",
      "year": 1980,
      "paragraph": "Section 438 CrPC confers wide amplitude...",
      "url": "https://indiankanoon.org/doc/697591/",
      "source": "indian_kanoon",
      "relevance_score": 0.96
    }
  ],
  "validation": {
    "citation_verified": true,
    "cross_consistent": true,
    "confidence_score": 0.91,
    "confidence_label": "HIGH",
    "rejection_reasons": []
  },
  "fallback": false,
  "latency_ms": 1840.5
}
```

### POST `/api/search`
Semantic + metadata-filtered corpus search.

### POST `/api/similar-cases`
Find cases similar to a given case ID or text snippet.

### GET `/api/case/{case_id}`
Retrieve full case document by ID.

### GET `/api/stats`
Corpus statistics and system info.

### GET `/api/health`
Health check.

---

## Confidence Score Calculation

The `ValidatorAgent` computes a multi-factor score:

| Factor | Weight | Condition |
|--------|--------|-----------|
| Average citation relevance | 40% | Mean of FAISS similarity scores |
| Citation verification | +30% | All doc_ids exist in retrieved set |
| Cross-document consistency | +20% | No contradictions detected by LLM |
| Citation count bonus | +10% (max) | 2% per citation, capped at 10% |
| Rejection penalty | −10% each | Per identified issue |

**Threshold**: Responses with confidence < 0.4 are **rejected** and the fallback is returned.

---

## Evaluation Metrics

| Metric | Target | How enforced |
|--------|--------|-------------|
| Citation accuracy | 100% | ValidatorAgent rejects unverified citations |
| Hallucination rate | 0% | LLM only sees retrieved context; fallback on insufficient data |
| Required legal references | 100% | Validator rejects missing case/court/year/reference fields |
| Response latency | < 5s | Pipeline optimized with embedding cache |
| Retrieval relevance | FAISS cosine similarity scores logged per query |

---

## Data Sources

### Indian Kanoon
- URL: https://indiankanoon.org
- API: https://api.indiankanoon.org (token required)
- Coverage: Indian Supreme Court, High Courts, Tribunals

### CourtListener
- URL: https://www.courtlistener.com
- API: https://www.courtlistener.com/api/ (free token)
- Coverage: US Federal courts, Supreme Court, Circuit courts

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o and embeddings |
| `DATABASE_URL` | No | PostgreSQL URL (defaults to SQLite in dev) |
| `FAISS_INDEX_PATH` | No | Path to FAISS index file |
| `COURTLISTENER_API_TOKEN` | No | CourtListener API token |
| `INDIAN_KANOON_API_TOKEN` | No | Indian Kanoon API token |

---

## Security Notes

- The system never exposes raw LLM outputs — all answers pass through the validator
- API keys are never logged or included in responses
- CORS is restricted to localhost in development; configure `allow_origins` for production
- Consider adding rate limiting (e.g., `slowapi`) for production deployments

---

## License

MIT — see LICENSE file.
