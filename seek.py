from bs4 import BeautifulSoup
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from io import BytesIO
import json
from lxml import html, etree
import re
import requests
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import sys
from time import sleep

import psycopg2


from utils import get_logger, utc_to_local, replace_accents
from managers import get_or_create_player
from models import Game, Team, Player, BatterGame, PitcherGame

log = get_logger(__name__)


def seek(game_date, from_file=False, force_overwrite=False):

    # 2018 season 3-29 - 10/1
    # 2019 season 3-20, 3-21 japan, 3-28 - 

    log.info("")
    log.info("----<>----<>----<>----<>----<>----<>----<>----<>----<>----<>----<>----<>----<>----<>----")

    if not game_date:
        game_date = timezone.now().date()

    log.info('<[ {} ]>'.format(game_date))

    # get games scoreboard for the day

    games, scoreboard = get_games(game_date, from_file)

    # iterate and process each game

    for game_id, game in games.items():

        # 2019 Japan games
        if game_date == date(2019,3,20) and game_id != 'mlb.g.390320111' \
          or game_date == date(2019, 3, 21) and game_id != 'mlb.g.390321111':
            log.debug('Skipping {} {}'.format(game_date, game_id))
            continue

        # temp placeholder
        yahoo_statuses = ['pregame', 'rain-delay', 'delay', 'postponed', 'cancelled', 'suspended',
                          'in_progress', 'final']

        status = game['status_type']

        if game_id not in scoreboard:
            # log.info('Game {} not in scoreboard, skipping'.format(game_id))
            continue

        if status in ['suspended', 'in_progress', 'final']:
            #log.info(game_type)

            log.info('Processing {} ({})'.format(game_id, game['status_type']))

            cur_game, game_data, stats = get_box(
                suffix=game['navigation_links']['boxscore']['url'],
                game_id=game_id,
                game=game,
                game_date=game_date,
                from_file=from_file)

            cur_game = parse_game_data(
                cur_game=cur_game,
                game_date=game_date, 
                game_id=game_id, 
                game=game, 
                status=status, 
                game_data=game_data,
                from_file=from_file)

            bstats = parse_batting_notes(
                away_batting=game_data['section_notes']['g.awayBatting']['0'],
                home_batting=game_data['section_notes']['g.homeBatting']['0'],
                pitching_notes=game_data['section_notes']['g.pitching']['0'],
                lineups=game_data['lineups'],
                game_id=game_id)


            pstats = parse_pitching_notes(
                pitching_notes=game_data['section_notes']['g.pitching']['0'],
                lineups=game_data['lineups'],
                game_id=game_id
            )

            parse_players(
                game=cur_game,
                stats=stats['playerStats'],
                lineups=game_data['lineups'],
                pstats=pstats,
                bstats=bstats,
                game_id=game_id,
                cur_game=cur_game
            )

        # else:
        #     log.debug('Skipping {} {}'.format(game_id, game['status_type']))


def get_games(game_date, from_file):

    # get the scoreboard for a given date

    base = 'https://sports.yahoo.com/mlb/scoreboard/?confId=&schedState=2&dateRange='

    url = base + '{}-{}-{}'.format(game_date.year, f'{game_date.month:02}', f'{game_date.day:02}')

    tries = 0
    while tries < 5:
        if from_file:
            fh = open("../Pages/2018-03-29.html")
            page = fh.read()
            fh.close()
        else:
            page = get_page(url)

        try:
            stores = get_stores(source=page)
        except Exception:
            log.warning("Bad request...")
            tries += 1
            if tries == 5:
                break
            sleep(1)
            continue

        games = stores['GamesStore']['games']
        scoreboard = stores['ScoreboardStore']['games']     # array of game 'valid' IDs
        return games, scoreboard

    raise Exception('Max retries hit')


def get_box(suffix, game_id, game, game_date, from_file=False):

    tries = 0
    while tries < 5:
        if from_file:
            #filename = "380329130.html"
            filename = "380329128.html"
            log.debug('filename ' + filename)
            fh = open("../Pages/" + filename)
            page = fh.read()
            fh.close()
        else:
            base = 'https://sports.yahoo.com'
            url = base + suffix
            page = get_page(url)

        try:
            stores = get_stores(source=page)
        except Exception:
            log.warning("Bad request...")
            tries += 1
            if tries == 5:
                break
            sleep(1)
            continue

        stats = stores['StatsStore']
        game_data = stores['GamesStore']['games'][game_id]

        cur_game = Game()
        # Thu, 29 Mar 2018 20:10:00 +0000
        cur_game.year = game_date.year
        cur_game.starttime = datetime.strptime(game['start_time'], '%a, %d %b %Y %H:%M:%S %z')
        # convert timestamp to PxT so date is accurate
        cur_game.start = utc_to_local(cur_game.starttime).date()
        cur_game.away_team = session.query(Team).filter(Team.yahoo_id==int(game['away_team_id'].replace('mlb.t.', ''))).one()
        cur_game.home_team = session.query(Team).filter(Team.yahoo_id==int(game['home_team_id'].replace('mlb.t.', ''))).one()
    
        # create any missing players
        check_players(
            players=stores['PlayersStore']['players'],
            away_team=cur_game.away_team,
            home_team=cur_game.home_team,
            lineups=game_data['lineups'],
            game_date=cur_game.start
        )

        return cur_game, game_data, stats

    raise Exception('Max retries hit')


