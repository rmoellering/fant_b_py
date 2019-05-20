import connexion
from decimal import Decimal
from flask import Flask, jsonify
import psycopg2
import requests
import sys
from time import sleep

from pinger import Pinger
from utils import get_logger, RepeatedTimer
from flask_cors import CORS

log = get_logger(__name__)

env = 'develop'
app = connexion.App(__name__, specification_dir='./openapi')

def get_conn():
	return psycopg2.connect(
		host='localhost',
		dbname='fant_b',
		user='robmo',
		password=''
	)

def search(body):
	conn = get_conn()
	cur = conn.cursor()
    
	name = body['name'].lower()

	sql = "SELECT yahoo_id, name FROM data_player WHERE LOWER(name) LIKE '%{}%';".format(name)
	print(sql)
	cur.execute(sql)

	resp = []
	for tpl in cur.fetchall():
		dct = {
			"id": tpl[0],
			"name": tpl[1]
		}
		resp.append(dct)

	cur.close()
	conn.close()
	return jsonify(cur.fetchall())

def execute_sql(sql):
	conn = get_conn()
	cur = conn.cursor()
    
	cur.execute(sql)

	return cur, conn

#@app.route('/api/get_teams')

def get_teams_list():
	cursor, connection = execute_sql(
		"SELECT id, name, owner " \
		"FROM ff_teams " \
		"ORDER BY id;"
	)

	response = psychopg_to_list(fields=['id', 'name', 'owner'], cursor=cursor)
	cursor.close()
	connection.close()
	return response

def get_teams():
	cursor, connection = execute_sql(		
		"SELECT id, abbr, city, name " \
		"FROM team " \
		"ORDER BY abbr;"
	)

	response = psychopg_to_json(fields=['id', 'abbr', 'city', 'name'], cursor=cursor)
	cursor.close()
	connection.close()
	return response

def search_players(stub):

	if len(stub) < 3:
		log.debug('Too short')
		return jsonify([{}])

	stub = stub.lower()

	cursor, connection = execute_sql(		
		"SELECT id AS value, name AS label " \
		"FROM player " \
		"WHERE lname like '%{}%' " \
		"ORDER BY name;".format(stub)
	)

	response = psychopg_to_json(fields=['value', 'label'], cursor=cursor)
	cursor.close()
	connection.close()
	return response

##################
# player graphs
##################

def small_date(date):
	date = str(date)
	parts = date.split('-')
	return parts[1].lstrip('0') + '/' + parts[2].lstrip('0')


def get_batting_agg(player_id, type, year=2019):
	if type == 'r':
		field = 'runs'
	elif type == 'hr':
		field = 'home_runs'
	elif type == 'rbi':
		field = 'runs_batted_in'
	else:
		raise Exception('Invalid data type: {}'.format(type))

	sql = \
		"SELECT g.start, sum(at_bats) as at_bats, sum(bg.{}) as {} " \
		"FROM batter_game bg " \
		  "JOIN game g ON g.id = bg.game_id " \
		"WHERE g.year = {} " \
		"GROUP BY 1 " \
		"ORDER BY 1;".format(field, field, year)

	cursor, connection = execute_sql(sql)

	result = {}
	ab = Decimal(0)
	r = Decimal(0)

	for tpl in cursor.fetchall():
		date = small_date(tpl[0])
		ab += Decimal(tpl[1])
		r += Decimal(tpl[2])

		result[date] = {}
		result[date]['league'] = round(r / ab, 3);
		result[date]['player'] = -1

	sql = \
		"SELECT g.start, sum(at_bats) as at_bats, sum(bg.{}) as {} " \
		"FROM batter_game bg " \
		  "JOIN game g ON g.id = bg.game_id " \
		"WHERE g.year = {} " \
		  "AND bg.player_id = {} " \
		"GROUP BY 1 " \
		"ORDER BY 1;".format(field, field, year, player_id)

	cursor.execute(sql)

	ab = Decimal(0)
	r = Decimal(0)

	for tpl in cursor.fetchall():
		date = small_date(tpl[0])
		ab += Decimal(tpl[1])
		r += Decimal(tpl[2])
		if ab > 0:
			result[date]['player'] = round(r / ab, 3);
		else:
			result[date]['player'] =  0

	# fill in any missing dates and flatten into list
	prev = 0
	response = []
	for date in result.keys():
		if result[date]['player'] == -1:
			result[date]['player'] = prev
		prev = result[date]['player']
		response.append({
			'date': date,
			'league': result[date]['league'],
			'player': result[date]['player']
		})

	cursor.close()
	connection.close()
	return jsonify(response)


