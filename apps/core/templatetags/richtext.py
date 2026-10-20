from django import template
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe

from apps.core.richtext import looks_like_html, sanitize_html

register = template.Library()


@register.filter
def rich(value):
    """Render a rich-text field. Older plain-text entries keep their line breaks."""
    if looks_like_html(value):
        return mark_safe(sanitize_html(value))
    # linebreaks() escapes the text itself before adding <p>/<br>.
    return mark_safe(linebreaks(value or '', autoescape=True))
