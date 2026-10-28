"""Builds llms.txt (a short summary) and llms-full.txt (the readable text of every public
page, as plain Markdown) for AI assistants.

Pages are rendered through their normal views, so llms-full.txt always matches what visitors see.
"""
from html.parser import HTMLParser

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory
from django.urls import resolve, reverse

from apps.blog.models import Blog

from .models import CostItem, FieldDocument, FinnAd, Plot
from .seo import BUSINESS, FAQ, PARTNERS, site_url
from .sitemaps import PUBLIC_PAGES

SKIP_TAGS = {'script', 'style', 'noscript', 'svg', 'video', 'form', 'button', 'input', 'textarea', 'select', 'label', 'template'}
BLOCK_TAGS = {'p', 'div', 'section', 'article', 'header', 'footer', 'aside', 'blockquote', 'br', 'tr', 'dt', 'dd'}
HEADINGS = {'h1': '#', 'h2': '##', 'h3': '###', 'h4': '####'}

# (page name, short description) for the llms.txt link list
PAGE_SUMMARIES = [
    ('tomter', 'Hyttetomter på Brakastølen: priser, hyttegrender, høyde over havet og tomtekart.'),
    ('hytter', 'Nøkkelferdige hytter fra Tinde Hytter, Leve Hytter og andre samarbeidspartnere.'),
    ('om_vaset', 'Om Vaset og Brakastølen: beliggenhet, natur og avstander.'),
    ('aktiviteter', 'Alpint, langrenn og sykkel på Vaset.'),
    ('om_oss', 'Om utbygger Tranberg Utvikling AS og samarbeidspartnere.'),
    ('nyheter', 'Nyheter fra Brakastølen.'),
    ('kontakt', 'Be om prospekt eller avtal visning.'),
]


