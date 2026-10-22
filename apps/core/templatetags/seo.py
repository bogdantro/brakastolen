"""Template tags that print structured data (JSON-LD) for search engines and AI assistants."""
import json

from django import template
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from apps.core import seo
from apps.core.richtext import sanitize_html

register = template.Library()


def render_jsonld(data):
    # '</' is escaped so text can never close the <script> tag early
    text = json.dumps(data, ensure_ascii=False, indent=None).replace('</', '<\\/')
    return mark_safe(f'<script type="application/ld+json">{text}</script>')


def plain(text, limit=None):
    """'<p>Fin <strong>tomt</strong></p>' -> 'Fin tomt', clipped at a word boundary.
    Sanitised first: strip_tags alone would keep the contents of a <script> tag."""
    text = ' '.join(strip_tags(sanitize_html(text or '')).split())
    if limit and len(text) > limit:
        text = text[:limit - 1].rsplit(' ', 1)[0] + '…'
    return text


def webpage(page_type, path, name):
    url = seo.absolute(path)
    return {
        '@type': page_type,
        '@id': url + '#webpage',
        'url': url,
        'name': name,
        'inLanguage': 'nb-NO',
        'isPartOf': {'@id': seo.site_url() + '/#website'},
        'about': {'@id': seo.organization_id()},
    }


@register.simple_tag
def schema_site():
    """Business, the cabin area and the website, printed on every page from base.html."""
    return render_jsonld(seo.graph(seo.business_schema(), seo.place_schema(), seo.website_schema()))


@register.simple_tag
def schema_breadcrumbs(*args):
    """{% schema_breadcrumbs "Nyheter" "/nyheter/" "Reguleringsplan vedtatt" "/nyheter/3/reguleringsplan-vedtatt/" %}"""
    items = list(zip(args[0::2], args[1::2]))
    return render_jsonld(seo.graph(seo.breadcrumb_schema(items)))


@register.simple_tag(takes_context=True)
def schema_service(context, name, description, service_type=''):
    path = context['request'].path
    return render_jsonld(seo.graph(
        seo.breadcrumb_schema([(name, path)]),
        seo.service_schema(name, description, path, service_type or None),
    ))


@register.simple_tag
def schema_faq():
    return render_jsonld(seo.graph(seo.faq_schema()))


@register.simple_tag
def schema_home():
    """Homepage: the page itself, the offer catalogue and the FAQ."""
    page = webpage('WebPage', '/', f"{seo.BUSINESS['name']} – hyttetomter på Vaset i Valdres")
    page['description'] = seo.BUSINESS['description']
    page['mainEntity'] = {'@id': seo.organization_id()}
    catalog = {
        '@type': 'OfferCatalog',
        '@id': seo.site_url() + '/#offers',
        'name': 'Tomter og hytter på Brakastølen',
        'itemListElement': [
            {
                '@type': 'Offer',
                'itemOffered': {'@type': 'Service', 'name': name, 'url': seo.absolute(reverse(url_name))},
                'seller': {'@id': seo.organization_id()},
            }
            for name, url_name in (('Hyttetomter', 'tomter'), ('Nøkkelferdige hytter', 'hytter'))
        ],
    }
    business = {'@id': seo.organization_id(), 'hasOfferCatalog': {'@id': seo.site_url() + '/#offers'}}
    return render_jsonld(seo.graph(page, business, catalog, seo.faq_schema()))


def plot_facts(plot):
    """Height and view as schema.org PropertyValues, for the plots that have them."""
    facts = []
    if plot.altitude:
        facts.append({'@type': 'PropertyValue', 'name': 'Høyde over havet', 'value': plot.altitude, 'unitText': 'moh.'})
    if plot.view_direction:
        facts.append({'@type': 'PropertyValue', 'name': 'Utsikt', 'value': plot.view_direction})
    return facts


