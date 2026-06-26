"""004_add_search_history

Revision ID: 004_add_search_history
Revises: 960ccc1ed031
Create Date: 2026-06-26 12:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '004_add_search_history'
down_revision: Union[str, None] = '960ccc1ed031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query', sa.String(length=1024), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=True),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('topic', sa.String(length=255), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('raw_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['discovery_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_search_history_query'), 'search_history', ['query'], unique=False)
    op.create_index(op.f('ix_search_history_session_id'), 'search_history', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_search_history_session_id'), table_name='search_history')
    op.drop_index(op.f('ix_search_history_query'), table_name='search_history')
    op.drop_table('search_history')
