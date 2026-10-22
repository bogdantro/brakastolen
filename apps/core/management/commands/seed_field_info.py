"""Load the facts shown under the plot map: the costs on top of the plot price, the zoning map,
and the FINN ad the client has sent so far.

    python manage.py seed_field_info            # add what is missing
    python manage.py seed_field_info --dry-run  # only show what would be added

The costs are the client's own table (22.10.2026). They are only added when there are no costs
yet, so changes made in Dashboard → Feltinfo are never overwritten. The FINN ad is matched on
its link and the document on its title, so running the command twice does no harm.
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import CostItem, FieldDocument, FinnAd

# (what, kr) – summed on the website as «Anleggsbidrag, engangsavgift» (90 000 kr)
FIXED_COSTS = [
    ('Engangsavgift Vaset Bru/Krokåne', 6000),
    ('Engangsavgift Nye Øyevegen', 10000),
    ('Innmelding til Vasetløypene', 5000),
    ('Kart og måleforretning', 24000),
    ('Anleggsbidrag strøm', 45000),
]
# (what, % of the plot price)
PERCENT_COSTS = [
    ('Dokumentavgift', '2.5'),
]

FINN_ADS = [
    {
        'title': 'Innflytningsklar Leve-hytte med spektakulær utsikt',
        'url': 'https://www.finn.no/realestate/leisuresale/ad.html?finnkode=371502243',
        'kind': 'Hytte til salgs, Brakastølvegen 116',
        'price': 5350000,
    },
]

ZONING_MAP = ('Reguleringskart – detaljregulering for Brakastølen', 'images/blog/reguleringsplan.png')


class Command(BaseCommand):
    help = 'Load the costs, the zoning map and the FINN ads shown under the plot map.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')

    def handle(self, *args, dry_run=False, **options):
        added = []
        with transaction.atomic():
            if not CostItem.objects.exists():
                for order, (label, amount) in enumerate(FIXED_COSTS, start=1):
                    CostItem.objects.create(label=label, amount=amount, order=order)
                for order, (label, percent) in enumerate(PERCENT_COSTS, start=len(FIXED_COSTS) + 1):
                    CostItem.objects.create(label=label, percent=percent, order=order)
                added.append(f'{len(FIXED_COSTS) + len(PERCENT_COSTS)} cost lines')

            for order, ad in enumerate(FINN_ADS, start=1):
                _, created = FinnAd.objects.get_or_create(url=ad['url'], defaults={**ad, 'order': order})
                if created:
                    added.append(f"FINN ad «{ad['title']}»")

            title, static_path = ZONING_MAP
            source = Path(settings.BASE_DIR) / 'static' / static_path
            if not FieldDocument.objects.filter(title=title).exists() and source.exists():
                if not dry_run:  # the file is copied into media/ – nothing to roll back in a dry run
                    with source.open('rb') as handle:
                        document = FieldDocument(title=title, order=1)
                        document.file.save('reguleringskart-brakastolen.png', File(handle), save=True)
                added.append(f'document «{title}»')

            if dry_run:
                transaction.set_rollback(True)

        prefix = 'Would add' if dry_run else 'Added'
        self.stdout.write(self.style.SUCCESS(f"{prefix}: {', '.join(added) or 'nothing – everything is there'}."))
