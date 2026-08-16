"""create trip members table

Revision ID: 5b1a3d90f231
Revises: 892c358a7734
Create Date: 2026-08-17 01:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5b1a3d90f231'
down_revision: Union[str, Sequence[str], None] = '892c358a7734'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trip_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('OWNER', 'MEMBER', name='memberrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trip_id', 'user_id', name='uq_trip_member_trip_user')
    )
    op.create_index(op.f('ix_trip_members_id'), 'trip_members', ['id'], unique=False)
    op.create_index(op.f('ix_trip_members_trip_id'), 'trip_members', ['trip_id'], unique=False)
    op.create_index(op.f('ix_trip_members_user_id'), 'trip_members', ['user_id'], unique=False)
    op.create_index('ix_trip_members_trip_user', 'trip_members', ['trip_id', 'user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_trip_members_trip_user', table_name='trip_members')
    op.drop_index(op.f('ix_trip_members_user_id'), table_name='trip_members')
    op.drop_index(op.f('ix_trip_members_trip_id'), table_name='trip_members')
    op.drop_index(op.f('ix_trip_members_id'), table_name='trip_members')
    op.drop_table('trip_members')
    sa.Enum(name='memberrole').drop(op.get_bind(), checkfirst=True)
