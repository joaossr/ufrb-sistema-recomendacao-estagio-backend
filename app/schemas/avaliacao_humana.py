import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AvaliacaoHumanaIn(BaseModel):
    concorda_com_llm: bool | None = None
    nota_humana: int | None = Field(default=None, ge=1, le=5)
    comentario: str | None = None


class AvaliacaoHumanaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recomendacao_id: uuid.UUID
    avaliador_usuario_id: uuid.UUID
    concorda_com_llm: bool | None
    nota_humana: int | None
    comentario: str | None
    created_at: datetime
