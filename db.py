import os
import secrets
import string
import datetime
import psycopg2


def run_query(sql, values=None):
    db = 'survivor'
    user = 'sv_user'
    pw = os.environ['PG_DB']
    host = 'localhost'
    cnxn = None
    data = []
    
    try:
        cnxn = psycopg2.connect(host=host, database=db, user=user, password=pw)
        cursor = cnxn.cursor()

        if values:
            cursor.execute(sql, values)
        else:
            cursor.execute(sql)

        if sql[0:5] == 'SELECT':
            data = cursor.fetchall()
        if sql[0:5] in ['UPDATE', 'INSERT']:
            cnxn.commit()
            
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    finally:
        if cnxn is not None:
            cnxn.close()

    return data


def get_usernames():
    """ Returns a list of usernames from the database"""
    sql = 'SELECT username from users'
    data = run_query(sql)

    if data:
        return [x[0] for x in data]
    return False


def get_links():
    """ Returns a list of links from the database"""
    sql = 'SELECT link from users'
    data = run_query(sql)

    if data:
        return [x[0] for x in data]
    return False


def get_years():
    sql = """SELECT year from years order by year desc"""
    return [x[0] for x in run_query(sql)]


def username_available(username):
    if username not in get_usernames():
        return True
    return False


def get_user_id(link):
    sql = 'SELECT id from users WHERE link = %s'
    values = (link, )
    return run_query(sql, values)[0][0]


def get_username(link):
    sql = 'SELECT username FROM users where link = %s'
    values = (link, )
    return run_query(sql, values)[0][0]


def add_user(username, email):
    char_set = string.ascii_lowercase + string.digits
    link = ''.join(secrets.choice(char_set) for _ in range(44))

    while link in get_links():
        link = ''.join(secrets.choice(char_set) for _ in range(44))

    sql = 'INSERT INTO users (username, email, link, admin, validated) VALUES (%s, %s, %s, %s, %s);'
    values = (username, email, link, False, False)
    run_query(sql, values)

    if get_username(link):
        return link
    return None


def add_user_picks(link, year):
    user_id = get_user_id(link)

    for i in range(0, 17):
        sql = 'INSERT INTO picks (user_id, year, week, team) VALUES (%s, %s, %s, %s);'
        values = (user_id, year, i + 1, '--')
        run_query(sql, values)


def add_paid_status(link, year):
    sql = 'INSERT INTO paid (user_id, year, paid, result) VALUES (%s, %s, %s, %s);'
    values = (get_user_id(link), year, False, 'A')
    run_query(sql, values)


def get_user_picks(link, year):
    sql = """
          SELECT p.week, p.team, p.result, l.lock_date
          FROM picks p
          JOIN locks l ON p.year = l.year AND p.week = l.week
          JOIN users u ON u.id = p.user_id
          WHERE u.link = %s
          AND p.year = %s
          ORDER BY p.week
          """
    values = (link, year)

    data = run_query(sql, values)
    picks = []
    for row in data:
        dl = row[3].strftime("%m-%d %I:%M PST")
        if datetime.datetime.now() > row[3]:
            picks.append([row[0], row[1], row[2], dl, False])
        else:
            picks.append([row[0], row[1], row[2], dl, True])
    return picks


def not_validated(link):
    sql = 'SELECT validated FROM users WHERE link = %s'
    values = (link, )
    return run_query(sql, values)[0][0]


def validate_link(link):
    sql = 'UPDATE users SET validated = %s WHERE link = %s AND validated = FALSE'
    values = (True, link)
    run_query(sql, values)


def set_retired(link, year):
    user_id = get_user_id(link)
    sql = "UPDATE paid SET result = 'R' WHERE user_id = %s AND year = %s"
    values = (user_id, year)
    run_query(sql, values)


def user_playing(link, year):
    sql = 'SELECT p.paid FROM paid p JOIN users u ON u.id = p.user_id WHERE u.link = %s AND p.year = %s'
    values = (link, year)
    data = run_query(sql, values)

    if data:
        return True
    return False


def user_retired(link, year):
    sql = 'SELECT p.result FROM paid p JOIN users u ON u.id = p.user_id WHERE u.link = %s AND p.year = %s'
    values = (link, year)
    data = run_query(sql, values)

    if data:
        if data[0][0] == 'R':
            return True
    return False


def year_locked(year):
    sql = 'SELECT lock FROM years WHERE year = %s'
    values = (year, )
    return run_query(sql, values)[0][0]


def week_locked(year, week):
    sql = 'SELECT lock_date FROM locks WHERE year = %s AND week = %s'
    values = (year, week)

    if datetime.datetime.now() > run_query(sql, values)[0][0]:
        return True
    return False


def valid_link(link):
    if link in get_links():
        return True
    return False


def valid_year(year):
    if int(year) in get_years():
        return True
    return False


def valid_week(week):
    if int(week) in range(1, 18):
        return True
    return False


def get_team_choices(link, year, week):
    user_id = get_user_id(link)

    sql = 'SELECT team FROM teams WHERE year = %s AND bye_week != %s'
    values = (year, week)
    teams = set([x[0] for x in run_query(sql, values)])

    sql = 'SELECT team FROM picks WHERE year = %s AND user_id = %s'
    values = (year, user_id)
    used = set([x[0] for x in run_query(sql, values)])

    return sorted(teams - used) + ['--']


def get_current_pick(link, year, week):
    user_id = get_user_id(link)

    sql = 'SELECT team from picks WHERE user_id = %s AND year = %s AND week = %s'
    values = (user_id, year, week)

    return run_query(sql, values)[0][0]


def update_pick(link, year, week, pick):
    user_id = get_user_id(link)

    sql = 'UPDATE picks SET team = %s WHERE user_id = %s AND year = %s and week = %s'
    values = (pick, user_id, year, week)
    run_query(sql, values)


def get_board(year):
    sql = """
          SELECT u.id, u.username, p.paid, p.result
          FROM users u
          JOIN paid p ON u.id = p.user_id
          WHERE p.year = %s
          ORDER BY p.result, u.username, p.paid
          """
    values = (year, )
    rows = run_query(sql, values)

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
              """
        values = (row[0], year, year)
        picks = run_query(sql, values)

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
    return run_query('SELECT year from current')[0][0]
