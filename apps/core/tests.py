import io
import json
import re
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.blog.models import Blog

from .models import Inquiry, Plot, PlotCategory, street_for_plot
from .richtext import sanitize_html
from .seo import BUSINESS
from .sitemaps import PUBLIC_PAGES
from .spam import is_trusted, make_form_token, spam_reason, untrusted_link_count
from .text import format_nok, norwegian_slugify

MEDIA_ROOT = tempfile.mkdtemp()


def image_file(name='photo.jpg', size=(40, 30), fmt='JPEG', color=(120, 140, 90)):
    """A real, tiny image Pillow can open."""
    buffer = io.BytesIO()
    mode = 'RGBA' if fmt == 'PNG' else 'RGB'
    Image.new(mode, size, color).save(buffer, fmt)
    content_type = 'image/png' if fmt == 'PNG' else 'image/jpeg'
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def make_form_token_in_past():
    """A signed 'form shown at' token from long ago – a person who took their time."""
    with mock.patch('apps.core.spam.time.time', return_value=1):
        return make_form_token()


def form_data(**kwargs):
    """A valid contact form post, filled in by a person a minute ago."""
    data = {
        'name': 'Kari Nordmann',
        'email': 'kari@example.no',
        'phone': '482 58 000',
        'interest': 'plot',
        'message': 'Vi vil gjerne komme på visning.',
        'consent': 'on',
        'hp_check': '',
        'form_ts': make_form_token_in_past(),
    }
    data.update(kwargs)
    return data


class MediaTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media = override_settings(MEDIA_ROOT=MEDIA_ROOT)
        cls._media.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media.disable()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------

class PageTests(MediaTestCase):
    def test_every_public_page_loads(self):
        for name in PUBLIC_PAGES:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_every_page_has_one_h1(self):
        for name in PUBLIC_PAGES:
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertEqual(html.count('<h1'), 1)

    def test_business_phone_comes_from_seo_business(self):
        response = self.client.get(reverse('kontakt'))
        self.assertContains(response, BUSINESS['phone_display'])
        self.assertContains(response, f'tel:{BUSINESS["phone"]}')

    def test_nav_has_the_avtal_visning_button(self):
        response = self.client.get('/')
        self.assertContains(response, 'Avtal visning')
        self.assertContains(response, f'{reverse("kontakt")}?interesse=viewing')

    def test_homepage_shows_hero_text_and_price(self):
        response = self.client.get('/')
        h1 = re.search(r'<h1>(.*?)</h1>', response.content.decode(), re.S).group(1)
        self.assertEqual(' '.join(re.sub(r'<[^>]+>', '', h1).split()), 'Stort utvalg av fantastiske tomter.')
        self.assertContains(response, '900 000 kr')

    def test_hero_images_are_read_from_the_folder_in_natural_order(self):
        from .views import natural_key
        self.assertEqual(sorted(['hero-10.jpg', 'hero-2.jpg'], key=natural_key), ['hero-2.jpg', 'hero-10.jpg'])

    def test_homepage_presents_the_cabin_suppliers_like_the_old_site(self):
        response = self.client.get('/')
        self.assertContains(response, 'Våre hytteleverandører')
        self.assertContains(response, 'https://www.tindehytter.no')
        self.assertContains(response, 'https://www.levehytter.no')

    def test_old_project_pages_redirect_to_the_suppliers(self):
        for old in ('/prosjekter/', '/prosjekter/ulven-hyttegrend/', '/prosjekter/ulven-hyttegrend/deling.jpg'):
            with self.subTest(url=old):
                response = self.client.get(old)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response['Location'], '/hytter/')

    def test_favicon_ico_points_to_the_real_icon(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response['Location'].endswith('images/favicon/favicon.ico'))

    def test_tomter_has_the_plot_picker_with_the_plots(self):
        Plot.objects.create(number='T10', price=900000, area_m2=1400)
        response = self.client.get(reverse('tomter'))
        self.assertContains(response, 'id="tomtevelger"')
        self.assertEqual([p['number'] for p in response.context['picker_plots']], ['T10'])
        self.assertIn('no-cache', response['Cache-Control'])


# ------------------------------------------------------------------
# Old URLs from the WordPress site
# ------------------------------------------------------------------

