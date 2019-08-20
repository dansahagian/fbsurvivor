import datetime
import smtplib
from email.mime.text import MIMEText

from survivor import db
from survivor.settings import SMTP_USER, SMTP_PASSWORD, SMTP_SERVER, SMTP_SENDER


def send_email(subject, recipients, message):
    username = SMTP_USER
    password = SMTP_PASSWORD
    server = SMTP_SERVER
    sender = SMTP_SENDER

    msg = MIMEText(message)

    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = sender

    cnxn = smtplib.SMTP_SSL(server)
    cnxn.login(username, password)
    try:
        cnxn.sendmail(sender, recipients, msg.as_string())
    finally:
        cnxn.quit()


def send_reminder():
    lock_date = db.get_lock_date().strftime("%m-%d %I:%M %p")
    subject = "Survivor Picks Reminder"
    message = f"Picks are due by {lock_date} PST!"
    week_day = datetime.datetime.today().weekday()

    if week_day == 3:
        recipients = db.get_players_without_picks()
    else:
        recipients = db.get_players()

    # send_email(subject, recipients, message)
    print(recipients)


def retired_picks():
    week = db.get_current_week()
    year = db.get_current_year()
    if week > 0:
        retired_players = db.get_retired_players()
        for player in retired_players:
            db.update_pick_result(player, year, week, "R")
