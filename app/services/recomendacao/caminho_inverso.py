"""
Caminho inverso (Fase 9 / passo 26): painel administrativo escolhe uma
vaga OU uma empresa e o sistema busca alunos compatíveis — mesma
arquitetura (texto → embedding → pgvector → regras → Qwen3), só que a
consulta parte da vaga/empresa em vez de partir do aluno. NUNCA afirma
que um aluno "vai ser contratado" — só compatibilidade.
"""

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.aluno import Aluno
from app.models.empresa import Empresa
from app.models.recomendacao import Recomendacao
from app.models.vaga import Vaga
from app.services.embeddings.search import buscar_alunos_similares_a_empresa, buscar_alunos_similares_a_vaga
from app.services.embeddings.text_representation import aluno_to_text, empresa_to_text, vaga_to_text
from app.services.recomendacao.analise import analisar_compatibilidade
from app.services.recomendacao.regras import curso_compativel

logger = logging.getLogger(__name__)

MAX_CANDIDATOS_PARA_LLM = 5


def _upsert_recomendacao(db: Session, aluno: Aluno, empresa: Empresa, vaga: Vaga | None, tipo: str, similaridade: float, analise: dict) -> Recomendacao:
    query = db.query(Recomendacao).filter(Recomendacao.aluno_id == aluno.id, Recomendacao.tipo == tipo)
    query = query.filter(Recomendacao.vaga_id == vaga.id) if vaga else query.filter(Recomendacao.vaga_id.is_(None), Recomendacao.empresa_id == empresa.id)
    existente = query.first()

    campos = {
        "similaridade": 1 - similaridade,
        "indice_compatibilidade": analise["indice"],
        "nivel": analise["nivel"],
        "pontos_compativeis": analise["pontos_compativeis"],
        "pontos_parciais": analise["pontos_parciais"],
        "lacunas": analise["lacunas"],
        "justificativa": analise["justificativa"],
        "modelo_llm": settings.ollama_llm_model,
        "modelo_embedding": settings.ollama_embed_model,
    }
    if existente:
        for campo, valor in campos.items():
            setattr(existente, campo, valor)
        db.flush()
        return existente

    nova = Recomendacao(
        aluno_id=aluno.id, empresa_id=empresa.id, vaga_id=vaga.id if vaga else None, tipo=tipo, **campos
    )
    db.add(nova)
    db.flush()
    return nova


def buscar_alunos_compativeis_com_vaga(
    db: Session, vaga: Vaga, top_k_vetorial: int = 20, max_llm: int = MAX_CANDIDATOS_PARA_LLM
) -> list[Recomendacao]:
    candidatos = buscar_alunos_similares_a_vaga(db, vaga.id, top_k=top_k_vetorial)
    if not candidatos:
        return []

    vaga_texto = vaga_to_text(vaga)
    resultados: list[Recomendacao] = []

    for aluno_id, similaridade in candidatos:
        aluno = db.get(Aluno, aluno_id)
        if aluno is None or not curso_compativel(aluno, vaga):
            continue

        analise = analisar_compatibilidade(aluno_to_text(aluno), vaga_texto)
        if analise is None:
            logger.warning("Pulei o aluno %s na busca reversa (vaga): analise indisponivel.", aluno.id)
            continue

        resultados.append(_upsert_recomendacao(db, aluno, vaga.empresa, vaga, "vaga_para_aluno", similaridade, analise))
        if len(resultados) >= max_llm:
            break

    db.commit()
    return resultados


def buscar_alunos_compativeis_com_empresa(
    db: Session, empresa: Empresa, top_k_vetorial: int = 20, max_llm: int = MAX_CANDIDATOS_PARA_LLM
) -> list[Recomendacao]:
    candidatos = buscar_alunos_similares_a_empresa(db, empresa.id, top_k=top_k_vetorial)
    if not candidatos:
        return []

    empresa_texto = empresa_to_text(empresa)
    resultados: list[Recomendacao] = []

    for aluno_id, similaridade in candidatos:
        aluno = db.get(Aluno, aluno_id)
        if aluno is None:
            continue

        analise = analisar_compatibilidade(aluno_to_text(aluno), empresa_texto)
        if analise is None:
            logger.warning("Pulei o aluno %s na busca reversa (empresa): analise indisponivel.", aluno.id)
            continue

        resultados.append(_upsert_recomendacao(db, aluno, empresa, None, "empresa_para_aluno", similaridade, analise))
        if len(resultados) >= max_llm:
            break

    db.commit()
    return resultados
