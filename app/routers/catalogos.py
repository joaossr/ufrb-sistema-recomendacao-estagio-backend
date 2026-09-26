"""
Leitura de centros/cursos — hoje o frontend ainda usa a lista
hardcoded em ui.js (mantida em sincronia manualmente com o seed), mas
expor isso já pela API prepara o terreno para a Fase 10 (autocomplete
via backend) sem exigir nenhuma migração de dado nova depois.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalogo import Centro, Curso
from app.schemas.catalogo import CentroOut, CursoOut

router = APIRouter(tags=["catalogos"])


@router.get("/centros", response_model=list[CentroOut])
def listar_centros(db: Session = Depends(get_db)):
    return db.query(Centro).order_by(Centro.id).all()


@router.get("/cursos", response_model=list[CursoOut])
def listar_cursos(db: Session = Depends(get_db)):
    return db.query(Curso).order_by(Curso.id).all()