def parse_game_data(cur_game, game_date, game_id, game, status, game_data, from_file=False):


    cur_game.set_status(status, session)
    cur_game.extract_yahoo_id(game_id)      # maybe overkill

    for old_game in session.query(Game).filter(Game.yahoo_id==cur_game.yahoo_id):
        log.info('Found dup game {}, deleting...'.format(old_game.yahoo_id))
        for batter_game in session.query(BatterGame).filter(BatterGame.game==old_game):
            session.delete(batter_game)
        for pitcher_game in session.query(PitcherGame).filter(PitcherGame.game==old_game):
            session.delete(pitcher_game)
        session.delete(old_game)
        session.commit()

    # TODO: fix this
    # capture progress for live games
    # if status == 'live':
    #     cur_game.progress = game.find(name='span').text

    # TODO: fix this?
    #if status != 'Upcoming':
    cur_game.away_runs = game['away_team_stats'][0]['runs']
    cur_game.away_hits = game['away_team_stats'][1]['hits']
    cur_game.away_errors = game['away_team_stats'][2]['errors']

    # TODO: fix this?
    #if status != 'Upcoming':
    cur_game.home_runs = game['home_team_stats'][0]['runs']
    cur_game.home_hits = game['home_team_stats'][1]['hits']
    cur_game.home_errors = game['home_team_stats'][2]['errors']

    log.info("{} {} @ {} {}".format(
        cur_game.away_team.full_name(), cur_game.away_runs,
        cur_game.home_team.full_name(), cur_game.home_runs))

    # inning-level runs

    inning_data = {}

    max_inning = None
    for period in game_data['game_periods']:
        inning = int(period['period_id'])
        inning_data[inning] = [period['away_points'], period['home_points']]
        max_inning = inning

    cur_game.inning_data = inning_data
    cur_game.innings = max_inning

    session.add(cur_game)
    session.commit()    

    return cur_game


def check_players(players, away_team, home_team, lineups, game_date):

    for player, data in players.items():

        if player in lineups["away_lineup"]["all"].keys():
            team = away_team
        elif player in lineups["home_lineup"]["all"].keys():
            team = home_team
        else:
            #log.debug('Player {} not found in lineups'.format(player))
            #raise Exception('Player {} not found in lineups'.format(player))
            continue

        #log.debug('Checking player {}'.format(player))
        yahoo_id = int(player.replace('mlb.p.', ''))
        get_or_create_player(session=session, yahoo_id=yahoo_id, team=team, data=data, game_date=game_date)

    return


def get_page(url):

    log.info(url)
    headers = {
        'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) ' +
            'Chrome/72.0.3626.121 Safari/537.36'
    }

    tries = 0
    max_tries = 5

    while tries < max_tries:

        page = requests.get(url, headers=headers)
        if page.status_code == 200:
            return page.content
        else:
            log.warning('{} trying to get {}'.format(page.status_code, url))

        tries += 1
        sleep(1)

    raise Exception('{} failures trying to get {}'.format(max_tries, url))


def get_stores(source):

    soup = BeautifulSoup(source, 'html.parser')

    scripts = soup.find_all("script")

    for script in scripts:

        if 'root.App.main' in script.text:
            for line in script.text.split('\n'):
                if 'root.App.main' in line:
                    # trim data for json-izing
                    line = line.replace('root.App.main =', '')
                    line = line[:-1]
                    react_js = json.loads(line)
                    return react_js['context']['dispatcher']['stores']

                    # ta daaaaaaaa, our entity IDs
                    # st = fin['context']['dispatcher']['stores']['ScoreboardStore']['games']

    raise Exception("Couldn't find react js in source.")


def parse_pitching_notes(pitching_notes, lineups, game_id):

    pitching_order = parse_lineup(
        lineup=lineups['away_lineup_order']['P'] + lineups['home_lineup_order']['P'],
        ltype='pitching lineups',
        game_id=game_id
    )

    # Pitches-strikes

    pstats = {}

    index = 0
    start_index = -1
    for dct in pitching_notes:
        if dct['header'] == 'Pitches-strikes':
            start_index = index
            break
        index += 1
    if start_index == -1:
        raise Exception('Pitches-strikes not found in pitching_notes')

    pitching_notes[start_index]['text'] = replace_accents(pitching_notes[start_index]['text'])
    raw = pitching_notes[start_index]['text'].split(',')
    pitchers_count = len(raw)

    for item in raw:
        m = re.match('(.*) (\d+)-(\d+).*', item)

        if not m:
            raise Exception('Pitches-strikes regex failed on {}'.format(item))

        pname = m.group(1).lstrip()

        pitcher = get_player_from_order(
            order=pitching_order,
            pname=pname,
            stat_name='Pitches-strikes',
            game_id=game_id
        )

        pstats[pitcher.id] = {
            'pitches': m.group(2),
            'strikes': m.group(3),
            'ground': 0,
            'fly': 0,
            'batters': 0,
        }

    # Ground balls-fly balls

    seen = []
    start_index += 1
    if pitching_notes[start_index]['header'] != 'Ground balls-fly balls':
        raise Exception('Ground balls-fly balls not found')

    raw = pitching_notes[start_index]['text'].split(',')
    if pitchers_count != len(raw):
        log.warning('Expecting {} pitchers in Ground balls-fly balls, found {}'.format(pitchers_count, len(raw)))

    for item in raw:
        m = re.match('(.*) (\d+)-(\d+).*', item)

        if not m:
            raise Exception('Ground balls-fly balls regex failed on {}'.format(item))

        pname = m.group(1).lstrip()

        pitcher = get_player_from_order(
            order=pitching_order,
            pname=pname,
            stat_name='Pitches-strikes',
            game_id=game_id
        )

        pstats[pitcher.id]['ground'] = m.group(2)
        pstats[pitcher.id]['fly'] = m.group(3)

    # Batters faced

    start_index += 1
    if pitching_notes[start_index]['header'] != 'Batters faced':
        raise Exception('Batters faced not found')

    raw = pitching_notes[start_index]['text'].split(',')
    # if pitchers_count != len(raw):
    #     log.warning('Expecting {} pitchers in Batters faced, found {}'.format(pitchers_count, len(raw)))

    for item in raw:

        # it appears yahoo puts no number if the batters faced is just 1

        batters = 1
        m = re.match('(.*) (\d+)', item)
        if m:
            batters = m.group(2)
            pname = m.group(1).lstrip()
        # else:
        #     pname = item.lstrip()
        #     log.warning('Batters faced regex failed on {}'.format(item))

        pitcher = get_player_from_order(
            order=pitching_order,
            pname=pname,
            stat_name='batters',
            game_id=game_id
        )

        pstats[pitcher.id]['batters'] = batters

    return pstats


