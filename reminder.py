import datetime

import db
import emailer


def main():

    lock_date = db.get_lock_date().strftime("%m-%d %I:%M %p")
    subject = 'Survivor Picks Reminder'
    message = "Picks are due by %s PST!" % lock_date
    week_day = datetime.datetime.today().weekday()

    if week_day == 3:
        who_to = db.get_players_without_picks()
    else:
        who_to = db.get_players()

    emailer.send_email(subject, who_to, message)


if __name__ == '__main__':
    main()
