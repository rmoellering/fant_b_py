import datetime
import os
import re
import sys
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Integer, String, DateTime, Date, Boolean, Numeric, JSON
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from utils import get_logger, replace_accents
 
log = get_logger(__name__)

class Stamped(object):
    # @declared_attr
    # def __tablename__(cls):
    #     return cls.__name__.lower()

    # # __table_args__ = {'mysql_engine': 'InnoDB'}
    # __table_args__ = {}

    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.datetime.utcnow)

Base = declarative_base()

class YahooBatting(object):
    AT_BATS = 2
    RUNS = 3
    HITS = 4
    HOME_RUNS = 7
    RBI = 8
    SB = 12
    BB = 14
    STRIKEOUTS = 17
    AVG = 23
    LOB = 53

    # CHOICES = (
    #     (AT_BATS, 'At Bats'),
    # )


class YahooPitching(object):

    W = 101
    L = 102
    SAVES = 107
    HITS = 111
    RUNS = 113
    EARNED_RUNS = 114
    HOME_RUNS = 115
    BB = 118
    STRIKEOUTS = 121
    HOLDS = 136
    IP = 139
    ERA = 140
    WHIP = 141
    BLOWN_SAVES = 147


class GameStatus(Base, Stamped):
    __tablename__ = 'game_status'

    name = Column(String(50))

    FUTURE = 1
    IN_PROGRESS = 2
    DELAYED = 3
    POSTPONED = 4
    FINISHED = 5
    OTHER = 6
    SUSPENDED = 7

    CHOICES = (
        (FUTURE, 'Future'),
        (IN_PROGRESS, 'In Progress'),
        (DELAYED, 'Delayed'),
        (POSTPONED, 'Postponed'),
        (FINISHED, 'Finished'),
        (OTHER, 'Other'),
        (SUSPENDED, 'Suspended')
    )


class Park(Base, Stamped):
    __tablename__ = 'park'

    name = Column(String(50))
    city = Column(String(25))
    state = Column(String(2))


class Team(Base, Stamped):
    __tablename__ = 'team'

    abbr = Column(String(3))
    name = Column(String(50), index=True)
    city = Column(String(25))
    state = Column(String(3))
    logo_sm = Column(String(100))
    logo_lg = Column(String(100))
    park_id = Column(Integer, ForeignKey('park.id'))
    park = relationship(Park)
    league = Column(String(1))
    division = Column(String(1))
    yahoo_id = Column(Integer, unique=True)

    # objects = TeamManager()

    # def fetch_logo_sm(self):
    #     log.info('Getting {} small logo...'.format(self.name))

    #@property
    def full_name(self):
        return '{} {}'.format(self.city, self.name)

    #@property
    def yahoo_name(self):
        return '{}-{}'.format(
            self.city.lower().replace(' ', '-').replace('.', ''),
            self.name.lower().replace(' ', '-')
        )


class Player(Base, Stamped):
    __tablename__ = 'player'

    yahoo_id = Column(Integer, unique=True)
    team_id = Column(Integer, ForeignKey('team.id'))
    team = relationship(Team)
    last_team_change = Column(Date)
    name = Column(String(50))
    first_name = Column(String(25))
    middle_name = Column(String(25))
    last_name = Column(String(25))
    suffix = Column(String(5))
    dob = Column(Date)
    number = Column(Integer)
    pname = Column(String(25), default='')     # 1st initial, last name, no accents
    lname = Column(String(25), default='', index=True)      # lower case full name, no accents, no punctuation

    # objects = PlayerManager()

    # @property
    def p_name(self):
        # create a short name of the type that is used in batting/pitching notes
        # 1st initial, last name, no accents

        p_name = format(replace_accents(self.first_name[0]))
        if self.middle_name:
            p_name = '{} {}'.format(p_name, replace_accents(self.middle_name))
        p_name = '{} {}'.format(p_name, replace_accents(self.last_name))
        if self.suffix:
            p_name = '{} {}'.format(p_name, replace_accents(self.suffix))

        p_name = p_name.rstrip('.')
        return p_name

    # # @property
    # def pitching_notes_name(self):
    #     return '{}-{}'.format(
    #         self.city.lower().replace(' ', '-').replace('.', ''),
    #         self.name.lower().replace(' ', '-')
    #     )

    # @property
    def alt_name(self):

        replace = {
            'V Nuno III': 'V Nuno',
            'D Ponce de Leon': 'D Poncedeleon',
            'M Wright': 'M Wright Jr',
        }
        if self.p_name in replace.keys():
            #log.debug('Replacing {} with {}'.format(self.p_name, replace[self.p_name]))
            return replace[self.p_name]
        else:
            return None


