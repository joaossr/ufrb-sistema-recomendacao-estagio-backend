"""
CRUD administrativo de empresas/convênios (Fase 5). Uso principal por
enquanto: base para os importadores de PDF (Fase 5) e COOPC (Fase 6) e
para o painel administrativo completo (Fase 10) — ainda não tem UI
própria no frontend.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.empresa import Convenio, Empresa
from app.models.usuario import Usuario
from app.schemas.empresa import ConvenioIn, ConvenioOut, EmpresaIn, EmpresaOut
from app.services.auditoria.log import registrar as registrar_log
from app.services.embeddings.service import regenerate_empresa_embedding
from app.services.importacao.convenio_status import parse_and_compute_status
from app.services.importacao.empresas import get_or_create_empresa

router = APIRouter(prefix="/admin", tags=["empresas"], dependencies=[Depends(require_admin)])


@router.get("/empresas", response_model=list[EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).order_by(Empresa.nome).all()


@router.post("/empresas", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED)
def criar_empresa(payload: EmpresaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(require_admin)):
    empresa, criada = get_or_create_empresa(db, nome=payload.nome, cnpj=payload.cnpj)
    if criada:
        registrar_log(db, usuario.id, "criar_empresa", "empresa", empresa.id, {"nome": empresa.nome})
    db.commit()
    db.refresh(empresa)
    regenerate_empresa_embedding(db, empresa)
    db.commit()
    return empresa


@router.get("/empresas/{empresa_id}", response_model=EmpresaOut)
def obter_empresa(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")
    return empresa


@router.get("/empresas/{empresa_id}/convenios", response_model=list[ConvenioOut])
def listar_convenios(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")
    return empresa.convenios


@router.post("/empresas/{empresa_id}/convenios", response_model=ConvenioOut, status_code=status.HTTP_201_CREATED)
def criar_convenio(
    empresa_id: uuid.UUID,
    payload: ConvenioIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_admin),
):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")

    data_fim, computed_status = parse_and_compute_status(payload.data_fim_original)

    convenio = Convenio(
        empresa_id=empresa.id,
        processo=payload.processo,
        data_inicio=payload.data_inicio,
        data_fim_original=payload.data_fim_original,
        data_fim=data_fim,
        status=computed_status,
        fonte=payload.fonte,
        pagina_origem=payload.pagina_origem,
        observacoes=payload.observacoes,
    )
    db.add(convenio)
    db.flush()
    registrar_log(
        db, usuario.id, "criar_convenio", "convenio", convenio.id, {"empresa_id": str(empresa.id), "processo": convenio.processo}
    )
    db.commit()
    db.refresh(convenio)
    return convenio


@router.get("/convenios/{convenio_id}", response_model=ConvenioOut)
def obter_convenio(convenio_id: uuid.UUID, db: Session = Depends(get_db)):
    convenio = db.get(Convenio, convenio_id)
    if convenio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convênio não encontrado.")
    return convenio
