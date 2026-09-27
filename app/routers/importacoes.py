"""
Endpoints administrativos de importação (Fase 5). Cada importação
gera um registro em `importacoes` (auditável — passo 30) com o
relatório e a lista de erros por linha.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.importacao import Importacao
from app.models.usuario import Usuario
from app.schemas.importacao import ImportacaoOut
from app.services.auditoria.log import registrar as registrar_log
from app.services.importacao.convenios_pdf import import_convenios_pdf

router = APIRouter(prefix="/admin/importacoes", tags=["importacoes"], dependencies=[Depends(require_admin)])

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/convenios-pdf", response_model=ImportacaoOut, status_code=status.HTTP_201_CREATED)
async def importar_convenios_pdf(
    file: UploadFile, db: Session = Depends(get_db), usuario: Usuario = Depends(require_admin)
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie um arquivo PDF.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo muito grande.")

    importacao = import_convenios_pdf(db, content, fonte=file.filename)
    registrar_log(
        db, usuario.id, "importar_convenios_pdf", "importacao", importacao.id,
        {"fonte": file.filename, "total_linhas": importacao.total_linhas, "sucesso": importacao.sucesso},
    )
    db.commit()
    return importacao


@router.get("", response_model=list[ImportacaoOut])
def listar_importacoes(db: Session = Depends(get_db)):
    return db.query(Importacao).order_by(Importacao.iniciado_em.desc()).all()


@router.get("/{importacao_id}", response_model=ImportacaoOut)
def obter_importacao(importacao_id: uuid.UUID, db: Session = Depends(get_db)):
    importacao = db.get(Importacao, importacao_id)
    if importacao is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importação não encontrada.")
    return importacao