class RedirectTests(TestCase):
    OLD_URLS = {
        '/oversiktskart/': '/tomter/',
        '/vare-finn-annonser/': '/hytter/',
        '/personvernerklaering/': '/personvern/',
        '/reguleringsplan-vedtatt/': '/nyheter/',
        '/skogsavvirkning-pabegynt/': '/nyheter/',
        '/baerar-i-ar/': '/nyheter/',
        '/category/ukategorisert/': '/nyheter/',
        '/author/webmaster/': '/nyheter/',
        '/feed/': '/nyheter/',
        '/wp-sitemap.xml': '/sitemap.xml',
        '/wp-sitemap-posts-page-1.xml': '/sitemap.xml',
        '/portfolio/centered-gallery/': '/hytter/',
        '/portfolio_cat/web/': '/hytter/',
        '/page_category/classic/': '/',
        '/classic-help-center/': '/',
        '/page-404-custom/': '/',
    }

    def test_old_urls_redirect_permanently(self):
        for old, new in self.OLD_URLS.items():
            with self.subTest(url=old):
                response = self.client.get(old)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response['Location'], new)

    def test_redirect_drops_old_query_strings(self):
        response = self.client.get('/oversiktskart/?fbclid=abc')
        self.assertEqual(response['Location'], '/tomter/')


# ------------------------------------------------------------------
# SEO files, structured data and headers
# ------------------------------------------------------------------

@override_settings(SITE_URL='https://www.xn--brakastlen-6cb.no', ALLOW_INDEXING=True)
class SeoTests(MediaTestCase):
    def test_robots_allows_ai_crawlers_and_points_to_sitemap(self):
        text = self.client.get('/robots.txt').content.decode()
        self.assertIn('User-agent: ClaudeBot', text)
        self.assertIn('User-agent: GPTBot', text)
        self.assertIn('Disallow: /dashboard/', text)
        self.assertIn('Sitemap: https://www.xn--brakastlen-6cb.no/sitemap.xml', text)

    @override_settings(ALLOW_INDEXING=False)
    def test_staging_blocks_everything(self):
        self.assertEqual(self.client.get('/robots.txt').content.decode(), 'User-agent: *\nDisallow: /\n')
        response = self.client.get('/')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    @override_settings(ALLOW_INDEXING=True)
    def test_live_site_is_indexable(self):
        response = self.client.get('/')
        self.assertNotIn('X-Robots-Tag', response)
        self.assertContains(response, 'index, follow, max-image-preview:large')

    def test_canonical_uses_site_url_not_request_host(self):
        response = self.client.get('/tomter/', HTTP_HOST='localhost')
        self.assertContains(response, '<link rel="canonical" href="https://www.xn--brakastlen-6cb.no/tomter/">')

    def test_sitemap_uses_site_url_and_lists_published_news(self):
        Blog.objects.create(title='Publisert nyhet', text='<p>Tekst</p>')
        draft = Blog.objects.create(title='Utkast nyhet', text='<p>Tekst</p>', is_published=False)
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('https://www.xn--brakastlen-6cb.no/tomter/', xml)
        self.assertNotIn('/prosjekter/', xml)
        self.assertIn('publisert-nyhet', xml)
        self.assertNotIn(draft.slug, xml)
        self.assertNotIn('example.com', xml)

    def test_every_page_has_business_json_ld(self):
        html = self.client.get('/').content.decode()
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        types = [node.get('@type') for block in blocks for node in json.loads(block)['@graph']]
        self.assertIn('LocalBusiness', types)
        self.assertIn('FAQPage', types)
        self.assertIn('Place', types)

    def test_json_ld_escapes_closing_tags(self):
        Plot.objects.create(number='</script><script>alert(1)</script>', price=900000)
        html = self.client.get(reverse('tomter')).content.decode()
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertIn('<\\/script>', html)

    def test_llms_txt_has_contact_facts_and_faq(self):
        text = self.client.get('/llms.txt').content.decode()
        self.assertIn(BUSINESS['phone_display'], text)
        self.assertIn(BUSINESS['org_number_display'], text)
        self.assertIn('Er det byggeklausul på tomtene?', text)

    def test_llms_full_txt_has_the_text_of_the_pages(self):
        post = Blog.objects.create(title='Ulven hyttegrend', text='<p>Ti tomter.</p>')
        cache.clear()
        text = self.client.get('/llms-full.txt').content.decode()
        self.assertIn('Kilde: https://www.xn--brakastlen-6cb.no/tomter/', text)
        self.assertIn('Panoramavegen', text)
        self.assertIn('Tinde Hytter', text)
        self.assertIn(post.title, text)

    def test_security_headers_are_set(self):
        response = self.client.get('/')
        self.assertIn("default-src 'self'", response['Content-Security-Policy'])
        self.assertIn('camera=()', response['Permissions-Policy'])
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_no_analytics_and_no_cookie_banner_without_ga_id(self):
        html = self.client.get('/').content.decode()
        self.assertNotIn('googletagmanager', html)
        self.assertNotIn('cookieBanner', html)

    @override_settings(GA_MEASUREMENT_ID='G-TEST123')
    def test_cookie_banner_and_consent_defaults_with_ga_id(self):
        response = self.client.get('/')
        self.assertContains(response, 'cookieBanner')
        self.assertContains(response, "analytics_storage: 'denied'")


