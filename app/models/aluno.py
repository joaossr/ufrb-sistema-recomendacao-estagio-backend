import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalogo import Curso, Tecnologia


class Aluno(Base):
    """Dados acadêmicos do estudante — 1:1 com um usuário autenticado.
    Espelha o formato hoje salvo em `dataService.js` (localStorage)."""

    __tablename__ = "alunos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), unique=True, nullable=False
    )
    matricula: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    nome_completo: Mapped[str | None] = mapped_column(String(255))
    lattes_id: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(30))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("cursos.id"))
    instituicao: Mapped[str | None] = mapped_column(String(255))
    nivel_formacao: Mapped[str | None] = mapped_column(String(50))
    status_formacao: Mapped[str | None] = mapped_column(String(50))
    ano_inicio_formacao: Mapped[str | None] = mapped_column(String(10))
    ano_fim_formacao: Mapped[str | None] = mapped_column(String(10))
    semestre_atual: Mapped[str | None] = mapped_column(String(10))
    previsao_conclusao: Mapped[str | None] = mapped_column(String(10))
    possui_experiencia: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    curso: Mapped["Curso | None"] = relationship()
    tcc: Mapped["Tcc | None"] = relationship(back_populates="aluno", uselist=False, cascade="all, delete-orphan")
    tecnologias: Mapped[list["AlunoTecnologia"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")
    conhecimentos: Mapped[list["AlunoConhecimento"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")
    idiomas: Mapped[list["IdiomaAluno"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")
    formacoes_complementares: Mapped[list["FormacaoComplementar"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )
    projetos: Mapped[list["Projeto"]] = relationship(back_populates="aluno", cascade="all, delete-orphan")
    experiencias: Mapped[list["ExperienciaProfissional"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )
    areas_interesse: Mapped[list["AlunoAreaInteresse"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )


class Tcc(Base):
    __tablename__ = "tccs"
    __table_args__ = (
        CheckConstraint(
            "situacao IN ('nao_iniciou', 'em_andamento', 'concluido')", name="ck_tccs_situacao"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id"), unique=True, nullable=False
    )
    situacao: Mapped[str] = mapped_column(String(20), nullable=False, server_default="nao_iniciou")
    titulo: Mapped[str | None] = mapped_column(String(500))
    resumo: Mapped[str | None] = mapped_column(Text)
    orientador: Mapped[str | None] = mapped_column(String(255))
    palavras_chave: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    aluno: Mapped["Aluno"] = relationship(back_populates="tcc")


class AlunoTecnologia(Base):
    __tablename__ = "aluno_tecnologias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    tecnologia_id: Mapped[int] = mapped_column(ForeignKey("tecnologias.id"), nullable=False)
    nivel: Mapped[str | None] = mapped_column(String(30))

    aluno: Mapped["Aluno"] = relationship(back_populates="tecnologias")
    tecnologia: Mapped["Tecnologia"] = relationship()


class AlunoConhecimento(Base):
    __tablename__ = "aluno_conhecimentos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    conhecimento_id: Mapped[int] = mapped_column(ForeignKey("conhecimentos.id"), nullable=False)
    nivel: Mapped[str | None] = mapped_column(String(30))

    aluno: Mapped["Aluno"] = relationship(back_populates="conhecimentos")


class IdiomaAluno(Base):
    """1:N direto (não é catálogo): vem tipicamente do Lattes, texto
    livre normalizado no parser (ver lattesParser.js -> versão Python)."""

    __tablename__ = "idiomas_aluno"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    leitura: Mapped[str | None] = mapped_column(String(30))
    fala: Mapped[str | None] = mapped_column(String(30))
    escrita: Mapped[str | None] = mapped_column(String(30))
    compreensao: Mapped[str | None] = mapped_column(String(30))

    aluno: Mapped["Aluno"] = relationship(back_populates="idiomas")


class FormacaoComplementar(Base):
    """Cursos/certificações além da formação principal — o que o
    Lattes chama de 'Formação Complementar' (ex.: cursos de extensão,
    minicursos), extraído na Fase 4 (importação do Lattes)."""

    __tablename__ = "formacoes_complementares"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(100))
    nome: Mapped[str] = mapped_column(String(500), nullable=False)
    instituicao: Mapped[str | None] = mapped_column(String(255))
    ano: Mapped[str | None] = mapped_column(String(10))

    aluno: Mapped["Aluno"] = relationship(back_populates="formacoes_complementares")


class Projeto(Base):
    __tablename__ = "projetos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    centro_id: Mapped[str | None] = mapped_column(ForeignKey("centros.id"))
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("cursos.id"))
    area_projeto_id: Mapped[int | None] = mapped_column(ForeignKey("areas_projeto.id"))
    tipo_projeto_id: Mapped[int | None] = mapped_column(ForeignKey("tipos_projeto.id"))
    link: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    aluno: Mapped["Aluno"] = relationship(back_populates="projetos")
    tecnologias: Mapped[list["ProjetoTecnologia"]] = relationship(
        back_populates="projeto", cascade="all, delete-orphan"
    )


class ProjetoTecnologia(Base):
    """Associativa projeto <-> tecnologia. Guarda o nome em texto além
    do FK opcional para tecnologia catalogada, pois o frontend atual
    aceita qualquer tecnologia digitada livremente no projeto."""

    __tablename__ = "projeto_tecnologias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    projeto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projetos.id"), nullable=False)
    tecnologia_id: Mapped[int | None] = mapped_column(ForeignKey("tecnologias.id"))
    nome: Mapped[str] = mapped_column(String(255), nullable=False)

    projeto: Mapped["Projeto"] = relationship(back_populates="tecnologias")


class ExperienciaProfissional(Base):
    __tablename__ = "experiencias_profissionais"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    empresa: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str] = mapped_column(String(255), nullable=False)
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    atual: Mapped[bool] = mapped_column(Boolean, server_default="false")
    area_atuacao: Mapped[str | None] = mapped_column(String(255))
    descricao: Mapped[str | None] = mapped_column(Text)
    tecnologias: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    aluno: Mapped["Aluno"] = relationship(back_populates="experiencias")


class AlunoAreaInteresse(Base):
    __tablename__ = "aluno_areas_interesse"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alunos.id"), nullable=False)
    area_interesse_id: Mapped[int] = mapped_column(ForeignKey("areas_interesse.id"), nullable=False)

    aluno: Mapped["Aluno"] = relationship(back_populates="areas_interesse")