class Game(Base, Stamped):
    __tablename__ = 'game'

    yahoo_id = Column(Integer, unique=True)
    year = Column(Integer, default=0)
    park_id = Column(Integer, ForeignKey('park.id'))
    park = relationship(Park)
    home_team_id = Column(Integer, ForeignKey('team.id'))
    home_team = relationship(Team, foreign_keys=[home_team_id])
    away_team_id = Column(Integer, ForeignKey('team.id'))
    away_team = relationship(Team, foreign_keys=[away_team_id])
    start = Column(Date, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status_id = Column(Integer, ForeignKey('game_status.id'))
    status = relationship(GameStatus)
    progress = Column(String(6))
    home_pitcher_id = Column(Integer, ForeignKey('player.id'))
    home_pitcher = relationship(Player, foreign_keys=[home_pitcher_id])
    away_pitcher_id = Column(Integer, ForeignKey('player.id'))
    away_pitcher = relationship(Player, foreign_keys=[away_pitcher_id])
    home_runs = Column(Integer, default=0)
    away_runs = Column(Integer, default=0)
    home_hits = Column(Integer, default=0)
    away_hits = Column(Integer, default=0)
    home_errors = Column(Integer, default=0)
    away_errors = Column(Integer, default=0)
    innings = Column(Integer, default=0)
    inning_data = Column(JSON)

    def set_status(self, yahoo_status, session):
        if yahoo_status == 'pregame':
            self.status = session.query(GameStatus).get(GameStatus.FUTURE)
        elif yahoo_status == 'in_progress':
            self.status = session.query(GameStatus).get(GameStatus.IN_PROGRESS)
        elif yahoo_status == 'final':
            self.status = session.query(GameStatus).get(GameStatus.FINISHED)
        elif yahoo_status == 'suspended':
            self.status = session.query(GameStatus).get(GameStatus.SUSPENDED)
        else:
            raise ValueError('Unrecognized yahoo status: {}'.format(yahoo_status))

    def extract_yahoo_id(self, source):
        # data-tst="GameItem-mlb.g.380815116"
        # url: /mlb/milwaukee-brewers-chicago-cubs-380815116/
        # {away first}-{away last}-{home first}-{away last}-{id}
        # m = re.match('GameItem-mlb.g.([0-9]+)', source)
        # if m:
        #     self.yahoo_id = m.group(1)
        # else:
        #     log.warn('Could not find yahoo game id')

        m = re.match('mlb.g.([0-9]+)', source)
        if m:
            self.yahoo_id = m.group(1)
        else:
            log.warn('Could not find yahoo game id')


class BatterGame(Base, Stamped):
    __tablename__ = 'batter_game'

    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player)
    team_id = Column(Integer, ForeignKey('team.id'))
    team = relationship(Team)
    game_id = Column(Integer, ForeignKey('game.id'))
    game = relationship(Game)
    at_bats = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    runs_batted_in = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    stolen_bases = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    left_on_base = Column(Integer, default=0)
    doubles = Column(Integer, default=0)
    triples = Column(Integer, default=0)
    hbp = Column(Integer, default=0)
    sac_fly = Column(Integer, default=0)
    gidp = Column(Integer, default=0)
    pitcher = Column(Boolean, default=False)
    catcher = Column(Boolean, default=False)
    first = Column(Boolean, default=False)
    second = Column(Boolean, default=False)
    third = Column(Boolean, default=False)
    shortstop = Column(Boolean, default=False)
    outfield = Column(Boolean, default=False)
    left = Column(Boolean, default=False)
    center = Column(Boolean, default=False)
    right = Column(Boolean, default=False)
    dh = Column(Boolean, default=False)
    pinch = Column(Boolean, default=False)
    runner = Column(Boolean, default=False)


