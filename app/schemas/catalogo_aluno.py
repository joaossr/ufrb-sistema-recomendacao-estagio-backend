import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TecnologiaIn(BaseModel):
    name: str
    level: str = "Básico"


class TecnologiaUpdate(BaseModel):
    level: str


class TecnologiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    level: str


class ProjetoIn(BaseModel):
    name: str
    description: str = ""
    academic_center: str | None = None
    course: str | None = None
    area: str | None = None
    type: str | None = None
    technologies: list[str] = []
    link: str | None = None


class ProjetoOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    academic_center: str | None
    course: str | None
    area: str | None
    type: str | None
    technologies: list[str]
    link: str | None
    created_at: datetime


class ExperienciaIn(BaseModel):
    company: str
    role: str
    work_area: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    technologies: list[str] = []


class ExperienciaOut(BaseModel):
    id: uuid.UUID
    company: str
    role: str
    work_area: str | None
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str | None
    technologies: list[str]
    created_at: datetime


class AreaInteresseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class AreaInteresseCreate(BaseModel):
    nome: str


class AreasInteresseSelecionadasUpdate(BaseModel):
    areas: list[str]
