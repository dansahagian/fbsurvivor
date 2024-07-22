from django.core.management.base import BaseCommand

from fbsurvivor.core.utils.helpers import cache_current_board


class Command(BaseCommand):
    help = "Cache the board for the current season."

    def handle(self, *args, **options):
        cache_current_board()
