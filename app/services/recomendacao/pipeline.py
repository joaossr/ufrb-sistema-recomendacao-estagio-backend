"""
Pipeline completo (Fase 8): perfil estruturado -> texto -> embedding
(já existente, Fase 7) -> busca vetorial -> regras objetivas -> Qwen3
-> Recomendacao auditável no Postgres. Nenhuma etapa pula a anterior.

MAX_CANDIDATOS_PARA_LLM existe por um motivo prático desta máquina:
cada chamada ao Qwen3 em CPU leva ~20-40s (ver README) — mandar os 20
candidatos da busca vetorial pro LLM em toda geração levaria minutos.
Aumentar isso é seguro (só mais lento) quando houver GPU utilizável.
"""

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.aluno import Aluno
from app.models.recomendacao import Recomendacao
from app.services.embeddings.search import buscar_vagas_similares_ao_aluno
from app.services.embeddings.text_representation import aluno_to_text, vaga_to_text
from app.services.recomendacao.analise import analisar_compatibilidade
from app.services.recomendacao.regras import CandidatoElegivel, filtrar_candidatos_elegiveis

logger = logging.getLogger(__name__)

MAX_CANDIDATOS_PARA_LLM = 5
TOP_K_VETORIAL_PADRAO = 20


def _upsert_recomendacao(db: Session, aluno: Aluno, candidato: CandidatoElegivel, analise: dict) -> Recomendacao:
    existente = (
        db.query(Recomendacao)
        .filter(
            Recomendacao.aluno_id == aluno.id,
            Recomendacao.vaga_id == candidato.vaga.id,
            Recomendacao.tipo == "aluno_para_vaga",
        )
        .first()
    )
    campos = {
        # cosine_distance do pgvector: 0 = idêntico, até 2 = oposto.
        # Guardamos como "similaridade" (1 - distância) só para ficar
        # mais intuitivo de ler no banco — continua sendo similaridade
        # semântica, nunca probabilidade de contratação.
        "similaridade": 1 - candidato.similaridade,
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
        aluno_id=aluno.id,
        empresa_id=candidato.vaga.empresa_id,
        vaga_id=candidato.vaga.id,
        tipo="aluno_para_vaga",
        **campos,
    )
    db.add(nova)
    db.flush()
    return nova


def gerar_recomendacoes_para_aluno(
    db: Session,
    aluno: Aluno,
    top_k_vetorial: int = TOP_K_VETORIAL_PADRAO,
    max_llm: int = MAX_CANDIDATOS_PARA_LLM,
) -> list[Recomendacao]:
    candidatos_vetoriais = buscar_vagas_similares_ao_aluno(db, aluno.id, top_k=top_k_vetorial)
    if not candidatos_vetoriais:
        return []

    elegiveis = filtrar_candidatos_elegiveis(db, aluno, candidatos_vetoriais, top_k=max_llm)
    if not elegiveis:
        return []

    aluno_texto = aluno_to_text(aluno)
    recomendacoes: list[Recomendacao] = []

    for candidato in elegiveis:
        vaga_texto = vaga_to_text(candidato.vaga)
        analise = analisar_compatibilidade(aluno_texto, vaga_texto)
        if analise is None:
            logger.warning("Pulei a vaga %s: analise indisponivel ou invalida.", candidato.vaga.id)
            continue
        recomendacoes.append(_upsert_recomendacao(db, aluno, candidato, analise))

    db.commit()
    return recomendacoes
