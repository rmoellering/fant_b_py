from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound

from models import Player
from utils import get_logger, utc_to_local, replace_accents, compress_string

log = get_logger(__name__)

def get_or_create_player(session, yahoo_id, team, data, game_date):

    try:
        player = session.query(Player).filter(Player.yahoo_id==yahoo_id).one()
        if player.team_id != team.id and (player.last_team_change is None or player.last_team_change < game_date):
            log.info("{} changing from {} to {} on {} last change {}".
                     format(player.name, player.team.name, team.name, game_date, player.last_team_change))
            player.team = team
            player.last_team_change = game_date
            player.number = data['uniform_number']
            player.date_updated = datetime.utcnow()

    except NoResultFound:
        log.info("Couldn't find {}, creating new player.".format(yahoo_id))

        # TODO: DOB?
        player = Player(
            yahoo_id=yahoo_id,
            team=team,
            name=data['display_name'],
            first_name=data['first_name'],
            middle_name=None,
            last_name=data['last_name'],
            suffix=None,
            number=data['uniform_number'],
            last_team_change=game_date,
            lname=compress_string(replace_accents(data['display_name']))
        )
        player.pname = player.p_name()
        session.add(player)
        log.debug('Created: {} | {} | {} | {} | {}|{}|{}|{}'.
                  format(player.yahoo_id, player.team.name, player.number, player.name,
                         player.first_name, player.middle_name, player.last_name, player.suffix))

    session.commit()

    return player

