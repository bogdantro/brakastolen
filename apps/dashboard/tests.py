import io
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.blog.models import Blog
from apps.core.models import Inquiry, InquiryNote, Plot, PlotCategory

from .models import ActivityLog, LoginAttempt

MEDIA_ROOT = tempfile.mkdtemp()
PASSWORD = 'et-langt-passord-123'


def image_file(name='photo.jpg'):
    buffer = io.BytesIO()
    Image.new('RGB', (40, 30), (120, 140, 90)).save(buffer, 'JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


def make_inquiry(**kwargs):
    defaults = {'name': 'Kari Nordmann', 'email': 'kari@example.no', 'phone': '+47 482 58 000', 'message': 'Hei'}
    defaults.update(kwargs)
    return Inquiry.objects.create(**defaults)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DashboardTestCase(TestCase):
    """Logged in as a staff member."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user('haakon', password=PASSWORD, is_staff=True, first_name='Haakon')
        self.client.force_login(self.user)


# ------------------------------------------------------------------
# Login and access
# ------------------------------------------------------------------

class AccessTests(TestCase):
    def test_visitors_are_sent_to_login(self):
        response = self.client.get(reverse('dashboard_home'))
        self.assertRedirects(response, reverse('dashboard_login'))

    def test_non_staff_users_are_sent_to_login(self):
        self.client.force_login(User.objects.create_user('kunde', password=PASSWORD))
        self.assertRedirects(self.client.get(reverse('dashboard_inquiries')), reverse('dashboard_login'))

    def test_staff_login_works_and_is_logged(self):
        User.objects.create_user('haakon', password=PASSWORD, is_staff=True)
        response = self.client.post(reverse('dashboard_login'), {'username': 'haakon', 'password': PASSWORD})
        self.assertRedirects(response, reverse('dashboard_home'))
        self.assertTrue(ActivityLog.objects.filter(action='Logget inn').exists())

    def test_wrong_password_gives_a_plain_message(self):
        User.objects.create_user('haakon', password=PASSWORD, is_staff=True)
        response = self.client.post(reverse('dashboard_login'), {'username': 'haakon', 'password': 'feil'})
        self.assertContains(response, 'Feil brukernavn eller passord.')

    def test_too_many_failures_lock_out_even_the_right_password(self):
        User.objects.create_user('haakon', password=PASSWORD, is_staff=True)
        for _ in range(5):
            self.client.post(reverse('dashboard_login'), {'username': 'haakon', 'password': 'feil'})
        response = self.client.post(reverse('dashboard_login'), {'username': 'haakon', 'password': PASSWORD})
        self.assertContains(response, 'For mange mislykkede forsøk. Prøv igjen om')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_old_failures_do_not_count(self):
        User.objects.create_user('haakon', password=PASSWORD, is_staff=True)
        for _ in range(5):
            attempt = LoginAttempt.objects.create(ip='127.0.0.1', username='haakon')
            LoginAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timedelta(hours=1))
        response = self.client.post(reverse('dashboard_login'), {'username': 'haakon', 'password': PASSWORD})
        self.assertRedirects(response, reverse('dashboard_home'))

    def test_logout_is_post_only(self):
        self.client.force_login(User.objects.create_user('haakon', password=PASSWORD, is_staff=True))
        self.assertEqual(self.client.get(reverse('dashboard_logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('dashboard_logout')), reverse('dashboard_login'))

    def test_dashboard_is_never_indexed(self):
        self.assertContains(self.client.get(reverse('dashboard_login')), 'noindex, nofollow')


# ------------------------------------------------------------------
# Overview and inquiries
# ------------------------------------------------------------------

class OverviewTests(DashboardTestCase):
    def test_overview_counts_and_chart(self):
        make_inquiry()
        make_inquiry(is_spam=True)
        response = self.client.get(reverse('dashboard_home'))
        self.assertEqual(response.context['unread_count'], 1)
        self.assertEqual(response.context['weekly']['total'], 1)
        self.assertEqual(len(response.context['weekly']['bars']), 12)

    def test_unread_badge_in_sidebar(self):
        make_inquiry()
        self.assertEqual(self.client.get(reverse('dashboard_home')).context['sidebar_unread'], 1)

    def test_every_dashboard_page_loads(self):
        plot = Plot.objects.create(number='7')
        post = Blog.objects.create(title='Nyhet', text='<p>x</p>')
        inquiry = make_inquiry()
        urls = [
            reverse('dashboard_home'), reverse('dashboard_inquiries'),
            reverse('dashboard_inquiry_detail', args=[inquiry.pk]),
            reverse('dashboard_plots'), reverse('dashboard_plot_create'), reverse('dashboard_plot_edit', args=[plot.pk]),
            reverse('dashboard_blog'), reverse('dashboard_blog_create'), reverse('dashboard_blog_edit', args=[post.pk]),
            reverse('dashboard_activity'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class InquiryTests(DashboardTestCase):
    def test_boxes_keep_spam_and_archive_out_of_the_inbox(self):
        make_inquiry(name='Innboks')
        make_inquiry(name='Arkivert', is_archived=True)
        make_inquiry(name='Spammer', is_spam=True)
        names = [i.name for i in self.client.get(reverse('dashboard_inquiries')).context['inquiries']]
        self.assertEqual(names, ['Innboks'])
        spam = self.client.get(reverse('dashboard_inquiries') + '?box=spam').context['inquiries']
        self.assertEqual([i.name for i in spam], ['Spammer'])

    def test_unknown_box_falls_back_to_inbox(self):
        self.assertEqual(self.client.get(reverse('dashboard_inquiries') + '?box=hack').context['box'], 'inbox')

    def test_search(self):
        make_inquiry(name='Kari')
        make_inquiry(name='Ola', email='ola@example.no')
        response = self.client.get(reverse('dashboard_inquiries') + '?q=ola')
        self.assertEqual([i.name for i in response.context['inquiries']], ['Ola'])

    def test_csv_export_opens_in_excel(self):
        make_inquiry(name='Åse Ødegård')
        response = self.client.get(reverse('dashboard_inquiries') + '?export=csv')
        content = response.content.decode('utf-8')
        self.assertTrue(content.startswith('﻿'))
        self.assertIn('Dato;Navn;E-post', content)
        self.assertIn('Åse Ødegård', content)
        self.assertIn(f'henvendelser-{timezone.localdate():%Y-%m-%d}.csv', response['Content-Disposition'])

    def test_opening_marks_as_read(self):
        inquiry = make_inquiry()
        self.client.get(reverse('dashboard_inquiry_detail', args=[inquiry.pk]))
        inquiry.refresh_from_db()
        self.assertTrue(inquiry.is_read)

    def test_reply_links_are_prefilled(self):
        inquiry = make_inquiry()
        response = self.client.get(reverse('dashboard_inquiry_detail', args=[inquiry.pk]))
        self.assertEqual(response.context['phone_clean'], '+4748258000')
        self.assertIn('Hei%20Kari', response.context['mailto_url'])
        self.assertIn('Haakon', response.context['mailto_url'])

    def test_status_change_is_logged(self):
        inquiry = make_inquiry()
        self.client.post(reverse('dashboard_inquiry_detail', args=[inquiry.pk]), {'action': 'status', 'status': 'viewing'})
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, 'viewing')
        self.assertTrue(ActivityLog.objects.filter(action='Endret status til «Visning avtalt»').exists())

    def test_unknown_status_is_ignored(self):
        inquiry = make_inquiry()
        self.client.post(reverse('dashboard_inquiry_detail', args=[inquiry.pk]), {'action': 'status', 'status': 'hack'})
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, 'new')

    def test_not_spam_restores_and_clears_reason(self):
        inquiry = make_inquiry(is_spam=True, spam_reason='honeypot')
        self.client.post(reverse('dashboard_inquiry_detail', args=[inquiry.pk]), {'action': 'not_spam'})
        inquiry.refresh_from_db()
        self.assertFalse(inquiry.is_spam)
        self.assertEqual(inquiry.spam_reason, '')

    def test_archive(self):
        inquiry = make_inquiry()
        self.client.post(reverse('dashboard_inquiry_detail', args=[inquiry.pk]), {'action': 'archive'})
        inquiry.refresh_from_db()
        self.assertTrue(inquiry.is_archived)

    def test_notes(self):
        inquiry = make_inquiry()
        url = reverse('dashboard_inquiry_detail', args=[inquiry.pk])
        self.client.post(url, {'action': 'add_note', 'text': 'Ringte tirsdag'})
        note = InquiryNote.objects.get()
        self.assertEqual(note.author, self.user)
        self.client.post(url, {'action': 'delete_note', 'note_id': note.pk})
        self.assertFalse(InquiryNote.objects.exists())

    def test_delete_needs_post(self):
        inquiry = make_inquiry()
        self.client.get(reverse('dashboard_inquiry_detail', args=[inquiry.pk]) + '?action=delete')
        self.assertTrue(Inquiry.objects.filter(pk=inquiry.pk).exists())
        self.client.post(reverse('dashboard_inquiry_detail', args=[inquiry.pk]), {'action': 'delete'})
        self.assertFalse(Inquiry.objects.filter(pk=inquiry.pk).exists())


# ------------------------------------------------------------------
# Plots
# ------------------------------------------------------------------

class PlotTests(DashboardTestCase):
    def test_create_edit_and_delete_a_plot(self):
        group = PlotCategory.objects.create(name='Byggetrinn 1')
        self.client.post(reverse('dashboard_plot_create'),
                         {'category': group.pk, 'number': 'T10', 'status': 'available', 'price': '900000'})
        plot = Plot.objects.get()
        self.assertEqual((str(plot), plot.category), ('Tomt T10', group))
        self.client.post(reverse('dashboard_plot_edit', args=[plot.pk]),
                         {'category': group.pk, 'number': 'T10', 'status': 'reserved', 'price': '950000'})
        plot.refresh_from_db()
        self.assertEqual(plot.price, 950000)
        self.client.post(reverse('dashboard_plot_delete', args=[plot.pk]))
        self.assertFalse(Plot.objects.exists())

    def test_price_can_be_typed_the_norwegian_way(self):
        self.client.post(reverse('dashboard_plot_create'), {'number': '67', 'status': 'available', 'price': '1 450 000'})
        self.assertEqual(Plot.objects.get(number='67').price, 1450000)


class PlotQuickEditTests(DashboardTestCase):
    """Changes straight from the plots list: one field at a time, saved and logged."""

    def setUp(self):
        super().setUp()
        self.category = PlotCategory.objects.create(name='Byggetrinn 1')
        self.plot = Plot.objects.create(number='11', price=1500000, area_m2=1600, category=self.category)
        self.url = reverse('dashboard_plot_quick', args=[self.plot.pk])

    def post_json(self, data):
        return self.client.post(self.url, data, HTTP_ACCEPT='application/json')

    def test_mark_as_sold(self):
        response = self.post_json({'status': 'sold'})
        self.assertEqual(response.json()['plot']['status'], 'sold')
        self.assertEqual(response.json()['summary']['sold'], 1)
        self.plot.refresh_from_db()
        self.assertEqual(self.plot.status, 'sold')
        self.assertTrue(ActivityLog.objects.filter(action='Markerte tomt 11 som solgt').exists())

    def test_change_price_only_touches_the_price(self):
        response = self.post_json({'price': '1.450.000 kr'})
        self.assertEqual(response.json()['plot']['priceDisplay'], '1 450 000 kr')
        self.plot.refresh_from_db()
        self.assertEqual((self.plot.price, self.plot.area_m2, self.plot.category), (1450000, 1600, self.category))
        self.assertTrue(ActivityLog.objects.filter(action='Endret prisen på tomt 11 til 1 450 000 kr').exists())

    def test_empty_price_means_ask_for_price(self):
        self.post_json({'price': ''})
        self.plot.refresh_from_db()
        self.assertIsNone(self.plot.price)

    def test_bad_price_is_refused_and_nothing_changes(self):
        response = self.post_json({'price': 'mange penger'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])
        self.plot.refresh_from_db()
        self.assertEqual(self.plot.price, 1500000)

    def test_change_and_remove_category(self):
        other = PlotCategory.objects.create(name='Byggetrinn 2')
        self.post_json({'category': other.pk})
        self.plot.refresh_from_db()
        self.assertEqual(self.plot.category, other)
        self.post_json({'category': ''})
        self.plot.refresh_from_db()
        self.assertIsNone(self.plot.category)
        self.assertTrue(ActivityLog.objects.filter(action='Fjernet kategorien på tomt 11').exists())

    def test_unchanged_value_is_not_logged(self):
        self.post_json({'status': 'available'})
        self.assertFalse(ActivityLog.objects.exists())

    def test_without_javascript_it_redirects_back_to_the_list(self):
        response = self.client.post(self.url, {'status': 'reserved', 'next': '/dashboard/tomter/?status=available'})
        self.assertRedirects(response, '/dashboard/tomter/?status=available', fetch_redirect_response=False)

    def test_next_never_leads_off_the_site(self):
        response = self.client.post(self.url, {'status': 'reserved', 'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('dashboard_plots'), fetch_redirect_response=False)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class PlotListTests(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.phase1 = PlotCategory.objects.create(name='Byggetrinn 1')
        self.phase2 = PlotCategory.objects.create(name='Byggetrinn 2')
        Plot.objects.create(number='9', price=900000, category=self.phase1)
        Plot.objects.create(number='11', price=1500000, category=self.phase1, status='sold')
        Plot.objects.create(number='35', price=1400000, category=self.phase2)

    def numbers(self, query=''):
        response = self.client.get(reverse('dashboard_plots') + query)
        return [p.number for p in response.context['plots']]

    def test_numbers_sort_as_numbers(self):
        self.assertEqual(self.numbers(), ['9', '11', '35'])

    def test_filters(self):
        self.assertEqual(self.numbers('?status=available'), ['9', '35'])
        self.assertEqual(self.numbers(f'?category={self.phase2.pk}'), ['35'])
        self.assertEqual(self.numbers('?q=3'), ['35'])
        self.assertEqual(self.numbers('?sort=price_desc'), ['11', '35', '9'])

    def test_summary_counts_value_of_available_plots_only(self):
        summary = self.client.get(reverse('dashboard_plots')).context['summary']
        self.assertEqual((summary['available'], summary['sold']), (2, 1))
        self.assertEqual(summary['available_value'], 2300000)

    def test_bulk_mark_as_sold(self):
        ids = list(Plot.objects.filter(number__in=['9', '35']).values_list('pk', flat=True))
        self.client.post(reverse('dashboard_plots_bulk'), {'plots': ids, 'status': 'sold'})
        self.assertEqual(Plot.objects.filter(status='sold').count(), 3)
        self.assertTrue(ActivityLog.objects.filter(action='Markerte 2 tomter som solgt', target='tomt 9, 35').exists())

    def test_bulk_move_to_category(self):
        ids = list(Plot.objects.values_list('pk', flat=True))
        self.client.post(reverse('dashboard_plots_bulk'), {'plots': ids, 'action': 'category', 'category': self.phase2.pk})
        self.assertEqual(Plot.objects.filter(category=self.phase2).count(), 3)

    def test_bulk_without_plots_explains_what_to_do(self):
        response = self.client.post(reverse('dashboard_plots_bulk'), {'status': 'sold'}, follow=True)
        self.assertContains(response, 'Velg minst én tomt')
        self.assertEqual(Plot.objects.filter(status='sold').count(), 1)

    def test_categories_can_be_added_renamed_and_deleted(self):
        url = reverse('dashboard_plot_categories')
        self.client.post(url, {'action': 'add', 'name': 'Byggetrinn 3'})
        new = PlotCategory.objects.get(name='Byggetrinn 3')
        self.client.post(url, {'action': 'rename', 'category_id': self.phase1.pk, 'name': 'Trinn 1'})
        self.phase1.refresh_from_db()
        self.assertEqual(self.phase1.name, 'Trinn 1')
        self.client.post(url, {'action': 'delete', 'category_id': self.phase1.pk})
        self.assertFalse(PlotCategory.objects.filter(pk=self.phase1.pk).exists())
        self.assertEqual(Plot.objects.filter(category__isnull=True).count(), 2)
        self.assertTrue(PlotCategory.objects.filter(pk=new.pk).exists())

    def test_deleted_plot_leaves_no_dead_links_in_the_activity_log(self):
        plot = Plot.objects.get(number='9')
        edit_url = reverse('dashboard_plot_edit', args=[plot.pk])
        self.client.post(reverse('dashboard_plot_quick', args=[plot.pk]), {'status': 'sold'})
        self.client.post(reverse('dashboard_plot_delete', args=[plot.pk]))
        self.assertFalse(ActivityLog.objects.filter(url=edit_url).exists())
        self.assertTrue(ActivityLog.objects.filter(action='Markerte tomt 9 som solgt').exists())

    def test_tampered_category_id_gives_404_not_a_crash(self):
        response = self.client.post(reverse('dashboard_plot_categories'), {'action': 'delete', 'category_id': 'abc'})
        self.assertEqual(response.status_code, 404)

    def test_greeting_says_good_evening_late_at_night(self):
        from unittest import mock
        from datetime import datetime
        night = timezone.make_aware(datetime(2026, 10, 21, 2, 0))
        with mock.patch('apps.dashboard.views.timezone.localtime', return_value=night):
            self.assertEqual(self.client.get(reverse('dashboard_home')).context['greeting'], 'God kveld')

    def test_duplicate_category_name_is_refused(self):
        response = self.client.post(reverse('dashboard_plot_categories'),
                                    {'action': 'add', 'name': 'Byggetrinn 1'}, follow=True)
        self.assertContains(response, 'Det finnes allerede en kategori med dette navnet.')

    def test_overview_shows_the_sales_map(self):
        Plot.objects.filter(number='9').update(map_x=100, map_y=100, map_shape='M90 90 L110 90 L110 110 Z')
        response = self.client.get(reverse('dashboard_home'))
        self.assertEqual([p['number'] for p in response.context['map_plots']], ['9'])
        self.assertEqual(response.context['plot_summary']['sold'], 1)
        self.assertContains(response, 'sales-map-data')


# ------------------------------------------------------------------
# News
# ------------------------------------------------------------------

class BlogTests(DashboardTestCase):
    def test_sidebar_has_no_projects(self):
        self.assertNotContains(self.client.get(reverse('dashboard_home')), 'Prosjekter')

    def test_create_post_as_draft_and_sanitised(self):
        self.client.post(reverse('dashboard_blog_create'),
                         {'title': 'Ny nyhet', 'text': '<p>Hei</p><img src=x onerror=alert(1)>'})
        post = Blog.objects.get()
        self.assertEqual(post.text, '<p>Hei</p>')
        self.assertFalse(post.is_published)

    def test_empty_text_is_refused(self):
        response = self.client.post(reverse('dashboard_blog_create'), {'title': 'Tom', 'text': '<p><br></p>'})
        self.assertContains(response, 'Nyheten kan ikke være tom.')

    def test_delete_post(self):
        post = Blog.objects.create(title='Slett meg', text='<p>x</p>')
        self.client.post(reverse('dashboard_blog_delete', args=[post.pk]))
        self.assertFalse(Blog.objects.exists())
        self.assertTrue(ActivityLog.objects.filter(action='Slettet nyhet', target='Slett meg').exists())


class ActivityTests(DashboardTestCase):
    def test_failed_logins_last_week_are_counted(self):
        LoginAttempt.objects.create(ip='10.0.0.1', username='x')
        self.assertEqual(self.client.get(reverse('dashboard_activity')).context['failed_logins'], 1)


class PlotMapTests(DashboardTestCase):
    def test_plot_position_from_the_map_is_saved(self):
        plot = Plot.objects.create(number='7')
        self.client.post(reverse('dashboard_plot_edit', args=[plot.pk]),
                         {'number': '7', 'status': 'available', 'map_x': '480', 'map_y': '379', 'map_rotation': '-15'})
        plot.refresh_from_db()
        self.assertEqual((plot.map_x, plot.map_y, plot.map_rotation), (480, 379, -15))
        self.assertTrue(plot.is_on_map)

    def test_plot_form_shows_the_other_plots_on_the_map(self):
        Plot.objects.create(number='1', map_x=100, map_y=100)
        plot = Plot.objects.create(number='2', map_x=200, map_y=200)
        response = self.client.get(reverse('dashboard_plot_edit', args=[plot.pk]))
        self.assertEqual([p['number'] for p in response.context['map_plots']], ['1'])

    def test_inquiry_shows_which_plot_it_is_about(self):
        plot = Plot.objects.create(number='21')
        inquiry = make_inquiry(plot=plot)
        self.assertContains(self.client.get(reverse('dashboard_inquiry_detail', args=[inquiry.pk])), 'Tomt 21')
        csv_text = self.client.get(reverse('dashboard_inquiries') + '?export=csv').content.decode('utf-8')
        self.assertIn(';21;', csv_text)


class MissingUserTests(DashboardTestCase):
    """Log entries and notes can lose their user (lockouts, deleted accounts) – pages must still load."""

    def test_overview_and_activity_load_with_an_entry_without_a_user(self):
        ActivityLog.objects.create(action='Innlogging sperret etter for mange forsøk', target='ukjent (127.0.0.1)')
        for name in ('dashboard_home', 'dashboard_activity'):
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), 'System')

    def test_note_whose_author_was_deleted_still_shows(self):
        inquiry = make_inquiry()
        author = User.objects.create_user('tidligere', password=PASSWORD, is_staff=True)
        InquiryNote.objects.create(inquiry=inquiry, author=author, text='Ringte mandag')
        author.delete()
        response = self.client.get(reverse('dashboard_inquiry_detail', args=[inquiry.pk]))
        self.assertContains(response, 'Ringte mandag')
        self.assertContains(response, 'Ukjent')

    def test_names_prefer_full_name(self):
        entry = ActivityLog.objects.create(user=self.user, action='Logget inn')
        self.assertEqual(entry.who, 'Haakon')
