"""Shrinking of oversized photos – used by `manage.py optimize_images` and on every upload."""
import os
import shutil

from PIL import Image, ImageOps

EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
MAX_EDGE = 2000
# Full-screen hero backgrounds get a little more room on large screens
MAX_EDGE_HERO = 2400
# Smaller files are left alone unless they are too big in pixels
MIN_BYTES = 400 * 1024
QUALITY = 80
# WebP effort 0–6: 2 is almost as small as 6 but about 6x faster, which matters
# when a whole gallery is uploaded in one request
WEBP_METHOD = 2


def optimize_image(path, max_edge=MAX_EDGE, backup=None, dry_run=False):
    """Resize and recompress the image at `path` in place, keeping its name and format.
    Returns the new file size (unchanged size = nothing was done).
    With `backup`, the original is copied there before it is replaced."""
    size = os.path.getsize(path)
    with Image.open(path) as image:
        image.load()
        fmt = image.format
        too_large = max(image.size) > max_edge
        if size < MIN_BYTES and not too_large:
            return size
        # Bake the camera rotation into the pixels, since the metadata is dropped
        image = ImageOps.exif_transpose(image)
        if too_large:
            image.thumbnail((max_edge, max_edge), Image.LANCZOS)

        tmp = path + '.tmp'
        # iPhones save JPEGs as MPO (a JPEG with an extra embedded image)
        if fmt in ('JPEG', 'MPO'):
            image.convert('RGB').save(tmp, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
        elif fmt == 'WEBP':
            image.save(tmp, 'WEBP', quality=QUALITY, method=6)
        elif fmt == 'PNG':
            image.save(tmp, 'PNG', optimize=True)
        else:
            return size

    new_size = os.path.getsize(tmp)
    # Only keep the result if it is clearly smaller
    if new_size >= size * 0.9 or dry_run:
        os.remove(tmp)
        return size if new_size >= size * 0.9 else new_size
    if backup is not None and not os.path.exists(backup):
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.copy2(path, backup)
    os.replace(tmp, path)
    return new_size


def shrink_upload(upload, max_edge=MAX_EDGE, to_webp=False):
    """Return a smaller copy of a freshly uploaded photo as a ContentFile, or None to keep it.
    With to_webp, every photo becomes WebP (transparency kept). Otherwise photos saved
    as PNG without transparency become JPEG, which is many times smaller."""
    import io
    from django.core.files.base import ContentFile

    upload.seek(0)
    with Image.open(upload) as image:
        image.load()
        fmt = image.format
        transparent = image.mode in ('RGBA', 'LA', 'PA') and image.getchannel('A').getextrema()[0] < 255
        if image.mode == 'P' and 'transparency' in image.info:
            transparent = True
        image = ImageOps.exif_transpose(image)
        if max(image.size) > max_edge:
            image.thumbnail((max_edge, max_edge), Image.LANCZOS)

        out = io.BytesIO()
        stem = os.path.splitext(os.path.basename(upload.name))[0]
        if to_webp:
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGBA' if transparent else 'RGB')
            image.save(out, 'WEBP', quality=QUALITY, method=WEBP_METHOD)
            name = stem + '.webp'
            upload.seek(0)
            # Always keep the WebP, unless the upload already was a smaller WebP
            if fmt == 'WEBP' and out.tell() >= upload.size:
                return None
            return ContentFile(out.getvalue(), name=name)
        if fmt in ('JPEG', 'MPO') or (fmt in ('PNG', 'WEBP') and not transparent):
            image.convert('RGB').save(out, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
            name = stem + '.jpg'
        elif fmt == 'WEBP':
            image.save(out, 'WEBP', quality=QUALITY, method=WEBP_METHOD)
            name = stem + '.webp'
        elif fmt == 'PNG':
            image.save(out, 'PNG', optimize=True)
            name = stem + '.png'
        else:
            return None
    upload.seek(0)
    if out.tell() >= upload.size * 0.9:
        return None
    return ContentFile(out.getvalue(), name=name)
