from fbsurvivor import settings
from fbsurvivor.core.models import Player
from fbsurvivor.core.utils.emails import send_email


class PlayerService:
    @staticmethod
    def create(username: str, email: str):
        player, created = Player.objects.get_or_create(username=username, email=email)

        if created:
            ps = f"If you didn't sign up, please email Dan at {settings.CONTACT}"
            login = f"{settings.DOMAIN}"
            subject = "Survivor User Account"
            recipients = [email]
            message = f"You can login here:\n\n{login}\n\n{ps}"

            send_email(subject, recipients, message)