# ------------------------------------------------------------------
# Contact form
# ------------------------------------------------------------------

class ContactFormTests(MediaTestCase):
    url = reverse('kontakt')

    def test_valid_inquiry_is_saved_and_redirects_with_thank_you(self):
        response = self.client.post(self.url, form_data(), follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, 'Takk for henvendelsen')
        inquiry = Inquiry.objects.get()
        self.assertEqual(inquiry.name, 'Kari Nordmann')
        self.assertTrue(inquiry.consent)
        self.assertFalse(inquiry.is_spam)

    def test_phone_is_optional(self):
        self.client.post(self.url, form_data(phone=''))
        self.assertEqual(Inquiry.objects.get().phone, '')

    def test_invalid_phone_is_rejected_in_norwegian(self):
        response = self.client.post(self.url, form_data(phone='ring meg'))
        self.assertContains(response, 'Skriv inn et gyldig telefonnummer')
        self.assertFalse(Inquiry.objects.exists())

    def test_consent_is_required(self):
        data = form_data()
        del data['consent']
        response = self.client.post(self.url, data)
        self.assertContains(response, 'Du må godta personvernerklæringen')
        self.assertFalse(Inquiry.objects.exists())

    def test_form_shown_again_keeps_what_was_typed(self):
        response = self.client.post(self.url, form_data(email='ikke-en-epost'))
        self.assertContains(response, 'Vi vil gjerne komme på visning.')

    def test_interest_is_prefilled_from_the_link(self):
        response = self.client.get(self.url + '?interesse=viewing')
        self.assertEqual(response.context['form'].initial['interest'], 'viewing')

    def test_unknown_interest_in_the_link_is_ignored(self):
        response = self.client.get(self.url + '?interesse=hack')
        self.assertNotIn('interest', response.context['form'].initial)

    def test_contact_page_is_never_cached(self):
        self.assertIn('no-cache', self.client.get(self.url)['Cache-Control'])

    def test_honeypot_marks_spam_but_looks_successful(self):
        response = self.client.post(self.url, form_data(hp_check='spam'), follow=True)
        self.assertContains(response, 'Takk for henvendelsen')
        inquiry = Inquiry.objects.get()
        self.assertTrue(inquiry.is_spam)
        self.assertEqual(inquiry.spam_reason, 'honeypot')

    def test_missing_token_marks_spam(self):
        self.client.post(self.url, form_data(form_ts=''))
        self.assertEqual(Inquiry.objects.get().spam_reason, 'missing token')

    def test_forged_token_marks_spam(self):
        self.client.post(self.url, form_data(form_ts='123:forged'))
        self.assertTrue(Inquiry.objects.get().is_spam)

    def test_submitted_too_fast_marks_spam(self):
        with mock.patch('apps.core.spam.time.time', return_value=1_000_000):
            token = make_form_token()
        with mock.patch('apps.core.spam.time.time', return_value=1_000_001):
            self.client.post(self.url, form_data(form_ts=token))
        self.assertEqual(Inquiry.objects.get().spam_reason, 'too fast')

    def test_one_soft_signal_alone_is_fine(self):
        self.client.post(self.url, form_data(message='Hei! Vi vurderer en tomt. https://example.com https://test.com'))
        self.assertFalse(Inquiry.objects.get().is_spam)

    def test_two_soft_signals_mark_spam(self):
        self.client.post(self.url, form_data(
            name='Cheap SEO https://spam.example',
            message='Best SEO backlinks https://a.example https://b.example',
        ))
        self.assertTrue(Inquiry.objects.get().is_spam)

    def test_rate_limit_alone_is_fine(self):
        with mock.patch('apps.core.views.over_rate_limit', return_value=True):
            self.client.post(self.url, form_data())
        self.assertFalse(Inquiry.objects.get().is_spam)

    def test_csrf_failure_gives_the_form_back_with_the_text(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, form_data(message='Teksten min skal ikke forsvinne'))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Teksten min skal ikke forsvinne', status_code=403)
        self.assertContains(response, 'trykk «Send» én gang til', status_code=403)
        self.assertContains(response, 'csrfmiddlewaretoken', status_code=403)

    def test_site_sends_no_email(self):
        self.client.post(self.url, form_data())
        self.assertEqual(Inquiry.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)


