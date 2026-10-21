from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from apps.blog import views as blog_views
from apps.core import views
from apps.core.sitemaps import SITEMAPS

handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'


def moved_to(name):
    """A permanent (301) redirect to a named page, so old links keep their Google ranking."""
    return RedirectView.as_view(pattern_name=name, permanent=True, query_string=False)


urlpatterns = [
    # Pages
    path('', views.hjemme, name='hjemme'),
    path('tomter/', views.tomter, name='tomter'),
    path('hytter/', views.hytter, name='hytter'),
    path('om-vaset/', views.om_vaset, name='om_vaset'),
    path('aktiviteter/', views.aktiviteter, name='aktiviteter'),
    path('om-oss/', views.om_oss, name='om_oss'),
    path('nyheter/', blog_views.nyheter, name='nyheter'),
    path('nyheter/<int:pk>/<slug:slug>/', blog_views.nyhet_detail, name='nyhet_detail'),
    path('kontakt/', views.kontakt, name='kontakt'),
    path('personvern/', views.personvern, name='personvern'),

    # SEO files
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('llms.txt', views.llms_txt, name='llms_txt'),
    path('llms-full.txt', views.llms_full_txt, name='llms_full_txt'),

    # Old URLs from the previous WordPress website – permanent redirects keep their Google ranking.
    # The full list with reasons is in CLIENT-BRIEF.md ("Page map").
    path('oversiktskart/', moved_to('tomter')),
    path('vare-finn-annonser/', moved_to('hytter')),
    path('personvernerklaering/', moved_to('personvern')),
    path('reguleringsplan-vedtatt/', moved_to('nyheter')),
    path('skogsavvirkning-pabegynt/', moved_to('nyheter')),
    path('baerar-i-ar/', moved_to('nyheter')),
    path('category/ukategorisert/', moved_to('nyheter')),
    path('author/webmaster/', moved_to('nyheter')),
    path('feed/', moved_to('nyheter')),
    path('wp-sitemap.xml', moved_to('sitemap')),
    re_path(r'^wp-sitemap-[\w-]+\.xml$', moved_to('sitemap')),
    # Leftover demo pages from the WordPress theme
    re_path(r'^portfolio(?:_cat)?/[\w-]+/?$', moved_to('hytter')),
    path('page_category/classic/', moved_to('hjemme')),
    path('classic-help-center/', moved_to('hjemme')),
    path('page-404-custom/', moved_to('hjemme')),

    # The project pages were replaced by the suppliers on the Hytter page
    path('prosjekter/', moved_to('hytter')),
    re_path(r'^prosjekter/[\w-]+/(?:deling\.jpg)?$', moved_to('hytter')),
    # Browsers ask for /favicon.ico by themselves (e.g. on the sitemap), whatever the page links to
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon/favicon.ico', permanent=True)),

    path('dashboard/', include('apps.dashboard.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    # On the live server nginx serves /media/ directly
    urlpatterns += [
        re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'), serve, {'document_root': settings.MEDIA_ROOT}),
    ]
