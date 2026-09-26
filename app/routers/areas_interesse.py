"""
Catálogo de áreas de interesse (compartilhado, com autocomplete +
"criar nova área" no frontend) e a seleção de áreas do aluno atual.
Equivalente a DataService.listInterestAreaCatalog/addInterestAreaToCatalog
e listInterests/setInterests.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno, AlunoAreaInteresse
from app.models.catalogo import AreaInteresse
from app.schemas.catalogo_aluno import AreaInteresseCreate, AreaInteresseOut, AreasInteresseSelecionadasUpdate

router = APIRouter(tags=["areas-interesse"])


@router.get("/areas-interesse", response_model=list[AreaInteresseOut])
def listar_catalogo(db: Session = Depends(get_db)):
    return db.query(AreaInteresse).order_by(AreaInteresse.nome).all()


@router.post("/areas-interesse", response_model=AreaInteresseOut, status_code=status.HTTP_201_CREATED)
def criar_area(payload: AreaInteresseCreate, db: Session = Depends(get_db)):
    nome = " ".join(payload.nome.strip().split())
    existente = db.query(AreaInteresse).filter(func.lower(AreaInteresse.nome) == nome.lower()).first()
    if existente:
        return existente
    area = AreaInteresse(nome=nome)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.get("/perfil/areas-interesse", response_model=list[str])
def listar_selecionadas(aluno: Aluno = Depends(get_current_aluno)):
    return [v.area_interesse.nome for v in aluno.areas_interesse]


@router.put("/perfil/areas-interesse", response_model=list[str])
def atualizar_selecionadas(
    payload: AreasInteresseSelecionadasUpdate,
    aluno: Aluno = Depends(get_current_aluno),
    db: Session = Depends(get_db),
):
    for vinculo in list(aluno.areas_interesse):
        db.delete(vinculo)

    for nome in payload.areas:
        area = db.query(AreaInteresse).filter(func.lower(AreaInteresse.nome) == nome.strip().lower()).first()
        if area is None:
            area = AreaInteresse(nome=nome.strip())
            db.add(area)
            db.flush()
        db.add(AlunoAreaInteresse(aluno_id=aluno.id, area_interesse_id=area.id))

    db.commit()
    db.refresh(aluno)
    return [v.area_interesse.nome for v in aluno.areas_interesse]