class SpamRuleTests(TestCase):
    def test_missing_space_after_full_stop_is_fine(self):
        self.assertEqual(untrusted_link_count('Fin tomt.Har dere visning?'), 0)

    def test_initial_in_name_is_not_a_link(self):
        self.assertEqual(untrusted_link_count('Ola N.Nordmann'), 0)

    def test_finn_and_own_site_links_do_not_count(self):
        self.assertEqual(untrusted_link_count('https://www.finn.no/realestate/123 www.brakastolen.no'), 0)

    def test_lookalike_domain_is_not_trusted(self):
        self.assertFalse(is_trusted('https://evilfinn.no/x'))
        self.assertFalse(is_trusted('https://finn.no.evil.com/x'))

    def test_html_links_always_count(self):
        self.assertEqual(untrusted_link_count('<a href="https://finn.no">x</a>'), 1)

    def test_foreign_script_alone_is_fine(self):
        data = {'name': 'Олена', 'message': 'Добрий день, цікавить ділянка'}
        self.assertEqual(spam_reason(data, make_form_token_in_past()), '')


# ------------------------------------------------------------------
# Images, rich text and helpers
# ------------------------------------------------------------------

class ImageTests(MediaTestCase):
    def test_new_news_photo_is_shrunk(self):
        post = Blog.objects.create(title='Stort bilde', text='<p>x</p>', image=image_file('stort.jpg', size=(2600, 1800)))
        with Image.open(post.image.path) as image:
            self.assertLessEqual(max(image.size), 2000)
            self.assertEqual(image.format, 'JPEG')  # also the share image: some apps don't show WebP

    def test_existing_photo_is_not_recompressed_on_edit(self):
        post = Blog.objects.create(title='Bilde', text='<p>x</p>', image=image_file())
        name = post.image.name
        post.title = 'Nytt navn'
        post.save()
        post.refresh_from_db()
        self.assertEqual(post.image.name, name)


class RichTextTests(TestCase):
    def test_scripts_and_their_content_are_removed(self):
        self.assertEqual(sanitize_html('<p>Hei<script>alert(1)</script></p>'), '<p>Hei</p>')

    def test_javascript_links_are_dropped(self):
        self.assertNotIn('javascript', sanitize_html('<a href="javascript:alert(1)">x</a>'))

    def test_external_links_open_safely(self):
        self.assertIn('rel="noopener nofollow"', sanitize_html('<a href="https://finn.no">Finn</a>'))

    def test_bold_becomes_strong(self):
        self.assertEqual(sanitize_html('<b>fet</b>'), '<strong>fet</strong>')

    def test_empty_editor_gives_empty_string(self):
        self.assertEqual(sanitize_html('<p><br></p>'), '')


class HelperTests(MediaTestCase):
    def test_norwegian_slugify_keeps_ae_oe_aa(self):
        self.assertEqual(norwegian_slugify('Hytte på Brakastølen'), 'hytte-pa-brakastolen')

    def test_format_nok(self):
        self.assertEqual(format_nok(900000), '900 000 kr')
        self.assertEqual(format_nok(None), '')

    def test_plot_group_name_is_its_category(self):
        self.assertEqual(Plot(number='1', category=PlotCategory(name='Byggetrinn 1')).group_name, 'Byggetrinn 1')
        self.assertEqual(Plot(number='2').group_name, '')

    def test_plot_street_follows_the_clients_number_ranges(self):
        self.assertEqual(street_for_plot('11'), 'Brakastølvegen')
        self.assertEqual(street_for_plot('13'), 'Brakastøllie')
        self.assertEqual(street_for_plot('28'), 'Brakastøllie')
        self.assertEqual(street_for_plot('29'), 'Nye Øyevegen')
        self.assertEqual(street_for_plot('63'), 'Øyebakkin')
        self.assertEqual(street_for_plot('66'), 'Nye Øyevegen')

    def test_plot_outside_the_ranges_gets_no_street(self):
        self.assertEqual(street_for_plot('67'), '')
        self.assertEqual(street_for_plot('T10'), '')


# ------------------------------------------------------------------
# Error pages
# ------------------------------------------------------------------

