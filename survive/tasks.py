import datetime
import smtplib
from email.mime.text import MIMEText

from survive.db import (
    get_lock_date, get_players, get_players_without_picks, get_current_week,
    get_current_year, get_retired_players, update_pick_result
)
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
        who_to = get_players_without_picks()
    else:
        who_to = get_players()
    if FLASK_ENV == "development":
        who_to = ['dan@dansahagian.com']

    send_email(subject, who_to, message)


def update_retired_picks():
    week = get_current_week()
    year = get_current_year()
    if week > 0:
        retired_players = get_retired_players()
        for player in retired_players:
            update_pick_result(player, year, week, "R")