def get_player_from_order(order, pname, stat_name, game_id):

        pname = replace_accents(pname)

        # clean up yahoo's mess
        if game_id in ['mlb.g.380405123', 'mlb.g.380330106', 'mlb.g.380401306', 'mlb.g.380401206'] \
                and pname == 'F Rivero':
            pname = 'F Vazquez'

        # 8/23/18 O P??rez
        elif game_id == 'mlb.g.380823102' and pname.startswith('O P') and pname.endswith('ez'):
            pname = 'O Perez'

        # 8/23/18 J Garc??a
        elif game_id == 'mlb.g.380823128' and pname.startswith('J Garc') and pname.endswith('a'):
            pname = 'J Garcia'

        pnames = [pname]
        if pname == 'M Wright Jr':
            pnames.append('M Wright')
        elif pname == 'V Nuno':
            pnames.append('V Nuno III')
        elif pname == 'D Poncedeleon':
            pnames.append('D Ponce de Leon')

        for pname in pnames:
            try:
                return order[pname]
            except KeyError:
                pass

        raise Exception('{} could not find {} in {}'.format(stat_name, pnames, order.keys()))


def parse_batting_notes(away_batting, home_batting, pitching_notes, lineups, game_id):

    away_batting_order = parse_lineup(lineup=lineups['away_lineup_order']['B'], ltype='away batter', game_id=game_id)
    home_batting_order = parse_lineup(lineup=lineups['home_lineup_order']['B'], ltype='home batter', game_id=game_id)
    bstats = {}

    for i in range(0, 2):

        if i == 0:
            batting_order = away_batting_order
            ltype = 'away'
            source = away_batting
        else:
            batting_order = home_batting_order
            ltype = 'home'
            source = home_batting

        # 2B, 3B, GIDP
        stypes = ['2B', '3B', 'GIDP', 'SF']

        for j in range(0, 4):

            stype = stypes[j]

            index = 0
            start_index = -1
            for dct in source:
                if dct['header'] == stype:
                    start_index = index
                    break
                index += 1
            if start_index == -1:
                #log.info('No {} for {} team'.format(stype, ltype))
                continue

            #log.debug('found {} at {} - {}'.format(stype, start_index, source[start_index]['text']))

            source[start_index]['text'] = replace_accents(source[start_index]['text'])
            if stype in ['GIDP', 'SF']:
                raw = source[start_index]['text'].split(',')
            else:
                raw = source[start_index]['text'].split('),')

            #log.debug(raw)
            for item in raw:

                increment = 1

                # "header": "2B",
                # "text": "K Bryant (1), W Contreras (1), J Heyward (1), T La Stella (1)"
                if stype in ['2B', '3B']:

                    # there's a following digit if > 1, e.g. X Bogaerts 2 (2)
                    m = re.match('(.*) (\d+) \(\d+.*', item)

                    if m:
                        bname = m.group(1).lstrip()
                        increment = int(m.group(2))
                    else:
                        m = re.match('(.*) \(\d+.*', item)

                        if m:
                            bname = m.group(1).lstrip()

                        else:
                            raise Exception('{} regex failed on {} [{}]'.format(stype, item, raw))

                # "header": "GIDP",
                # "text": "J Bour, M Rojas"
                else:
                    m = re.match('(.*) (\d+)', item)

                    # there's a following digit if > 1, e.g. X Bogaerts 2
                    if m:
                        bname = m.group(1).lstrip()
                        increment = int(m.group(2))
                    else:
                        bname = item.lstrip()

                # 8/23/18 Y D??az, E N????ez
                if game_id == 'mlb.g.380823102':
                    if bname.startswith('Y D') and bname.endswith('az'):
                        bname = 'Y Diaz'
                    elif bname.startswith('E N') and bname.endswith('ez'):
                        bname = 'E Nunez'

                # 8/23/18 E Su??rez, J B??ez
                elif game_id == 'mlb.g.380823116':
                    if bname.startswith('E Su') and bname.endswith('ez'):
                        bname = 'E Suarez'
                    elif bname.startswith('J B') and bname.endswith('ez'):
                        bname = 'J Baez'

                # 8/23/18 A Garc??a
                elif game_id == 'mlb.g.380823106':
                    if bname.startswith('A Garc') and bname.endswith('a'):
                        bname = 'A Garcia'

                elif game_id == 'mlb.g.380912124' and bname == 'D Poncedeleon':
                    bname = 'D Ponce de Leon'

                if bname not in batting_order.keys():
                    raise Exception('Could not find {} {} in batting_order {}'.
                                    format(stype, bname, batting_order.keys()))

                batter = batting_order[bname]

                #log.debug('{} {}'.format(stype, batter.name))
                if batter.id not in bstats.keys():
                    bstats[batter.id] = {
                        '2B': 0,
                        '3B': 0,
                        'SF': 0,
                        'HBP': 0,
                        'GIDP': 0,
                    }

                bstats[batter.id][stype] += increment

    # HBP

    away_pitching_order = parse_lineup(lineup=lineups['away_lineup_order']['P'], ltype='away pitcher', game_id=game_id)
    home_pitching_order = parse_lineup(lineup=lineups['home_lineup_order']['P'], ltype='home pitcher', game_id=game_id)

    index = 0
    start_index = -1
    for dct in pitching_notes:
        if dct['header'] == 'HBP':
            start_index = index
            break
        index += 1

    if start_index > -1:
        pitching_notes[start_index]['text'] = replace_accents(pitching_notes[start_index]['text'])
        raw = pitching_notes[start_index]['text'].split(',')

        #log.debug(raw)
        for item in raw:

            # {
            #     "header": "HBP",
            #     "text": "D Dietrich (by M Montgomery), J B\u00e1ez (by J Ure\u00f1a), A Rizzo (by J Ure\u00f1a), A Russell (by J Ure\u00f1a)"
            # },

            increment = 1

            m = re.match('(.*) (\d+) \(by (.*)\)', item)

            if m:
                bname = m.group(1).lstrip()
                increment = int(m.group(2).lstrip())
                pname = m.group(3).lstrip()

            else:
                m = re.match('(.*) \(by (.*)\)', item)

                if m:
                    bname = m.group(1).lstrip()
                    pname = m.group(2).lstrip()
                else:
                    raise Exception('{} regex failed on {}'.format('HBP', item))

            # 8/23/18 R Acu??a Jr
            if game_id == 'mlb.g.380823128':
                if bname[:5] == 'R Acu' and bname[-2:] == 'Jr':
                    bname = 'R Acuna Jr'
            elif game_id in['mlb.g.380403118', 'mlb.g.380419106', 'mlb.g.380527130', 'mlb.g.380624115', 'mlb.g.380803113', \
                    'mlb.g.380902107', 'mlb.g.380915101']:
                if pname == 'M Wright Jr':
                    pname = 'M Wright'
            elif game_id in['mlb.g.380821119']:
                if pname == 'D Poncedeleon':
                    pname = 'D Ponce de Leon'
            elif game_id in['mlb.g.380905114', 'mlb.g.380926130']:
                if pname == 'V Nuno':
                    pname = 'V Nuno III'

            if bname in away_batting_order.keys() and pname in home_pitching_order.keys():
                batter = away_batting_order[bname]
            elif bname in home_batting_order.keys() and pname in away_pitching_order.keys():
                batter = home_batting_order[bname]
            else:
                log.info('AB {}'.format(away_batting_order.keys()))
                log.info('HP {}'.format(home_pitching_order.keys()))
                log.info('HB {}'.format(home_batting_order.keys()))
                log.info('AP {}'.format(away_pitching_order.keys()))

                raise Exception('Could not find {} in batting orders and {} in pitching orders'.format(bname, pname))

            if batter.id not in bstats.keys():
                bstats[batter.id] = {
                    '2B': 0,
                    '3B': 0,
                    'SF': 0,
                    'HBP': 0,
                    'GIDP': 0,
                }

            bstats[batter.id]['HBP'] += increment
    else:
        #log.info('No {} found'.format('HBP'))
        pass

    return bstats


