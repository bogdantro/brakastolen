"""Allowlist HTML sanitizer for the dashboard's rich-text fields.

Only simple formatting survives (bold, italics, headings, lists, links);
everything else – scripts, styles, event handlers, unknown tags – is dropped.
"""
import re
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'a', 'h2', 'h3', 'blockquote'}
VOID_TAGS = {'br'}
# Content inside these is removed entirely, not just the tags.
DROP_CONTENT_TAGS = {'script', 'style', 'iframe', 'object', 'embed', 'template', 'noscript'}
SAFE_URL = re.compile(r'^(https?://|mailto:|tel:|/|#)', re.IGNORECASE)
TAG_RE = re.compile(r'<[a-zA-Z/][^>]*>')
EMPTY_BLOCK_RE = re.compile(r'<(p|h2|h3|li)>(\s|<br>|&nbsp;|\xa0)*</\1>')


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open_tags = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return
        if tag == 'b':
            tag = 'strong'
        elif tag == 'i':
            tag = 'em'
        attr_str = ''
        if tag == 'a':
            href = (dict(attrs).get('href') or '').strip()
            if not SAFE_URL.match(href):
                return
            attr_str = f' href="{escape(href, quote=True)}"'
            if href.lower().startswith('http'):
                attr_str += ' target="_blank" rel="noopener nofollow"'
        if tag in ('li', 'p') and self.open_tags and self.open_tags[-1] == tag:
            self.out.append(f'</{self.open_tags.pop()}>')
        self.out.append(f'<{tag}{attr_str}>')
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag == 'br' and not self.skip_depth:
            self.out.append('<br>')

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        tag = {'b': 'strong', 'i': 'em'}.get(tag, tag)
        if tag in self.open_tags:
            # Close anything left open inside it so the markup stays balanced.
            while self.open_tags:
                last = self.open_tags.pop()
                self.out.append(f'</{last}>')
                if last == tag:
                    break

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(escape(data, quote=False))

    def result(self):
        while self.open_tags:
            self.out.append(f'</{self.open_tags.pop()}>')
        return ''.join(self.out)


def sanitize_html(value):
    if not value:
        return ''
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    html = parser.result().strip()
    # The editor leaves empty paragraphs behind (<p></p>, <p><br></p>).
    html = EMPTY_BLOCK_RE.sub('', html).strip()
    # An editor that has been emptied leaves behind things like <p><br></p>.
    if not TAG_RE.sub('', html).strip():
        return ''
    return html


def looks_like_html(value):
    return bool(value) and bool(TAG_RE.search(value))
