import logging
import smtplib
import threading
from email.mime.text import MIMEText

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections

from fbsurvivor.core.models import EmailLogRecord
from fbsurvivor.core.utils.authentication import CODE_EXPIRATION_MINUTES
from fbsurvivor.settings import ENV, SMTP_PASSWORD, SMTP_SENDER, SMTP_SERVER, SMTP_USER

logger = logging.getLogger(__name__)


def log_email(subject: str, recipients: list[str]):
    for recipient in recipients:
        EmailLogRecord.objects.create(subject=subject, email=recipient)


def send_email_async(subject, recipients, message) -> None:
    """Send off the request thread so the response doesn't wait on SMTP.

    The login flow needs this: a synchronous send makes the known-email path
    seconds slower than the unknown-email path, which leaks account existence
    by timing no matter what we sleep on the other branch.
    """
    if ENV == "dev":
        send_email(subject, recipients, message)
        return

    def run():
        try:
            send_email(subject, recipients, message)
        except Exception:
            logger.exception("Email failed: %s to %s", subject, recipients)
        finally:
            connections.close_all()

    threading.Thread(target=run, daemon=True).start()


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


def send_new_player_email(user: User) -> None:
    ps = f"If you didn't sign up, please email Dan at {settings.CONTACT}"
    login = f"{settings.DOMAIN}"
    subject = "Survivor User Account"
    recipients = [user.email]
    message = f"You can login here:\n\n{login}\n\n{ps}"

    send_email(subject, recipients, message)


def send_login_code(user: User, code: str) -> None:
    subject = "Survivor Login"
    expiration = f"{CODE_EXPIRATION_MINUTES} minutes"

    message = f"Use the code below to login. It expires in {expiration}.\n\n{code}"

    send_email_async(subject, [user.email], message)
