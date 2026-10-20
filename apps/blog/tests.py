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