def parse_lineup(lineup, ltype, game_id):
    player_order = {}
    for plyr in lineup:
        yahoo_id = int(plyr.replace('mlb.p.', ''))
        player = session.query(Player).filter(Player.yahoo_id==yahoo_id).one()
        pname = player.pname

        if pname in player_order.keys():

            # yahoo slop
            if pname == 'C Joseph' \
                    and game_id in ['mlb.g.380619120', 'mlb.g.380911101', 'mlb.g.380914101', 'mlb.g.380918101',
                                    'mlb.g.380924102', 'mlb.g.380926202']:
                continue
            elif pname == 'D Smith' \
                    and game_id in ['mlb.g.380623121', 'mlb.g.380624121', 'mlb.g.380629128', 'mlb.g.380819122',
                                    'mlb.g.380822121', 'mlb.g.380907121', 'mlb.g.380909121', 'mlb.g.380913221',
                                    'mlb.g.380917122', 'mlb.g.380918122', 'mlb.g.380923120', 'mlb.g.380925121',
                                    'mlb.g.380927121', 'mlb.g.380929121']:
                continue
            elif pname == 'T Williams' and game_id in ['mlb.g.380922123']:
                continue
            # doubled up in the lineup
            elif pname == 'W Difo' and game_id in ['mlb.g.380701122']:
                continue
            elif pname == 'M Reynolds' and game_id in ['mlb.g.380727128', 'mlb.g.380728128']:
                continue
            # 8/21/18 doubled up in the lineup
            elif pname == 'K Herrera' and game_id in ['mlb.g.380821120']:
                continue
            # 9/8/18 doubled up in the lineup
            elif pname == 'G Holland' and game_id in ['mlb.g.380908320']:
                continue
            # 9/13/18 doubled up in the lineup
            elif pname == 'Y Lopez' and game_id in ['mlb.g.380913127']:
                continue

            elif pname == 'A Sanchez' \
                    and game_id in ['mlb.g.390505122', 'mlb.g.390510119', 'mlb.g.390516120']:
                continue

            log.debug('LINEUP {}'.format(lineup))
            log.debug('PLAYER ORDER {}'.format(player_order.keys()))
            raise Exception("Duplicate {} {}".format(ltype, pname))

        player_order[pname] = player
        if player.alt_name():
            player_order[player.alt_name()] = player

    return player_order


