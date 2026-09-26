"""
GET /api/health — prova que FastAPI consegue falar com o PostgreSQL
antes de qualquer funcionalidade mais complexa ser construída em cima
(regra explícita da Fase 1: testar a comunicação primeiro).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "unavailable"

    return {"status": "ok", "database": database_status}
