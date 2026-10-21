"""Load the real plots at Brakastølen, as listed on the current website's plot map.

    python manage.py seed_plots              # add the plots that don't exist yet
    python manage.py seed_plots --dry-run    # only show what would change
    python manage.py seed_plots --overwrite  # also reset price, size, status and category
                                             # of existing plots to the website's values

The data (apps/core/data/brakastolen-plots.json) was read from brakastølen.no's plot map:
number, size, price, sold or not, and each plot's outline on the site plan. The category
follows the 2022 plot map: Byggetrinn 1 is plots 1–34, Byggetrinn 2 is plots 35–66.

Safe to run again: plots are matched on their number. Without --overwrite an existing plot
keeps everything the client has changed in the dashboard; only a missing map outline or
category is filled in. Example plots from the old design sketch are removed.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Plot, PlotCategory

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'brakastolen-plots.json'
EXAMPLE_NOTE = 'Eksempeldata fra designskissen'
OVERWRITE_FIELDS = ['status', 'area_m2', 'price', 'note', 'category']
MAP_FIELDS = ['map_x', 'map_y', 'map_shape']


class Command(BaseCommand):
    help = 'Load the real plots from brakastølen.no (numbers, sizes, prices, status and map outlines).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')
        parser.add_argument('--overwrite', action='store_true',
                            help="Reset existing plots' price, size, status and category to the website's values.")

    def handle(self, *args, dry_run=False, overwrite=False, **options):
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        with transaction.atomic():
            report = self.load(data, overwrite)
            if dry_run:
                transaction.set_rollback(True)

        prefix = 'Would have ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}created {report['created']}, updated {report['updated']}, "
            f"left {report['unchanged']} unchanged, removed {report['examples']} example plots."
        ))

    def load(self, data, overwrite):
        examples, _ = Plot.objects.filter(note=EXAMPLE_NOTE).delete()

        categories = {}
        for order, name in enumerate(data['categories'], start=1):
            categories[name], _ = PlotCategory.objects.get_or_create(name=name, defaults={'order': order})

        report = {'created': 0, 'updated': 0, 'unchanged': 0, 'examples': examples}
        for order, row in enumerate(data['plots'], start=1):
            values = {
                'status': row['status'],
                'area_m2': row['area_m2'],
                'price': row['price'],
                'note': row['note'],
                'category': categories[row['category']],
                'map_x': row['map_x'],
                'map_y': row['map_y'],
                'map_shape': row['map_shape'],
            }
            plot = Plot.objects.filter(number=row['number'], project__isnull=True).first()
            if plot is None:
                Plot.objects.create(number=row['number'], order=order, **values)
                report['created'] += 1
                continue

            fields = list(OVERWRITE_FIELDS) if overwrite else []
            if not plot.map_shape:
                fields += MAP_FIELDS
            if plot.category_id is None and 'category' not in fields:
                fields.append('category')
            changed = [name for name in fields if getattr(plot, name) != values[name]]
            if not changed:
                report['unchanged'] += 1
                continue
            for name in changed:
                setattr(plot, name, values[name])
            plot.save(update_fields=changed + ['updated_at'])
            report['updated'] += 1
        return report
