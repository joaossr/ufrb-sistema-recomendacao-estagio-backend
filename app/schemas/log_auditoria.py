import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogAuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID | None
    acao: str
    entidade_tipo: str | None
    entidade_id: uuid.UUID | None
    detalhes: dict | None
    created_at: datetime
