"""
CRUD de projetos do aluno. `technologies` chega como lista de strings
(igual ao frontend hoje: o modal de projeto aceita qualquer tecnologia
digitada) — guardada em `projeto_tecnologias.nome`, sem exigir que
exista no catálogo `tecnologias`.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno, Projeto, ProjetoTecnologia
from app.models.catalogo import AreaProjeto, Curso, TipoProjeto
from app.schemas.catalogo_aluno import ProjetoIn, ProjetoOut
from app.services.embeddings.service import regenerate_aluno_embedding

router = APIRouter(prefix="/perfil/projetos", tags=["projetos"])


def _serialize(projeto: Projeto) -> ProjetoOut:
    return ProjetoOut(
        id=projeto.id,
        name=projeto.nome,
        description=projeto.descricao or "",
        academic_center=projeto.centro_id,
        course=projeto.curso.nome if projeto.curso else None,
        area=projeto.area_projeto.nome if projeto.area_projeto else None,
        type=projeto.tipo_projeto.nome if projeto.tipo_projeto else None,
        technologies=[t.nome for t in projeto.tecnologias],
        link=projeto.link,
        created_at=projeto.created_at,
    )


def _find_or_none(db: Session, model, nome: str | None):
    if not nome:
        return None
    return db.query(model).filter(model.nome == nome).first()


@router.get("", response_model=list[ProjetoOut])
def listar(aluno: Aluno = Depends(get_current_aluno)):
    return [_serialize(p) for p in aluno.projetos]


@router.post("", response_model=ProjetoOut, status_code=status.HTTP_201_CREATED)
def adicionar(payload: ProjetoIn, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    curso = _find_or_none(db, Curso, payload.course)
    area = (_find_or_none(db, AreaProjeto, payload.area) or _create_catalogo(db, AreaProjeto, payload.area)) if payload.area else None
    tipo = (_find_or_none(db, TipoProjeto, payload.type) or _create_catalogo(db, TipoProjeto, payload.type)) if payload.type else None

    projeto = Projeto(
        aluno_id=aluno.id,
        nome=payload.name.strip(),
        descricao=payload.description.strip(),
        centro_id=payload.academic_center or None,
        curso_id=curso.id if curso else None,
        area_projeto_id=area.id if area else None,
        tipo_projeto_id=tipo.id if tipo else None,
        link=payload.link.strip() if payload.link else None,
    )
    db.add(projeto)
    db.flush()

    for nome_tec in payload.technologies:
        db.add(ProjetoTecnologia(projeto_id=projeto.id, nome=nome_tec))

    db.commit()
    db.refresh(projeto)
    regenerate_aluno_embedding(db, aluno)
    db.commit()
    return _serialize(projeto)


def _create_catalogo(db: Session, model, nome: str):
    item = model(nome=nome.strip())
    db.add(item)
    db.flush()
    return item


@router.put("/{projeto_id}", response_model=ProjetoOut)
def atualizar(
    projeto_id: uuid.UUID, payload: ProjetoIn, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)
):
    projeto = db.query(Projeto).filter(Projeto.id == projeto_id, Projeto.aluno_id == aluno.id).first()
    if projeto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")

    projeto.nome = payload.name.strip()
    projeto.descricao = payload.description.strip()
    projeto.centro_id = payload.academic_center or None
    curso = _find_or_none(db, Curso, payload.course)
    projeto.curso_id = curso.id if curso else None
    if payload.area:
        area = _find_or_none(db, AreaProjeto, payload.area) or _create_catalogo(db, AreaProjeto, payload.area)
        projeto.area_projeto_id = area.id
    else:
        projeto.area_projeto_id = None
    if payload.type:
        tipo = _find_or_none(db, TipoProjeto, payload.type) or _create_catalogo(db, TipoProjeto, payload.type)
        projeto.tipo_projeto_id = tipo.id
    else:
        projeto.tipo_projeto_id = None
    projeto.link = payload.link.strip() if payload.link else None

    for existente in list(projeto.tecnologias):
        db.delete(existente)
    for nome_tec in payload.technologies:
        db.add(ProjetoTecnologia(projeto_id=projeto.id, nome=nome_tec))

    db.commit()
    db.refresh(projeto)
    regenerate_aluno_embedding(db, aluno)
    db.commit()
    return _serialize(projeto)


@router.delete("/{projeto_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(projeto_id: uuid.UUID, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    projeto = db.query(Projeto).filter(Projeto.id == projeto_id, Projeto.aluno_id == aluno.id).first()
    if projeto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    db.delete(projeto)
    db.commit()
    regenerate_aluno_embedding(db, aluno)
    db.commit()
