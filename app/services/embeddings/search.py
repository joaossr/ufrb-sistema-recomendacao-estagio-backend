"""
Busca semântica via pgvector (Fase 7 / passo 19). Distância de
cosseno, Top 20 por padrão. IMPORTANTE (repetido de propósito, é um
dos três princípios centrais do sistema): o valor retornado aqui é
SIMILARIDADE SEMÂNTICA entre textos, nunca uma probabilidade de
contratação ou qualquer medida de "chance de conseguir a vaga". As
Fases 8-9 aplicam regras objetivas e o Qwen3 EM CIMA destes candidatos
— esta função não decide nada sozinha.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.embedding import Embedding

TOP_K_PADRAO = 20


def _embedding_da_entidade(db: Session, entidade_tipo: str, entidade_id: uuid.UUID) -> Embedding | None:
    return (
        db.query(Embedding)
        .filter(Embedding.entidade_tipo == entidade_tipo, Embedding.entidade_id == entidade_id)
        .first()
    )


def buscar_similares(
    db: Session,
    *,
    vetor_origem: list[float],
    entidade_tipo_alvo: str,
    top_k: int = TOP_K_PADRAO,
    excluir_entidade_id: uuid.UUID | None = None,
) -> list[tuple[uuid.UUID, float]]:
    """Retorna [(entidade_id, distancia_cosseno)], mais similar primeiro
    (distância menor = mais similar). Não junta com Vaga/Empresa/Aluno
    aqui — cada chamador decide o que fazer com os ids."""
    query = db.query(Embedding.entidade_id, Embedding.vetor.cosine_distance(vetor_origem).label("distancia")).filter(
        Embedding.entidade_tipo == entidade_tipo_alvo
    )
    if excluir_entidade_id:
        query = query.filter(Embedding.entidade_id != excluir_entidade_id)

    resultados = query.order_by("distancia").limit(top_k).all()
    return [(row.entidade_id, float(row.distancia)) for row in resultados]


def buscar_vagas_similares_ao_aluno(db: Session, aluno_id: uuid.UUID, top_k: int = TOP_K_PADRAO):
    embedding_aluno = _embedding_da_entidade(db, "aluno", aluno_id)
    if embedding_aluno is None:
        return []
    return buscar_similares(db, vetor_origem=embedding_aluno.vetor, entidade_tipo_alvo="vaga", top_k=top_k)


def buscar_empresas_similares_ao_aluno(db: Session, aluno_id: uuid.UUID, top_k: int = TOP_K_PADRAO):
    embedding_aluno = _embedding_da_entidade(db, "aluno", aluno_id)
    if embedding_aluno is None:
        return []
    return buscar_similares(db, vetor_origem=embedding_aluno.vetor, entidade_tipo_alvo="empresa", top_k=top_k)


def buscar_alunos_similares_a_vaga(db: Session, vaga_id: uuid.UUID, top_k: int = TOP_K_PADRAO):
    """Caminho inverso (Fase 9): usado pelo painel administrativo para
    achar candidatos a partir de uma vaga."""
    embedding_vaga = _embedding_da_entidade(db, "vaga", vaga_id)
    if embedding_vaga is None:
        return []
    return buscar_similares(db, vetor_origem=embedding_vaga.vetor, entidade_tipo_alvo="aluno", top_k=top_k)


def buscar_alunos_similares_a_empresa(db: Session, empresa_id: uuid.UUID, top_k: int = TOP_K_PADRAO):
    embedding_empresa = _embedding_da_entidade(db, "empresa", empresa_id)
    if embedding_empresa is None:
        return []
    return buscar_similares(db, vetor_origem=embedding_empresa.vetor, entidade_tipo_alvo="aluno", top_k=top_k)