@override_settings(DEBUG=False)
class ErrorPageTests(TestCase):
    def test_404_helps_the_visitor_on(self):
        response = self.client.get('/finnes-ikke/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Vi fant ikke siden', status_code=404)
        self.assertContains(response, BUSINESS['phone_display'], status_code=404)

    def test_500_page_renders(self):
        from django.test import RequestFactory
        from .views import custom_500
        request = RequestFactory().get('/')
        request.user = mock.Mock(is_authenticated=False)
        response = custom_500(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn('Noe gikk galt', response.content.decode())

    def test_500_falls_back_when_full_page_breaks(self):
        from django.test import RequestFactory
        from .views import custom_500
        with mock.patch('apps.core.views.render', side_effect=RuntimeError('broken template')), \
                self.assertLogs('apps.core.views', level='ERROR'):
            response = custom_500(RequestFactory().get('/'))
        self.assertEqual(response.status_code, 500)
        self.assertIn(BUSINESS['phone_display'], response.content.decode())


# ------------------------------------------------------------------
# Plot picker on the homepage
# ------------------------------------------------------------------

class PlotPickerTests(MediaTestCase):
    def picker_data(self):
        html = self.client.get('/').content.decode()
        match = re.search(r'<script id="plot-picker-data" type="application/json">(.*?)</script>', html, re.S)
        return json.loads(match.group(1))

    def test_picker_lists_the_plots_with_map_positions_and_outlines(self):
        group = PlotCategory.objects.create(name='Byggetrinn 1')
        Plot.objects.create(category=group, number='T10', price=900000, area_m2=1400, map_x=200, map_y=300,
                            map_shape='M190 290 L210 290 L210 310 Z')
        data = self.picker_data()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['number'], 'T10')
        self.assertEqual((data[0]['x'], data[0]['y']), (200, 300))
        self.assertEqual(data[0]['group'], 'Byggetrinn 1')
        self.assertEqual(data[0]['shape'], 'M190 290 L210 290 L210 310 Z')

    def test_picker_has_height_view_and_finn_link(self):
        Plot.objects.create(number='12', altitude=980, view_direction='Sørvest mot Jotunheimen',
                            finn_url='https://www.finn.no/realestate/plots/ad.html?finnkode=1')
        data = self.picker_data()[0]
        self.assertEqual((data['altitude'], data['view']), (980, 'Sørvest mot Jotunheimen'))
        self.assertEqual(data['finnUrl'], 'https://www.finn.no/realestate/plots/ad.html?finnkode=1')

    def test_new_plot_gets_its_street_and_the_picker_shows_it(self):
        Plot.objects.create(number='40')
        self.assertEqual(self.picker_data()[0]['street'], 'Øyebakkin')

    def test_street_set_by_hand_is_kept(self):
        Plot.objects.create(number='40', street='Brakastølvegen')
        self.assertEqual(Plot.objects.get().street, 'Brakastølvegen')

    def test_map_can_only_be_dragged_when_zoomed_in(self):
        # plot-picker.js: zooming out below the frame and dragging at normal size are both off
        script = (Path(settings.BASE_DIR) / 'static' / 'js' / 'plot-picker.js').read_text(encoding='utf-8')
        self.assertIn('const ZOOM_MIN = 1;', script)
        self.assertIn('zoom <= ZOOM_MIN) return;', script)

    def test_plot_on_the_map_has_coordinates_for_the_sun_panel(self):
        Plot.objects.create(number='11', map_x=51.4, map_y=410.7)
        Plot.objects.create(number='99')
        on_map, off_map = sorted(self.picker_data(), key=lambda plot: plot['number'])
        self.assertEqual((on_map['lat'], on_map['lon']), (61.02056, 8.94288))
        self.assertEqual((off_map['lat'], off_map['lon']), (None, None))

    def test_map_road_names_follow_the_clients_street_list(self):
        """Brakastøllie was drawn on the road through plots 38–63, which is Øyebakkin."""
        plan = (Path(settings.BASE_DIR) / 'static' / 'images' / 'map' / 'brakastolen-plan.svg').read_text(encoding='utf-8')
        self.assertEqual(plan.count('>BRAKASTØLLIE</text>'), 1)
        self.assertEqual(plan.count('>ØYEBAKKIN</text>'), 2)
        self.assertIn('>BRAKASTØLVEGEN</text>', plan)
        self.assertIn('>NYE ØYEVEGEN</text>', plan)

    def test_plot_without_position_is_still_listed(self):
        Plot.objects.create(number='5')
        self.assertIsNone(self.picker_data()[0]['x'])

    def test_plot_number_cannot_break_out_of_the_json(self):
        Plot.objects.create(number='</script><b>')
        html = self.client.get('/').content.decode()
        self.assertNotIn('</script><b>', html)

    def test_contact_page_has_the_plot_picker_instead_of_the_faq(self):
        response = self.client.get(reverse('kontakt'))
        self.assertContains(response, 'id="tomtevelger"')
        self.assertNotContains(response, 'class="faq-list"')

    def test_homepage_is_never_cached(self):
        self.assertIn('no-cache', self.client.get('/')['Cache-Control'])

    def test_viewing_request_from_picker_is_saved_with_the_plot(self):
        plot = Plot.objects.create(number='21', price=1250000)
        response = self.client.post(reverse('kontakt'), form_data(plot=plot.pk, interest='viewing'),
                                    HTTP_ACCEPT='application/json')
        self.assertEqual(response.json()['ok'], True)
        inquiry = Inquiry.objects.get()
        self.assertEqual(inquiry.plot, plot)
        self.assertEqual(inquiry.interest, 'viewing')

    def test_picker_errors_come_back_as_json_per_field(self):
        response = self.client.post(reverse('kontakt'), form_data(email='feil'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['fields'])
        self.assertFalse(Inquiry.objects.exists())

    def test_unknown_plot_cannot_be_attached(self):
        response = self.client.post(reverse('kontakt'), form_data(plot=9999), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('plot', response.json()['fields'])

    def test_contact_page_without_plot_still_works(self):
        self.client.post(reverse('kontakt'), form_data())
        self.assertIsNone(Inquiry.objects.get().plot)


class HomepageContentTests(MediaTestCase):
    def test_every_supplier_has_a_card_with_photo_and_link(self):
        from .seo import FEATURED_SUPPLIERS, SUPPLIERS
        html = self.client.get('/').content.decode()
        for name, _, _, url, photo, *_ in FEATURED_SUPPLIERS + SUPPLIERS:
            with self.subTest(supplier=name):
                self.assertIn(name.replace('&', '&amp;'), html)
                self.assertIn(f'href="{url}"', html)
                self.assertIn(photo, html)
        self.assertIn('https://www.rhkvalitetsbygg.no', html)

    def test_footer_has_no_tranberg_group_and_the_logo_is_the_deer(self):
        html = self.client.get('/').content.decode()
        self.assertNotIn('Tranberg-gruppen', html)
        self.assertIn('images/logo/tranberg-hjort-hvit', html)
        self.assertIn('Vaset · Valdres', html)

    def test_hero_text_has_no_boxes_and_one_colour(self):
        html = self.client.get('/').content.decode()
        hero = html[html.index('<section class="hero"'):html.index('</section>')]
        self.assertNotIn('class="line', hero)
        # The heading's two lines are plain spans – no colour class on any of them
        self.assertEqual(re.findall(r'<span class="([^"]+)"', hero[hero.index('<h1'):hero.index('</h1>')]),
                         ['hero-line', 'hero-line'])
        self.assertNotIn('class="step', hero)

    def test_jotunheimen_line_lies_on_the_photo(self):
        html = self.client.get('/').content.decode()
        photo = html[html.index('<figure class="intro-photo"'):html.index('</figure>', html.index('<figure class="intro-photo"'))]
        self.assertIn('Her er det åpent og vilt landskap', photo)

    def test_every_activity_is_a_slide_in_the_carousel(self):
        from .views import HOME_ACTIVITIES
        response = self.client.get('/')
        self.assertContains(response, '<li class="activity-slide">', count=len(HOME_ACTIVITIES))
        self.assertContains(response, 'data-carousel-prev')
        self.assertContains(response, 'data-carousel-next')

    def test_footer_columns_are_company_contact_and_site(self):
        html = self.client.get('/').content.decode()
        footer = html[html.index('<footer'):]
        for text in ['Selskapsinfo', BUSINESS['company'], BUSINESS['street'], f"{BUSINESS['postal_code']} {BUSINESS['city']}",
                     BUSINESS['org_number_display'], 'Kontakt utbygger', 'Nettsiden']:
            with self.subTest(text=text):
                self.assertIn(text, footer)
        # The old line of text under the logo is gone
        self.assertNotIn('Hyttetomter 900–1050 meter over havet', footer)

    def test_prices_carry_the_omk_star(self):
        self.assertContains(self.client.get('/'), 'omk.*</a>')

    def test_the_star_leads_to_the_costs(self):
        response = self.client.get('/')
        self.assertContains(response, 'href="#omkostninger"')
        self.assertContains(response, 'id="omkostninger"')


class FieldInfoTests(MediaTestCase):
    """Costs, documents, maps and FINN ads under the plot map."""

    def setUp(self):
        super().setUp()
        call_command('seed_field_info', stdout=io.StringIO())

    def test_costs_are_listed_with_the_one_off_total_and_the_document_fee(self):
        html = self.client.get('/').content.decode()
        self.assertIn('Anleggsbidrag, engangsavgift', html)
        self.assertIn('90 000 kr', html)
        self.assertIn('Anleggsbidrag strøm', html)
        self.assertIn('I tillegg: dokumentavgift', html)
        self.assertIn('2,5 % av tomteprisen', html)

    def test_zoning_map_maps_and_finn_ad_are_linked(self):
        html = self.client.get('/').content.decode()
        self.assertIn('Reguleringsplan for Brakastølen – plankart', html)
        self.assertIn('Reguleringsbestemmelser for Brakastølen', html)
        self.assertIn('PDF, 7,2 MB', html)
        self.assertIn('norgeskart.no', html)
        self.assertIn('https://www.google.com/maps/search/', html)
        self.assertIn('finnkode=371502243', html)

    def test_every_tranberg_tinde_and_leve_ad_is_listed(self):
        """The client asked for all their FINN ads at Brakastølen, the cabin makers' included."""
        html = self.client.get('/').content.decode()
        for code in ['471023190', '470544998', '400288938', '280027233', '374061108', '339408992',
                     '426219618', '422876484', '276521226', '276520828', '284633576']:
            with self.subTest(finnkode=code):
                self.assertIn(f'finnkode={code}', html)
        self.assertIn('Tinde Hytter', html)
        self.assertIn('Leve Hytter', html)

    def test_only_available_plots_with_a_finn_link_join_the_ad_list(self):
        Plot.objects.create(number='77', finn_url='https://www.finn.no/ad.html?finnkode=77')
        Plot.objects.create(number='78', status='sold', finn_url='https://www.finn.no/ad.html?finnkode=78')
        html = self.client.get('/').content.decode()
        self.assertIn('finnkode=77', html)
        self.assertNotIn('finnkode=78', html)

    def test_seeding_twice_adds_nothing(self):
        from .models import CostItem, FieldDocument, FinnAd
        call_command('seed_field_info', stdout=io.StringIO())
        self.assertEqual((CostItem.objects.count(), FinnAd.objects.count(), FieldDocument.objects.count()), (6, 12, 2))

    def test_the_old_png_of_the_plan_is_replaced_by_the_pdf(self):
        from django.core.files.base import ContentFile
        from .models import FieldDocument
        old = FieldDocument(title='Reguleringskart – detaljregulering for Brakastølen')
        old.file.save('gammel.png', ContentFile(b'x'), save=True)
        call_command('seed_field_info', stdout=io.StringIO())
        self.assertFalse(FieldDocument.objects.filter(title='Reguleringskart – detaljregulering for Brakastølen').exists())

    def test_contact_page_names_the_land_seller(self):
        response = self.client.get(reverse('kontakt'))
        self.assertContains(response, 'Haakon B. Edland')
        self.assertContains(response, 'Tomteselger')


class SeedSiteTests(MediaTestCase):
    def test_one_command_fills_a_new_server_and_is_safe_to_repeat(self):
        from .models import CostItem, FieldDocument, FinnAd
        call_command('seed_site', stdout=io.StringIO())
        call_command('seed_site', stdout=io.StringIO())
        self.assertEqual(Plot.objects.count(), 54)
        self.assertEqual(Plot.objects.get(number='11').altitude, 985)
        self.assertEqual((CostItem.objects.count(), FinnAd.objects.count(), FieldDocument.objects.count()), (6, 12, 2))
        self.assertEqual(Blog.objects.count(), 6)


class StaticFilesTests(TestCase):
    def test_missing_collectstatic_never_crashes_a_page(self):
        """The live server once answered every page with a 500: «Missing staticfiles manifest entry
        for 'images/og/og-default.jpg'» – collectstatic had not been run."""
        from .storage import ForgivingManifestStorage
        storage = ForgivingManifestStorage(location=tempfile.mkdtemp())
        self.assertRegex(storage.url('images/og/og-default.jpg'), r'^/static/images/og/og-default\.jpg\?v=[0-9a-f]{12}$')

    def collect(self, css):
        """A static/ folder with one stylesheet, collected into a staticfiles/ folder.
        Returns (source file, storage reading that staticfiles/ folder)."""
        from .storage import ForgivingManifestStorage
        source_dir, root = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, source_dir)
        self.addCleanup(shutil.rmtree, root)
        source = Path(source_dir) / 'site.css'
        source.write_text(css, encoding='utf-8')
        overrides = override_settings(STATIC_ROOT=root, STATICFILES_DIRS=[source_dir], STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'apps.core.storage.ForgivingManifestStorage'},
        })
        overrides.enable()
        self.addCleanup(overrides.disable)
        call_command('collectstatic', interactive=False, verbosity=0)
        return source, ForgivingManifestStorage(location=root)

    def test_collected_file_gets_its_hashed_name(self):
        _, storage = self.collect('body { color: red; }')
        self.assertRegex(storage.url('site.css'), r'^/static/site\.[0-9a-f]{12}\.css$')

    def test_file_changed_after_collectstatic_is_never_served_stale(self):
        """An update without collectstatic used to keep every visitor on the old, year-cached CSS."""
        source, storage = self.collect('body { color: red; }')
        old_url = storage.url('site.css')
        source.write_text('body { color: blue; }', encoding='utf-8')
        with self.assertLogs('apps.core.storage', level='WARNING'):
            new_url = storage.url('site.css')
        self.assertRegex(new_url, r'^/static/site\.css\?v=[0-9a-f]{12}$')
        self.assertNotEqual(old_url, new_url)


