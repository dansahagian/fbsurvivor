from datetime import datetime

from django.core.management.base import BaseCommand

from fbsurvivor.core.models import Season, Week


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("filename", type=str)

    def handle(self, *args, **options):
        year = options["year"]
        filename = options["filename"]

        n_created = 0
        n_updated = 0

        season, _ = Season.objects.get_or_create(year=year)

        with open(filename, "r") as f:
            for line in f:
                week_num, lock_datetime = line.strip("/n").split(",")
                lock_datetime = datetime.fromisoformat(lock_datetime)

                _, created = Week.objects.update_or_create(
                    season=season, week_num=week_num, defaults={"lock_datetime": lock_datetime}
                )

                if created:
                    n_created += 1
                else:
                    n_updated += 1

        print(f"Created: {n_created} and Updated: {n_updated} weeks!")
