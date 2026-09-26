"""
CRUD de tecnologias/conhecimentos do aluno. O catálogo (`tecnologias`)
é compartilhado entre todos os alunos — evita duplicidade tipo "Python"
vs "python"; a associação com nível fica em `aluno_tecnologias`.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno, AlunoTecnologia
from app.models.catalogo import Tecnologia
from app.schemas.catalogo_aluno import TecnologiaIn, TecnologiaOut, TecnologiaUpdate

router = APIRouter(prefix="/perfil/tecnologias", tags=["tecnologias"])


def _get_or_create_tecnologia(db: Session, nome: str) -> Tecnologia:
    nome = nome.strip()
    existente = db.query(Tecnologia).filter(func.lower(Tecnologia.nome) == nome.lower()).first()
    if existente:
        return existente
    tecnologia = Tecnologia(nome=nome)
    db.add(tecnologia)
    db.flush()
    return tecnologia


def _serialize(vinculo: AlunoTecnologia) -> TecnologiaOut:
    return TecnologiaOut(id=vinculo.id, name=vinculo.tecnologia.nome, level=vinculo.nivel or "Básico")


@router.get("", response_model=list[TecnologiaOut])
def listar(aluno: Aluno = Depends(get_current_aluno)):
    return [_serialize(v) for v in aluno.tecnologias]


@router.post("", response_model=TecnologiaOut, status_code=status.HTTP_201_CREATED)
def adicionar(payload: TecnologiaIn, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    tecnologia = _get_or_create_tecnologia(db, payload.name)
    vinculo = AlunoTecnologia(aluno_id=aluno.id, tecnologia_id=tecnologia.id, nivel=payload.level)
    db.add(vinculo)
    db.commit()
    db.refresh(vinculo)
    return _serialize(vinculo)


@router.put("/{vinculo_id}", response_model=TecnologiaOut)
def atualizar(
    vinculo_id: uuid.UUID,
    payload: TecnologiaUpdate,
    aluno: Aluno = Depends(get_current_aluno),
    db: Session = Depends(get_db),
):
    vinculo = db.query(AlunoTecnologia).filter(
        AlunoTecnologia.id == vinculo_id, AlunoTecnologia.aluno_id == aluno.id
    ).first()
    if vinculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnologia não encontrada.")
    vinculo.nivel = payload.level
    db.commit()
    db.refresh(vinculo)
    return _serialize(vinculo)


@router.delete("/{vinculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(vinculo_id: uuid.UUID, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    vinculo = db.query(AlunoTecnologia).filter(
        AlunoTecnologia.id == vinculo_id, AlunoTecnologia.aluno_id == aluno.id
    ).first()
    if vinculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnologia não encontrada.")
    db.delete(vinculo)
    db.commit()
