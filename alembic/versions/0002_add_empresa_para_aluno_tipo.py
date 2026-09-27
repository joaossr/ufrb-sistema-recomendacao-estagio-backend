"""adiciona 'empresa_para_aluno' ao tipo de recomendacao (Fase 9 - caminho inverso a partir de empresa)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_recomendacoes_tipo", "recomendacoes", type_="check")
    op.create_check_constraint(
        "ck_recomendacoes_tipo",
        "recomendacoes",
        "tipo IN ('aluno_para_vaga', 'aluno_para_empresa', 'vaga_para_aluno', 'empresa_para_aluno')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_recomendacoes_tipo", "recomendacoes", type_="check")
    op.create_check_constraint(
        "ck_recomendacoes_tipo",
        "recomendacoes",
        "tipo IN ('aluno_para_vaga', 'aluno_para_empresa', 'vaga_para_aluno')",
    )
