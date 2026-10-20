from django.conf import settings

from .seo import BUSINESS, site_url


def seo(request):
    return {
        'site_url': site_url(),
        'business': BUSINESS,
        'ga_id': settings.GA_MEASUREMENT_ID,
        'allow_indexing': settings.ALLOW_INDEXING,
        'cookie_consent_name': settings.COOKIE_CONSENT_NAME,
    }