class GeoTests(TestCase):
    def test_plan_point_becomes_coordinates_at_brakastolen(self):
        from .geo import plan_to_latlon
        self.assertEqual(plan_to_latlon(51.4, 410.7), (61.02056, 8.94288))

    def test_plots_13_to_28_lie_at_the_brakastollie_addresses(self):
        """The first fit put every plot ~175 m off. Kartverket's 16 addresses on Brakastøllie
        (one per plot 13–28) average 61.01774 N, 8.94588 E."""
        import math
        from .geo import plan_to_latlon
        data = json.loads((Path(__file__).parent / 'data' / 'brakastolen-plots.json').read_text(encoding='utf-8'))
        plots = [p for p in data['plots'] if 13 <= int(p['number']) <= 28]
        lat, lon = plan_to_latlon(sum(p['map_x'] for p in plots) / len(plots), sum(p['map_y'] for p in plots) / len(plots))
        metres = math.hypot((lat - 61.01774) * 111195, (lon - 8.94588) * 111195 * math.cos(math.radians(61.0177)))
        self.assertLess(metres, 50)

    def test_plot_on_the_map_gets_a_sun_link(self):
        plot = Plot(number='11', map_x=51.4, map_y=410.7)
        self.assertEqual(plot.sun_url, 'https://www.suncalc.org/#/61.02056,8.94288,17')
        self.assertEqual(Plot(number='99').sun_url, '')

    def test_business_coordinates_are_at_the_field_not_vaset_centre(self):
        self.assertAlmostEqual(BUSINESS['latitude'], 61.017, delta=0.005)
        self.assertAlmostEqual(BUSINESS['longitude'], 8.947, delta=0.005)


