import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Recomendacao(Base):
    """Resultado auditável do pipeline (busca vetorial -> regras ->
    Qwen3). `similaridade` é a distância/similaridade de cosseno do
    pgvector; `indice_compatibilidade` é o índice interno gerado pelo
    LLM (passo 22) — NUNCA uma probabilidade de contratação, em
    nenhuma das duas colunas."""

    __tablename__ = "recomendacoes"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('aluno_para_vaga', 'aluno_para_empresa', 'vaga_para_aluno', 'empresa_para_aluno')",
            name="ck_recomendacoes_tipo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    vaga_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vagas.id"))
    similaridade: Mapped[float | None] = mapped_column(Float)
    indice_compatibilidade: Mapped[float | None] = mapped_column(Float)
    nivel: Mapped[str | None] = mapped_column(String(50))
    pontos_compativeis: Mapped[list | None] = mapped_column(JSONB)
    pontos_parciais: Mapped[list | None] = mapped_column(JSONB)
    lacunas: Mapped[list | None] = mapped_column(JSONB)
    justificativa: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    modelo_llm: Mapped[str | None] = mapped_column(String(100))
    modelo_embedding: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
