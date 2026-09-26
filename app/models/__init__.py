"""
Importa todos os models para que `Base.metadata` fique completo — é o
que o Alembic (autogenerate) e os testes de integração usam como fonte
única de verdade do schema.
"""

from app.core.database import Base
from app.models.usuario import Usuario
from app.models.catalogo import (
    Centro,
    Curso,
    Tecnologia,
    Conhecimento,
    AreaProjeto,
    TipoProjeto,
    AreaInteresse,
)
from app.models.aluno import (
    Aluno,
    Tcc,
    AlunoTecnologia,
    AlunoConhecimento,
    IdiomaAluno,
    FormacaoComplementar,
    Projeto,
    ProjetoTecnologia,
    ExperienciaProfissional,
    AlunoAreaInteresse,
)
from app.models.empresa import Empresa, Convenio
from app.models.vaga import Vaga
from app.models.embedding import Embedding
from app.models.recomendacao import Recomendacao
from app.models.importacao import Importacao

__all__ = [
    "Base",
    "Usuario",
    "Centro",
    "Curso",
    "Tecnologia",
    "Conhecimento",
    "AreaProjeto",
    "TipoProjeto",
    "AreaInteresse",
    "Aluno",
    "Tcc",
    "AlunoTecnologia",
    "AlunoConhecimento",
    "IdiomaAluno",
    "FormacaoComplementar",
    "Projeto",
    "ProjetoTecnologia",
    "ExperienciaProfissional",
    "AlunoAreaInteresse",
    "Empresa",
    "Convenio",
    "Vaga",
    "Embedding",
    "Recomendacao",
    "Importacao",
]
