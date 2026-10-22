"""Static files on the live server: content-hashed names when `collectstatic` has been run,
plain names straight from static/ when it hasn't – never a crashed page.

With WhiteNoise's manifest storage every {% static %} is looked up in the manifest that
`collectstatic` writes. If that was skipped (or a file was added after it), Django raises
"Missing staticfiles manifest entry" and the whole page becomes a 500. Here the page gets the
plain file name instead, which WhiteNoise serves from static/ (WHITENOISE_USE_FINDERS).
"""
import logging

from whitenoise.storage import CompressedManifestStaticFilesStorage

log = logging.getLogger(__name__)


class ForgivingManifestStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unhashed = set()  # warn once per file, not on every page view

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            if name not in self.unhashed:
                self.unhashed.add(name)
                log.warning('%s is not in the collectstatic manifest – serving it from static/ unhashed. '
                            'Run "python manage.py collectstatic" for year-long caching.', name)
            return name