class MainText(HTMLParser):
    """Collect the text inside <main> as Markdown-ish lines."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.skip = 0
        self.lines = []
        self.current = ''
        self.prefix = ''

    def flush(self):
        # Soft hyphens only help line-breaking in the browser; remove them from the text
        text = ' '.join(self.current.replace('­', '').split())
        # Skip lines that are only numbering, like "01"
        if text.isdigit():
            text = ''
        if text:
            self.lines.append(self.prefix + text)
        self.current = ''
        self.prefix = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self.in_main = True
            return
        if not self.in_main:
            return
        if tag in SKIP_TAGS:
            self.skip += 1
            return
        if tag in HEADINGS:
            self.flush()
            self.lines.append('')
            self.prefix = HEADINGS[tag] + ' '
        elif tag == 'li':
            self.flush()
            self.prefix = '- '
        elif tag in BLOCK_TAGS:
            self.flush()

    def handle_endtag(self, tag):
        if tag == 'main':
            self.flush()
            self.in_main = False
            return
        if not self.in_main:
            return
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if tag in HEADINGS or tag == 'li' or tag in BLOCK_TAGS:
            self.flush()

    def handle_data(self, data):
        if self.in_main and not self.skip:
            self.current += ' ' + data


def page_text(path):
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    request.session = SessionStore()
    match = resolve(path)
    response = match.func(request, *match.args, **match.kwargs)
    if hasattr(response, 'render'):
        response.render()
    if response.status_code != 200:
        return ''
    parser = MainText()
    parser.feed(response.content.decode('utf-8'))
    parser.flush()

    # Drop repeated lines (buttons and labels that appear twice) and extra blank lines
    lines, seen = [], set()
    for line in parser.lines:
        if line and not line.startswith('#'):
            if line in seen:
                continue
            seen.add(line)
        if line == '' and (not lines or lines[-1] == ''):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()


def fact_lines():
    b = BUSINESS
    return [
        f"- Utbygger og grunneier: {b['company']} (org.nr. {b['org_number_display']})",
        f"- {b['manager_title']}: {b['manager']}",
        f"- {b['contact_title']}: {b['contact_name']}, telefon {b['phone_display']}",
        f"- Telefon: {b['phone_display']}",
        f"- E-post: {b['email']}",
        f"- Beliggenhet: {b['place_name']}, {b['municipality']} kommune, {b['region']}",
        f"- Forretningsadresse: {b['street']}, {b['postal_code']} {b['city']}",
        f"- Tomter fra: {b['price_from_display']} + omkostninger",
        f"- Høyde: {b['altitude']}",
        f"- Avstand: Fagernes {b['distances']['Fagernes']}, Oslo {b['distances']['Oslo']}",
    ]


def build_llms_summary():
    url = site_url()
    b = BUSINESS
    lines = [
        f"# {b['name']} – {b['tagline']}",
        '',
        f"> {b['description']}",
        '',
        'Brakastølen ligger høyt og flott ved Panoramavegen mellom Valdres og Hemsedal, med åpent fjellandskap '
        'og utsikt mot Jotunheimen. Tomtene fordeler seg på mindre hyttegrender, og det er ingen byggeklausul. '
        f"Utbygger er {b['company']}, som også leverer nøkkelferdige hytter sammen med faste samarbeidspartnere.",
        '',
        '## Kontakt',
        *fact_lines(),
        f"- Kontaktskjema og visning: {url}{reverse('kontakt')}",
        f"- Fullstendig tekstinnhold for AI: {url}/llms-full.txt",
        '',
        '## Sider',
    ]
    lines += [f"- [{name.replace('_', ' ').capitalize()}]({url}{reverse(name)}): {text}" for name, text in PAGE_SUMMARIES]
    lines.append('')

    available = Plot.objects.public().available().count()
    if available:
        lines += ['## Ledige tomter', f'- {available} ledige tomter akkurat nå: {url}{reverse("tomter")}', '']

    costs = list(CostItem.objects.all())
    if costs:
        lines.append('## Omkostninger i tillegg til tomteprisen')
        lines += [f'- {c.label}: {c.amount_display}' for c in costs]
        lines.append('')

    documents = FieldDocument.objects.filter(is_published=True)
    if documents:
        lines.append('## Reguleringsplan')
        lines += [f'- [{doc.title}]({url}{doc.file.url})' for doc in documents]
        lines.append('')

    ads = FinnAd.objects.filter(is_active=True)
    plot_ads = [f'- [{ad.title}]({ad.url})' for ad in ads if ad.category == 'plot']
    plot_ads += [f'- [Hyttetomt {plot.number}]({plot.finn_url})'
                 for plot in Plot.objects.public().available().exclude(finn_url='')]
    cabin_ads = [f'- [{ad.title}]({ad.url})' for ad in ads if ad.category == 'cabin']
    for heading, items in [('## Tomter på FINN', plot_ads), ('## Hytter på FINN', cabin_ads)]:
        if items:
            lines += [heading, *items, '']

    lines.append('## Samarbeidspartnere')
    lines += [f'- {role}: {name}' for role, name, _ in PARTNERS]
    lines.append('')

    lines.append('## Ofte stilte spørsmål')
    for item in FAQ:
        lines += [f"### {item['question']}", item['answer'], '']
    return '\n'.join(lines)


def build_llms_full():
    url = site_url()
    b = BUSINESS
    parts = [
        f"# {b['name']} – fullstendig innhold",
        '',
        f"> {b['description']}",
        '',
        f'Dette er hele tekstinnholdet på nettsiden, samlet for AI-assistenter. Kortversjon: {url}/llms.txt',
        '',
        '## Fakta',
        *fact_lines(),
        '',
    ]

    pages = [reverse(name) for name in PUBLIC_PAGES]
    pages += [post.get_absolute_url() for post in Blog.objects.public()]

    for path in pages:
        text = page_text(path)
        if not text:
            continue
        parts += ['---', '', f'Kilde: {url}{path}', '', text, '']
    return '\n'.join(parts)
