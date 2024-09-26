from fbsurvivor.core.models import PlayerStatus, Week
from fbsurvivor.core.services import SeasonService
from fbsurvivor.core.utils.deadlines import get_reminder_message
from fbsurvivor.core.utils.emails import send_email


def send_reminders():
    for season in SeasonService.get_live():
        season_service = SeasonService(season)

        next_week: Week = season_service.get_next_week()

        if not next_week:
            return

        message = get_reminder_message(season, next_week)

        if not message:
            return

        subject = f"Survivor {season.description}: Week {next_week.week_num} Reminder"
        message = f"Week {next_week.week_num} Locks:\n\n" + message

        if email_recipients := list(PlayerStatus.objects.for_email_reminders(next_week)):
            send_email(subject, email_recipients, message)