def parse_players(game, stats, lineups, pstats, bstats, game_id, cur_game):

    # "playerStats": {
    #     "mlb.p.7790": {
    #         "mlb.stat_variation.2": {
    #             "mlb.stat_type.4": "0",

    # AB R H RBI HR SB BB K LOB AVG
    for y_player, data in stats.items():

        if 'mlb.stat_variation.2' not in data.keys():
            #log.debug('Player {} in stats, but does not appear to have played.'.format(player))
            continue

        # 4/2/18 Sisco data is there, but didn't play
        elif game_id == 'mlb.g.380402118' and y_player == 'mlb.p.10155':
            continue
            #lineups['home_lineup']['all'][y_player] = 1

        # 4/17/18 Tepera is missing
        elif game_id == 'mlb.g.380417314' and y_player == 'mlb.p.9959':
            lineups['away_lineup']['P'][y_player] = {'order': '3'}
            lineups['home_lineup']['all'][y_player] = 1
            pstats[541] = {'pitches': 26, 'strikes': 19, 'ground': 2, 'fly': 0, 'batters': 5}

        # 6/18/18 ghost players
        elif game_id == 'mlb.g.380618120' \
                and y_player in ['mlb.p.9100', 'mlb.p.8179', 'mlb.p.10293', 'mlb.p.8641', 'mlb.p.9642', 'mlb.p.9642',
                               'mlb.p.9224', 'mlb.p.8289', 'mlb.p.9603', 'mlb.p.9768', 'mlb.p.7746', 'mlb.p.10624',
                               'mlb.p.7071', 'mlb.p.9097', 'mlb.p.9251']:
            continue

        # 6/19/18 C Joseph
        elif game_id == 'mlb.g.380619120':
            bstats[154] = {'2B': 1, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            bstats[1137] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 6/19/18 D Smith
        elif game_id == 'mlb.g.380623121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 22, 'strikes': 9, 'ground': 2, 'fly': 0, 'batters': 5}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 6/24/18 D Smith
        elif game_id == 'mlb.g.380624121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 21, 'strikes': 13, 'ground': 2, 'fly': 0, 'batters': 5}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 6/29/18 D Smith
        elif game_id == 'mlb.g.380629128':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 12, 'strikes': 5, 'ground': 2, 'fly': 1, 'batters': 4}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 7/1/18 Sean Doolittle pitched but didn't hit
        # elif game_id == 'mlb.g.380701122' and y_player == 'mlb.p.8641':
        #     lineups['home_lineup']['all'][y_player] = 1

        # 7/27/18 M Reynolds
        elif game_id == 'mlb.g.380727128':
            # Mark 8030
            bstats[1021] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Matt 9913
            bstats[783] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 7/28/18 M Reynolds
        elif game_id == 'mlb.g.380728128':
            # Mark 8030
            bstats[1021] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Matt 9913
            bstats[783] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 8/19/18 D Smith
        elif game_id == 'mlb.g.380819122':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 8, 'strikes': 6, 'ground': 2, 'fly': 0, 'batters': 3}
            # Dominic
            bstats[1005] = {'2B': 1, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 8/22/18 D Smith
        elif game_id == 'mlb.g.380822121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 11, 'strikes': 6, 'ground': 0, 'fly': 1, 'batters': 4}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/7/18 D Smith
        elif game_id == 'mlb.g.380907121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 22, 'strikes': 14, 'ground': 2, 'fly': 2, 'batters': 5}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/8/18 ghost players - weird because M Reynolds has stats for 9/8 (dbl-header)
        elif game_id == 'mlb.g.380908320' and y_player in ['mlb.p.8030']:
            continue

        # 9/9/18 D Smith
        elif game_id == 'mlb.g.380909121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 21, 'strikes': 15, 'ground': 2, 'fly': 4, 'batters': 7}
            # Dominic
            bstats[1005] = {'2B': 1, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/11/18 C Joseph
        elif game_id == 'mlb.g.380619120':
            # Caleb
            bstats[154] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Corban
            bstats[1137] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/13/18 D Smith
        elif game_id == 'mlb.g.380913221':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 16, 'strikes': 9, 'ground': 2, 'fly': 0, 'batters': 5}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/14/18 C Joseph
        elif game_id == 'mlb.g.380914101':
            # Caleb
            bstats[154] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Corban
            bstats[1137] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/17/18 D Smith
        elif game_id == 'mlb.g.380917122':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 8, 'strikes': 4, 'ground': 1, 'fly': 1, 'batters': 2}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/18/18 D Smith
        elif game_id == 'mlb.g.380918122':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 16, 'strikes': 12, 'ground': 3, 'fly': 1, 'batters': 5}
            # Dominic
            bstats[1005] = {'2B': 1, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/18/18 C Joseph
        elif game_id == 'mlb.g.380918101':
            # Caleb
            bstats[154] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Corban
            bstats[1137] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/22/18 T Williams
        elif game_id == 'mlb.g.380922123':
            # Taylor
            bstats[801] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[801] = {'pitches': 15, 'strikes': 10, 'ground': 2, 'fly': 0, 'batters': 3}
            # Trevor
            bstats[699] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[699] = {'pitches': 95, 'strikes': 65, 'ground': 6, 'fly': 4, 'batters': 22}

        # 9/23/18 D Smith
        elif game_id == 'mlb.g.380923120':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 25, 'strikes': 20, 'ground': 3, 'fly': 1, 'batters': 8}
            # Dominic
            bstats[1005] = {'2B': 1, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/24/18 C Joseph
        elif game_id == 'mlb.g.380924102':
            # Caleb
            bstats[154] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Corban
            bstats[1137] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/25/18 D Smith
        elif game_id == 'mlb.g.380925121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 13, 'strikes': 7, 'ground': 0, 'fly': 0, 'batters': 3}
            # Dominic
            bstats[1005] = {'2B': 1, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/26/18 C Joseph
        elif game_id == 'mlb.g.380926202':
            # Caleb
            bstats[154] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            # Corban
            bstats[1137] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/27/18 D Smith
        elif game_id == 'mlb.g.380927121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 6, 'strikes': 5, 'ground': 1, 'fly': 1, 'batters': 3}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 9/29/18 D Smith
        elif game_id == 'mlb.g.380929121':
            # Drew
            bstats[1153] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[1153] = {'pitches': 11, 'strikes': 7, 'ground': 0, 'fly': 2, 'batters': 3}
            # Dominic
            bstats[1005] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 5/5/19 A Sanchez
        elif game_id == 'mlb.g.390505122':
            # Anibal
            bstats[761] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[761] = {'pitches': 108, 'strikes': 70, 'ground': 2, 'fly': 4, 'batters': 22}
            # Adrian
            bstats[1189] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 5/10/19 Y Ramirez did not play
        elif game_id == 'mlb.g.390510101' and y_player == 'mlb.p.10991':
            continue

        # 5/10/19 A Sanchez
        elif game_id == 'mlb.g.390510119':
            # Anibal
            bstats[761] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[761] = {'pitches': 89, 'strikes': 57, 'ground': 6, 'fly': 3, 'batters': 21}
            # Adrian
            bstats[1189] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}

        # 5/10/19 A Sanchez
        elif game_id == 'mlb.g.390516120':
            # Anibal
            bstats[761] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}
            pstats[761] = {'pitches': 31, 'strikes': 19, 'ground': 1, 'fly': 1, 'batters': 6}
            # Adrian
            bstats[1189] = {'2B': 0, '3B': 0, 'HBP': 0, 'GIDP': 0, 'SF': 0}



        if y_player in lineups['away_lineup']['all'].keys():
            side = 'away'
            team = cur_game.away_team
        elif y_player in lineups['home_lineup']['all'].keys():
            side = 'home'
            team = cur_game.home_team
        else:
            log.error(lineups['away_lineup']['all'].keys())
            log.error(lineups['home_lineup']['all'].keys())
            log.error(stats.keys())
            log.error(data)
            raise Exception('Player ID not found in lineups {}'.format(y_player))

        yahoo_id = int(y_player.replace('mlb.p.', ''))
        player = session.query(Player).filter(Player.yahoo_id==yahoo_id).one()

        # TODO: clean up, enum or dict?
        batting = {
            'AB': 'mlb.stat_type.2',
            'R': 'mlb.stat_type.3',
            'H': 'mlb.stat_type.4',
            'HR': 'mlb.stat_type.7',
            'RBI': 'mlb.stat_type.8',
            'SB': 'mlb.stat_type.12',
            'BB': 'mlb.stat_type.14',
            'K': 'mlb.stat_type.17',
            'AVG': 'mlb.stat_type.23',
            'LOB': 'mlb.stat_type.53'
        }

        pitching = {
            'W': 'mlb.stat_type.101',
            'L': 'mlb.stat_type.102',
            'SV': 'mlb.stat_type.107',
            'H': 'mlb.stat_type.111',
            'R': 'mlb.stat_type.113',
            'ER': 'mlb.stat_type.114',
            'HR': 'mlb.stat_type.115',
            'BB': 'mlb.stat_type.118',
            'K': 'mlb.stat_type.121',
            'HLD': 'mlb.stat_type.136',
            'IP': 'mlb.stat_type.139',
            'ERA': 'mlb.stat_type.140',
            'WHIP': 'mlb.stat_type.141',
            'BS': 'mlb.stat_type.147',
        }

        # TODO: batting order, sub/PH

        data = data['mlb.stat_variation.2']

        # if batting['AB'] in data.keys():
        if y_player in lineups['{}_lineup'.format(side)]['B'].keys():

            if player.id in bstats.keys():
                doubles = bstats[player.id]['2B']
                triples = bstats[player.id]['3B']
                hbp = bstats[player.id]['HBP']
                sac_fly = bstats[player.id]['SF']
                gidp = bstats[player.id]['GIDP']
            else:
                doubles = 0
                triples = 0
                hbp = 0
                sac_fly = 0
                gidp = 0

            pitcher, catcher, first, second, third, shortstop, outfield, left, center, right, dh, pinch, runner = \
                (False, False, False, False, False, False, False, False, False, False, False, False, False)

            positions = lineups['{}_lineup'.format(side)]['B'][y_player]['position'].split('-')

            for position in positions:
                if position == 'P':
                    pitcher = True
                elif position == 'C':
                    catcher = True
                elif position == '1B':
                    first = True
                elif position == '2B':
                    second = True
                elif position == 'SS':
                    shortstop = True
                elif position == '3B':
                    third = True
                elif position == 'LF':
                    outfield = True
                    left = True
                elif position == 'CF':
                    outfield = True
                    center = True
                elif position == 'RF':
                    outfield = True
                    right = True
                elif position == 'DH':
                    dh = True
                elif position == 'PH':
                    pinch = True
                elif position == 'PR':
                    runner = True
                else:
                    raise Exception('Position not recognized: {} from {}'.format(position, positions))            

            batter_game = BatterGame(
                player=player,
                game=game,
                team=team,
                at_bats=int(data[batting['AB']]),
                runs=int(data[batting['R']]),
                hits=int(data[batting['H']]),
                runs_batted_in=int(data[batting['RBI']]),
                home_runs=int(data[batting['HR']]),
                stolen_bases=int(data[batting['SB']]),
                walks=int(data[batting['BB']]),
                strikeouts=int(data[batting['K']]),
                left_on_base=int(data[batting['LOB']]),
                doubles=doubles,
                triples=triples,
                hbp=hbp,
                sac_fly=sac_fly,
                gidp=gidp,
                pitcher=pitcher,
                catcher=catcher,
                first=first,
                second=second,
                third=third,
                shortstop=shortstop,
                outfield=outfield,
                left=left,
                center=center,
                right=right,
                dh=dh,
                pinch=pinch,
                runner=runner
            )
            session.add(batter_game)
            session.commit()

        if pitching['ER'] in data.keys():

            # TODO need to parse the bs object 'g.pitching'

            innings = Decimal(data[pitching['IP']])

            pname = player.p_name()

            # if pname not in pstats.keys() and pname in replace.keys():
            #     pname = replace[pname]

            if player.id in pstats.keys():
                #log.debug('{} {} {}'.format(pname, player.id, pstats[player.id]))
                pitches = pstats[player.id]['pitches']
                strikes = pstats[player.id]['strikes']
                ground_balls = pstats[player.id]['ground']
                fly_balls = pstats[player.id]['fly']
                batters = pstats[player.id]['batters']
            elif game_id == 'mlb.g.380417314' and pname in ['R Tepera']:
                continue
            elif game_id == 'mlb.g.380504124' and pname == "D Leone"\
                    or game_id == 'mlb.g.380623126' and pname == "J Lyles":
                pitches = 0
                strikes = 0
                ground_balls = 0
                fly_balls = 0
                batters = 0

            # sure, yahoo, just toss all these randos in...
            elif game_id == 'mlb.g.380618120' and \
                    pname in['G Gonzalez', 'C Green', 'S Doolittle', 'M Tanaka', 'A Warren', 'C Shreve', 'R Madson']:
                continue

            # weird ?? chars in notes pitcher name
            elif game_id == 'mlb.g.380823102' and pname == 'O Pérez':
                pitches = 5
                strikes = 4
                ground_balls = 0
                fly_balls = 1
                batters = 2
            # weird ?? chars in notes pitcher name
            elif game_id == 'mlb.g.380823128' and pname == 'J García':
                pitches = 39
                strikes = 19
                ground_balls = 2
                fly_balls = 1
                batters = 9
            elif game_id == 'mlb.g.380926120' and pname in ['K Glover']:
                continue
            elif game_id == 'mlb.g.380922123' and pname == 'T Williams':
                pitches = 15
                strikes = 10
                ground_balls = 2
                fly_balls = 0
                batters = 3
            else:
                log.debug(pstats.keys())
                #log.debug(pstats)
                #log.debug(data)
                raise Exception('Couldn''t find pitcher {} {} in pstats'.format(player.id, pname))

            spot = int(lineups['{}_lineup'.format(side)]['P'][y_player]['order'])
            if spot == 1:
                start = True
                relief = False
            else:
                start = False
                relief = True

            pitcher_game = PitcherGame(
                player=player,
                game=game,
                team=team,
                spot=spot,
                innings=innings,
                whole_innings=innings - (innings % 1),
                partial_innings = (innings % 1) * 10,
                outs=(innings % 1) * 10,
                hits=int(data[pitching['H']]),
                runs=int(data[pitching['R']]),
                earned_runs=int(data[pitching['ER']]),
                walks=int(data[pitching['BB']]),
                strikeouts=int(data[pitching['K']]),
                home_runs=int(data[pitching['HR']]),
                pitches=pitches,
                strikes=strikes,
                ground_balls=ground_balls,
                fly_balls=fly_balls,
                batters=batters,
                win=int(data[pitching['W']]),
                loss=int(data[pitching['L']]),
                hold=int(data[pitching['HLD']]),
                sv=int(data[pitching['SV']]),
                blown=int(data[pitching['BS']]),
                start=start,
                relief=relief
            )
            session.add(pitcher_game)
            session.commit()
        # else:
        #     log.debug('Player {} {} is not a pitcher'.format(player.yahoo_id, player.name))


