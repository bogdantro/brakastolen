"""Static files on the live server: content-hashed names when `collectstatic` is up to date,
and never an old CSS or JS file when it isn't – never a crashed page either.

With WhiteNoise's manifest storage every {% static %} is looked up in the manifest that
`collectstatic` writes, and the hashed file is cached by browsers for a year. Two things can
go wrong on an update:

- a file is missing from the manifest (collectstatic was skipped, or the file is new): Django
  would raise "Missing staticfiles manifest entry" and the page would be a 500;
- a file was changed but collectstatic wasn't run again: the manifest still points at the old
  hashed file, so every visitor keeps getting the old CSS – even after a hard reload.

In both cases the page links the current file from static/ instead (WHITENOISE_USE_FINDERS),
with a hash of its content in the URL (main.css?v=3f2a1c9e0b), so a changed file always gets a
new URL and no browser can show a stale copy. The log says which files, once per change.
"""
import filecmp
import hashlib
import logging
import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.storage import FileSystemStorage
from whitenoise.storage import CompressedManifestStaticFilesStorage

log = logging.getLogger(__name__)

# Characters of the content hash put in ?v= – the same length Django uses in hashed names
VERSION_LENGTH = 12


class ForgivingManifestStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # name -> (source mtime, source size, version or None). Checked with one os.stat per
        # file and request, so the files are only compared/hashed again when they change.
        self.freshness = {}

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:  # not in the manifest – url() below links the source file instead
            return name

    def url(self, name, force=False):
        version = self.stale_version(name)
        if version:
            return f'{FileSystemStorage.url(self, name)}?v={version}'
        return super().url(name, force)

    def stale_version(self, name):
        """None when collectstatic's copy of `name` is current; otherwise a short hash of the
        file in static/ to put in the URL. 'css/a.css' -> None or '3f2a1c9e0b4d'."""
        source = finders.find(name) if name else None
        if not source or not isinstance(source, str):
            return None  # not one of our files (or only in staticfiles/) – leave it to the manifest
        try:
            stat = os.stat(source)
        except OSError:
            return None

        cached = self.freshness.get(name)
        if cached and cached[:2] == (stat.st_mtime, stat.st_size):
            return cached[2]

        collected = os.path.join(settings.STATIC_ROOT, name)
        current = (name in self.hashed_files and os.path.exists(collected)
                   and filecmp.cmp(source, collected, shallow=False))
        version = None
        if not current:
            with open(source, 'rb') as f:
                version = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()[:VERSION_LENGTH]
            log.warning('%s has changed since "collectstatic" (or was never collected) – serving it '
                        'from static/ as ?v=%s. Run "python manage.py collectstatic" for year-long caching.',
                        name, version)
        self.freshness[name] = (stat.st_mtime, stat.st_size, version)
        return version
