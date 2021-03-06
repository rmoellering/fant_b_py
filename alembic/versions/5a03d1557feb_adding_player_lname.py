"""adding player.lname

Revision ID: 5a03d1557feb
Revises: f5de4b180c1c
Create Date: 2019-05-06 12:39:48.552228

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a03d1557feb'
down_revision = 'f5de4b180c1c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('player', sa.Column('lname', sa.String(length=25), nullable=True))
    op.create_index(op.f('ix_player_lname'), 'player', ['lname'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_player_lname'), table_name='player')
    op.drop_column('player', 'lname')
    # ### end Alembic commands ###
