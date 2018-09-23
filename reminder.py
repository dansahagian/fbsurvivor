import datetime
import db
import emailer


def get_players():
    sql = """
          SELECT email
          FROM users u
          JOIN paid p ON p.user_id = u.id
          WHERE p.year = (SELECT year FROM current)
          AND p.result != 'R'
          AND u.validated = True
          """

    return [x[0] for x in db.query_db(sql)]


def get_players_without_picks():
    sql = """
          SELECT u.email, pk.team
          FROM users u
          JOIN paid pd ON pd.user_id = u.id
          JOIN picks pk ON pk.user_id = u.id
          WHERE pd.year = (SELECT year FROM current)
          AND pk.year = (SELECT year FROM current)
          AND pk.week = (SELECT min(week) FROM locks WHERE
                         lock_date > CURRENT_TIMESTAMP)
          AND pk.team = '--'
          AND pd.result != 'R'
          AND u.validated = True
          """

    return [x[0] for x in db.query_db(sql)]


def get_lock_date():
    sql = """
          SELECT lock_date
          FROM locks
          WHERE year = (SELECT year FROM current)
          """
    current_date = datetime.datetime.now()

    return min([x[0] for x in db.query_db(sql) if x[0] > current_date])


def main():

    lock_date = get_lock_date().strftime("%m-%d %I:%M %p")
    subject = 'Survivor Picks Reminder'
    message = "Picks are due by %s PST!" % lock_date
    week_day = datetime.datetime.today().weekday()
    if week_day == 3:
        who_to = get_players_without_picks()
    else:
        who_to = get_players()

    emailer.send_email(subject, who_to, message)


if __name__ == '__main__':
    main()
