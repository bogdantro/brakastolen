"""Shrink oversized photos in static/images and media/ so pages load fast.

    python manage.py optimize_images            # optimise everything
    python manage.py optimize_images --dry-run  # only show what would change

Run it again whenever new photos are added to static/images (uploads through the
dashboard are shrunk automatically). Files keep their name and format, so no
template or database changes are needed. The untouched original of every changed
file is copied to originals/ first (kept out of git), so nothing is lost – and a
file that already has a backup is skipped, so photos are never compressed twice.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.images import EXTENSIONS, MAX_EDGE, MAX_EDGE_HERO, optimize_image

# The plot map is read by zooming in, so it keeps more pixels than a photo
MAX_EDGE_MAP = 3200


def edge_for(rel):
    """'hero/hero-1.jpg' -> 2400, 'misc/tomtekart-2022.png' -> 3200, anything else -> 2000."""
    if rel.startswith('hero/'):
        return MAX_EDGE_HERO
    if 'tomtekart' in rel:
        return MAX_EDGE_MAP
    return MAX_EDGE


class Command(BaseCommand):
    help = 'Resize and recompress oversized photos in static/images and media/.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report, change nothing.')

    def handle(self, *args, dry_run=False, **options):
        base = settings.BASE_DIR
        folders = [(base / 'static' / 'images', 'static-images'), (settings.MEDIA_ROOT, 'media')]
        before = after = changed = 0
        for folder, backup_name in folders:
            for root, _, files in os.walk(folder):
                for name in sorted(files):
                    if not name.lower().endswith(EXTENSIONS):
                        continue
                    path = os.path.join(root, name)
                    rel = os.path.relpath(path, folder)
                    backup = base / 'originals' / backup_name / rel
                    if backup.exists():
                        continue
                    size = os.path.getsize(path)
                    max_edge = edge_for(rel.replace('\\', '/'))
                    try:
                        new_size = optimize_image(path, max_edge, backup=str(backup), dry_run=dry_run)
                    except Exception as error:  # a broken file must not stop the rest
                        self.stderr.write(f'Skipped {rel}: {error}')
                        continue
                    before += size
                    after += new_size
                    if new_size != size:
                        changed += 1
                        self.stdout.write(f'{size // 1024:>6} KB -> {new_size // 1024:>5} KB  {rel}')
        verb = 'Would shrink' if dry_run else 'Shrank'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} {changed} files: {before / 1e6:.0f} MB -> {after / 1e6:.0f} MB'
        ))
