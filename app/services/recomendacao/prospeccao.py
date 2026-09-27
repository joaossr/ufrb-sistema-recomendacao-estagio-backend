"""
Prospecção (Fase 9 / passo 25): uma empresa pode ser semanticamente
compatível com o perfil do aluno mesmo sem ter nenhuma vaga ativa no
momento. Nesse caso o sistema NUNCA deve dizer "vaga disponível" — é
"empresa potencial para prospecção", uma sugestão de contato, não uma
oportunidade concreta. Mesma arquitetura da Fase 8 (busca vetorial →
regras → Qwen3), só que aluno<->empresa em vez de aluno<->vaga.
"""

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.aluno import Aluno
from app.models.empresa import Empresa
from app.models.recomendacao import Recomendacao
from app.routers.vagas import empresa_tem_vaga_ativa
from app.services.embeddings.search import buscar_empresas_similares_ao_aluno
from app.services.embeddings.text_representation import aluno_to_text, empresa_to_text
from app.services.recomendacao.analise import analisar_compatibilidade

logger = logging.getLogger(__name__)

MAX_CANDIDATOS_PARA_LLM = 3  # menor que o de vagas (5): cada geracao soma tempo, e prospeccao e secundaria a vaga ativa


def _upsert_prospeccao(db: Session, aluno: Aluno, empresa: Empresa, similaridade: float, analise: dict) -> Recomendacao:
    existente = (
        db.query(Recomendacao)
        .filter(
            Recomendacao.aluno_id == aluno.id,
            Recomendacao.empresa_id == empresa.id,
            Recomendacao.vaga_id.is_(None),
            Recomendacao.tipo == "aluno_para_empresa",
        )
        .first()
    )
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

    nova = Recomendacao(aluno_id=aluno.id, empresa_id=empresa.id, vaga_id=None, tipo="aluno_para_empresa", **campos)
    db.add(nova)
    db.flush()
    return nova


def gerar_prospeccoes_para_aluno(
    db: Session, aluno: Aluno, top_k_vetorial: int = 20, max_llm: int = MAX_CANDIDATOS_PARA_LLM
) -> list[Recomendacao]:
    candidatos = buscar_empresas_similares_ao_aluno(db, aluno.id, top_k=top_k_vetorial)
    if not candidatos:
        return []

    aluno_texto = aluno_to_text(aluno)
    prospeccoes: list[Recomendacao] = []

    for empresa_id, similaridade in candidatos:
        empresa = db.get(Empresa, empresa_id)
        if empresa is None:
            continue
        # Se a empresa já tem vaga ativa, ela é coberta pelo fluxo de
        # recomendação de vaga (Fase 8) — prospecção é só para quem
        # NÃO tem oportunidade concreta aberta agora.
        if empresa_tem_vaga_ativa(db, empresa.id):
            continue

        analise = analisar_compatibilidade(aluno_texto, empresa_to_text(empresa))
        if analise is None:
            logger.warning("Pulei a empresa %s na prospecção: analise indisponivel ou invalida.", empresa.id)
            continue

        prospeccoes.append(_upsert_prospeccao(db, aluno, empresa, similaridade, analise))
        if len(prospeccoes) >= max_llm:
            break

    db.commit()
    return prospeccoes