def parse_pitchers(data, team, game, pitches_strikes, ground_fly, batters_faced):

    tbody = data.find('tbody')

    # IP H R ER BB K HR WHIP ERA
    spot = 1
    for tr in tbody.find_all('tr'):
        pitcher = tr.find('th')
        link = pitcher.find('a')
        name = link.text
        player = Player.objects.get_or_create(link=link['href'], name=name, team=team)

        stats = tr.find_all('td')
        innings = Decimal(stats[0].text)

        # TODO: pitching order, IBB, HBP
        # TODO: handle same last name for 2 or more pitchers in a game
        p_name = player.p_name

        subs = {
            'Felipe Vázquez': 'F Rivero',
            'Eduardo Rodriguez': 'E Rodríguez',
            'Yefrey Ramirez': 'Y Ramírez',
            'Yefry Ramírez': 'Y Ramirez',
            'Austin L. Adams': 'A Adams',
            'José Fernández': 'J Fernandez'
        }
        #'Oliver Pérez': 'O P??rez'

        found = False
        subbed = False
        while not found:
            m = re.match('.*{} (\d+)-(\d+).*'.format(p_name), pitches_strikes)
            if m:
                pitches = m.group(1)
                strikes = m.group(2)
                found = True
            else:
                if innings == Decimal(0):
                    pitches = 0
                    strikes = 0
                    found = True
                elif player.name in subs and not subbed:
                    log.warning('Swapping {} for {} based on {}'.format(subs[player.name], p_name, player.name))
                    p_name = subs[player.name]
                    subbed = True
                # TODO: haven't solved this one yet...  O P??rez
                elif player.name == 'Oliver Pérez' and game.start == date(2018, 8, 23):
                    pitches = 5
                    strikes = 4
                    found = True
                elif player.name == 'Jarlin García' and game.start == date(2018, 8, 23):
                    pitches = 39
                    strikes = 19
                    found = True
                else:
                    raise ValueError("Couldn't pitches-strikes for : [{} {}]\n{}".format(p_name, player.name, pitches_strikes))

        m = re.match('.*{} (\d+)-(\d+).*'.format(p_name), ground_fly)
        if m:
            ground_balls = m.group(1)
            fly_balls = m.group(2)
        else:
            if innings == Decimal(0):
                ground_balls = 0
                fly_balls = 0
            # see above
            elif player.name == 'Oliver Pérez' and game.start == date(2018, 8, 23):
                ground_balls = 0
                fly_balls = 1
            elif player.name == 'Jarlin García' and game.start == date(2018, 8, 23):
                ground_balls = 2
                fly_balls = 1
            else:
                raise ValueError("Couldn't ground-fly for : {}\n{}".format(p_name, ground_fly))

        # TODO: how can you have 0.2 IP and 0 batters faced?  pickoff?
        m = re.match('.*{} (\d+).*'.format(p_name), batters_faced)
        if m:
            batters = m.group(1)
        else:
            # TODO: < 1
            if innings in[Decimal(0), Decimal('0.1'), Decimal('0.2')]:
                batters = 0
            # see above
            elif player.name == 'Oliver Pérez' and game.start == date(2018, 8, 23):
                batters = 2
            elif player.name == 'Jarlin García' and game.start == date(2018, 8, 23):
                batters = 9
            else:
                raise ValueError("Couldn't batters for : {} (ip {})\n{}".format(player.p_name, innings, batters_faced))

        spans = pitcher.find_all('span')
        if len(spans) == 3:
            result = spans[1].text
            win = 'W' in result
            loss = 'L' in result
            hold = 'H' in result
            sv = 'SV' in result
            blown = 'BS' in result
        else:
            win = False
            loss = False
            hold = False
            sv = False
            blown = False

        PitcherGame.objects.create(
                player=player,
                game=game,
                team=team,
                spot=spot,
                innings=innings,
                whole_innings=innings - (innings % 1),
                outs=(innings % 1) * 10,
                hits=int(stats[1].text),
                runs=int(stats[2].text),
                earned_runs=int(stats[3].text),
                walks=int(stats[4].text),
                strikeouts=int(stats[5].text),
                home_runs=int(stats[6].text),
                pitches=pitches,
                strikes=strikes,
                ground_balls=ground_balls,
                fly_balls=fly_balls,
                batters=batters,
                win=win,
                loss=loss,
                hold=hold,
                sv=sv,
                blown=blown
            )
        spot += 1


