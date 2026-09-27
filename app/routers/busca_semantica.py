"""
Fase 7 (passo 19) exposta como endpoint testável: busca semântica pura,
sem regras objetivas nem Qwen3 ainda (Fase 8). O campo `distancia` é
similaridade de cosseno — NUNCA probabilidade de contratação.
"""

from fastapi import APIRouter, Depends

from app.core.deps import get_current_aluno
from app.core.database import get_db
from app.models.aluno import Aluno
from app.models.vaga import Vaga
from app.schemas.busca_semantica import VagaSimilarOut
from app.services.embeddings.search import buscar_vagas_similares_ao_aluno
from sqlalchemy.orm import Session

router = APIRouter(prefix="/perfil/busca-semantica", tags=["busca-semantica"])


@router.get("/vagas", response_model=list[VagaSimilarOut])
def vagas_similares(aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    resultados = buscar_vagas_similares_ao_aluno(db, aluno.id)
    saida = []
    for vaga_id, distancia in resultados:
        vaga = db.get(Vaga, vaga_id)
        if vaga is None:
            continue
        saida.append(VagaSimilarOut(vaga_id=vaga.id, titulo=vaga.titulo, empresa=vaga.empresa.nome, distancia=distancia))
    return saida
