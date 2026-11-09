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


SENDER = str(SMTP_SENDER)


def log_email(subject: str, recipients: list[str]):
    for recipient in recipients:
        EmailLogRecord.objects.create(subject=subject, email=recipient)


def send_email_async(subject: str, email_address: str, message: str) -> None:
    """Send off the request thread so the response doesn't wait on SMTP.

    The login flow needs this: a synchronous send makes the known-email path
    seconds slower than the unknown-email path, which leaks account existence
    by timing no matter what we sleep on the other branch.
    """
    if ENV == "dev":
        send_addressed_email(subject, email_address, message)
        return

    def run():
        try:
            send_addressed_email(subject, email_address, message)
        except Exception:
            logger.exception("Email failed: %s to %s", subject, email_address)
        finally:
            connections.close_all()

    threading.Thread(target=run, daemon=True).start()


def _build_msg(subject: str, to: str, message: str) -> MIMEText:
    msg = MIMEText(message)
    msg["Subject"] = f"🏈 {subject} 🏈"
    msg["From"] = SENDER
    msg["To"] = to
    return msg


def _send_email(recipients: list[str], msg: MIMEText) -> None:
    subject = str(msg["Subject"])

    if ENV == "dev":
        body = msg.get_payload(decode=True)
        if isinstance(body, bytes):
            body = body.decode()
        print(f"\n\nSending Email to {len(recipients)} players...\n{subject}\n\n{body}\n\n")
        log_email(subject, recipients)
        return

    server = str(SMTP_SERVER)
    user = str(SMTP_USER)
    passwd = str(SMTP_PASSWORD)

    conn = smtplib.SMTP_SSL(server)
    conn.login(user, passwd)
    try:
        conn.sendmail(SENDER, recipients, msg.as_string())
    finally:
        conn.quit()

    log_email(subject, recipients)


def send_addressed_email(subject: str, email_address: str, message: str) -> None:
    _send_email([email_address], _build_msg(subject, email_address, message))


def send_bulk_email(subject: str, recipients: list[str], message: str) -> None:
    _send_email(recipients, _build_msg(subject, SENDER, message))


def send_new_player_email(user: User) -> None:
    ps = f"If you didn't sign up, please email Dan at {settings.CONTACT}"
    login = f"{settings.DOMAIN}"
    subject = "Survivor User Account"
    message = f"You can login here:\n\n{login}\n\n{ps}"

    send_addressed_email(subject, user.email, message)


def send_login_code(user: User, code: str) -> None:
    subject = "Survivor Login"
    expiration = f"{CODE_EXPIRATION_MINUTES} minutes"

    message = f"Use the code below to login. It expires in {expiration}.\n\n{code}"

    send_addressed_email(subject, user.email, message)
