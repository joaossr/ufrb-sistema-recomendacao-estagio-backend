import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fonte: str
    tipo_arquivo: str
    iniciado_em: datetime
    finalizado_em: datetime | None
    total_linhas: int | None
    sucesso: int | None
    erros: list | None
    relatorio: dict | None
