import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.empresa import Empresa


class Vaga(Base):
    """`status` distingue vaga ativa/encerrada (passo 15). 'Empresa
    para prospecção' (passo 25) não é um status de vaga — é o caso em
    que uma empresa é semanticamente compatível mas NÃO tem nenhuma
    Vaga com status='ativa'; isso é calculado na consulta, não
    armazenado aqui."""

    __tablename__ = "vagas"
    __table_args__ = (CheckConstraint("status IN ('ativa', 'encerrada')", name="ck_vagas_status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    convenio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("convenios.id"))
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    atividades: Mapped[str | None] = mapped_column(Text)
    requisitos: Mapped[str | None] = mapped_column(Text)
    cursos: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    areas: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    tecnologias: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    modalidade: Mapped[str | None] = mapped_column(String(50))
    localizacao: Mapped[str | None] = mapped_column(String(255))
    bolsa: Mapped[str | None] = mapped_column(String(100))
    carga_horaria: Mapped[str | None] = mapped_column(String(50))
    beneficios: Mapped[str | None] = mapped_column(Text)
    quantidade: Mapped[int | None] = mapped_column(Integer)
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ativa")
    link: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship()
