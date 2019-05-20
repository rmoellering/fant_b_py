from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils import get_logger
from models import Team, GameStatus

log = get_logger(__name__)

log.info('Connecting...')
engine = create_engine('postgresql://robmo:@localhost:5432/fant_b')
Session = sessionmaker(bind=engine)
session = Session()

log.info('Creating GameStatuses...')
session.add(GameStatus(id=1, name="Future"))
session.add(GameStatus(id=2, name="In Progress"))
session.add(GameStatus(id=3, name="Delayed"))
session.add(GameStatus(id=4, name="Postponed"))
session.add(GameStatus(id=5, name="Finished"))
session.add(GameStatus(id=6, name="Other"))
session.commit()

log.info('Creating Teams...')
session.add(Team(id=9, abbr="BOS", name="Red Sox", city="Boston", state="MA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/redsox_wblrgr_70x70.png",
            logo_lg="", park=None, league="A", division="E", yahoo_id=2))
session.add(Team(id=6, abbr="BAL", name="Orioles", city="Baltimore", state="MD", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/orioles_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="E", yahoo_id=1))
session.add(Team(id=7, abbr="TB", name="Rays", city="Tampa Bay", state="FL", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/rays_lrgr_70x70.3.png",
            logo_lg="", park=None, league="A", division="E", yahoo_id=30))
session.add(Team(id=8, abbr="NYY", name="Yankees", city="New York", state="NY", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/yankees_wblrgr_70x70.png",
            logo_lg="", park=None, league="A", division="E", yahoo_id=10))
session.add(Team(id=17, abbr="TOR", name="Blue Jays", city="Toronto", state="TOR", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/bluejays_lrgr_70x70.6.png",
            logo_lg="", park=None, league="A", division="E", yahoo_id=14))

session.add(Team(id=11, abbr="CLE", name="Indians", city="Cleveland", state="OH", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/indians_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="C", yahoo_id=5))
session.add(Team(id=18, abbr="KC", name="Royals", city="Kansas City", state="MO", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/royals_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="C", yahoo_id=7))
session.add(Team(id=25, abbr="CHW", name="White Sox", city="Chicago", state="IL", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/whitesox_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="C", yahoo_id=4))
session.add(Team(id=26, abbr="DET", name="Tigers", city="Detroit", state="MI", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/tigers_wblrgr_70x70.png",
            logo_lg="", park=None, league="A", division="C", yahoo_id=6))
session.add(Team(id=28, abbr="MIN", name="Twins", city="Minneapolis", state="MN", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/twins_wblrgr_70x70.png",
            logo_lg="", park=None, league="A", division="C", yahoo_id=9))

session.add(Team(id=3, abbr="SEA", name="Mariners", city="Seattle", state="WA", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180412/mariners_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="W", yahoo_id=12))
session.add(Team(id=4, abbr="OAK", name="Athletics", city="Oakland", state="CA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/athletics_wblrgr_70x70.png",
            logo_lg="", park=None, league="A", division="W", yahoo_id=11))
session.add(Team(id=16, abbr="HOU", name="Astros", city="Houston", state="TX", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180604/70x70/astros.1.png",
            logo_lg="", park=None, league="A", division="W", yahoo_id=18))
session.add(Team(id=21, abbr="LAA", name="Angels", city="Anaheim", state="CA", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/angels_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="W", yahoo_id=3))
session.add(Team(id=29, abbr="TEX", name="Rangers", city="Arlington", state="TX", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/tx_rangers_lrgr_70x70.1.png",
            logo_lg="", park=None, league="A", division="W", yahoo_id=13))

session.add(Team(id=5, abbr="NYM", name="Mets", city="New York", state="NY", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/mets_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="E", yahoo_id=21))
session.add(Team(id=10, abbr="PHI", name="Phillies", city="Philadelphia", state="PA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/phillies_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="E", yahoo_id=22))
session.add(Team(id=13, abbr="MIA", name="Marlins", city="Miami", state="FL", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/marlins_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="E", yahoo_id=28))
session.add(Team(id=14, abbr="ATL", name="Braves", city="Atlanta", state="GA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/braves_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="E", yahoo_id=15))
session.add(Team(id=19, abbr="WAS", name="Nationals", city="Washington", state="DC", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/nationals_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="E", yahoo_id=20))

session.add(Team(id=1, abbr="MIL", name="Brewers", city="Milwaukee", state="WI", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/brewers_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="C", yahoo_id=8))
session.add(Team(id=2, abbr="CHC", name="Cubs", city="Chicago", state="IL", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/cubs_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="C", yahoo_id=16))
session.add(Team(id=12, abbr="CIN", name="Reds", city="Cincinnati", state="OH", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/reds_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="C", yahoo_id=17))
session.add(Team(id=20, abbr="STL", name="Cardinals", city="St Louis", state="MO", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/cardinals_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="C", yahoo_id=24))
session.add(Team(id=27, abbr="PIT", name="Pirates", city="Pittsburgh", state="PA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/pirates_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="C", yahoo_id=23))

session.add(Team(id=15, abbr="COL", name="Rockies", city="Denver", state="CO", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/rockies_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="W", yahoo_id=27))
session.add(Team(id=22, abbr="SD", name="Padres", city="San Diego", state="CA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/padres_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="W", yahoo_id=25))
session.add(Team(id=23, abbr="SF", name="Giants", city="San Francisco", state="CA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/giants_lrgr_70x70.1.png",
            logo_lg="", park=None, league="N", division="W", yahoo_id=26))
session.add(Team(id=24, abbr="LAD", name="Dodgers", city="Los Angeles", state="CA", \
            logo_sm="https://s.yimg.com/xe/assets/logos/cv/api/default/20180410/dodgers_wblrgr_70x70.png",
            logo_lg="", park=None, league="N", division="W", yahoo_id=19))
session.add(Team(id=30, abbr="ARI", name="Diamondbacks", city="Phoenix", state="AZ", \
            logo_sm="https://s.yimg.com/xe/logos/cv/api/default/20180411/diamondbacks_lrgr_70x70.2.png",
            logo_lg="", park=None, league="N", division="W", yahoo_id=29))

session.commit()
session.close()
log.info('Done')

