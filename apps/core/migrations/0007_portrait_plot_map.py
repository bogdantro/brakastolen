"""The plot map now stands upright like the map on the old website (720 × 1000) instead of
being turned a quarter (960 × 760). Moves every saved position and outline to the new drawing.

Both drawings come from the same site plan, so one exact transform covers every plot –
also plots the client placed by hand in the dashboard.
"""
import re

from django.db import migrations

# Old drawing: old = (OLD_TX - OLD_SCALE * y, OLD_TY + OLD_SCALE * x) for a point (x, y) of the plan
OLD_TX, OLD_TY, OLD_SCALE = 1065.883, -15.590, 1.38325
# New drawing: new = (NEW_TX + NEW_SCALE * x, NEW_TY + NEW_SCALE * y)
NEW_TX, NEW_TY, NEW_SCALE = -40.6838765, -116.5004091, 1.3462030
NUMBER = r'-?\d+(?:\.\d+)?'


def old_to_new(x, y):
    plan_x = (y - OLD_TY) / OLD_SCALE
    plan_y = (OLD_TX - x) / OLD_SCALE
    return NEW_TX + NEW_SCALE * plan_x, NEW_TY + NEW_SCALE * plan_y


def new_to_old(x, y):
    plan_x = (x - NEW_TX) / NEW_SCALE
    plan_y = (y - NEW_TY) / NEW_SCALE
    return OLD_TX - OLD_SCALE * plan_y, OLD_TY + OLD_SCALE * plan_x


def move_shape(shape, convert):
    """'M524.2 79.0 L…' -> the same outline in the other drawing (pairs of numbers after M/L)."""
    def replace(match):
        x, y = convert(float(match.group(1)), float(match.group(2)))
        return f'{match.group(0)[0]}{x:.1f} {y:.1f}'
    return re.sub(rf'[ML]\s*({NUMBER})[ ,]+({NUMBER})', replace, shape)


def move_plots(apps, convert, turn):
    Plot = apps.get_model('core', 'Plot')
    for plot in Plot.objects.exclude(map_x__isnull=True).exclude(map_y__isnull=True):
        x, y = convert(plot.map_x, plot.map_y)
        plot.map_x, plot.map_y = round(x, 1), round(y, 1)
        plot.map_shape = move_shape(plot.map_shape, convert) if plot.map_shape else ''
        # Hand-placed parcels were turned to fit the old drawing; undo the quarter turn
        plot.map_rotation = ((plot.map_rotation + turn + 180) % 360) - 180
        plot.save(update_fields=['map_x', 'map_y', 'map_shape', 'map_rotation'])


def forward(apps, schema_editor):
    move_plots(apps, old_to_new, -90)


def backward(apps, schema_editor):
    move_plots(apps, new_to_old, 90)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_plot_view_and_finn_link'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
