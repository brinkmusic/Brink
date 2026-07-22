"""add User.bio (T48)

Revision ID: a1c47f9e2b30
Revises: 3978f11ad4da
Create Date: 2026-07-22 00:00:00.000000

Hand-written (not --autogenerate, which needs a live DB): adds the nullable `bio` text column to
the public "User" table so a user can set a short profile bio (T48). Nullable with no default, so
existing rows simply get NULL. `downgrade` drops the column again.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c47f9e2b30'
down_revision: Union[str, None] = '3978f11ad4da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new nullable bio column to the "User" table (public schema).
    op.add_column('User', sa.Column('bio', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('User', 'bio')
