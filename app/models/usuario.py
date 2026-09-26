import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Usuario(Base):
    """Autenticação — separada dos dados acadêmicos (ver Aluno). Um
    usuário 'admin' não tem uma linha correspondente em `alunos`."""

    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint("role IN ('aluno', 'admin')", name="ck_usuarios_role"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    matricula: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="aluno")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
