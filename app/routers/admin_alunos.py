"""
Fase 10 (passo 27): o painel administrativo finalmente enxerga os
alunos reais — antes disso, `listAllProfilesForAdmin` no frontend só
mostrava os perfis fictícios de demonstração porque não existia
endpoint nenhum para isso.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.aluno import Aluno
from app.models.embedding import Embedding
from app.routers.experiencias import _serialize as serializar_experiencia
from app.routers.perfil import _serialize as serializar_perfil
from app.routers.projetos import _serialize as serializar_projeto
from app.routers.tecnologias import _serialize as serializar_tecnologia
from app.schemas.admin_aluno import AlunoDetalheOut, AlunoListaOut

router = APIRouter(prefix="/admin/alunos", tags=["admin-alunos"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[AlunoListaOut])
def listar(db: Session = Depends(get_db)):
    alunos = db.query(Aluno).order_by(Aluno.created_at.desc()).all()
    saida = []
    for aluno in alunos:
        tem_embedding = (
            db.query(Embedding).filter(Embedding.entidade_tipo == "aluno", Embedding.entidade_id == aluno.id).first()
            is not None
        )
        saida.append(
            AlunoListaOut(
                id=aluno.id,
                matricula=aluno.matricula,
                nome_completo=aluno.nome_completo,
                email=aluno.email,
                curso=aluno.curso.nome if aluno.curso else None,
                semestre_atual=aluno.semestre_atual,
                num_tecnologias=len(aluno.tecnologias),
                num_projetos=len(aluno.projetos),
                num_experiencias=len(aluno.experiencias),
                num_areas_interesse=len(aluno.areas_interesse),
                tem_embedding=tem_embedding,
                created_at=aluno.created_at,
            )
        )
    return saida


@router.get("/{aluno_id}", response_model=AlunoDetalheOut)
def detalhar(aluno_id: uuid.UUID, db: Session = Depends(get_db)):
    aluno = db.get(Aluno, aluno_id)
    if aluno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    return AlunoDetalheOut(
        perfil=serializar_perfil(aluno),
        tecnologias=[serializar_tecnologia(v) for v in aluno.tecnologias],
        projetos=[serializar_projeto(p) for p in aluno.projetos],
        experiencias=[serializar_experiencia(e) for e in aluno.experiencias],
        areas_interesse=[v.area_interesse.nome for v in aluno.areas_interesse],
    )
