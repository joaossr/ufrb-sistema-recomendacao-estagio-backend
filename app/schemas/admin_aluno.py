import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.catalogo_aluno import ExperienciaOut, ProjetoOut, TecnologiaOut
from app.schemas.perfil import PerfilOut


class AlunoListaOut(BaseModel):
    id: uuid.UUID
    matricula: str
    nome_completo: str | None
    email: str | None
    curso: str | None
    semestre_atual: str | None
    num_tecnologias: int
    num_projetos: int
    num_experiencias: int
    num_areas_interesse: int
    tem_embedding: bool
    created_at: datetime


class AlunoDetalheOut(BaseModel):
    perfil: PerfilOut
    tecnologias: list[TecnologiaOut]
    projetos: list[ProjetoOut]
    experiencias: list[ExperienciaOut]
    areas_interesse: list[str]
