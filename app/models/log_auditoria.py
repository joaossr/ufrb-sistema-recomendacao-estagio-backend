import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogAuditoria(Base):
    """Log de auditoria (Fase 11 / passo 30) das ações administrativas
    que mudam estado (criar/editar/excluir empresa, convênio, vaga;
    login com sucesso/falha) — complementa `recomendacoes` (auditoria
    das análises do LLM, Fase 8) e `importacoes` (auditoria das
    importações, Fase 5), que já registravam sua própria fatia disso.
    Somente leitura pelo admin; nenhum endpoint apaga ou edita um
    registro já gravado."""

    __tablename__ = "logs_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    entidade_tipo: Mapped[str | None] = mapped_column(String(50))
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detalhes: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
