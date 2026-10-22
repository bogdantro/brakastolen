"""Fill a new server with everything the website starts with, in one go.

    python manage.py seed_site            # plots, costs, FINN ad, zoning map and news
    python manage.py seed_site --dry-run  # only show what would be added

Runs, in order: seed_plots (the 54 plots with prices, sold status, heights and map outlines),
seed_field_info (costs, the zoning map, the FINN ad) and seed_blog (the news from the old site).
Each of them only adds what is missing, so it is safe to run again – nothing the client has
changed in the dashboard is overwritten.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

SEEDS = ['seed_plots', 'seed_field_info', 'seed_blog']


class Command(BaseCommand):
    help = 'Load the plots, the field info and the news – everything a new server starts with.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')

    def handle(self, *args, dry_run=False, **options):
        for name in SEEDS:
            self.stdout.write(self.style.MIGRATE_HEADING(f'{name}:'))
            call_command(name, dry_run=dry_run, stdout=self.stdout, stderr=self.stderr)
        self.stdout.write(self.style.SUCCESS('Done. Next: python manage.py createsuperuser (tick «staff»).'))
