import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Blog
from .views import reading_minutes

MEDIA_ROOT = tempfile.mkdtemp()


def make_post(**kwargs):
    defaults = {'title': 'Nye tomter på Brakastølen', 'text': '<p>Tekst om tomtene.</p>', 'excerpt': 'Kort.'}
    defaults.update(kwargs)
    return Blog.objects.create(**defaults)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class BlogTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_list_shows_only_published_posts(self):
        make_post(title='Publisert')
        make_post(title='Utkast', is_published=False)
        response = self.client.get(reverse('nyheter'))
        self.assertContains(response, 'Publisert')
        self.assertNotContains(response, 'Utkast')

    def test_slug_spells_out_norwegian_letters(self):
        self.assertEqual(make_post(title='Bærår i år?').slug, 'baerar-i-ar')

    def test_post_page_loads(self):
        post = make_post()
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, 'Tekst om tomtene.')
        self.assertContains(response, 'BlogPosting')

    def test_draft_is_404_for_visitors(self):
        post = make_post(is_published=False)
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)

    def test_staff_can_preview_a_draft(self):
        post = make_post(is_published=False)
        self.client.force_login(User.objects.create_user('staff', password='x' * 16, is_staff=True))
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 200)

    def test_old_slug_redirects_to_the_new_one(self):
        post = make_post()
        response = self.client.get(reverse('nyhet_detail', args=[post.pk, 'gammel-tittel']))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], post.get_absolute_url())

    def test_post_text_is_sanitised_when_shown(self):
        post = make_post(text='<p>Hei</p><script>alert(1)</script>')
        self.assertNotContains(self.client.get(post.get_absolute_url()), 'alert(1)')

    def test_reading_minutes(self):
        self.assertEqual(reading_minutes('ord ' * 450), 3)
        self.assertEqual(reading_minutes(''), 1)

    def test_seed_publishes_real_news_and_keeps_placeholders_as_drafts(self):
        call_command('seed_blog', stdout=io.StringIO())
        call_command('seed_blog', stdout=io.StringIO())
        self.assertEqual(Blog.objects.count(), 6)
        self.assertTrue(Blog.objects.get(title='Ulven hyttegrend').is_published)
        self.assertFalse(Blog.objects.get(title='Reguleringsplan vedtatt').is_published)
        self.assertFalse(Blog.objects.filter(is_published=True, text__icontains='lorem').exists())
        self.assertEqual(Blog.objects.get(title='Bærår i år?').created_at.year, 2020)


@override_settings(MEDIA_ROOT=MEDIA_ROOT, SITE_URL='https://www.xn--brakastlen-6cb.no')
class NewsArticleTests(TestCase):
    def test_article_has_the_plot_picker_and_is_never_cached(self):
        response = self.client.get(make_post().get_absolute_url())
        self.assertContains(response, 'id="tomtevelger"')
        self.assertIn('no-cache', response['Cache-Control'])

    def test_share_link_uses_site_url_not_the_request_host(self):
        post = make_post()
        response = self.client.get(post.get_absolute_url(), HTTP_HOST='localhost')
        self.assertContains(response, f'data-copy-link="https://www.xn--brakastlen-6cb.no{post.get_absolute_url()}"')

    def test_tall_image_is_shown_whole_beside_the_text(self):
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (30, 60), 'white').save(buffer, 'JPEG')
        post = make_post(image=SimpleUploadedFile('annonse.jpg', buffer.getvalue(), content_type='image/jpeg'))
        self.assertContains(self.client.get(post.get_absolute_url()), 'article-figure is-portrait')
