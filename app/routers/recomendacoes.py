"""
Fase 8: dispara o pipeline completo (busca vetorial -> regras
objetivas -> Qwen3 -> Recomendacao). Síncrono de propósito nesta fase
— cada candidato analisado pelo Qwen3 leva dezenas de segundos nesta
máquina (CPU-only, ver README), então esta chamada pode demorar.
A Fase 9 constrói a interface que consome isto (recomendacoes.html).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno
from app.models.recomendacao import Recomendacao
from app.schemas.recomendacao import RecomendacaoOut
from app.services.recomendacao.pipeline import gerar_recomendacoes_para_aluno

router = APIRouter(prefix="/perfil/recomendacoes", tags=["recomendacoes"])


@router.post("/gerar", response_model=list[RecomendacaoOut])
def gerar(aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    return gerar_recomendacoes_para_aluno(db, aluno)


@router.get("", response_model=list[RecomendacaoOut])
def listar(aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    return (
        db.query(Recomendacao)
        .filter(Recomendacao.aluno_id == aluno.id, Recomendacao.tipo == "aluno_para_vaga")
        .order_by(Recomendacao.indice_compatibilidade.desc())
        .all()
    )
