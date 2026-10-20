"""Set the sites framework's Site row to the real domain, so nothing depends on
Django's 'example.com' default."""
from urllib.parse import urlparse

from django.conf import settings
from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    domain = urlparse(settings.SITE_URL).netloc or 'www.xn--brakastlen-6cb.no'
    Site.objects.update_or_create(pk=settings.SITE_ID, defaults={'domain': domain, 'name': 'Brakastølen'})


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(set_site_domain, migrations.RunPython.noop),
    ]