class PortraitMapTests(TestCase):
    """The map stands like the old website's (east up). Old positions are moved by migration 0007."""

    def migration(self):
        import importlib
        return importlib.import_module('apps.core.migrations.0007_portrait_plot_map')

    def test_old_position_moves_to_the_same_spot_on_the_standing_map(self):
        x, y = self.migration().old_to_new(524.2, 79.0)  # plot 11 on the old turned map
        self.assertAlmostEqual(x, 51.4, delta=0.2)
        self.assertAlmostEqual(y, 410.7, delta=0.2)

    def test_transform_can_be_undone(self):
        m = self.migration()
        x, y = m.new_to_old(*m.old_to_new(300.0, 200.0))
        self.assertAlmostEqual(x, 300.0, places=3)
        self.assertAlmostEqual(y, 200.0, places=3)

    def test_outlines_move_point_by_point(self):
        moved = self.migration().move_shape('M524.2 79.0 L530 80 Z', self.migration().old_to_new)
        self.assertTrue(moved.startswith('M51.4 410.7 L'))
        self.assertTrue(moved.endswith(' Z'))

    def test_seed_data_lies_inside_the_standing_map(self):
        call_command('seed_plots', stdout=io.StringIO())
        for plot in Plot.objects.all():
            with self.subTest(plot=plot.number):
                self.assertTrue(0 < plot.map_x < 720 and 0 < plot.map_y < 1000)


