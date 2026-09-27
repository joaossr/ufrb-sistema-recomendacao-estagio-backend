"""
CRUD administrativo de vagas (Fase 6 / passo 15). `status` distingue
vaga ativa/encerrada. "Empresa para prospecção" (passo 25) não é
armazenado aqui — é calculado nas Fases 7-9 (empresa semanticamente
compatível sem nenhuma vaga com status='ativa'); `empresa_tem_vaga_ativa`
já deixa essa consulta pronta para quando chegar a hora.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.embedding import Embedding
from app.models.empresa import Convenio, Empresa
from app.models.vaga import Vaga
from app.schemas.vaga import VagaIn, VagaOut, VagaStatusUpdate
from app.services.embeddings.service import regenerate_empresa_embedding, regenerate_vaga_embedding

router = APIRouter(prefix="/admin", tags=["vagas"], dependencies=[Depends(require_admin)])


def empresa_tem_vaga_ativa(db: Session, empresa_id: uuid.UUID) -> bool:
    return db.query(Vaga).filter(Vaga.empresa_id == empresa_id, Vaga.status == "ativa").first() is not None


def _regenerate_vaga_e_empresa(db: Session, vaga: Vaga):
    """O texto da empresa (`empresa_to_text`) agrega cursos/áreas/
    tecnologias das vagas dela — por isso qualquer mudança numa vaga
    também invalida o embedding da empresa."""
    regenerate_vaga_embedding(db, vaga)
    regenerate_empresa_embedding(db, vaga.empresa)
    db.commit()


def _validate_convenio(db: Session, empresa_id: uuid.UUID, convenio_id: uuid.UUID | None):
    if convenio_id is None:
        return
    convenio = db.get(Convenio, convenio_id)
    if convenio is None or convenio.empresa_id != empresa_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O convênio informado não pertence a esta empresa.",
        )


@router.get("/vagas", response_model=list[VagaOut])
def listar_vagas(status_filtro: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Vaga)
    if status_filtro:
        query = query.filter(Vaga.status == status_filtro)
    return query.order_by(Vaga.created_at.desc()).all()


@router.get("/empresas/{empresa_id}/vagas", response_model=list[VagaOut])
def listar_vagas_da_empresa(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")
    return db.query(Vaga).filter(Vaga.empresa_id == empresa_id).order_by(Vaga.created_at.desc()).all()


@router.post("/empresas/{empresa_id}/vagas", response_model=VagaOut, status_code=status.HTTP_201_CREATED)
def criar_vaga(empresa_id: uuid.UUID, payload: VagaIn, db: Session = Depends(get_db)):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")
    _validate_convenio(db, empresa_id, payload.convenio_id)

    vaga = Vaga(empresa_id=empresa_id, **payload.model_dump())
    db.add(vaga)
    db.commit()
    db.refresh(vaga)
    _regenerate_vaga_e_empresa(db, vaga)
    return vaga


@router.get("/vagas/{vaga_id}", response_model=VagaOut)
def obter_vaga(vaga_id: uuid.UUID, db: Session = Depends(get_db)):
    vaga = db.get(Vaga, vaga_id)
    if vaga is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    return vaga


@router.put("/vagas/{vaga_id}", response_model=VagaOut)
def atualizar_vaga(vaga_id: uuid.UUID, payload: VagaIn, db: Session = Depends(get_db)):
    vaga = db.get(Vaga, vaga_id)
    if vaga is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    _validate_convenio(db, vaga.empresa_id, payload.convenio_id)

    for field, value in payload.model_dump().items():
        setattr(vaga, field, value)

    db.commit()
    db.refresh(vaga)
    _regenerate_vaga_e_empresa(db, vaga)
    return vaga


@router.put("/vagas/{vaga_id}/status", response_model=VagaOut)
def atualizar_status_vaga(vaga_id: uuid.UUID, payload: VagaStatusUpdate, db: Session = Depends(get_db)):
    vaga = db.get(Vaga, vaga_id)
    if vaga is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    vaga.status = payload.status
    db.commit()
    db.refresh(vaga)
    return vaga


@router.delete("/vagas/{vaga_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_vaga(vaga_id: uuid.UUID, db: Session = Depends(get_db)):
    vaga = db.get(Vaga, vaga_id)
    if vaga is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    empresa = vaga.empresa
    db.query(Embedding).filter(Embedding.entidade_tipo == "vaga", Embedding.entidade_id == vaga.id).delete()
    db.delete(vaga)
    db.commit()
    regenerate_empresa_embedding(db, empresa)
    db.commit()
