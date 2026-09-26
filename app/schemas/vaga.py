import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class VagaIn(BaseModel):
    convenio_id: uuid.UUID | None = None
    titulo: str = Field(min_length=1, max_length=500)
    descricao: str | None = None
    atividades: str | None = None
    requisitos: str | None = None
    cursos: list[str] = []
    areas: list[str] = []
    tecnologias: list[str] = []
    modalidade: str | None = None
    localizacao: str | None = None
    bolsa: str | None = None
    carga_horaria: str | None = None
    beneficios: str | None = None
    quantidade: int | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    link: str | None = None


class VagaStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ativa|encerrada)$")


class VagaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empresa_id: uuid.UUID
    convenio_id: uuid.UUID | None
    titulo: str
    descricao: str | None
    atividades: str | None
    requisitos: str | None
    cursos: list[str] | None
    areas: list[str] | None
    tecnologias: list[str] | None
    modalidade: str | None
    localizacao: str | None
    bolsa: str | None
    carga_horaria: str | None
    beneficios: str | None
    quantidade: int | None
    data_inicio: date | None
    data_fim: date | None
    status: str
    link: str | None
    created_at: datetime
