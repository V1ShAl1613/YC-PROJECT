from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "legal-ai-backend",
        "version": "1.0.0",
    }