def get_batting_pct(player_id, type, year=2019):

	# OBP = (Hits + Walks + Hit by Pitch) / (At Bats + Walks + Hit by Pitch + Sacrifice Flies)
	if type == 'obp':
		a = "SUM(hits + walks + hbp)"
		b = "SUM(at_bats + walks + hbp + sac_fly)"
	# SLG = Total Bases / At Bats
	elif type == 'slg':
		a = "SUM(bg.home_runs) * 4 + SUM(triples) * 3 + SUM(doubles) * 2 + (SUM(hits) - (SUM(bg.home_runs) + SUM(triples) + SUM(doubles)))"
		b = "SUM(at_bats)"
	else:
		raise Exception('Invalid data type: {}'.format(type))

	# league

	sql = \
		"SELECT g.start, {} as num, {} as denom " \
		"FROM batter_game bg " \
		  "JOIN game g ON g.id = bg.game_id " \
		"WHERE g.year = {} " \
		"GROUP BY 1 " \
		"ORDER BY 1;".format(a, b, year)

	cursor, connection = execute_sql(sql)

	result = {}
	num = Decimal(0)
	denom = Decimal(0)

	for tpl in cursor.fetchall():
		date = small_date(tpl[0])
		num += Decimal(tpl[1])
		denom += Decimal(tpl[2])

		result[date] = {}
		result[date]['league'] = round(num / denom, 3);
		result[date]['player'] = -1

	# player

	sql = \
		"SELECT g.start, {} as num, {} as denom " \
		"FROM batter_game bg " \
		  "JOIN game g ON g.id = bg.game_id " \
		"WHERE g.year = {} " \
		  "AND bg.player_id = {} " \
		"GROUP BY 1 " \
		"ORDER BY 1;".format(a, b, year, player_id)

	cursor.execute(sql)

	num = Decimal(0)
	denom = Decimal(0)

	for tpl in cursor.fetchall():
		date = small_date(tpl[0])
		num += Decimal(tpl[1])
		denom += Decimal(tpl[2])
		if denom > 0:
			result[date]['player'] = round(num / denom, 3);
		else:
			result[date]['player'] =  0

	# fill in any missing dates and flatten into list
	prev = 0
	response = []
	for date in result.keys():
		if result[date]['player'] == -1:
			result[date]['player'] = prev
		prev = result[date]['player']
		response.append({
			'date': date,
			'league': result[date]['league'],
			'player': result[date]['player']
		})


	cursor.close()
	connection.close()
	return jsonify(response)


def get_player_runs(player_id):
	return get_batting_agg(player_id, 'r')


def get_player_home_runs(player_id):
	return get_batting_agg(player_id, 'hr')


def get_player_rbi(player_id):
	return get_batting_agg(player_id, 'rbi')


def get_player_obp(player_id):
	return get_batting_pct(player_id, 'obp')


def get_player_slg(player_id):
	return get_batting_pct(player_id, 'slg')


