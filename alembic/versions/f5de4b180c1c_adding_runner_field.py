"""adding runner field

Revision ID: f5de4b180c1c
Revises: c539c6f42bc3
Create Date: 2019-05-04 17:31:42.156055

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5de4b180c1c'
down_revision = 'c539c6f42bc3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('batter_game', sa.Column('runner', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('batter_game', 'runner')
    # ### end Alembic commands ###