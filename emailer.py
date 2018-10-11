import os
import smtplib
from email.mime.text import MIMEText

WHO_FROM = os.environ['WHO_FROM']
SMTP_SER = os.environ['SMTP_SER']
USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']


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
