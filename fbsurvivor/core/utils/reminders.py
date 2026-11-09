from fbsurvivor.core.queries import (
    get_current_season,
    get_emails_for_reminders,
    get_next_week,
)
from fbsurvivor.core.utils.deadlines import get_reminder_message
from fbsurvivor.core.utils.emails import send_bulk_email


def send_reminders():
    current_season = get_current_season()

    next_week = get_next_week(current_season)
    if not next_week:
        return

    message = get_reminder_message(current_season, next_week)
    if not message:
        return

    week_text = f"Week {next_week.week_num}"
    subject = f"Survivor {current_season.year}: Week {next_week.week_num} Reminder"
    warning = f"If you received this email, you have not submitted your pick for {week_text}."
    message = f"{warning}\n\n{week_text} Locks:\n\n" + message

    if email_recipients := get_emails_for_reminders(next_week):
        send_bulk_email(subject, email_recipients, message)
