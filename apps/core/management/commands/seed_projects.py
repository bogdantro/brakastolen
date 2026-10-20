"""Load Brakastølen's real projects (from the old website) with their photos.

    python manage.py seed_projects            # create the projects that don't exist yet
    python manage.py seed_projects --dry-run  # only show what would be created

Photos are copied from static/images/projects and static/images/hero into media/, the
same way a dashboard upload is stored. A project whose title already exists is skipped,
so running the command twice does no harm and never overwrites the client's edits.
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Project, ProjectImage

STATIC_IMAGES = Path(settings.BASE_DIR) / 'static' / 'images'

PROJECTS = [
    {
        'title': 'Ulven hyttegrend',
        'category': 'hyttegrend',
        'status': 'for_sale',
        'location': 'Brakastølen, Vaset',
        'excerpt': 'Felt med kun 10 tomter på oversiden av Brakastølen. Langrennssporet går rett forbi feltet.',
        'description': (
            '<p>Feltet ligger på oversiden av Brakastølen. Adkomsten er via Nye Øyevegen, og man følger videre '
            'Ulsetbekkvegen til feltet. Feltet ligger i enden på vegen og består kun av 10 tomter. Her er 9 av '
            'tomtene solgt pr i dag. Langrennssporet går rett forbi feltet.</p>'
            '<p>Kontakt oss for prospekt på feltet.</p>'
        ),
        'image': 'hero/hero-1-tranberg-utvikling-vaset.jpg',
        'plot_count': 10,
        'access': 'Via Nye Øyevegen og videre Ulsetbekkvegen',
        'has_view': True,
        'has_ski_trail': True,
        'is_featured': True,
        'gallery': [],
    },
    {
        'title': 'Tinde Hytter på Brakastølen',
        'category': 'hytte',
        'status': 'to_order',
        'location': 'Brakastølen, Vaset',
        'supplier': 'Tinde Hytter',
        'excerpt': 'Kvalitetshytter fra Tinde Hytter – bygget spesielt for deg og dine, på tomta du velger.',
        'description': (
            '<p>Tinde Hytter vet at det finnes like mange tinder som det er mennesker. Derfor har Tinde utviklet '
            'gode serier av kvalitetshytter – alle med hver sine særtrekk og egenskaper. Tinde bygger din hytte '
            'spesielt for deg og dine, slik blir den et sted der du kan dyrke de gode opplevelser i livet.</p>'
            '<p>Les mer om Tinde Hytter på <a href="https://www.tindehytter.no">www.tindehytter.no</a>.</p>'
        ),
        'image': 'projects/tinde-vaset-3939.jpg',
        'image_credit': 'Pål Harald Uthus, Uthus Photography',
        'has_view': True,
        'has_fireplace': True,
        'is_featured': True,
        'gallery': [
            'projects/tinde-vaset-3992.jpg',
            'projects/tinde-vaset-4030.jpg',
            'projects/tinde-hytte-01-12031236.jpg',
            'projects/tinde-hytte-02-12031237.jpg',
            'projects/tinde-hytte-03-12031239.jpg',
            'projects/tinde-hytte-04-12031241.jpg',
            'projects/tinde-hytte-05-12031243.jpg',
            'projects/tinde-hytte-06-12031244.jpg',
            'projects/tinde-hytte-07-12031245.jpg',
            'projects/tinde-hytte-08-12031246.jpg',
            'projects/tinde-hytte-09-12031247.jpg',
        ],
    },
    {
        'title': 'Leve Hytter – Vy-serien',
        'category': 'hytte',
        'status': 'to_order',
        'location': 'Brakastølen, Vaset',
        'supplier': 'Leve Hytter',
        'excerpt': 'Moderne kvalitetshytter med tidløst design og solid håndverk, utviklet med en av Norges fremste arkitekter.',
        'description': (
            '<p>Leve Hytter lager moderne kvalitetshytter med god arkitektur. Ei hytte skal vare i mange generasjoner. '
            'Derfor er Leve Hytter opptatt av at den skal fremstå som tidløs, i motsetning til gammaldags.</p>'
            '<p>Leve Hytter sin hytteserie heter Vy, og er utviklet i samarbeid med en av Norges fremste arkitekter. '
            'Den kommer i flere grunnmodeller og størrelser, med gode valgmuligheter. Du får ei gjennomtenkt hytte, '
            'akkurat tilpasset deg.</p>'
            '<p>Les mer om Leve Hytter på <a href="https://www.levehytter.no">www.levehytter.no</a>.</p>'
        ),
        'image': 'projects/leve-hytter-vy-overblikk.jpg',
        'has_view': True,
        'has_fireplace': True,
        'is_featured': True,
        'gallery': [
            ('projects/leve-hytte-utsikt-til-syndin.jpg', 'Utsikt til Syndin fra en Leve-hytte'),
            ('projects/leve-hytter-interior.jpg', 'Interiør fra Leve Hytter'),
            ('projects/leve-hytter-interior-hellerud.jpg', 'Interiør fra Leve Hytter'),
            ('projects/leve-hytter-ildsted-hellerud.jpg', 'Ildsted i Leve-hytte'),
            ('projects/leve-hytter-lyivy.jpg', 'Leve-hytte i vinterkveld'),
        ],
    },
]

FACT_KEYS = ('supplier', 'plot_count', 'access', 'image_credit', 'has_view', 'has_fireplace', 'has_ski_trail')


def attach(field, relative_path):
    """Copy a photo from static/images into the model's upload folder."""
    path = STATIC_IMAGES / relative_path
    with path.open('rb') as handle:
        field.save(path.name, File(handle), save=False)


class Command(BaseCommand):
    help = 'Create the projects from the old website (Ulven hyttegrend, Tinde Hytter, Leve Hytter).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')

    def handle(self, *args, dry_run=False, **options):
        created = skipped = photos = 0
        for order, data in enumerate(PROJECTS, start=1):
            if Project.objects.filter(title=data['title']).exists():
                skipped += 1
                self.stdout.write(f'Skipped (exists): {data["title"]}')
                continue
            if dry_run:
                created += 1
                self.stdout.write(f'Would create: {data["title"]} with {len(data["gallery"]) + 1} photos')
                continue
            with transaction.atomic():
                project = Project(
                    title=data['title'],
                    category=data['category'],
                    status=data['status'],
                    location=data['location'],
                    excerpt=data['excerpt'],
                    description=data['description'],
                    is_featured=data.get('is_featured', False),
                    is_published=True,
                    order=order,
                    **{key: data[key] for key in FACT_KEYS if key in data},
                )
                attach(project.image, data['image'])
                project.save()
                for position, item in enumerate(data['gallery'], start=1):
                    relative_path, caption = item if isinstance(item, tuple) else (item, '')
                    image = ProjectImage(project=project, caption=caption, order=position)
                    attach(image.image, relative_path)
                    image.save()
                photos += 1 + len(data['gallery'])
            created += 1
            self.stdout.write(f'Created: {project.title} ({1 + len(data["gallery"])} photos)')

        verb = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(f'{verb} {created} projects ({photos} photos), skipped {skipped}.'))
