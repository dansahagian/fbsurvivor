import smtplib
from email.mime.text import MIMEText

from fbsurvivor.core.models import EmailLogRecord
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

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SMTP_SENDER
    msg["To"] = SMTP_SENDER

    conn = smtplib.SMTP_SSL(SMTP_SERVER)
    conn.login(SMTP_USER, SMTP_PASSWORD)
    try:
        conn.sendmail(SMTP_SENDER, recipients, msg.as_string())
    finally:
        conn.quit()

    log_email(subject, recipients)

    return None
