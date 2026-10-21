import io
import json
import re
import shutil
import tempfile
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.blog.models import Blog

from . import notify
from .models import Inquiry, Plot, PlotCategory
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
        # The heading is split into spans for the stepped layout; compare its visible text
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
        self.assertTrue(response['Location'].endswith('images/favicon/favicon-32.png'))

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

    def test_spam_never_sends_email(self):
        with mock.patch('apps.core.views.notify.send_inquiry') as send:
            self.client.post(self.url, form_data(hp_check='x'))
        send.assert_not_called()


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
# E-mail notice
# ------------------------------------------------------------------

class NotifyTests(MediaTestCase):
    def make_inquiry(self):
        return Inquiry.objects.create(name='Kari Nordmann', email='kari@example.no', interest='viewing')

    @override_settings(EMAIL_HOST='', INQUIRY_NOTIFY_EMAILS=['post@brakastolen.no'])
    def test_no_email_without_mail_server(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            notify.send_inquiry(self.make_inquiry())
        self.assertEqual(callbacks, [])

    @override_settings(EMAIL_HOST='smtp.example.no', INQUIRY_NOTIFY_EMAILS=['post@brakastolen.no'],
                       EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_email_has_every_field_and_a_dashboard_link(self):
        inquiry = self.make_inquiry()
        with mock.patch('apps.core.notify.close_old_connections'):
            notify.send_now(inquiry.pk)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('Kari Nordmann', body)
        self.assertIn('Visning', body)
        self.assertIn(reverse('dashboard_inquiry_detail', args=[inquiry.pk]), body)

    @override_settings(EMAIL_HOST='smtp.example.no', INQUIRY_NOTIFY_EMAILS=['post@brakastolen.no'])
    def test_broken_mail_server_is_logged_not_raised(self):
        inquiry = self.make_inquiry()
        with mock.patch('apps.core.notify.send_mail', side_effect=OSError('down')), \
                mock.patch('apps.core.notify.close_old_connections'), \
                self.assertLogs('apps.core.notify', level='ERROR'):
            notify.send_now(inquiry.pk)


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

    @override_settings(EMAIL_HOST='smtp.example.no', INQUIRY_NOTIFY_EMAILS=['post@brakastolen.no'],
                       EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_email_names_the_plot(self):
        inquiry = Inquiry.objects.create(name='Kari', email='kari@example.no', plot=Plot.objects.create(number='21'))
        with mock.patch('apps.core.notify.close_old_connections'):
            notify.send_now(inquiry.pk)
        self.assertIn('Tomt: Tomt 21', mail.outbox[0].body)


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
