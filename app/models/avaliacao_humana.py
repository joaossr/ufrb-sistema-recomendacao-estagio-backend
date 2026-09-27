import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AvaliacaoHumana(Base):
    """Avaliação humana de uma Recomendacao já gerada pelo Qwen3 (Fase
    11 / passo 32) — a estrutura de avaliação científica do TCC: um
    avaliador (sempre um admin, por ora) registra se concorda com o
    nível dado pelo LLM e uma nota independente, para depois comparar
    LLM x humano na dissertação. Nunca é o LLM avaliando a si mesmo:
    é sempre uma pessoa preenchendo isto pelo painel administrativo.
    """

    __tablename__ = "avaliacoes_humanas"
    __table_args__ = (
        CheckConstraint("nota_humana IS NULL OR nota_humana BETWEEN 1 AND 5", name="ck_avaliacoes_nota_humana"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recomendacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recomendacoes.id"), nullable=False
    )
    avaliador_usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    concorda_com_llm: Mapped[bool | None] = mapped_column(Boolean)
    nota_humana: Mapped[int | None] = mapped_column(Integer)
    comentario: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
