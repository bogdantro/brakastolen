"""Small text helpers shared by models, templates and seed commands."""
from django.utils.text import slugify

# Django's slugify drops æ and ø entirely ("Øyer" -> "yer"), so spell them out first
NORWEGIAN = str.maketrans({'æ': 'ae', 'ø': 'o', 'å': 'a', 'Æ': 'Ae', 'Ø': 'O', 'Å': 'A'})


def norwegian_slugify(value):
    """'Hytte på Brakastølen' -> 'hytte-pa-brakastolen'."""
    return slugify(str(value).translate(NORWEGIAN))


def format_nok(amount):
    """900000 -> '900 000 kr'. None or 0 -> ''."""
    if not amount:
        return ''
    return f'{int(amount):,} kr'.replace(',', ' ')


def format_number(value):
    """2053 -> '2 053'. None -> ''."""
    if value in (None, ''):
        return ''
    return f'{int(value):,}'.replace(',', ' ')
