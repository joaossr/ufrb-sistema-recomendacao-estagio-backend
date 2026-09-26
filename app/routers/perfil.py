"""
GET/PUT /api/perfil — substitui DataService.getProfile()/saveProfile()
(hoje localStorage) por um CRUD real sobre `alunos`/`tccs`/
`idiomas_aluno`. Mantém a MESMA forma plana que o frontend já usa
(course/course_id/tcc_status/... no mesmo objeto), para minimizar o
impacto na migração do dataService.js.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno
from app.models.aluno import Aluno, IdiomaAluno, Tcc
from app.schemas.perfil import PerfilOut, PerfilUpdate

router = APIRouter(tags=["perfil"])

# Campos que existem com nomes diferentes no JSON (frontend) e no model
# (Aluno). Todo campo do PerfilUpdate que não estiver aqui nem for
# tratado à parte (tcc_*, languages) é um bug de digitação — falharia
# alto (AttributeError) em vez de silenciosamente não salvar nada.
_ALUNO_FIELD_MAP = {
    "course_id": "curso_id",
    "linkedin_url": "linkedin_url",
    "semester": "semestre_atual",
    "expected_graduation": "previsao_conclusao",
    "has_experience": "possui_experiencia",
    "full_name": "nome_completo",
    "lattes_id": "lattes_id",
    "institution": "instituicao",
    "education_level": "nivel_formacao",
    "education_status": "status_formacao",
    "education_start_year": "ano_inicio_formacao",
    "education_end_year": "ano_fim_formacao",
}
_TCC_FIELDS = {"tcc_status": "situacao", "tcc_title": "titulo", "tcc_summary": "resumo", "tcc_advisor": "orientador", "tcc_keywords": "palavras_chave"}


def _serialize(aluno: Aluno) -> PerfilOut:
    return PerfilOut(
        id=aluno.id,
        full_name=aluno.nome_completo or "",
        lattes_id=aluno.lattes_id or "",
        course=aluno.curso.nome if aluno.curso else "",
        course_id=aluno.curso_id,
        institution=aluno.instituicao or "",
        education_level=aluno.nivel_formacao or "",
        education_status=aluno.status_formacao or "",
        education_start_year=aluno.ano_inicio_formacao or "",
        education_end_year=aluno.ano_fim_formacao or "",
        email=aluno.email or "",
        phone=aluno.telefone or "",
        registration_number=aluno.matricula,
        linkedin_url=aluno.linkedin_url or "",
        semester=aluno.semestre_atual or "",
        expected_graduation=aluno.previsao_conclusao or "",
        has_experience=aluno.possui_experiencia,
        tcc_status=aluno.tcc.situacao if aluno.tcc else "nao_iniciou",
        tcc_title=(aluno.tcc.titulo or "") if aluno.tcc else "",
        tcc_summary=(aluno.tcc.resumo or "") if aluno.tcc else "",
        tcc_advisor=(aluno.tcc.orientador or "") if aluno.tcc else "",
        tcc_keywords=(aluno.tcc.palavras_chave or []) if aluno.tcc else [],
        languages=[
            {
                "name": lang.nome,
                "reading": lang.leitura or "",
                "speaking": lang.fala or "",
                "writing": lang.escrita or "",
                "comprehension": lang.compreensao or "",
            }
            for lang in aluno.idiomas
        ],
        updated_at=aluno.updated_at,
    )


@router.get("/perfil", response_model=PerfilOut)
def get_perfil(aluno: Aluno = Depends(get_current_aluno)):
    return _serialize(aluno)


@router.put("/perfil", response_model=PerfilOut)
def update_perfil(payload: PerfilUpdate, aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)

    tcc_changes = {}
    languages = changes.pop("languages", None)
    for key in list(_TCC_FIELDS.keys()):
        if key in changes:
            tcc_changes[_TCC_FIELDS[key]] = changes.pop(key)

    for key, value in changes.items():
        setattr(aluno, _ALUNO_FIELD_MAP[key], value)

    if tcc_changes:
        if aluno.tcc is None:
            aluno.tcc = Tcc(aluno_id=aluno.id, situacao="nao_iniciou")
            db.add(aluno.tcc)
        for attr, value in tcc_changes.items():
            setattr(aluno.tcc, attr, value)

    if languages is not None:
        for existing in list(aluno.idiomas):
            db.delete(existing)
        for lang in languages:
            db.add(
                IdiomaAluno(
                    aluno_id=aluno.id,
                    nome=lang["name"],
                    leitura=lang.get("reading") or None,
                    fala=lang.get("speaking") or None,
                    escrita=lang.get("writing") or None,
                    compreensao=lang.get("comprehension") or None,
                )
            )

    db.commit()
    db.refresh(aluno)
    return _serialize(aluno)
