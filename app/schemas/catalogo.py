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
