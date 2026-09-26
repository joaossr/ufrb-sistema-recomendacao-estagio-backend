"""
Catálogos padronizados — evitam duplicidade tipo "IA" vs "Inteligência
Artificial" ao centralizar o autocomplete (Fase 10 / passo 28) numa
única tabela por conceito, em vez de texto livre espalhado pelas
tabelas de aluno/projeto.
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Centro(Base):
    __tablename__ = "centros"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)

    cursos: Mapped[list["Curso"]] = relationship(back_populates="centro")


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centro_id: Mapped[str] = mapped_column(ForeignKey("centros.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)

    centro: Mapped["Centro"] = relationship(back_populates="cursos")


class Tecnologia(Base):
    __tablename__ = "tecnologias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class Conhecimento(Base):
    __tablename__ = "conhecimentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class AreaProjeto(Base):
    __tablename__ = "areas_projeto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class TipoProjeto(Base):
    __tablename__ = "tipos_projeto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class AreaInteresse(Base):
    __tablename__ = "areas_interesse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
