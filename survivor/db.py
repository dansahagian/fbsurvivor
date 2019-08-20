import datetime
import secrets
import string

import psycopg2

from survivor.settings import *


def get_db_conn():
    db = DATABASE
    user = PG_USER
    pw = PG_PASSWORD
    host = PG_HOST

    return psycopg2.connect(host=host, database=db, user=user, password=pw)


def select(sql, values=None):
    data = []
    conn = get_db_conn()

    try:
        cursor = conn.cursor()
        if values:
            cursor.execute(sql, values)
        else:
            cursor.execute(sql)
        data = cursor.fetchall()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

    return data


def update(sql, values=None):
    conn = get_db_conn()

    try:
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


def select_list(sql, values=None):
    data = select(sql, values)
    if data:
        return [x[0] for x in data]
    return []


def get_usernames():
    sql = "SELECT username from users"
    return select_list(sql)


def get_links():
    sql = "SELECT link from users"
    return select_list(sql)


def get_years():
    sql = "SELECT year from years order by year desc"
    return select_list(sql)


def get_user_id(link):
    sql = "SELECT id from users WHERE link = %s"
    values = (link,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return 0


def get_user_id_from_username(username):
    sql = "SELECT id from users WHERE username = %s"
    values = (username,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return 0


def get_username(link):
    sql = "SELECT username FROM users where link = %s"
    values = (link,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return ""


def get_email(link):
    sql = "SELECT email FROM users where link = %s"
    values = (link,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return ""


def is_admin(link):
    sql = "SELECT admin FROM users where link = %s"
    values = (link,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return False


def get_links_from_email(email):
    sql = "SELECT link FROM users where email = %s"
    values = (email,)
    return select_list(sql, values)


def add_user(username, email):
    char_set = string.ascii_lowercase + string.digits
    link = "".join(secrets.choice(char_set) for _ in range(44))

    while link in get_links():
        link = "".join(secrets.choice(char_set) for _ in range(44))

    sql = """
          INSERT INTO users (username, email, link, admin, confirmed)
          VALUES (%s, %s, %s, %s, %s);
          """
    values = (username, email, link, False, False)
    update(sql, values)

    if get_username(link):
        return link
    return ""


def add_user_picks(link, year):
    year = int(year)

    user_id = get_user_id(link)

    for i in range(0, 17):
        sql = "INSERT INTO picks (user_id, year, week, team) VALUES (%s, %s, %s, %s);"
        values = (user_id, year, i + 1, "--")
        update(sql, values)


def add_paid_status(link, year):
    year = int(year)

    sql = "INSERT INTO paid (user_id, year, paid, result) VALUES (%s, %s, %s, %s);"
    values = (get_user_id(link), year, False, "A")
    update(sql, values)


def get_user_picks(link, year):
    year = int(year)

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

    data = select(sql, values)
    picks = []
    for row in data:
        dl = row[3].strftime("%m-%d %I:%M PST")
        if datetime.datetime.now() > row[3]:
            picks.append([row[0], row[1], row[2], dl, False])
        else:
            picks.append([row[0], row[1], row[2], dl, True])
    return picks


def email_confirmed(link):
    sql = "SELECT confirmed FROM users WHERE link = %s"
    values = (link,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return False


def confirm_email(link):
    sql = "UPDATE users SET confirmed = TRUE WHERE link = %s;"
    values = (link,)
    update(sql, values)


def set_retired(link, year):
    year = int(year)

    user_id = get_user_id(link)
    sql = "UPDATE paid SET result = 'R' WHERE user_id = %s AND year = %s;"
    values = (user_id, year)
    update(sql, values)


def user_playing(link, year):
    year = int(year)

    sql = """
          SELECT p.paid FROM paid p 
          JOIN users u ON u.id = p.user_id
          WHERE u.link = %s AND p.year = %s
          """
    values = (link, year)
    data = select(sql, values)

    if data:
        return True
    return False


def user_retired(link, year):
    year = int(year)

    sql = """
          SELECT p.result FROM paid p
          JOIN users u ON u.id = p.user_id
          WHERE u.link = %s AND p.year = %s
          """
    values = (link, year)
    data = select(sql, values)

    if data:
        if data[0][0] == "R":
            return True
    return False


def year_locked(year):
    year = int(year)

    sql = "SELECT lock FROM years WHERE year = %s"
    values = (year,)
    data = select(sql, values)
    if data:
        return data[0][0]
    return True


def week_locked(year, week):
    year = int(year)
    week = int(week)

    sql = "SELECT lock_date FROM locks WHERE year = %s AND week = %s"
    values = (year, week)
    data = select(sql, values)
    if data:
        return datetime.datetime.now() > select(sql, values)[0][0]
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


def username_available(username):
    if username not in get_usernames():
        return True
    return False


def get_team_choices(link, year, week):
    year = int(year)
    week = int(week)
    user_id = get_user_id(link)

    sql = "SELECT team FROM teams WHERE year = %s AND bye_week != %s"
    values = (year, week)
    teams = set([x[0] for x in select(sql, values)])

    sql = "SELECT team FROM picks WHERE year = %s AND user_id = %s"
    values = (year, user_id)
    used = set([x[0] for x in select(sql, values)])

    return sorted(teams - used) + ["--"]


def get_current_pick(link, year, week):
    year = int(year)
    week = int(week)
    user_id = get_user_id(link)

    sql = "SELECT team from picks WHERE user_id = %s AND year = %s AND week = %s"
    values = (user_id, year, week)
    data = select(sql, values)
    if data:
        return data[0][0]
    return []


def update_pick(link, year, week, pick):
    year = int(year)
    week = int(week)
    user_id = get_user_id(link)

    sql = "UPDATE picks SET team = %s WHERE user_id = %s AND year = %s AND week = %s"
    values = (pick, user_id, year, week)
    update(sql, values)


def update_pick_result(user_id, year, week, result):
    sql = "UPDATE picks SET result = %s WHERE user_id = %s AND year = %s AND week = %s"
    values = (result, user_id, year, week)
    update(sql, values)


def get_board(year):
    year = int(year)
    sql = """
          SELECT u.id, u.username, p.paid, p.result
          FROM users u
          JOIN paid p ON u.id = p.user_id
          WHERE p.year = %s
          ORDER BY p.result, u.username, p.paid
          """
    values = (year,)
    rows = select(sql, values)

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
        picks = select(sql, values)

        wins = len([x[1] for x in picks if x[1] == "W"])
        loss = len([x[1] for x in picks if x[1] == "L"])

        line = [row[1], row[2], row[3], wins, loss, picks]
        data.append(line)

        data.sort(key=lambda x: x[0].lower())  # sort by username
        data.sort(key=lambda x: x[4])  # sort by losses
        data.sort(key=lambda x: x[3], reverse=True)  # sort by wins
        data.sort(key=lambda x: x[2])  # sort by player status

    return data


def get_current_year():
    return select("SELECT year from current")[0][0]


def get_players():
    sql = """
          SELECT email
          FROM users u
          JOIN paid p ON p.user_id = u.id
          WHERE p.year = %s
          AND p.result != %s
          AND u.confirmed = %s
          """

    values = (get_current_year(), "R", True)
    return select_list(sql, values)


def get_retired_players():
    sql = """
          SELECT u.id
          FROM users u
          JOIN paid p ON P.user_id = u.id
          WHERE p.year = %s
          AND p.result = %s
          AND u.confirmed = %s
          """

    values = (get_current_year(), "R", True)
    return select_list(sql, values)


def get_players_without_picks():
    year = get_current_year()

    sql = """
          SELECT u.email
          FROM users u
          JOIN paid pd ON pd.user_id = u.id
          JOIN picks pk ON pk.user_id = u.id
          WHERE pd.year = %s
          AND pk.year = %s
          AND pk.week = (SELECT min(week) FROM locks WHERE
                         lock_date > CURRENT_TIMESTAMP)
          AND (pk.team = '--' or u.username = 'DanTheAutomator')
          AND pd.result != %s
          AND u.confirmed = %s
          """

    values = (year, year, "R", True)
    return select_list(sql, values)


def get_lock_date():
    sql = "SELECT MIN(lock_date) FROM locks WHERE lock_date > %s"
    values = (datetime.datetime.now(),)
    return select(sql, values)[0][0]


def get_current_week():
    sql = "SELECT week FROM locks WHERE lock_date = %s"

    values = (get_lock_date(),)
    return select(sql, values)[0][0] - 1


def get_paid_statuses(year):
    sql = """
          SELECT username, p.paid
          FROM users u 
          JOIN paid p ON p.user_id = u.id
          WHERE p.year = %s
          ORDER BY p.paid, username
          """
    values = (year,)
    return select(sql, values)


def is_paid(link, year):
    sql = "SELECT p.paid FROM paid p WHERE year = %s and user_id = %s"
    values = (year, get_user_id(link))
    data = select(sql, values)
    return data[0][0] if data else False


def update_paid_status(year, username):
    sql = "UPDATE paid SET paid = TRUE WHERE year = %s and user_id = %s"
    values = (year, get_user_id_from_username(username))
    update(sql, values)
