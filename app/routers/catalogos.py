"""
Leitura de catálogos para autocomplete (Fase 10 / passo 28): centros,
cursos, tecnologias, áreas e tipos de projeto. Todos públicos de
propósito (mesmo comportamento de areas_interesse.py desde a Fase 3)
— são listas de termos padronizados compartilhados, não dado pessoal.
Cursos ainda espelham a lista hardcoded em ui.js (mantida em sincronia
manualmente com o seed); migrar o frontend para consumir isto é
opcional e de baixo risco, não obrigatório para esta fase.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalogo import AreaProjeto, Centro, Curso, Tecnologia, TipoProjeto
from app.schemas.catalogo import AreaProjetoOut, CentroOut, CursoOut, TecnologiaCatalogoOut, TipoProjetoOut

router = APIRouter(tags=["catalogos"])


@router.get("/centros", response_model=list[CentroOut])
def listar_centros(db: Session = Depends(get_db)):
    return db.query(Centro).order_by(Centro.id).all()


@router.get("/cursos", response_model=list[CursoOut])
def listar_cursos(db: Session = Depends(get_db)):
    return db.query(Curso).order_by(Curso.id).all()


@router.get("/tecnologias", response_model=list[TecnologiaCatalogoOut])
def listar_tecnologias(db: Session = Depends(get_db)):
    return db.query(Tecnologia).order_by(Tecnologia.nome).all()


@router.get("/areas-projeto", response_model=list[AreaProjetoOut])
def listar_areas_projeto(db: Session = Depends(get_db)):
    return db.query(AreaProjeto).order_by(AreaProjeto.nome).all()


@router.get("/tipos-projeto", response_model=list[TipoProjetoOut])
def listar_tipos_projeto(db: Session = Depends(get_db)):
    return db.query(TipoProjeto).order_by(TipoProjeto.nome).all()