class BatterSummary(Base, Stamped):
    __tablename__ = 'batter_summary'

    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player)
    year = Column(Integer, default=0)
    games = Column(Integer, default=0)
    at_bats = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    runs_batted_in = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    stolen_bases = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    left_on_base = Column(Integer, default=0)
    doubles = Column(Integer, default=0)
    triples = Column(Integer, default=0)
    hbp = Column(Integer, default=0)
    sac_fly = Column(Integer, default=0)
    obp = Column(Numeric(precision=4, scale=3))
    slugging = Column(Numeric(precision=4, scale=3))


class BatterRank(Base, Stamped):
    __tablename__ = 'batter_rank'

    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player)
    r = Column(Integer, default=0)
    hr = Column(Integer, default=0)
    rbi = Column(Integer, default=0)
    obp = Column(Integer, default=0)
    slg = Column(Integer, default=0)


class PitcherGame(Base, Stamped):
    __tablename__ = 'pitcher_game'

    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player)
    team_id = Column(Integer, ForeignKey('team.id'))
    team = relationship(Team)
    game_id = Column(Integer, ForeignKey('game.id'))
    game = relationship(Game)
    spot = Column(Integer, default=0)           # can't use 'order'
    innings = Column(Numeric(precision=3, scale=1))
    whole_innings = Column(Integer, default=0)
    partial_innings = Column(Integer, default=0)
    outs = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    pitches = Column(Integer, default=0)
    strikes = Column(Integer, default=0)
    ground_balls = Column(Integer, default=0)
    fly_balls = Column(Integer, default=0)
    batters = Column(Integer, default=0)
    win = Column(Integer, default=0)
    loss = Column(Integer, default=0)
    hold = Column(Integer, default=0)
    sv = Column(Integer, default=0)         # can't overload 'save'
    blown = Column(Integer, default=0)
    start = Column(Boolean, default=False)
    relief = Column(Boolean, default=False)

    # @property
    # def balls(self):
    #     return self.pitches - self.strikes


class PitcherSummary(Base, Stamped):
    __tablename__ = 'pitcher_summary'

    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player)
    year = Column(Integer, default=0)
    games = Column(Integer, default=0)
    innings = Column(Numeric(precision=3, scale=1))
    whole_innings = Column(Integer, default=0)
    partial_innings = Column(Integer, default=0)
    outs = Column(Integer, default=0)
    hits = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    earned_runs = Column(Integer, default=0)
    walks = Column(Integer, default=0)
    strikeouts = Column(Integer, default=0)
    home_runs = Column(Integer, default=0)
    pitches = Column(Integer, default=0)
    strikes = Column(Integer, default=0)
    ground_balls = Column(Integer, default=0)
    fly_balls = Column(Integer, default=0)
    batters = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    holds = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    blown = Column(Integer, default=0)
    era = Column(Numeric(precision=6, scale=2))
    whip = Column(Numeric(precision=6, scale=2))


class PitcherRank(Base, Stamped):
    __tablename__ = 'pitcher_rank'

    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player)
    w = Column(Integer, default=0)
    k = Column(Integer, default=0)
    hs = Column(Integer, default=0)
    era = Column(Integer, default=0)
    whip = Column(Integer, default=0)


class FantasyAverage(Base, Stamped):
    __tablename__ = 'fantasy_average'

    date = Column(Date, index=True)

    # r/hr/rbi per AB
    runs = Column(Numeric(precision=4, scale=3))
    home_runs = Column(Numeric(precision=4, scale=3))
    rbi = Column(Numeric(precision=4, scale=3))
    obp = Column(Numeric(precision=4, scale=3))
    slg = Column(Numeric(precision=4, scale=3))

    # w/k/svh per IP
    wins = Column(Numeric(precision=4, scale=3))
    strikeouts = Column(Numeric(precision=4, scale=3))
    save_hold = Column(Numeric(precision=4, scale=3))
    era = Column(Numeric(precision=4, scale=3))
    whip = Column(Numeric(precision=4, scale=3))



#engine = create_engine('postgresql://robmo:@localhost:5432/fant_b')
#Base.metadata.bind = engine        
#Base.metadata.create_all()
