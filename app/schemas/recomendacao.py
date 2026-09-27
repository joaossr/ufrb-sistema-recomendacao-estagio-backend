import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecomendacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aluno_id: uuid.UUID
    empresa_id: uuid.UUID | None
    vaga_id: uuid.UUID | None
    similaridade: float | None
    indice_compatibilidade: float | None
    nivel: str | None
    pontos_compativeis: list | None
    pontos_parciais: list | None
    lacunas: list | None
    justificativa: str | None
    tipo: str
    modelo_llm: str | None
    modelo_embedding: str | None
    created_at: datetime
