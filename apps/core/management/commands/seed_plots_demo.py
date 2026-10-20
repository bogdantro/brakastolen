"""Load the EXAMPLE plots from the Webiser plot-picker prototype, so the picker can be tried locally.

    python manage.py seed_plots_demo            # create the example plots that don't exist yet
    python manage.py seed_plots_demo --dry-run  # only show what would be created

These numbers, sizes, prices and map positions are illustrative – the prototype says so itself.
They must never reach the live site: the command refuses to run unless DEBUG=True. Before launch,
the client enters the real plots in Dashboard → Tomter (and places each one on the map there).
A plot number that already exists is skipped, so running the command twice does no harm.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Plot

# (number, area m², price kr – 0 means sold, x, y) – straight from the prototype
EXAMPLE_PLOTS = [
    (11, 1500, 1500000, 232, 226), (12, 1700, 1450000, 291, 205), (13, 1900, 0, 350, 187),
    (14, 1800, 0, 409, 171), (15, 1500, 0, 468, 154), (16, 1300, 1900000, 522, 142),
    (17, 1200, 1850000, 208, 276), (18, 1400, 0, 269, 256), (19, 1300, 0, 328, 239),
    (20, 1200, 1300000, 389, 222), (21, 1100, 1250000, 449, 206), (22, 1400, 0, 510, 192),
    (23, 1200, 1050000, 252, 409), (24, 1600, 1750000, 313, 387), (25, 1300, 1500000, 374, 366),
    (26, 1500, 1350000, 435, 344), (27, 1600, 0, 496, 324), (28, 1600, 0, 557, 301),
    (29, 1500, 1450000, 231, 469), (30, 1600, 1200000, 292, 447), (31, 1800, 1150000, 353, 425),
    (32, 1200, 1200000, 414, 403), (33, 1500, 1600000, 475, 383), (34, 1600, 1150000, 536, 360),
    (35, 1300, 1450000, 446, 553), (36, 1400, 1200000, 507, 532),
]
# The last row of plots sits along a slightly different road angle
ROTATION = -20
ROTATION_LAST_ROW = -17
LAST_ROW_FROM = 24


class Command(BaseCommand):
    help = 'Create the example plots from the plot-picker prototype (local development only).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')

    def handle(self, *args, dry_run=False, **options):
        if not settings.DEBUG:
            raise CommandError(
                'This loads EXAMPLE plots with made-up prices and only runs with DEBUG=True. '
                'Enter the real plots in the dashboard instead.'
            )
        created = skipped = 0
        for index, (number, area, price, x, y) in enumerate(EXAMPLE_PLOTS):
            if Plot.objects.filter(number=str(number)).exists():
                skipped += 1
                continue
            if dry_run:
                created += 1
                self.stdout.write(f'Would create: tomt {number}')
                continue
            Plot.objects.create(
                number=str(number),
                area_m2=area,
                price=price or None,
                status='available' if price else 'sold',
                note='Eksempeldata fra designskissen',
                map_x=x,
                map_y=y,
                map_rotation=ROTATION_LAST_ROW if index >= LAST_ROW_FROM else ROTATION,
                order=index,
            )
            created += 1
        verb = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.WARNING(
            f'{verb} {created} EXAMPLE plots, skipped {skipped}. Replace them with real plots before launch.'
        ))
