"""Shrink photos as they are uploaded in the dashboard, so a 6 MB camera photo
or a PNG screenshot of a photo never ends up on the website as-is."""
import logging

from django.core.files.uploadedfile import UploadedFile
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.blog.models import Blog

from .images import shrink_upload

logger = logging.getLogger(__name__)

IMAGE_FIELDS = {
    Blog: ['image'],
}

# Fields stored as WebP – the smallest format all current browsers show. News photos stay
# JPEG: they double as the share image, and LinkedIn and some apps don't show WebP previews.
WEBP_FIELDS = set()


@receiver(pre_save)
def shrink_new_uploads(sender, instance, **kwargs):
    for name in IMAGE_FIELDS.get(sender, []):
        field_file = getattr(instance, name)
        upload = getattr(field_file, '_file', None)
        # Only files uploaded in this save – existing photos are never recompressed
        if not isinstance(upload, UploadedFile):
            continue
        try:
            smaller = shrink_upload(upload, to_webp=(sender, name) in WEBP_FIELDS)
        except Exception:  # an odd file is still better stored as-is than a failed upload
            logger.warning('Could not shrink upload %s', upload.name, exc_info=True)
            continue
        if smaller is not None:
            setattr(instance, name, smaller)
