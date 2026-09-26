import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Empresa(Base):
    """Uma empresa pode ter vários convênios e várias vagas — por isso
    é sua própria tabela, nunca embutida em convênio/vaga."""

    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    cnpj: Mapped[str | None] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(500), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    convenios: Mapped[list["Convenio"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")


class Convenio(Base):
    """Status calculado deterministicamente (Fase 5 / passo 13), nunca
    pelo LLM: vigente/vencido/indeterminado a partir de `data_fim`.
    `data_fim_original` preserva o texto bruto do PDF para auditoria,
    mesmo quando `data_fim` não pôde ser parseada com segurança."""

    __tablename__ = "convenios"
    __table_args__ = (
        CheckConstraint(
            "status IN ('vigente', 'vencido', 'indeterminado')", name="ck_convenios_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    processo: Mapped[str | None] = mapped_column(String(100))
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim_original: Mapped[str | None] = mapped_column(String(50))
    data_fim: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="indeterminado")
    fonte: Mapped[str | None] = mapped_column(String(255))
    pagina_origem: Mapped[str | None] = mapped_column(String(20))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    observacoes: Mapped[str | None] = mapped_column(Text)

    empresa: Mapped["Empresa"] = relationship(back_populates="convenios")
