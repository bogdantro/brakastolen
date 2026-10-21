from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import Blog

# Every public page with a fixed URL. llms.py uses the same list.
PUBLIC_PAGES = [
    'hjemme', 'tomter', 'hytter', 'om_vaset', 'aktiviteter',
    'om_oss', 'nyheter', 'kontakt', 'personvern',
]


class SiteSitemap(Sitemap):
    """Always use the public domain, whatever the Site table or request host says."""
    protocol = urlparse(settings.SITE_URL).scheme or 'https'

    def get_domain(self, site=None):
        return urlparse(settings.SITE_URL).netloc


class PageSitemap(SiteSitemap):
    changefreq = 'monthly'

    def items(self):
        return PUBLIC_PAGES

    def location(self, item):
        return reverse(item)


class BlogSitemap(SiteSitemap):
    changefreq = 'monthly'

    def items(self):
        return Blog.objects.public()

    def lastmod(self, post):
        return post.updated_at


SITEMAPS = {
    'pages': PageSitemap,
    'blog': BlogSitemap,
}
