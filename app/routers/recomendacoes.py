"""
Fase 8 (recomendação aluno->vaga) + Fase 9 (prospecção e caminho
inverso). Síncrono de propósito — cada candidato analisado pelo Qwen3
leva alguns segundos a dezenas de segundos (ver README), então estas
chamadas podem demorar; o frontend mostra um estado de carregamento.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_aluno, require_admin
from app.models.aluno import Aluno
from app.models.empresa import Empresa
from app.models.recomendacao import Recomendacao
from app.models.usuario import Usuario
from app.models.vaga import Vaga
from app.schemas.recomendacao import (
    AlunoResumoOut,
    ConvenioResumoOut,
    EmpresaResumoOut,
    GeracaoAlunoResultadoOut,
    GeracaoRecomendacoesResumoOut,
    RecomendacaoDetalhadaOut,
    VagaResumoOut,
)
from app.services.auditoria.log import registrar as registrar_log
from app.services.recomendacao.caminho_inverso import buscar_alunos_compativeis_com_empresa, buscar_alunos_compativeis_com_vaga
from app.services.recomendacao.pipeline import gerar_recomendacoes_para_aluno
from app.services.recomendacao.prospeccao import gerar_prospeccoes_para_aluno

logger = logging.getLogger(__name__)

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
# Aluno: só visualiza (Fase 12) — quem gera é sempre o admin, em lote,
# para todos os alunos de uma vez (ver `gerar_para_todos` abaixo).
# --------------------------------------------------------------------
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
# Admin: geração em lote para TODOS os alunos (Fase 12) — substitui o
# botão "Gerar recomendações" que existia na área do aluno. A lógica
# de compatibilidade (busca vetorial -> regras -> Qwen3) é a mesma de
# sempre (Fases 8/9); o que muda é quem dispara e para quantos alunos
# de uma vez.
# --------------------------------------------------------------------
@router.post(
    "/admin/recomendacoes/gerar",
    response_model=GeracaoRecomendacoesResumoOut,
    dependencies=[Depends(require_admin)],
)
def gerar_para_todos_os_alunos(db: Session = Depends(get_db), usuario: Usuario = Depends(require_admin)):
    alunos = db.query(Aluno).all()
    detalhes: list[GeracaoAlunoResultadoOut] = []
    total_recomendacoes = 0
    total_prospeccoes = 0
    com_erro = 0

    for aluno in alunos:
        try:
            recomendacoes = gerar_recomendacoes_para_aluno(db, aluno)
            prospeccoes = gerar_prospeccoes_para_aluno(db, aluno)
            total_recomendacoes += len(recomendacoes)
            total_prospeccoes += len(prospeccoes)
            detalhes.append(
                GeracaoAlunoResultadoOut(
                    aluno_id=aluno.id,
                    matricula=aluno.matricula,
                    nome_completo=aluno.nome_completo,
                    recomendacoes_geradas=len(recomendacoes),
                    prospeccoes_geradas=len(prospeccoes),
                )
            )
        except Exception as exc:
            # Um aluno com dado problemático (ex.: perfil incompleto,
            # falha pontual do Ollama que escapou do tratamento interno)
            # nunca pode interromper o processamento dos demais — é
            # exatamente o motivo de este loop nunca deixar propagar.
            db.rollback()
            com_erro += 1
            logger.warning("Falha ao gerar recomendacoes para aluno %s: %s", aluno.id, exc)
            detalhes.append(
                GeracaoAlunoResultadoOut(
                    aluno_id=aluno.id,
                    matricula=aluno.matricula,
                    nome_completo=aluno.nome_completo,
                    recomendacoes_geradas=0,
                    prospeccoes_geradas=0,
                    erro=str(exc),
                )
            )

    registrar_log(
        db, usuario.id, "gerar_recomendacoes_todos_alunos", None, None,
        {
            "alunos_processados": len(alunos),
            "alunos_com_erro": com_erro,
            "total_recomendacoes_geradas": total_recomendacoes,
            "total_prospeccoes_geradas": total_prospeccoes,
        },
    )
    db.commit()

    return GeracaoRecomendacoesResumoOut(
        alunos_processados=len(alunos),
        alunos_com_erro=com_erro,
        total_recomendacoes_geradas=total_recomendacoes,
        total_prospeccoes_geradas=total_prospeccoes,
        detalhes=detalhes,
    )


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
