"""add trip planning and itinerary fields

Revision ID: 892c358a7734
Revises: 2de51bce06b3
Create Date: 2026-08-12 00:59:20.394730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '892c358a7734'
down_revision: Union[str, Sequence[str], None] = '2de51bce06b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("num_travellers", sa.Integer(), nullable=True),
    )
    op.add_column(
        "trips",
        sa.Column("budget", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "trips",
        sa.Column("special_requirements", sa.Text(), nullable=True),
    )
    op.add_column(
        "trips",
        sa.Column("itinerary", sa.JSON(), nullable=True),
    )
    op.add_column(
        "trips",
        sa.Column("destination_image", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trips", "destination_image")
    op.drop_column("trips", "itinerary")
    op.drop_column("trips", "special_requirements")
    op.drop_column("trips", "budget")
    op.drop_column("trips", "num_travellers")