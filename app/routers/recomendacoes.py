"""
Fase 8 (recomendação aluno->vaga) + Fase 9 (prospecção e caminho
inverso). Síncrono de propósito — cada candidato analisado pelo Qwen3
leva alguns segundos a dezenas de segundos (ver README), então estas
chamadas podem demorar; o frontend mostra um estado de carregamento.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno, require_admin
from app.models.aluno import Aluno
from app.models.empresa import Empresa
from app.models.recomendacao import Recomendacao
from app.models.vaga import Vaga
from app.schemas.recomendacao import (
    AlunoResumoOut,
    ConvenioResumoOut,
    EmpresaResumoOut,
    RecomendacaoDetalhadaOut,
    VagaResumoOut,
)
from app.services.recomendacao.caminho_inverso import buscar_alunos_compativeis_com_empresa, buscar_alunos_compativeis_com_vaga
from app.services.recomendacao.pipeline import gerar_recomendacoes_para_aluno
from app.services.recomendacao.prospeccao import gerar_prospeccoes_para_aluno

router = APIRouter(tags=["recomendacoes"])


def _serializar(db: Session, rec: Recomendacao, incluir_aluno: bool = False) -> RecomendacaoDetalhadaOut:
    empresa = db.get(Empresa, rec.empresa_id) if rec.empresa_id else None
    vaga_out = None
    if rec.vaga_id:
        vaga = db.get(Vaga, rec.vaga_id)
        if vaga:
            convenio_out = None
            if vaga.convenio:
                convenio_out = ConvenioResumoOut(status=vaga.convenio.status, data_fim=vaga.convenio.data_fim)
            vaga_out = VagaResumoOut(
                id=vaga.id,
                titulo=vaga.titulo,
                modalidade=vaga.modalidade,
                localizacao=vaga.localizacao,
                bolsa=vaga.bolsa,
                carga_horaria=vaga.carga_horaria,
                link=vaga.link,
                status=vaga.status,
                convenio=convenio_out,
            )

    aluno_out = None
    if incluir_aluno:
        aluno = db.get(Aluno, rec.aluno_id)
        if aluno:
            aluno_out = AlunoResumoOut(
                id=aluno.id,
                nome_completo=aluno.nome_completo,
                matricula=aluno.matricula,
                curso=aluno.curso.nome if aluno.curso else None,
            )

    return RecomendacaoDetalhadaOut(
        id=rec.id,
        tipo=rec.tipo,
        nivel=rec.nivel,
        indice_compatibilidade=rec.indice_compatibilidade,
        similaridade=rec.similaridade,
        pontos_compativeis=rec.pontos_compativeis or [],
        pontos_parciais=rec.pontos_parciais or [],
        lacunas=rec.lacunas or [],
        justificativa=rec.justificativa,
        empresa=EmpresaResumoOut(id=empresa.id, nome=empresa.nome) if empresa else EmpresaResumoOut(id=uuid.uuid4(), nome="—"),
        vaga=vaga_out,
        aluno=aluno_out,
        created_at=rec.created_at,
    )


# --------------------------------------------------------------------
# Aluno: recomendações de vaga + prospecção de empresas (Fase 8 e 9)
# --------------------------------------------------------------------
@router.post("/perfil/recomendacoes/gerar", response_model=list[RecomendacaoDetalhadaOut])
def gerar(aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    recomendacoes = gerar_recomendacoes_para_aluno(db, aluno)
    prospeccoes = gerar_prospeccoes_para_aluno(db, aluno)
    todas = recomendacoes + prospeccoes
    todas.sort(key=lambda r: r.indice_compatibilidade or 0, reverse=True)
    return [_serializar(db, r) for r in todas]


@router.get("/perfil/recomendacoes", response_model=list[RecomendacaoDetalhadaOut])
def listar(aluno: Aluno = Depends(get_current_aluno), db: Session = Depends(get_db)):
    registros = (
        db.query(Recomendacao)
        .filter(
            Recomendacao.aluno_id == aluno.id,
            Recomendacao.tipo.in_(["aluno_para_vaga", "aluno_para_empresa"]),
        )
        .order_by(Recomendacao.indice_compatibilidade.desc())
        .all()
    )
    return [_serializar(db, r) for r in registros]


# --------------------------------------------------------------------
# Admin: caminho inverso (Fase 9 / passo 26)
# --------------------------------------------------------------------
@router.post(
    "/admin/vagas/{vaga_id}/recomendacoes/gerar",
    response_model=list[RecomendacaoDetalhadaOut],
    dependencies=[Depends(require_admin)],
)
def gerar_para_vaga(vaga_id: uuid.UUID, db: Session = Depends(get_db)):
    vaga = db.get(Vaga, vaga_id)
    if vaga is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    resultados = buscar_alunos_compativeis_com_vaga(db, vaga)
    return [_serializar(db, r, incluir_aluno=True) for r in resultados]


@router.post(
    "/admin/empresas/{empresa_id}/recomendacoes/gerar",
    response_model=list[RecomendacaoDetalhadaOut],
    dependencies=[Depends(require_admin)],
)
def gerar_para_empresa(empresa_id: uuid.UUID, db: Session = Depends(get_db)):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada.")
    resultados = buscar_alunos_compativeis_com_empresa(db, empresa)
    return [_serializar(db, r, incluir_aluno=True) for r in resultados]