def get_pitching_agg(player_id, type, year=2019):
	if type == 'w':
		a = "SUM(win) AS wins"
		b = "count(pg.id) AS starts"
	elif type == 'k':
		a = "SUM(strikeouts) AS ks"
		b = "SUM(whole_innings) + SUM(CAST(partial_innings AS decimal)) / 3 AS starts"
	elif type == 'sh':
		field = 'runs_batted_in'
	else:
		raise Exception('Invalid data type: {}'.format(type))

	sql = \
		"SELECT g.start, {}, {} " \
		"FROM pitcher_game pg " \
		  "JOIN game g ON g.id = pg.game_id " \
		"WHERE g.year = {} " \
		"GROUP BY 1 " \
		"ORDER BY 1;".format(a, b, year)

	cursor, connection = execute_sql(sql)

	result = {}
	num = Decimal(0)
	denom = Decimal(0)

	for tpl in cursor.fetchall():
		date = small_date(tpl[0])
		num += Decimal(tpl[1])
		denom += Decimal(tpl[2])

		result[date] = {}
		result[date]['league'] = round(num / denom, 3);
		result[date]['player'] = -1

	sql = \
		"SELECT g.start, {}, {} " \
		"FROM pitcher_game pg " \
		  "JOIN game g ON g.id = pg.game_id " \
		"WHERE g.year = {} " \
		  "AND pg.player_id = {} " \
		"GROUP BY 1 " \
		"ORDER BY 1;".format(a, b, year, player_id)

	cursor.execute(sql)

	num = Decimal(0)
	denom = Decimal(0)

	for tpl in cursor.fetchall():
		date = small_date(tpl[0])
		num += Decimal(tpl[1])
		denom += Decimal(tpl[2])
		if denom > 0:
			result[date]['player'] = round(num / denom, 3);
		else:
			result[date]['player'] =  0

	# fill in any missing dates and flatten into list
	prev = 0
	response = []
	for date in result.keys():
		if result[date]['player'] == -1:
			result[date]['player'] = prev
		prev = result[date]['player']
		response.append({
			'date': date,
			'league': result[date]['league'],
			'player': result[date]['player']
		})

	cursor.close()
	connection.close()
	return jsonify(response)


def get_player_wins(player_id):
	return get_pitching_agg(player_id, 'w')


def get_player_ks(player_id):
	return get_pitching_agg(player_id, 'k')


def get_team_runs(team_id):

	sql = \
		"SELECT g.start, count(g.id) AS games, sum(home_runs + away_runs) AS runs " \
		"FROM game g " \
		"WHERE g.year = 2019 " \
		"GROUP BY 1 " \
		"ORDER BY g.start;".format(team_id)

	cursor, connection = execute_sql(sql)

	result = {}

	games = Decimal(0)
	runs = Decimal(0)

	for tpl in cursor.fetchall():

		games += tpl[1]
		runs += Decimal(tpl[2]) / 2
		date = str(tpl[0])

		result[date] = { "average": round(runs / games, 2), "team": Decimal(0.00)}

		log.debug('Storing {} runs {} games {} avg {}'.format(date, tpl[2], tpl[1], round(runs / games, 2)))

	sql = \
		"SELECT g.start, sum(CASE WHEN home_team_id = {} THEN home_runs ELSE away_runs END) AS runs " \
		"FROM game g " \
		"WHERE g.year = 2019 " \
			"AND (g.home_team_id = {} OR g.away_team_id = {}) " \
		"GROUP BY 1 " \
		"ORDER BY g.start;".format(team_id, team_id, team_id)

	games = Decimal(0)
	runs = Decimal(0)

	cursor, connection = execute_sql(sql)

	for tpl in cursor.fetchall():

		games += 1
		date = str(tpl[0])

		if date in result.keys():
			runs += tpl[1]
			result[date]['team'] = round(runs / games, 2)

			log.debug('Storing {} runs {} games {} avg {}'.format(date, tpl[1], games, round(runs / games, 2)))

		else:
			log.error('{} not found in games list'.format(date))


	prev = Decimal(0.00)
	for date in result.keys():
		if result[date]['team'] == Decimal(0.00) and prev != Decimal(0.00):
			result[date]['team'] = prev
			log.debug('No data for {}, carrying over {}'.format(date, prev))
		else:
			prev = result[date]['team']

	cursor.close()
	connection.close()
	log.debug(result)
	return jsonify(result)


