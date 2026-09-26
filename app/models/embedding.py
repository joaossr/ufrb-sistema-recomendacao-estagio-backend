import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class Embedding(Base):
    """Tabela separada de propósito (passo 4): nunca uma coluna vetor
    dentro de `alunos`/`empresas`/`vagas`, para não misturar dado
    estrutural com representação de IA. `entidade_tipo` + `entidade_id`
    aponta para a linha original (sem FK física, já que pode apontar
    para três tabelas diferentes); a Fase 7 garante a consistência via
    código de serviço, não via constraint de banco."""

    __tablename__ = "embeddings"
    __table_args__ = (
        CheckConstraint("entidade_tipo IN ('aluno', 'empresa', 'vaga')", name="ck_embeddings_entidade_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    entidade_tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entidade_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    vetor: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim), nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    texto_base: Mapped[str] = mapped_column(Text, nullable=False)
    gerado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
