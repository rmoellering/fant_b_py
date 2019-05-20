"""Initial migration

Revision ID: c766dbc2b61b
Revises: 
Create Date: 2019-04-20 17:53:23.112420

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c766dbc2b61b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('game_status',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('park',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('city', sa.String(length=25), nullable=True),
    sa.Column('state', sa.String(length=2), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('team',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('abbr', sa.String(length=3), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('city', sa.String(length=25), nullable=True),
    sa.Column('state', sa.String(length=3), nullable=True),
    sa.Column('logo_sm', sa.String(length=100), nullable=True),
    sa.Column('logo_lg', sa.String(length=100), nullable=True),
    sa.Column('park_id', sa.Integer(), nullable=True),
    sa.Column('league', sa.String(length=1), nullable=True),
    sa.Column('division', sa.String(length=1), nullable=True),
    sa.Column('yahoo_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['park_id'], ['park.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('yahoo_id')
    )
    op.create_index(op.f('ix_team_name'), 'team', ['name'], unique=False)
    op.create_table('player',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('yahoo_id', sa.Integer(), nullable=True),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.Column('last_team_change', sa.Date(), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=True),
    sa.Column('first_name', sa.String(length=25), nullable=True),
    sa.Column('middle_name', sa.String(length=25), nullable=True),
    sa.Column('last_name', sa.String(length=25), nullable=True),
    sa.Column('suffix', sa.String(length=5), nullable=True),
    sa.Column('dob', sa.Date(), nullable=True),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.Column('pname', sa.String(length=25), nullable=True),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('yahoo_id')
    )
    op.create_table('batter_rank',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('r', sa.Integer(), nullable=True),
    sa.Column('hr', sa.Integer(), nullable=True),
    sa.Column('rbi', sa.Integer(), nullable=True),
    sa.Column('obp', sa.Integer(), nullable=True),
    sa.Column('slg', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['player_id'], ['player.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('batter_summary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('games', sa.Integer(), nullable=True),
    sa.Column('at_bats', sa.Integer(), nullable=True),
    sa.Column('runs', sa.Integer(), nullable=True),
    sa.Column('hits', sa.Integer(), nullable=True),
    sa.Column('runs_batted_in', sa.Integer(), nullable=True),
    sa.Column('home_runs', sa.Integer(), nullable=True),
    sa.Column('stolen_bases', sa.Integer(), nullable=True),
    sa.Column('walks', sa.Integer(), nullable=True),
    sa.Column('strikeouts', sa.Integer(), nullable=True),
    sa.Column('left_on_base', sa.Integer(), nullable=True),
    sa.Column('doubles', sa.Integer(), nullable=True),
    sa.Column('triples', sa.Integer(), nullable=True),
    sa.Column('hbp', sa.Integer(), nullable=True),
    sa.Column('sac_fly', sa.Integer(), nullable=True),
    sa.Column('obp', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('slugging', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.ForeignKeyConstraint(['player_id'], ['player.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('game',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('yahoo_id', sa.Integer(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('park_id', sa.Integer(), nullable=True),
    sa.Column('home_team_id', sa.Integer(), nullable=True),
    sa.Column('away_team_id', sa.Integer(), nullable=True),
    sa.Column('start', sa.Date(), nullable=True),
    sa.Column('start_time', sa.DateTime(), nullable=True),
    sa.Column('end_time', sa.DateTime(), nullable=True),
    sa.Column('status_id', sa.Integer(), nullable=True),
    sa.Column('progress', sa.String(length=6), nullable=True),
    sa.Column('home_pitcher_id', sa.Integer(), nullable=True),
    sa.Column('away_pitcher_id', sa.Integer(), nullable=True),
    sa.Column('home_runs', sa.Integer(), nullable=True),
    sa.Column('away_runs', sa.Integer(), nullable=True),
    sa.Column('home_hits', sa.Integer(), nullable=True),
    sa.Column('away_hits', sa.Integer(), nullable=True),
    sa.Column('home_errors', sa.Integer(), nullable=True),
    sa.Column('away_errors', sa.Integer(), nullable=True),
    sa.Column('innings', sa.Integer(), nullable=True),
    sa.Column('inning_data', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['away_pitcher_id'], ['player.id'], ),
    sa.ForeignKeyConstraint(['away_team_id'], ['team.id'], ),
    sa.ForeignKeyConstraint(['home_pitcher_id'], ['player.id'], ),
    sa.ForeignKeyConstraint(['home_team_id'], ['team.id'], ),
    sa.ForeignKeyConstraint(['park_id'], ['park.id'], ),
    sa.ForeignKeyConstraint(['status_id'], ['game_status.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('yahoo_id')
    )
    op.create_index(op.f('ix_game_start'), 'game', ['start'], unique=False)
    op.create_table('pitcher_rank',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('w', sa.Integer(), nullable=True),
    sa.Column('k', sa.Integer(), nullable=True),
    sa.Column('hs', sa.Integer(), nullable=True),
    sa.Column('era', sa.Integer(), nullable=True),
    sa.Column('whip', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['player_id'], ['player.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pitcher_summary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('games', sa.Integer(), nullable=True),
    sa.Column('innings', sa.Numeric(precision=3, scale=1), nullable=True),
    sa.Column('whole_innings', sa.Integer(), nullable=True),
    sa.Column('partial_innings', sa.Integer(), nullable=True),
    sa.Column('outs', sa.Integer(), nullable=True),
    sa.Column('hits', sa.Integer(), nullable=True),
    sa.Column('runs', sa.Integer(), nullable=True),
    sa.Column('earned_runs', sa.Integer(), nullable=True),
    sa.Column('walks', sa.Integer(), nullable=True),
    sa.Column('strikeouts', sa.Integer(), nullable=True),
    sa.Column('home_runs', sa.Integer(), nullable=True),
    sa.Column('pitches', sa.Integer(), nullable=True),
    sa.Column('strikes', sa.Integer(), nullable=True),
    sa.Column('ground_balls', sa.Integer(), nullable=True),
    sa.Column('fly_balls', sa.Integer(), nullable=True),
    sa.Column('batters', sa.Integer(), nullable=True),
    sa.Column('wins', sa.Integer(), nullable=True),
    sa.Column('losses', sa.Integer(), nullable=True),
    sa.Column('holds', sa.Integer(), nullable=True),
    sa.Column('saves', sa.Integer(), nullable=True),
    sa.Column('blown', sa.Integer(), nullable=True),
    sa.Column('era', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('whip', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['player_id'], ['player.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('batter_game',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.Column('game_id', sa.Integer(), nullable=True),
    sa.Column('at_bats', sa.Integer(), nullable=True),
    sa.Column('runs', sa.Integer(), nullable=True),
    sa.Column('hits', sa.Integer(), nullable=True),
    sa.Column('runs_batted_in', sa.Integer(), nullable=True),
    sa.Column('home_runs', sa.Integer(), nullable=True),
    sa.Column('stolen_bases', sa.Integer(), nullable=True),
    sa.Column('walks', sa.Integer(), nullable=True),
    sa.Column('strikeouts', sa.Integer(), nullable=True),
    sa.Column('left_on_base', sa.Integer(), nullable=True),
    sa.Column('doubles', sa.Integer(), nullable=True),
    sa.Column('triples', sa.Integer(), nullable=True),
    sa.Column('hbp', sa.Integer(), nullable=True),
    sa.Column('sac_fly', sa.Integer(), nullable=True),
    sa.Column('gidp', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['game_id'], ['game.id'], ),
    sa.ForeignKeyConstraint(['player_id'], ['player.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pitcher_game',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_updated', sa.DateTime(), nullable=True),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.Column('game_id', sa.Integer(), nullable=True),
    sa.Column('spot', sa.Integer(), nullable=True),
    sa.Column('innings', sa.Numeric(precision=3, scale=1), nullable=True),
    sa.Column('whole_innings', sa.Integer(), nullable=True),
    sa.Column('partial_innings', sa.Integer(), nullable=True),
    sa.Column('outs', sa.Integer(), nullable=True),
    sa.Column('hits', sa.Integer(), nullable=True),
    sa.Column('runs', sa.Integer(), nullable=True),
    sa.Column('earned_runs', sa.Integer(), nullable=True),
    sa.Column('walks', sa.Integer(), nullable=True),
    sa.Column('strikeouts', sa.Integer(), nullable=True),
    sa.Column('home_runs', sa.Integer(), nullable=True),
    sa.Column('pitches', sa.Integer(), nullable=True),
    sa.Column('strikes', sa.Integer(), nullable=True),
    sa.Column('ground_balls', sa.Integer(), nullable=True),
    sa.Column('fly_balls', sa.Integer(), nullable=True),
    sa.Column('batters', sa.Integer(), nullable=True),
    sa.Column('win', sa.Integer(), nullable=True),
    sa.Column('loss', sa.Integer(), nullable=True),
    sa.Column('hold', sa.Integer(), nullable=True),
    sa.Column('sv', sa.Integer(), nullable=True),
    sa.Column('blown', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['game_id'], ['game.id'], ),
    sa.ForeignKeyConstraint(['player_id'], ['player.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('pitcher_game')
    op.drop_table('batter_game')
    op.drop_table('pitcher_summary')
    op.drop_table('pitcher_rank')
    op.drop_index(op.f('ix_game_start'), table_name='game')
    op.drop_table('game')
    op.drop_table('batter_summary')
    op.drop_table('batter_rank')
    op.drop_table('player')
    op.drop_index(op.f('ix_team_name'), table_name='team')
    op.drop_table('team')
    op.drop_table('park')
    op.drop_table('game_status')
    # ### end Alembic commands ###
