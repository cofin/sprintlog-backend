"""is_task_type

Revision ID: 92daeb7cb32c
Revises: b0c3d687d336
Create Date: 2023-05-28 18:31:46.413288

"""
import sqlalchemy as sa
from alembic import op
from litestar.contrib.sqlalchemy.types import GUID

__all__ = ["downgrade", "upgrade"]


sa.GUID = GUID

# revision identifiers, used by Alembic.
revision = "92daeb7cb32c"
down_revision = "b0c3d687d336"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("backlog", sa.Column("type", sa.String(), nullable=False, server_default="backlog"))
    op.create_index(op.f("ix_backlog_type"), "backlog", ["type"], unique=False)
    op.drop_column("backlog", "is_task")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("backlog", sa.Column("is_task", sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.drop_index(op.f("ix_backlog_type"), table_name="backlog")
    op.drop_column("backlog", "type")
    # ### end Alembic commands ###
