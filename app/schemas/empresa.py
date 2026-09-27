import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EmpresaIn(BaseModel):
    nome: str
    cnpj: str | None = None


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    nome_normalizado: str
    cnpj: str | None
    area: str | None
    segmento: str | None
    cidade: str | None
    uf: str | None
    created_at: datetime


class ConvenioIn(BaseModel):
    processo: str | None = None
    data_inicio: date | None = None
    data_fim_original: str | None = None
    fonte: str | None = None
    pagina_origem: str | None = None
    observacoes: str | None = None


class ConvenioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empresa_id: uuid.UUID
    processo: str | None
    data_inicio: date | None
    data_fim_original: str | None
    data_fim: date | None
    status: str
    fonte: str | None
    pagina_origem: str | None
    importado_em: datetime
    observacoes: str | None
