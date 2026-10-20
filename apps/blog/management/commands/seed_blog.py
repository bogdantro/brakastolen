"""Load the news posts from the old website.

    python manage.py seed_blog            # create the posts that don't exist yet
    python manage.py seed_blog --dry-run  # only show what would be created

Published: the real news from the old front page ("Nyheter" section).
Drafts: the old WordPress posts, which only had a title and placeholder text (Lorem ipsum),
and the el-bike campaign, whose end date is unknown. The client fills in or confirms these
in the dashboard before publishing. A post whose title already exists is skipped.
"""
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.blog.models import Blog

STATIC_IMAGES = Path(settings.BASE_DIR) / 'static' / 'images'

MISSING_TEXT = (
    '<p>Teksten til denne nyheten manglet på den gamle nettsiden (den inneholdt bare plassholdertekst). '
    'Skriv inn den ekte teksten før nyheten publiseres.</p>'
)

POSTS = [
    {
        'title': 'Ulven hyttegrend',
        'excerpt': 'Feltet på oversiden av Brakastølen består kun av 10 tomter, og langrennssporet går rett forbi.',
        'text': (
            '<p>Feltet ligger på oversiden av Brakastølen. Adkomsten er via Nye Øyevegen, og man følger videre '
            'Ulsetbekkvegen til feltet. Feltet ligger i enden på vegen og består kun av 10 tomter. Her er 9 av '
            'tomtene solgt pr i dag. Langrennssporet går rett forbi feltet.</p>'
            '<p>Kontakt oss for prospekt på feltet.</p>'
        ),
        'image': 'misc/tomtekart-2022-02-01.png',
        'image_alt': 'Tomtekart over Brakastølen med hyttegrendene',
        'is_published': True,
    },
    {
        'title': 'Våre samarbeidspartnere på Brakastølen',
        'excerpt': 'Fra tomt og grunnmur til finansiering og oppgjør – dette er partnerne vi bruker på Brakastølen.',
        'text': (
            '<h2>Hytteleverandører</h2>'
            '<ul><li>Tinde Hytter</li>'
            '<li>FAUN Gruppen: Leve Hytter, Telemarkhytter, Øverbygg, Nordlyshytter, Familiehytta</li>'
            '<li>Slidre Bygg &amp; Prosjektering</li></ul>'
            '<h2>Andre samarbeidspartnere</h2>'
            '<ul><li>Opparbeidelse av tomt og grunnmur – VA Entreprenør AS</li>'
            '<li>Planlegging av hytte på tomt – Plan og Oppmåling Valdres AS</li>'
            '<li>Finansiering – SpareBank 1 Hallingdal Valdres</li>'
            '<li>Oppgjørsmegler – EIE Fjellmegleren Fagernes</li>'
            '<li>Byggesak – Vestre Slidre kommune</li></ul>'
        ),
        'image': 'misc/annonse-2023-07-samarbeidspartnere.png',
        'image_alt': 'Annonse for Brakastølen med bilder fra Vaset',
        'is_published': True,
    },
    {
        'title': 'Kampanje: to gratis el-sykler med hyttetomta',
        'excerpt': 'De som kjøper hyttetomt nå, får med to el-sykler til en verdi av ca. 60 000 kr.',
        'text': (
            '<p>De som kjøper hyttetomt nå, får med 2 gratis el-sykler til en verdi på ca. kr 60 000. '
            'El-syklene er av samme type eller lignende som de som er kåret «Best i test». '
            'Syklene leveres av Intersport på Vaset.</p>'
            '<p>Vi har stort utvalg i fantastiske tomter. Alle tomtene har spektakulær utsikt i 180 grader, '
            'samt sol fra morgen til kveld. Det er ikke byggeklausul på tomtene.</p>'
        ),
        'image': 'misc/annonse-2024-07-05.png',
        'image_alt': 'Annonse for hyttetomter på Brakastølen',
        # Still on the old front page, but no end date is given – the client confirms before publishing
        'is_published': False,
    },
    {
        'title': 'Reguleringsplan vedtatt',
        'text': MISSING_TEXT,
        'image': 'blog/reguleringsplan.png',
        'image_alt': 'Reguleringsplan for Brakastølen',
        'is_published': False,
        'date': datetime(2020, 6, 30, 0, 59),
    },
    {
        'title': 'Skogsavvirkning påbegynt',
        'text': MISSING_TEXT,
        'image': 'blog/hogst.jpg',
        'image_alt': 'Tømmerstabler etter hogst på Brakastølen',
        'is_published': False,
        'date': datetime(2020, 6, 30, 1, 0),
    },
    {
        'title': 'Bærår i år?',
        'text': MISSING_TEXT,
        'is_published': False,
        'date': datetime(2020, 6, 30, 1, 1),
    },
]


class Command(BaseCommand):
    help = 'Create the news posts from the old website (real news published, placeholder posts as drafts).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')

    def handle(self, *args, dry_run=False, **options):
        created = skipped = 0
        for data in POSTS:
            if Blog.objects.filter(title=data['title']).exists():
                skipped += 1
                self.stdout.write(f'Skipped (exists): {data["title"]}')
                continue
            state = 'published' if data['is_published'] else 'draft'
            if dry_run:
                created += 1
                self.stdout.write(f'Would create ({state}): {data["title"]}')
                continue
            post = Blog(
                title=data['title'],
                excerpt=data.get('excerpt', ''),
                text=data['text'],
                image_alt=data.get('image_alt', ''),
                is_published=data['is_published'],
            )
            if data.get('image'):
                path = STATIC_IMAGES / data['image']
                with path.open('rb') as handle:
                    post.image.save(path.name, File(handle), save=False)
            post.save()
            if data.get('date'):
                # Keep the original publishing date from the old site
                Blog.objects.filter(pk=post.pk).update(created_at=timezone.make_aware(data['date']))
            created += 1
            self.stdout.write(f'Created ({state}): {post.title}')

        verb = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(f'{verb} {created} posts, skipped {skipped}.'))
