"""
Geração e armazenamento de embeddings (Fase 7 / passo 18). Chamado
depois de qualquer mudança relevante em aluno/empresa/vaga — se o
Ollama estiver fora do ar, registra um aviso e NÃO derruba a operação
que disparou a atualização (salvar o perfil não pode depender de o
Ollama estar de pé).
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.aluno import Aluno
from app.models.embedding import Embedding
from app.models.empresa import Empresa
from app.models.vaga import Vaga
from app.services.embeddings.text_representation import aluno_to_text, empresa_to_text, vaga_to_text
from app.services.ollama.client import OllamaError, generate_embedding

logger = logging.getLogger(__name__)


def _upsert_embedding(db: Session, entidade_tipo: str, entidade_id: uuid.UUID, texto: str, modelo: str) -> Embedding:
    existente = (
        db.query(Embedding)
        .filter(Embedding.entidade_tipo == entidade_tipo, Embedding.entidade_id == entidade_id)
        .first()
    )
    vetor = generate_embedding(texto)

    if existente:
        existente.vetor = vetor
        existente.modelo = modelo
        existente.texto_base = texto
        db.flush()
        return existente

    novo = Embedding(entidade_tipo=entidade_tipo, entidade_id=entidade_id, vetor=vetor, modelo=modelo, texto_base=texto)
    db.add(novo)
    db.flush()
    return novo


def regenerate_aluno_embedding(db: Session, aluno: Aluno) -> Embedding | None:
    from app.core.config import settings

    texto = aluno_to_text(aluno)
    if not texto.strip():
        return None
    try:
        return _upsert_embedding(db, "aluno", aluno.id, texto, settings.ollama_embed_model)
    except OllamaError as exc:
        logger.warning("Não foi possível gerar embedding do aluno %s: %s", aluno.id, exc)
        return None


def regenerate_empresa_embedding(db: Session, empresa: Empresa) -> Embedding | None:
    from app.core.config import settings

    texto = empresa_to_text(empresa)
    if not texto.strip():
        return None
    try:
        return _upsert_embedding(db, "empresa", empresa.id, texto, settings.ollama_embed_model)
    except OllamaError as exc:
        logger.warning("Não foi possível gerar embedding da empresa %s: %s", empresa.id, exc)
        return None


def regenerate_vaga_embedding(db: Session, vaga: Vaga) -> Embedding | None:
    from app.core.config import settings

    texto = vaga_to_text(vaga)
    if not texto.strip():
        return None
    try:
        return _upsert_embedding(db, "vaga", vaga.id, texto, settings.ollama_embed_model)
    except OllamaError as exc:
        logger.warning("Não foi possível gerar embedding da vaga %s: %s", vaga.id, exc)
        return None
