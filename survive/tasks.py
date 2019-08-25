import smtplib
from email.mime.text import MIMEText

from survive.db import *
from survive.settings import *


def send_email(subject, recipients, message):
    sender = SMTP_SENDER
    server = SMTP_SERVER
    username = SMTP_USER
    password = SMTP_PASSWORD

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
    lock_date = get_lock_date().strftime("%m-%d %I:%M %p")
    subject = "Survivor Picks Reminder"
    message = f"Picks are due by {lock_date} PST!"
    week_day = datetime.datetime.today().weekday()

    if week_day == 3:
        recipients = get_players_without_picks()
    else:
        recipients = get_players()
    if FLASK_ENV == "development":
        recipients = [DEV_EMAIL]

    send_email(subject, recipients, message)


def update_retired_picks():
    week = get_current_week()
    year = get_current_year()
    if week > 0:
        retired_players = get_retired_players()
        for player in retired_players:
            update_pick_result(player, year, week, "R")
