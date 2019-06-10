import os
import secrets
import string
import datetime
import psycopg2


def query_db(sql):
    db = 'survivor'
    user = 'sv_user'
    pw = os.environ['PG_DB']
    host = 'localhost'

    try:
        cnxn = psycopg2.connect(host=host, database=db, user=user, password=pw)
        cursor = cnxn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if cnxn is not None:
            cnxn.close()


def insert_db(sql, values):
    db = 'survivor'
    user = 'sv_user'
    pw = os.environ['PG_DB']
    host = 'localhost'

    try:
        cnxn = psycopg2.connect(host=host, database=db, user=user, password=pw)
        cursor = cnxn.cursor()
        cursor.execute(sql, values)
        cnxn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return False
    finally:
        if cnxn is not None:
            cnxn.close()


def username_available(username):
    sql = """SELECT username from users"""

    if username not in [x[0] for x in query_db(sql)]:
        return True
    return False


def get_user_id(link):
    sql = """SELECT id from users WHERE link = '%s'""" % (link)
    return query_db(sql)[0][0]


def get_username(link):
    sql = "SELECT username FROM users where link = '%s'" % (link)
    return query_db(sql)[0][0]


def add_user(username, email):
    char_set = string.ascii_lowercase + string.digits
    link = ''.join(secrets.choice(char_set) for _ in range(44))

    while link in [x[0] for x in query_db('SELECT link FROM users')]:
        link = ''.join(secrets.choice(char_set) for _ in range(44))

    sql = """
          INSERT INTO users (username, email, link, admin, validated)
          VALUES (%s, %s, %s, %s, %s);
          """
    values = (username, email, link, False, False)

    insert_db(sql, values)
    return link


def add_user_picks(link, year):
    user_id = get_user_id(link)

    for i in range(0, 17):
        sql = """
              INSERT INTO picks (user_id, year, week, team)
              VALUES (%s, %s, %s, %s);
              """
        values = (user_id, year, i + 1, '--')
        insert_db(sql, values)


def add_paid_status(link, year):
    sql = """
          INSERT INTO paid (user_id, year, paid, result)
          VALUES (%s, %s, %s, %s);
          """
    values = (get_user_id(link), year, False, 'A')
    insert_db(sql, values)


def get_user_picks(link, year):
    sql = """
          SELECT p.week, p.team, p.result, l.lock_date
          FROM picks p
          JOIN locks l ON p.year = l.year AND p.week = l.week
          JOIN users u ON u.id = p.user_id
          WHERE u.link = '%s'
          AND p.year = %s
          ORDER BY p.week
          """ % (link, year)

    data = query_db(sql)
    picks = []
    for row in data:
        dl = row[3].strftime("%m-%d %I:%M PST")
        if datetime.datetime.now() > row[3]:
            picks.append([row[0], row[1], row[2], dl, False])
        else:
            picks.append([row[0], row[1], row[2], dl, True])
    return picks


def not_validated(link):
    sql = "SELECT validated FROM users WHERE link = %s" % link
    return query_db(sql)[0][0]


def validate_link(link):
    sql = """
          UPDATE users
          SET validated = %s
          WHERE link = %s AND validated = FALSE
          """

    values = (True, link)

    insert_db(sql, values)


def set_retired(link, year):
    sql = """
          UPDATE paid
          SET result = 'R'
          WHERE user_id = %s AND year = %s
          """

    values = (get_user_id(link), year)

    insert_db(sql, values)


def user_playing(link, year):
    sql = """
          SELECT p.paid FROM paid p
          JOIN users u ON u.id = p.user_id
          WHERE u.link = '%s'
          AND p.year = %s
          """ % (link, year)

    data = query_db(sql)
    if data:
        return True
    return False


def user_retired(link, year):
    sql = """
          SELECT p.result FROM paid p 
          JOIN users u ON u.id = p.user_id
          WHERE u.link = '%s'
          AND p.year = %s
          """ % (link, year)

    data = query_db(sql)
    if data[0][0] == 'R':
        return True
    return False


def get_years():
    sql = """SELECT year from years order by year desc"""
    return [x[0] for x in query_db(sql)]


def year_locked(year):
    sql = """SELECT lock FROM years WHERE year = %s""" % year
    return query_db(sql)[0][0]


def week_locked(year, week):
    sql = """
          SELECT lock_date FROM locks
          WHERE year = %s AND week = %s
          """ % (year, week)

    if datetime.datetime.now() > query_db(sql)[0][0]:
        return True
    return False


def valid_link(link):
    sql = """SELECT link from users"""

    if link in [x[0] for x in query_db(sql)]:
        return True
    return False


def valid_year(year):
    sql = """SELECT year from years"""

    if year in [str(x[0]) for x in query_db(sql)]:
        return True
    return False


def valid_week(week):
    if int(week) in range(1, 18):
        return True
    return False


def get_team_choices(link, year, week):
    user_id = get_user_id(link)

    sql = """
          SELECT team FROM teams
          WHERE year = %s AND bye_week != %s
          """ % (year, week)
    teams = set([x[0] for x in query_db(sql)])

    sql = """SELECT team FROM picks
             WHERE year = %s AND user_id = %s
          """ % (year, user_id)

    used = set([x[0] for x in query_db(sql)])

    return sorted(list(teams - used) + ['--'])


def get_current_pick(link, year, week):
    sql = """
          SELECT team from picks
          WHERE user_id = %s AND year = %s AND week = %s
          """ % (get_user_id(link), year, week)

    return query_db(sql)[0][0]


def update_pick(link, year, week, pick):
    sql = """
          UPDATE picks
          SET team = %s
          WHERE user_id = %s AND year = %s and week = %s
          """
    values = (pick, get_user_id(link), year, week)

    insert_db(sql, values)


def get_board(year):
    sql = """
          SELECT u.id, u.username, p.paid, p.result
          FROM users u
          JOIN paid p ON u.id = p.user_id
          WHERE p.year = %s
          ORDER BY p.result, u.username, p.paid
          """ % (year)

    rows = query_db(sql)

    data = []
    for row in rows:
        sql = """
              SELECT p.team, p.result
              FROM picks p
              JOIN locks l ON l.week = p.week AND l.year = p.year
              WHERE user_id = %s AND p.year = %s AND p.week <=
              (SELECT max(week) FROM locks
               WHERE CURRENT_TIMESTAMP > lock_date AND year = %s
              )
              ORDER BY p.week ASC
              """ % (row[0], year, year)

        picks = query_db(sql)
        wins = len([x[1] for x in picks if x[1] == 'W'])
        loss = len([x[1] for x in picks if x[1] == 'L'])

        line = [row[1], row[2], row[3], wins, loss, picks]
        data.append(line)

        data.sort(key=lambda x: x[0].lower())  # sort by username
        data.sort(key=lambda x: x[4])  # sort by losses
        data.sort(key=lambda x: x[3], reverse=True)  # sort by wins
        data.sort(key=lambda x: x[2])  # sort by player status

    return data


def get_current_year():
    return query_db('SELECT year from current')[0][0]
