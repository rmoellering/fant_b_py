
import psycopg2
import requests
import sys

from utils import get_logger, RepeatedTimer, replace_accents, compress_string

log = get_logger(__name__)

def get_conn():
	return psycopg2.connect(
		host='localhost',
		dbname='fant_b',
		user='robmo',
		password=''
	)

connection = get_conn()
cursor = connection.cursor()

sql = "SELECT id, name FROM player;"
cursor.execute(sql)

for tpl in cursor.fetchall():
	id = tpl[0]
	name = tpl[1]

	lname = replace_accents(name)
	lname = compress_string(lname)

	cursor2 = connection.cursor()
	sql = "UPDATE player SET lname = '{}' WHERE id = {};".format(lname, id)
	cursor2.execute(sql)

	log.debug('{} => {}'.format(name, lname))

connection.commit()

cursor2.close()
cursor.close()
connection.close()
