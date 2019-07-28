import os
import smtplib
from email.mime.text import MIMEText

from settings import *

WHO_FROM = SMTP_SENDER
SMTP_SER = SMTP_SERVER
USERNAME = SMTP_USER
PASSWORD = SMTP_PASSWORD


def send_email(subject, who_to, message):

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = WHO_FROM
    msg['To'] = WHO_FROM

    cnxn = smtplib.SMTP_SSL(SMTP_SER)
    cnxn.login(USERNAME, PASSWORD)
    try:
        cnxn.sendmail(WHO_FROM, who_to, msg.as_string())
    finally:
        cnxn.quit()
