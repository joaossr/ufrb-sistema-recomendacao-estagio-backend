from pydantic import BaseModel, ConfigDict


class CentroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str


class CursoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    centro_id: str
    nome: str


class TecnologiaCatalogoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class AreaProjetoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class TipoProjetoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
