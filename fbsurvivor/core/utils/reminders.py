from fbsurvivor.core.services import PlayerStatusQuery, SeasonService
from fbsurvivor.core.utils.deadlines import get_reminder_message
from fbsurvivor.core.utils.emails import send_email


def send_reminders():
    current_season = SeasonService.get_current()

    season_service = SeasonService(current_season)

    next_week = season_service.get_next_week()
    if not next_week:
        return

    message = get_reminder_message(current_season, next_week)
    if not message:
        return

    subject = f"Survivor {current_season.year}: Week {next_week.week_num} Reminder"
    message = f"Week {next_week.week_num} Locks:\n\n" + message

    if email_recipients := list(PlayerStatusQuery.for_email_reminders(next_week)):
        send_email(subject, email_recipients, message)
