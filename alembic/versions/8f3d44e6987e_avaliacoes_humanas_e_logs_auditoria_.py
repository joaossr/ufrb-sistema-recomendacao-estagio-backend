"""avaliacoes_humanas e logs_auditoria (Fase 11)

Revision ID: 8f3d44e6987e
Revises: 0002
Create Date: 2026-09-26 23:05:11.700617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f3d44e6987e'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('logs_auditoria',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('usuario_id', sa.UUID(), nullable=True),
    sa.Column('acao', sa.String(length=100), nullable=False),
    sa.Column('entidade_tipo', sa.String(length=50), nullable=True),
    sa.Column('entidade_id', sa.UUID(), nullable=True),
    sa.Column('detalhes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('avaliacoes_humanas',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('recomendacao_id', sa.UUID(), nullable=False),
    sa.Column('avaliador_usuario_id', sa.UUID(), nullable=False),
    sa.Column('concorda_com_llm', sa.Boolean(), nullable=True),
    sa.Column('nota_humana', sa.Integer(), nullable=True),
    sa.Column('comentario', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('nota_humana IS NULL OR nota_humana BETWEEN 1 AND 5', name='ck_avaliacoes_nota_humana'),
    sa.ForeignKeyConstraint(['avaliador_usuario_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['recomendacao_id'], ['recomendacoes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('avaliacoes_humanas')
    op.drop_table('logs_auditoria')
