"""
Fase 2: só um endpoint mínimo para provar que `require_admin` bloqueia
quem não é administrador. O painel administrativo de verdade (listar
alunos, empresas, convênios, importações...) é a Fase 10 (passo 27).
"""

from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.models.usuario import Usuario

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def ping(usuario: Usuario = Depends(require_admin)):
    return {"ok": True, "admin": usuario.matricula}
