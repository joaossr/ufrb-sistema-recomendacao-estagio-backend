import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Importacao(Base):
    """Histórico de cada rodada de importação (PDF de convênios, CSV/
    XLSX da COOPC) — usado no relatório pós-importação (passo 12) e no
    painel administrativo (passo 27, 'importações, erros e registros
    que precisam de revisão')."""

    __tablename__ = "importacoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    fonte: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_arquivo: Mapped[str] = mapped_column(String(20), nullable=False)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_linhas: Mapped[int | None] = mapped_column(Integer)
    sucesso: Mapped[int | None] = mapped_column(Integer)
    erros: Mapped[list | None] = mapped_column(JSONB)
    relatorio: Mapped[dict | None] = mapped_column(JSONB)
