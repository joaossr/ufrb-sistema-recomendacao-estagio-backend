"""
Importação do Currículo Lattes — Fase 4. Fluxo: upload do XML ->
prévia (sem gravar nada) -> confirmação do usuário -> grava no
PostgreSQL. O e-mail institucional e a matrícula NUNCA são
sobrescritos por aqui (já vêm da conta, ver Fase 2/3).
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno, FormacaoComplementar, IdiomaAluno
from app.routers.perfil import _serialize as serialize_perfil
from app.schemas.lattes import LattesConfirmRequest, LattesConfirmResponse, LattesPreviewOut
from app.services.embeddings.service import regenerate_aluno_embedding
from app.services.lattes.course_matching import find_standard_course_by_name
from app.services.lattes.parser import parse_lattes_xml

router = APIRouter(prefix="/perfil/lattes", tags=["lattes"])

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB — um currículo Lattes em XML nunca chega perto disso


@router.post("/preview", response_model=LattesPreviewOut)
async def preview(file: UploadFile, aluno: Aluno = Depends(get_current_aluno)):
    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecione o arquivo XML exportado do Currículo Lattes.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo muito grande.")

    result = parse_lattes_xml(content)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.error)

    return LattesPreviewOut(
        full_name=result.full_name,
        lattes_id=result.lattes_id,
        formations=[f.__dict__ for f in result.formations],
        languages=[
            {
                "name": lang.name,
                "reading": lang.reading,
                "speaking": lang.speaking,
                "writing": lang.writing,
                "comprehension": lang.comprehension,
            }
            for lang in result.languages
        ],
        complementary_formations=[c.__dict__ for c in result.complementary_formations],
    )


@router.post("/confirmar", response_model=LattesConfirmResponse)
def confirmar(
    payload: LattesConfirmRequest, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)
):
    aluno.nome_completo = payload.full_name or aluno.nome_completo
    aluno.lattes_id = payload.lattes_id or aluno.lattes_id

    course_matched = True
    if payload.chosen_formation:
        chosen = payload.chosen_formation
        aluno.instituicao = chosen.institution
        aluno.nivel_formacao = chosen.level
        aluno.status_formacao = chosen.status
        aluno.ano_inicio_formacao = chosen.start_year
        aluno.ano_fim_formacao = chosen.end_year

        curso = find_standard_course_by_name(db, chosen.course)
        if curso:
            aluno.curso_id = curso.id
        else:
            course_matched = False

    for existing in list(aluno.idiomas):
        db.delete(existing)
    for lang in payload.languages:
        db.add(
            IdiomaAluno(
                aluno_id=aluno.id,
                nome=lang.name,
                leitura=lang.reading or None,
                fala=lang.speaking or None,
                escrita=lang.writing or None,
                compreensao=lang.comprehension or None,
            )
        )

    existentes = {fc.nome.strip().lower() for fc in aluno.formacoes_complementares}
    for comp in payload.complementary_formations:
        if not comp.nome or comp.nome.strip().lower() in existentes:
            continue
        db.add(
            FormacaoComplementar(
                aluno_id=aluno.id, tipo=comp.tipo or None, nome=comp.nome, instituicao=comp.instituicao or None, ano=comp.ano or None
            )
        )
        existentes.add(comp.nome.strip().lower())

    db.commit()
    db.refresh(aluno)
    regenerate_aluno_embedding(db, aluno)
    db.commit()

    return LattesConfirmResponse(perfil=serialize_perfil(aluno), course_matched=course_matched)