class SeedPlotsTests(TestCase):
    def test_loads_the_real_plots_with_outlines_and_categories(self):
        call_command('seed_plots', stdout=io.StringIO())
        self.assertEqual(Plot.objects.count(), 54)
        self.assertEqual(Plot.objects.filter(status='sold').count(), 12)
        self.assertEqual(Plot.objects.get(number='64').price, 900000)
        plot = Plot.objects.get(number='13')
        self.assertEqual((plot.status, plot.category.name), ('sold', 'Byggetrinn 1'))
        self.assertEqual(Plot.objects.get(number='35').category.name, 'Byggetrinn 2')
        self.assertTrue(all(p.map_shape.startswith('M') and p.is_on_map for p in Plot.objects.all()))

    def test_running_again_keeps_the_clients_changes(self):
        call_command('seed_plots', stdout=io.StringIO())
        Plot.objects.filter(number='11').update(price=1234000, status='reserved')
        call_command('seed_plots', stdout=io.StringIO())
        plot = Plot.objects.get(number='11')
        self.assertEqual((plot.price, plot.status), (1234000, 'reserved'))
        self.assertEqual(Plot.objects.count(), 54)

    def test_overwrite_resets_to_the_websites_values(self):
        call_command('seed_plots', stdout=io.StringIO())
        Plot.objects.filter(number='11').update(price=1234000)
        call_command('seed_plots', overwrite=True, stdout=io.StringIO())
        self.assertEqual(Plot.objects.get(number='11').price, 1500000)

    def test_dry_run_changes_nothing_and_example_plots_are_removed(self):
        Plot.objects.create(number='99', note='Eksempeldata fra designskissen')
        call_command('seed_plots', dry_run=True, stdout=io.StringIO())
        self.assertEqual(Plot.objects.count(), 1)
        call_command('seed_plots', stdout=io.StringIO())
        self.assertFalse(Plot.objects.filter(number='99').exists())
