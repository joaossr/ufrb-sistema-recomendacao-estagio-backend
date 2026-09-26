import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno, ExperienciaProfissional
from app.schemas.catalogo_aluno import ExperienciaIn, ExperienciaOut

router = APIRouter(prefix="/perfil/experiencias", tags=["experiencias"])


def _serialize(exp: ExperienciaProfissional) -> ExperienciaOut:
    return ExperienciaOut(
        id=exp.id,
        company=exp.empresa,
        role=exp.cargo,
        work_area=exp.area_atuacao,
        start_date=exp.data_inicio,
        end_date=exp.data_fim,
        is_current=exp.atual,
        description=exp.descricao,
        technologies=exp.tecnologias or [],
        created_at=exp.created_at,
    )


@router.get("", response_model=list[ExperienciaOut])
def listar(aluno: Aluno = Depends(get_current_aluno)):
    return [_serialize(e) for e in aluno.experiencias]


@router.post("", response_model=ExperienciaOut, status_code=status.HTTP_201_CREATED)
def adicionar(payload: ExperienciaIn, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    exp = ExperienciaProfissional(
        aluno_id=aluno.id,
        empresa=payload.company.strip(),
        cargo=payload.role.strip(),
        area_atuacao=payload.work_area,
        data_inicio=payload.start_date,
        data_fim=payload.end_date,
        atual=payload.is_current,
        descricao=payload.description,
        tecnologias=payload.technologies,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return _serialize(exp)


@router.delete("/{experiencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(experiencia_id: uuid.UUID, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    exp = db.query(ExperienciaProfissional).filter(
        ExperienciaProfissional.id == experiencia_id, ExperienciaProfissional.aluno_id == aluno.id
    ).first()
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiência não encontrada.")
    db.delete(exp)
    db.commit()
