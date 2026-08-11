"""create_google_calendar_connections_table

Revision ID: 2de51bce06b3
Revises: e07f4f1a95a3
Create Date: 2026-08-11 19:31:00.246421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2de51bce06b3'
down_revision: Union[str, Sequence[str], None] = 'e07f4f1a95a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('google_calendar_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_google_calendar_connections_id'), 'google_calendar_connections', ['id'], unique=False)
    op.create_index(op.f('ix_google_calendar_connections_user_id'), 'google_calendar_connections', ['user_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_google_calendar_connections_user_id'), table_name='google_calendar_connections')
    op.drop_index(op.f('ix_google_calendar_connections_id'), table_name='google_calendar_connections')
    op.drop_table('google_calendar_connections')
