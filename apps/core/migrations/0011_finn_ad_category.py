"""Sort the FINN ads into plots and cabins, so they can be listed under separate headings
(client feedback 28.10.2026). FINN's own link says what an ad is: /realestate/plots/ for a plot,
/realestate/leisuresale/ (and anything else) for a cabin."""
from django.db import migrations, models


def sort_ads(apps, schema_editor):
    FinnAd = apps.get_model('core', 'FinnAd')
    FinnAd.objects.exclude(url__contains='/plots/').update(category='cabin')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_finn_ads_brakastolen'),
    ]

    operations = [
        migrations.AddField(
            model_name='finnad',
            name='category',
            field=models.CharField(choices=[('plot', 'Tomt'), ('cabin', 'Hytte')], default='plot', max_length=10, verbose_name='Tomt eller hytte'),
        ),
        migrations.RunPython(sort_ads, migrations.RunPython.noop),
    ]
