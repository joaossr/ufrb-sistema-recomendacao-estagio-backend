import uuid

from pydantic import BaseModel


class VagaSimilarOut(BaseModel):
    vaga_id: uuid.UUID
    titulo: str
    empresa: str
    distancia: float