def get_stacked_score(team_id):

	sql = \
		"SELECT p.name, p.position, " \
		  "SUM(CASE WHEN pg.position = 'BN' THEN 0 ELSE pg.score END) AS active_score, " \
		  "SUM(CASE WHEN pg.position != 'BN' THEN 0 ELSE pg.score END) AS bench_score, " \
		  "SUM(pg.score) AS score " \
		"FROM ff_player_games pg " \
			"JOIN ff_players p ON p.id = pg.player_id " \
		"WHERE team_id = {} " \
		"GROUP BY 1,2 " \
		"ORDER BY 3 desc;".format(team_id)
	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['name', 'position', 'active_score', 'bench_score', 'total'], cursor=cursor)
	response = [['Player', 'Active', 'Bench']]
	for res in results:
		response.append(['{} ({})'.format(res['name'], res['position']), res['active_score'], res['bench_score']])
	cursor.close()
	connection.close()
	return jsonify(response)


def get_stacked_score_by_position(team_id):

	sql = \
		"SELECT p.name, p.position, " \
		  "SUM(CASE WHEN pg.position = 'BN' THEN 0 ELSE pg.score END) AS active_score, " \
		  "SUM(CASE WHEN pg.position != 'BN' THEN 0 ELSE pg.score END) AS bench_score, " \
		  "SUM(pg.score) AS score " \
		"FROM ff_player_games pg " \
			"JOIN ff_players p ON p.id = pg.player_id " \
		"WHERE team_id = {} " \
		"GROUP BY 1,2 " \
		"ORDER BY 3 desc;".format(team_id)
	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['name', 'position', 'active_score', 'bench_score', 'total'], cursor=cursor)
	response = [['Player', 'Active', 'Bench']]
	positions = ['QB', 'WR', 'RB', 'TE', 'DEF', 'K']
	for pos in positions:
		for res in results:
			if res['position'] != pos:
				continue
			response.append(['{} ({})'.format(res['name'], res['position']), res['active_score'], res['bench_score']])
		if pos != 'K':
			response.append(['', 0, 0])
	cursor.close()
	connection.close()
	return jsonify(response)


def get_player_score(team_id):

	sql = \
		"SELECT p.name, p.position, SUM(pg.score) AS score " \
		"FROM ff_player_games pg " \
			"JOIN ff_players p ON p.id = pg.player_id " \
		"WHERE team_id = {} " \
		"GROUP BY 1,2 " \
		"ORDER BY 3 desc;".format(team_id)
	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['name', 'position', 'score'], cursor=cursor)
	response = [['Player', 'Score']]
	for res in results:
		response.append(['{} ({})'.format(res['name'], res['position']), res['score']])
	cursor.close()
	connection.close()
	return jsonify(response)


def get_active_player_score(team_id):

	sql = \
		"SELECT p.name, p.position, SUM(pg.score) AS score " \
		"FROM ff_player_games pg " \
			"JOIN ff_players p ON p.id = pg.player_id " \
		"WHERE team_id = {} " \
		  "AND pg.position != 'BN' " \
		"GROUP BY 1,2 " \
		"ORDER BY 3 desc;".format(team_id)
	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['name', 'position', 'score'], cursor=cursor)
	response = [['Player', 'Score']]
	for res in results:
		response.append(['{} ({})'.format(res['name'], res['position']), res['score']])
	cursor.close()
	connection.close()
	return jsonify(response)


def get_player_performance(team_id):

	sql = \
		"SELECT p.name, p.position, SUM(pg.score - pg.projected) " \
		"FROM ff_player_games pg " \
			"JOIN ff_players p ON p.id = pg.player_id " \
		"WHERE team_id = {} " \
		"GROUP BY 1,2 " \
		"ORDER BY 3 desc;".format(team_id)
	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['name', 'position', 'performance'], cursor=cursor)
	response = [['Player', 'Performance']]
	for res in results:
		response.append(['{} ({})'.format(res['name'], res['position']), res['performance']])
	cursor.close()
	connection.close()
	return jsonify(response)


