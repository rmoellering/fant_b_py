import datetime
import os
import sys
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from utils import get_logger, replace_accents

from models import GameStatus, Park, Team, Player, Game, BatterGame, BatterSummary, BatterRank, PitcherGame, PitcherSummary, PitcherRank

exit('OBSOLETE: USE ALEMBIC')

log = get_logger(__name__)

Base = declarative_base()

table_list = [
    GameStatus.__table__, 
    Park.__table__,
    Team.__table__,
    Player.__table__,
    Game.__table__,
    BatterGame.__table__,
    BatterSummary.__table__,
    BatterRank.__table__,
    PitcherGame.__table__,
    PitcherSummary.__table__,
    PitcherRank.__table__
]

engine = create_engine('postgresql://robmo:@localhost:5432/fant_b')
Base.metadata.bind = engine        
Base.metadata.create_all(tables=table_list)
