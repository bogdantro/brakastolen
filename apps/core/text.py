"""Small text helpers shared by models, templates and seed commands."""
import re

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


def format_phone(raw):
    """'+47 91234567' -> ('912 34 567', '+4791234567'). Unknown formats are left as typed,
    with digits only (and a leading +) for the link."""
    raw = (raw or '').strip()
    digits = re.sub(r'\D', '', raw)
    if digits.startswith('0047'):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith('47'):
        digits = digits[2:]
    if len(digits) == 8:
        # Mobile numbers (4xx, 9xx) are written 3-2-3 in Norway, landlines 2-2-2-2
        if digits[0] in '49':
            display = f'{digits[:3]} {digits[3:5]} {digits[5:]}'
        else:
            display = f'{digits[:2]} {digits[2:4]} {digits[4:6]} {digits[6:]}'
        return display, f'+47{digits}'
    return raw, ('+' if raw.startswith('+') else '') + digits
