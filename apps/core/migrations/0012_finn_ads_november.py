"""FINN ads, client feedback 05.11.2026: the Leve cabin at Brakastølvegen 116 is sold and comes off
the website, and the e-bike campaign is gone from the «Solrike panoramatomter» ad on FINN, so it
goes from the title here too. A title the client has already changed in the dashboard is left alone."""
from django.db import migrations

SOLD_CODES = ['371502243']  # Innflytningsklar Leve-hytte med spektakulær utsikt

# finnkode -> (title with the campaign, title without)
RENAMED = {
    '470544998': ('Solrike panoramatomter – kampanje: 2 gratis el-sykler ved kjøp',
                  'Solrike panoramatomter – Brakastølen/Vaset'),
}


def update_ads(apps, schema_editor):
    FinnAd = apps.get_model('core', 'FinnAd')
    for code in SOLD_CODES:
        FinnAd.objects.filter(url__endswith=f'finnkode={code}').delete()
    for code, (old_title, new_title) in RENAMED.items():
        FinnAd.objects.filter(url__endswith=f'finnkode={code}', title=old_title).update(title=new_title)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_finn_ad_category'),
    ]

    operations = [
        migrations.RunPython(update_ads, migrations.RunPython.noop),
    ]
