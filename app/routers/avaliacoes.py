"""
Avaliação humana de recomendações já geradas pelo Qwen3 (Fase 11 /
passo 32) — a estrutura de avaliação científica do TCC: permite um
admin registrar se concorda com o nível dado pelo LLM e uma nota
independente, para comparar LLM x avaliação humana na dissertação.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.avaliacao_humana import AvaliacaoHumana
from app.models.recomendacao import Recomendacao
from app.models.usuario import Usuario
from app.schemas.avaliacao_humana import AvaliacaoHumanaIn, AvaliacaoHumanaOut

router = APIRouter(prefix="/admin", tags=["avaliacoes"], dependencies=[Depends(require_admin)])


@router.post(
    "/recomendacoes/{recomendacao_id}/avaliacoes",
    response_model=AvaliacaoHumanaOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_avaliacao(
    recomendacao_id: uuid.UUID,
    payload: AvaliacaoHumanaIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_admin),
):
    recomendacao = db.get(Recomendacao, recomendacao_id)
    if recomendacao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recomendação não encontrada.")

    avaliacao = AvaliacaoHumana(
        recomendacao_id=recomendacao_id,
        avaliador_usuario_id=usuario.id,
        concorda_com_llm=payload.concorda_com_llm,
        nota_humana=payload.nota_humana,
        comentario=payload.comentario,
    )
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    return avaliacao


@router.get("/recomendacoes/{recomendacao_id}/avaliacoes", response_model=list[AvaliacaoHumanaOut])
def listar_avaliacoes_da_recomendacao(recomendacao_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(AvaliacaoHumana)
        .filter(AvaliacaoHumana.recomendacao_id == recomendacao_id)
        .order_by(AvaliacaoHumana.created_at.desc())
        .all()
    )


@router.get("/avaliacoes", response_model=list[AvaliacaoHumanaOut])
def listar_todas_avaliacoes(db: Session = Depends(get_db)):
    """Lista completa para exportar/analisar fora do sistema (ex.:
    comparar `nivel` do LLM com `nota_humana`/`concorda_com_llm` no
    capítulo de avaliação do TCC)."""
    return db.query(AvaliacaoHumana).order_by(AvaliacaoHumana.created_at.desc()).all()