##################
# league graphs
##################

def get_best_season():

	# get all teams and initialize response

	sql = \
		"SELECT id, name " \
		"FROM ff_teams " \
		"ORDER BY id;"

	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['id', 'name'], cursor=cursor)
	lst = ['Week']
	for res in results:
		lst.append(res['name'])
	response = [lst]

	# now get our data, can't go past week 14 coz of playoffs

	sql = \
		"SELECT g.week, g.self_id, g.best - g.score AS delta " \
		"FROM ff_games g " \
		"WHERE g.week < 15 " \
		"ORDER BY g.week, g.self_id;"

	cursor.execute(sql)

	results = psychopg_to_list(fields=['week', 'self_id', 'delta'], cursor=cursor)

	# one dummy position at 0
	cum = [Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
	cur_week = 0

	for res in results:
		if res['week'] != cur_week:
			if cur_week > 0:
				response.append(lst)
			cur_week = res['week']
			lst = [cur_week]
		cum[res['self_id']] += res['delta']
		lst.append(cum[res['self_id']])

	response.append(lst)
	cursor.close()
	connection.close()
	log.debug(jsonify(response))
	return jsonify(response)


def get_season_score():

	teams = get_teams_list()
	lst = ['Week']
	for res in teams:
		lst.append(res['name'])
	response = [lst]

	# initialize values
	for i in range(1, 17):
		response.append([i, Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), 
			Decimal(0), Decimal(0), Decimal(0)])

	sql = \
		"SELECT g.week, g.self_id, g.score " \
		"FROM ff_games g " \
		"ORDER BY g.week, g.self_id;"

	cursor, connection = execute_sql(sql)

	results = psychopg_to_list(fields=['week', 'self_id', 'delta'], cursor=cursor)

	# one dummy position at 0
	# cum = [Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), 
	# 	Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
	cur_week = 0

	for res in results:
		# if res['week'] != cur_week:
		# 	if cur_week > 0:
		# 		response.append(lst)
		# 	cur_week = res['week']
		# 	lst = [cur_week]
		#cum[res['self_id']] += res['delta']

		if res['week'] != cur_week:
			if res['week'] > 1:
				for i in range(1, len(teams) + 1):
					response[res['week']][i] = response[res['week'] - 1][i]
			cur_week = res['week']

		response[res['week']][res['self_id']] += res['delta']


		# lst.append(cum[res['self_id']])

	response.append(lst)
	cursor.close()
	connection.close()
	log.debug(jsonify(response))
	return jsonify(response)


def psychopg_to_list(fields, cursor):
	response = []
	for tpl in cursor.fetchall():
		entry = {}
		for i in range(0, len(fields)):
			entry[fields[i]] = tpl[i]
		response.append(entry)
	return response


def psychopg_to_json(fields, cursor):
	response = psychopg_to_list(fields, cursor)
	return jsonify(response)

log.debug('__name__ : {}'.format(__name__))


if __name__ == '__main__':

	monitor_port = 5000
	app_port = 5001

	if len(sys.argv) == 2:
		app_port = sys.argv[1]
	interval = 300
	log.info('PORT {} ARGS {}'.format(app_port, len(sys.argv)))
	log.info(sys.argv)

	pinger = Pinger(
		app_name='reporting',
		app_host='127.0.0.1', 
		app_port=app_port,
		monitor_host='127.0.0.1', 
		monitor_port=monitor_port,
		interval=interval
	)
	rt = RepeatedTimer(interval=interval, function=pinger.ping)

	try:
		log.debug('add_api')
		app.add_api('swagger.yml')
		# NOTE: debug=True causes the restart
		if env == 'develop':
			log.debug('CORS')
			CORS(app.app)
		log.debug('run')
		app.run(host='127.0.0.1', port=app_port, debug=False)
	finally:
		pinger.shutdown()
		rt.stop()