def get_max():
    connection = psycopg2.connect(
        host='localhost',
        dbname='fant_b',
        user='robmo',
        password=''
    )
    cursor = connection.cursor()

    sql = 'SELECT start, cnt ' \
        'FROM (SELECT start, COUNT(*) AS cnt ' \
            'FROM game ' \
            'GROUP BY 1 ' \
            'ORDER BY 1 desc ' \
            'LIMIT 5) sq1 '\
        'ORDER BY 1;'

    cursor.execute(sql)

    for tpl in cursor.fetchall():
        print(tpl[0], tpl[1])

    cursor.close()
    connection.close()


##------...........-------##------...........-------##------...........-------##------...........-------##------...........-------##
##------...........-------##------...........-------##------...........-------##------...........-------##------...........-------##
##------...........-------##------...........-------##------...........-------##------...........-------##------...........-------##

engine = create_engine('postgresql://robmo:@localhost:5432/fant_b')
Session = sessionmaker(bind=engine)
session = Session()

# 2018 started 3/29, ended 10/1
# 2019 japanese games 3/20, 3/21 SEA/OAK , starts 3/28 (earliest ever!)

if len(sys.argv) > 1:
    # get max game date
    if sys.argv[1] == 'max':
        get_max()
        exit()

    # process 1 day
    else:        
        cur_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        if len(sys.argv) > 2:
            today = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
        else:
            today = cur_date

else:
    cur_date = date(2018, 8, 23)
    today = date(2018, 10, 1)
    #today = cur_date

all_star = [date(2018, 7, 17)]

while cur_date <= today:

    # skip all star game
    if cur_date not in all_star:
        seek(game_date=cur_date, from_file=False)
    else:
        log.info('Skipping All Star Game: {}'.format(cur_date))
    cur_date += relativedelta(days=1)

session.commit()
session.close()
