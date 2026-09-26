"""schema inicial — Fase 1 (infraestrutura + modelo de dados completo)

Revision ID: 0001
Revises:
Create Date: 2026-09-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("matricula", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="aluno"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('aluno', 'admin')", name="ck_usuarios_role"),
        sa.UniqueConstraint("matricula", name="uq_usuarios_matricula"),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )
    op.create_index("ix_usuarios_matricula", "usuarios", ["matricula"])
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    op.create_table(
        "centros",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
    )

    op.create_table(
        "cursos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("centro_id", sa.String(20), sa.ForeignKey("centros.id"), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
    )

    op.create_table(
        "tecnologias",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False, unique=True),
    )

    op.create_table(
        "conhecimentos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False, unique=True),
    )

    op.create_table(
        "areas_projeto",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False, unique=True),
    )

    op.create_table(
        "tipos_projeto",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False, unique=True),
    )

    op.create_table(
        "areas_interesse",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(255), nullable=False, unique=True),
    )

    op.create_table(
        "alunos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuarios.id"), nullable=False, unique=True),
        sa.Column("matricula", sa.String(50), nullable=False),
        sa.Column("nome_completo", sa.String(255)),
        sa.Column("lattes_id", sa.String(50)),
        sa.Column("email", sa.String(255)),
        sa.Column("telefone", sa.String(30)),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("curso_id", sa.Integer, sa.ForeignKey("cursos.id")),
        sa.Column("instituicao", sa.String(255)),
        sa.Column("nivel_formacao", sa.String(50)),
        sa.Column("status_formacao", sa.String(50)),
        sa.Column("ano_inicio_formacao", sa.String(10)),
        sa.Column("ano_fim_formacao", sa.String(10)),
        sa.Column("semestre_atual", sa.String(10)),
        sa.Column("previsao_conclusao", sa.String(10)),
        sa.Column("possui_experiencia", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("matricula", name="uq_alunos_matricula"),
    )
    op.create_index("ix_alunos_matricula", "alunos", ["matricula"])

    op.create_table(
        "tccs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False, unique=True),
        sa.Column("situacao", sa.String(20), nullable=False, server_default="nao_iniciou"),
        sa.Column("titulo", sa.String(500)),
        sa.Column("resumo", sa.Text),
        sa.Column("orientador", sa.String(255)),
        sa.Column("palavras_chave", postgresql.ARRAY(sa.String)),
        sa.CheckConstraint("situacao IN ('nao_iniciou', 'em_andamento', 'concluido')", name="ck_tccs_situacao"),
    )

    op.create_table(
        "aluno_tecnologias",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("tecnologia_id", sa.Integer, sa.ForeignKey("tecnologias.id"), nullable=False),
        sa.Column("nivel", sa.String(30)),
    )

    op.create_table(
        "aluno_conhecimentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("conhecimento_id", sa.Integer, sa.ForeignKey("conhecimentos.id"), nullable=False),
        sa.Column("nivel", sa.String(30)),
    )

    op.create_table(
        "idiomas_aluno",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("leitura", sa.String(30)),
        sa.Column("fala", sa.String(30)),
        sa.Column("escrita", sa.String(30)),
        sa.Column("compreensao", sa.String(30)),
    )

    op.create_table(
        "formacoes_complementares",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("tipo", sa.String(100)),
        sa.Column("nome", sa.String(500), nullable=False),
        sa.Column("instituicao", sa.String(255)),
        sa.Column("ano", sa.String(10)),
    )

    op.create_table(
        "projetos",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("nome", sa.String(500), nullable=False),
        sa.Column("descricao", sa.Text),
        sa.Column("centro_id", sa.String(20), sa.ForeignKey("centros.id")),
        sa.Column("curso_id", sa.Integer, sa.ForeignKey("cursos.id")),
        sa.Column("area_projeto_id", sa.Integer, sa.ForeignKey("areas_projeto.id")),
        sa.Column("tipo_projeto_id", sa.Integer, sa.ForeignKey("tipos_projeto.id")),
        sa.Column("link", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projeto_tecnologias",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("projeto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projetos.id"), nullable=False),
        sa.Column("tecnologia_id", sa.Integer, sa.ForeignKey("tecnologias.id")),
        sa.Column("nome", sa.String(255), nullable=False),
    )

    op.create_table(
        "experiencias_profissionais",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("empresa", sa.String(255), nullable=False),
        sa.Column("cargo", sa.String(255), nullable=False),
        sa.Column("data_inicio", sa.Date),
        sa.Column("data_fim", sa.Date),
        sa.Column("atual", sa.Boolean, server_default="false"),
        sa.Column("area_atuacao", sa.String(255)),
        sa.Column("descricao", sa.Text),
        sa.Column("tecnologias", postgresql.ARRAY(sa.String)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "aluno_areas_interesse",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("area_interesse_id", sa.Integer, sa.ForeignKey("areas_interesse.id"), nullable=False),
    )

    op.create_table(
        "empresas",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("cnpj", sa.String(20), unique=True),
        sa.Column("nome", sa.String(500), nullable=False),
        sa.Column("nome_normalizado", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_empresas_nome_normalizado", "empresas", ["nome_normalizado"])

    op.create_table(
        "convenios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("processo", sa.String(100)),
        sa.Column("data_inicio", sa.Date),
        sa.Column("data_fim_original", sa.String(50)),
        sa.Column("data_fim", sa.Date),
        sa.Column("status", sa.String(20), nullable=False, server_default="indeterminado"),
        sa.Column("fonte", sa.String(255)),
        sa.Column("pagina_origem", sa.String(20)),
        sa.Column("importado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("observacoes", sa.Text),
        sa.CheckConstraint("status IN ('vigente', 'vencido', 'indeterminado')", name="ck_convenios_status"),
    )

    op.create_table(
        "vagas",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("convenio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("convenios.id")),
        sa.Column("titulo", sa.String(500), nullable=False),
        sa.Column("descricao", sa.Text),
        sa.Column("atividades", sa.Text),
        sa.Column("requisitos", sa.Text),
        sa.Column("cursos", postgresql.ARRAY(sa.String)),
        sa.Column("areas", postgresql.ARRAY(sa.String)),
        sa.Column("tecnologias", postgresql.ARRAY(sa.String)),
        sa.Column("modalidade", sa.String(50)),
        sa.Column("localizacao", sa.String(255)),
        sa.Column("bolsa", sa.String(100)),
        sa.Column("carga_horaria", sa.String(50)),
        sa.Column("beneficios", sa.Text),
        sa.Column("quantidade", sa.Integer),
        sa.Column("data_inicio", sa.Date),
        sa.Column("data_fim", sa.Date),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativa"),
        sa.Column("link", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('ativa', 'encerrada')", name="ck_vagas_status"),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("entidade_tipo", sa.String(20), nullable=False),
        sa.Column("entidade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vetor", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.Column("texto_base", sa.Text, nullable=False),
        sa.Column("gerado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("entidade_tipo IN ('aluno', 'empresa', 'vaga')", name="ck_embeddings_entidade_tipo"),
    )
    op.create_index("ix_embeddings_entidade_tipo", "embeddings", ["entidade_tipo"])
    op.create_index("ix_embeddings_entidade_id", "embeddings", ["entidade_id"])

    op.create_table(
        "recomendacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("aluno_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alunos.id"), nullable=False),
        sa.Column("empresa_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("empresas.id")),
        sa.Column("vaga_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vagas.id")),
        sa.Column("similaridade", sa.Float),
        sa.Column("indice_compatibilidade", sa.Float),
        sa.Column("nivel", sa.String(50)),
        sa.Column("pontos_compativeis", postgresql.JSONB),
        sa.Column("pontos_parciais", postgresql.JSONB),
        sa.Column("lacunas", postgresql.JSONB),
        sa.Column("justificativa", sa.Text),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("modelo_llm", sa.String(100)),
        sa.Column("modelo_embedding", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "tipo IN ('aluno_para_vaga', 'aluno_para_empresa', 'vaga_para_aluno')",
            name="ck_recomendacoes_tipo",
        ),
    )

    op.create_table(
        "importacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("fonte", sa.String(100), nullable=False),
        sa.Column("tipo_arquivo", sa.String(20), nullable=False),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finalizado_em", sa.DateTime(timezone=True)),
        sa.Column("total_linhas", sa.Integer),
        sa.Column("sucesso", sa.Integer),
        sa.Column("erros", postgresql.JSONB),
        sa.Column("relatorio", postgresql.JSONB),
    )


def downgrade() -> None:
    op.drop_table("importacoes")
    op.drop_table("recomendacoes")
    op.drop_index("ix_embeddings_entidade_id", table_name="embeddings")
    op.drop_index("ix_embeddings_entidade_tipo", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_table("vagas")
    op.drop_table("convenios")
    op.drop_index("ix_empresas_nome_normalizado", table_name="empresas")
    op.drop_table("empresas")
    op.drop_table("aluno_areas_interesse")
    op.drop_table("experiencias_profissionais")
    op.drop_table("projeto_tecnologias")
    op.drop_table("projetos")
    op.drop_table("formacoes_complementares")
    op.drop_table("idiomas_aluno")
    op.drop_table("aluno_conhecimentos")
    op.drop_table("aluno_tecnologias")
    op.drop_table("tccs")
    op.drop_index("ix_alunos_matricula", table_name="alunos")
    op.drop_table("alunos")
    op.drop_table("areas_interesse")
    op.drop_table("tipos_projeto")
    op.drop_table("areas_projeto")
    op.drop_table("conhecimentos")
    op.drop_table("tecnologias")
    op.drop_table("cursos")
    op.drop_table("centros")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_index("ix_usuarios_matricula", table_name="usuarios")
    op.drop_table("usuarios")
