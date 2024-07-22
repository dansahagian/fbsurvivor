from django.core.management.base import BaseCommand

from fbsurvivor.core.models import Season, Team


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("filename", type=str)

    def handle(self, *args, **options):
        year = options["year"]
        filename = options["filename"]

        n_created = 0
        n_updated = 0

        season = Season.objects.get(year=year)

        with open(filename, "r") as f:
            for line in f:
                bye_week, team_code, name = line.strip("/n").split(",")

                _, created = Team.objects.update_or_create(
                    season=season,
                    bye_week=bye_week,
                    team_code=team_code,
                    name=name,
                )

                if created:
                    n_created += 1
                else:
                    n_updated += 1

        print(f"Created: {n_created} and Updated: {n_updated} teams!")
