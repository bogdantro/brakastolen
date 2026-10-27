"""Add every FINN ad from Tranberg Utvikling, Tinde Hytter and Leve Hytter at Brakastølen
(a FINN search for «Brakastølen», 27.10.2026). Ads already there (matched on the link) are
left as the client has them in the dashboard."""
from django.db import migrations

# A copy of the list in seed_field_info as it was when this migration was written:
# (title, FINN section, finnkode, what the ad is, price in kr)
ADS = [
    ('Eksklusiv tomt med panoramautsikt og sol fra morgen til kveld', 'plots', 471023190,
     'Tomt, Brakastølvegen 110 – Tranberg Utvikling', 1850000),
    ('Solrike panoramatomter – kampanje: 2 gratis el-sykler ved kjøp', 'plots', 470544998,
     'Tomter, Øyebakkin – Tranberg Utvikling', 1400000),
    ('Drømmetomter – solvendt, luftig og med panoramautsikt', 'plots', 400288938,
     'Tomter, Brakastøllie – Tranberg Utvikling', 1500000),
    ('Brakastølen 2 – solvendte fjelltomter med spektakulær utsikt', 'plots', 280027233,
     'Tomter, Nye Øyevegen – Tranberg Utvikling', 900000),
    ('Hytte «Nordlys» med stor hems – tomt og grunnarbeid inkludert', 'leisuresale', 374061108,
     'Hytte med tomt, Nye Øyevegen tomt 64 – Tranberg Utvikling', 4223000),
    ('Stor, eksklusiv hytte med hems og spektakulær utsikt', 'leisuresale', 339408992,
     'Hytte med tomt, Brakastøllie 13 – Tranberg Utvikling', 8592000),
    ('Nøkkelferdig familiehytte med 5 soverom og flott utsikt', 'leisuresale', 426219618,
     'Hytte med tomt, Brakastøllie – Tinde Hytter', 5620000),
    ('Eksklusiv hytte med tømmerdetaljer og flott utsikt', 'leisuresale', 422876484,
     'Hytte med tomt, Brakastøllie – Tinde Hytter', 7450000),
    ('Nøkkelferdig hytte med 4 soverom, god utsikt og sol', 'leisuresale', 276521226,
     'Hytte med tomt, Øyebakkin – Tinde Hytter', 4800000),
    ('Nøkkelferdig og arealeffektiv hytte med 4 soverom og 2 bad', 'leisuresale', 276520828,
     'Hytte med tomt, Øyebakkin – Tinde Hytter', 4860000),
    ('Utsiktshytte på solrik tomt ca. 1000 moh. – tomt, graving og betong inkludert', 'leisuresale', 284633576,
     'Hytte med tomt, Brakastøllie – Leve Hytter', 5440000),
]


def add_ads(apps, schema_editor):
    FinnAd = apps.get_model('core', 'FinnAd')
    start = FinnAd.objects.count() + 1
    for order, (title, section, code, kind, price) in enumerate(ADS, start=start):
        url = f'https://www.finn.no/realestate/{section}/ad.html?finnkode={code}'
        FinnAd.objects.get_or_create(url=url, defaults={'title': title, 'kind': kind, 'price': price, 'order': order})


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_plot_street'),
    ]

    operations = [
        migrations.RunPython(add_ads, migrations.RunPython.noop),
    ]
