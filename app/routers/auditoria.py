"""
Leitura do log de auditoria (Fase 11 / passo 30). Só leitura — quem
grava é `app/services/auditoria/log.py`, chamado de dentro dos
routers que mudam estado (auth, empresas, vagas, importações).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.log_auditoria import LogAuditoria
from app.schemas.log_auditoria import LogAuditoriaOut

router = APIRouter(prefix="/admin", tags=["auditoria"], dependencies=[Depends(require_admin)])


@router.get("/logs-auditoria", response_model=list[LogAuditoriaOut])
def listar_logs(
    entidade_tipo: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(LogAuditoria)
    if entidade_tipo:
        query = query.filter(LogAuditoria.entidade_tipo == entidade_tipo)
    return query.order_by(LogAuditoria.created_at.desc()).limit(min(limit, 500)).all()
