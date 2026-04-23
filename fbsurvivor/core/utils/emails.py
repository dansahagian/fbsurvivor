import smtplib
from email.mime.text import MIMEText

from django.conf import settings

from fbsurvivor.core.models import EmailLogRecord, Player
from fbsurvivor.settings import ENV, SMTP_PASSWORD, SMTP_SENDER, SMTP_SERVER, SMTP_USER


def log_email(subject: str, recipients: list[str]):
    for recipient in recipients:
        EmailLogRecord.objects.create(subject=subject, email=recipient)


def send_email(subject, recipients, message) -> None:
    subject = f"🏈 {subject} 🏈"

    if ENV == "dev":
        print(f"\n\nSending Email to {len(recipients)} players...\n{subject}\n\n{message}\n\n")
        log_email(subject, recipients)
        return None

    sender = str(SMTP_SENDER)
    server = str(SMTP_SERVER)
    user = str(SMTP_USER)
    passwd = str(SMTP_PASSWORD)

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = sender

    conn = smtplib.SMTP_SSL(server)
    conn.login(user, passwd)
    try:
        conn.sendmail(sender, recipients, msg.as_string())
    finally:
        conn.quit()

    log_email(subject, recipients)

    return None


def send_new_player_email(player: Player) -> None:
    ps = f"If you didn't sign up, please email Dan at {settings.CONTACT}"
    login = f"{settings.DOMAIN}"
    subject = "Survivor User Account"
    recipients = [player.email]
    message = f"You can login here:\n\n{login}\n\n{ps}"

    send_email(subject, recipients, message)
