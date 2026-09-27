"""empresa ganha area, segmento, cidade, uf (Fase 12)

Revision ID: ffb1c4999a6f
Revises: 8f3d44e6987e
Create Date: 2026-09-27 02:12:23.263013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ffb1c4999a6f'
down_revision: Union[str, None] = '8f3d44e6987e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('empresas', sa.Column('area', sa.String(length=255), nullable=True))
    op.add_column('empresas', sa.Column('segmento', sa.String(length=255), nullable=True))
    op.add_column('empresas', sa.Column('cidade', sa.String(length=255), nullable=True))
    op.add_column('empresas', sa.Column('uf', sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column('empresas', 'uf')
    op.drop_column('empresas', 'cidade')
    op.drop_column('empresas', 'segmento')
    op.drop_column('empresas', 'area')
