"""Merge multiple heads

Revision ID: fc80d4e0b3bf
Revises: bb30007db09f, c39aabddb579
Create Date: 2025-04-28 15:20:18.719440

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc80d4e0b3bf'
down_revision = ('bb30007db09f', 'c39aabddb579')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
