"""Number formatting for the dashboard's templates."""
from django import template

from apps.core.text import format_number

register = template.Library()


@register.filter
def thousands(value):
    """1500000 -> '1 500 000' (for price inputs). None -> ''."""
    return format_number(value)


@register.filter
def millions(value):
    """68400000 -> '68,4 mill. kr'; under a million -> '900 000 kr'."""
    if not value:
        return '0 kr'
    if value < 1_000_000:
        return f'{format_number(value)} kr'
    text = f'{value / 1_000_000:.1f}'.replace('.', ',').replace(',0', '')
    return f'{text} mill. kr'