@register.simple_tag
def schema_plots(plots):
    """Tomter page: each plot for sale as an Offer, plus the FAQ and breadcrumbs."""
    offers = []
    for plot in plots:
        if plot.status != 'available' or not plot.price:
            continue
        offers.append({
            '@type': 'Offer',
            'name': str(plot),
            'price': plot.price,
            'priceCurrency': 'NOK',
            'availability': 'https://schema.org/InStock',
            'seller': {'@id': seo.organization_id()},
            'itemOffered': {
                '@type': 'Accommodation',
                'name': f'Hyttetomt {plot.number}',
                'containedInPlace': {'@id': seo.place_id()},
                **({'floorSize': {'@type': 'QuantitativeValue', 'value': plot.area_m2, 'unitCode': 'MTK'}} if plot.area_m2 else {}),
                **({'additionalProperty': facts} if (facts := plot_facts(plot)) else {}),
            },
            **({'url': plot.finn_url} if plot.finn_url else {}),
        })
    page = webpage('CollectionPage', reverse('tomter'), 'Hyttetomter på Brakastølen')
    nodes = [page, seo.breadcrumb_schema([('Tomter', reverse('tomter'))]), seo.faq_schema()]
    if offers:
        nodes.append({'@type': 'OfferCatalog', 'name': 'Ledige hyttetomter', 'itemListElement': offers})
    return render_jsonld(seo.graph(*nodes))


@register.simple_tag
def schema_about():
    b = seo.BUSINESS
    page = webpage('AboutPage', reverse('om_oss'), f"Om {b['company']}")
    page['mainEntity'] = {'@id': seo.organization_id()}
    person = {
        '@type': 'Person',
        '@id': seo.site_url() + reverse('om_oss') + '#daglig-leder',
        'name': b['manager'],
        'jobTitle': b['manager_title'],
        'worksFor': {'@id': seo.organization_id()},
    }
    return render_jsonld(seo.graph(page, person, seo.breadcrumb_schema([('Om oss', reverse('om_oss'))])))


@register.simple_tag
def schema_contact():
    page = webpage('ContactPage', reverse('kontakt'), f"Kontakt {seo.BUSINESS['name']}")
    return render_jsonld(seo.graph(page, seo.breadcrumb_schema([('Kontakt', reverse('kontakt'))])))


def blog_posting(post, full=False):
    url = seo.absolute(post.get_absolute_url())
    data = {
        '@type': 'BlogPosting',
        '@id': url + '#article',
        'headline': post.title[:110],
        'description': post.meta_description or post.excerpt or plain(post.text, 160),
        'url': url,
        'mainEntityOfPage': url,
        'datePublished': post.created_at.isoformat(),
        'dateModified': post.updated_at.isoformat(),
        'inLanguage': 'nb-NO',
        'author': {'@type': 'Person', 'name': post.author} if post.author else {'@id': seo.organization_id()},
        'publisher': {'@id': seo.organization_id()},
    }
    if post.image:
        data['image'] = seo.absolute(post.image.url)
    if full:
        text = plain(post.text)
        data['articleBody'] = text
        data['wordCount'] = len(text.split())
    return data


@register.simple_tag
def schema_blog(posts):
    blog = {
        '@type': 'Blog',
        '@id': seo.site_url() + reverse('nyheter') + '#blog',
        'url': seo.absolute(reverse('nyheter')),
        'name': f"Nyheter – {seo.BUSINESS['name']}",
        'inLanguage': 'nb-NO',
        'publisher': {'@id': seo.organization_id()},
        'blogPost': [blog_posting(p) for p in posts],
    }
    return render_jsonld(seo.graph(blog, seo.breadcrumb_schema([('Nyheter', reverse('nyheter'))])))


@register.simple_tag
def schema_blog_post(post):
    crumbs = seo.breadcrumb_schema([('Nyheter', reverse('nyheter')), (post.title, post.get_absolute_url())])
    return render_jsonld(seo.graph(blog_posting(post, full=True), crumbs))
