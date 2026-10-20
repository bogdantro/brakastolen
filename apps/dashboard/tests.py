import io
import json
import os
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
from apps.core.models import Inquiry, InquiryNote, Plot, Project, ProjectImage

from .models import ActivityLog, LoginAttempt

MEDIA_ROOT = tempfile.mkdtemp()
PASSWORD = 'et-langt-passord-123'


def image_file(name='photo.jpg'):
    buffer = io.BytesIO()
    Image.new('RGB', (40, 30), (120, 140, 90)).save(buffer, 'JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


def make_project(**kwargs):
    defaults = {'title': 'Ulven hyttegrend', 'image': image_file(), 'is_published': True}
    defaults.update(kwargs)
    return Project.objects.create(**defaults)


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
        project = make_project()
        plot = Plot.objects.create(project=project, number='7')
        post = Blog.objects.create(title='Nyhet', text='<p>x</p>')
        inquiry = make_inquiry()
        urls = [
            reverse('dashboard_home'), reverse('dashboard_inquiries'),
            reverse('dashboard_inquiry_detail', args=[inquiry.pk]),
            reverse('dashboard_projects'), reverse('dashboard_project_create'),
            reverse('dashboard_project_edit', args=[project.pk]), reverse('dashboard_project_trash'),
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
# Projects
# ------------------------------------------------------------------

class ProjectTests(DashboardTestCase):
    def project_data(self, **kwargs):
        data = {'title': 'Nytt felt', 'category': 'hyttegrend', 'status': 'for_sale', 'image': image_file(),
                'description': '<p>Fint</p><script>alert(1)</script>'}
        data.update(kwargs)
        return data

    def test_new_project_form_defaults_to_draft(self):
        form = self.client.get(reverse('dashboard_project_create')).context['form']
        self.assertFalse(form.initial['is_published'])

    def test_create_project_sanitises_text_and_logs(self):
        response = self.client.post(reverse('dashboard_project_create'), self.project_data())
        project = Project.objects.get()
        self.assertRedirects(response, reverse('dashboard_project_edit', args=[project.pk]))
        self.assertEqual(project.description, '<p>Fint</p>')
        self.assertFalse(project.is_published)
        self.assertTrue(ActivityLog.objects.filter(action='Opprettet prosjekt (lagret som utkast)').exists())

    def test_publishing_is_logged(self):
        project = make_project(is_published=False)
        data = self.project_data(title=project.title, is_published='on')
        del data['image']
        self.client.post(reverse('dashboard_project_edit', args=[project.pk]), data)
        self.assertTrue(ActivityLog.objects.filter(action='Publiserte prosjekt').exists())

    def test_gallery_upload_one_file_per_request(self):
        project = make_project()
        url = reverse('dashboard_project_image_upload', args=[project.pk])
        self.assertEqual(self.client.post(url, {'file': image_file()}).json(), {'ok': True})
        self.assertEqual(project.gallery_images.count(), 1)

    def test_gallery_upload_rejects_a_fake_image(self):
        project = make_project()
        fake = SimpleUploadedFile('virus.jpg', b'not an image', content_type='image/jpeg')
        response = self.client.post(reverse('dashboard_project_image_upload', args=[project.pk]), {'file': fake})
        self.assertEqual(response.status_code, 400)
        self.assertIn('«virus.jpg»', response.json()['error'])

    def test_upload_done_gives_one_message_and_one_log_entry(self):
        project = make_project()
        response = self.client.post(reverse('dashboard_project_images_done', args=[project.pk]),
                                    {'images': '3', 'failed': ['a.heic']})
        self.assertEqual(response.json()['redirect'], reverse('dashboard_project_edit', args=[project.pk]))
        self.assertEqual(ActivityLog.objects.filter(action='Lastet opp 3 bilde(r)').count(), 1)

    def test_duplicate_copies_files_physically(self):
        project = make_project()
        ProjectImage.objects.create(project=project, image=image_file('galleri.jpg'))
        self.client.post(reverse('dashboard_project_duplicate', args=[project.pk]))
        copy = Project.objects.exclude(pk=project.pk).get()
        self.assertFalse(copy.is_published)
        self.assertNotEqual(copy.image.name, project.image.name)
        self.assertTrue(os.path.exists(copy.image.path))
        self.assertNotEqual(copy.gallery_images.get().image.name, project.gallery_images.get().image.name)

    def test_delete_moves_to_trash_and_restore_brings_it_back(self):
        project = make_project()
        self.client.post(reverse('dashboard_project_delete', args=[project.pk]))
        self.assertFalse(Project.objects.public().filter(pk=project.pk).exists())
        self.client.post(reverse('dashboard_project_restore', args=[project.pk]))
        self.assertTrue(Project.objects.public().filter(pk=project.pk).exists())

    def test_delete_is_post_only(self):
        project = make_project()
        self.assertEqual(self.client.get(reverse('dashboard_project_delete', args=[project.pk])).status_code, 405)

    def test_purge_deletes_the_files_too(self):
        project = make_project(deleted_at=timezone.now())
        path = project.image.path
        self.client.post(reverse('dashboard_project_purge', args=[project.pk]))
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())
        self.assertFalse(os.path.exists(path))

    def test_purge_refuses_projects_not_in_the_trash(self):
        project = make_project()
        self.assertEqual(self.client.post(reverse('dashboard_project_purge', args=[project.pk])).status_code, 404)

    def test_reorder(self):
        first, second = make_project(title='A'), make_project(title='B')
        response = self.client.post(reverse('dashboard_projects_reorder'), json.dumps({'ids': [second.pk, first.pk]}),
                                    content_type='application/json')
        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(list(Project.objects.values_list('title', flat=True)), ['B', 'A'])

    def test_reorder_with_bad_json_gives_a_message(self):
        response = self.client.post(reverse('dashboard_projects_reorder'), 'ikke json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_gallery_image_delete_removes_file(self):
        image = ProjectImage.objects.create(project=make_project(), image=image_file('galleri.jpg'))
        path = image.image.path
        self.client.post(reverse('dashboard_project_image_delete', args=[image.pk]))
        self.assertFalse(ProjectImage.objects.exists())
        self.assertFalse(os.path.exists(path))


# ------------------------------------------------------------------
# Plots
# ------------------------------------------------------------------

class PlotTests(DashboardTestCase):
    def test_create_edit_and_delete_a_plot(self):
        group = make_project(category='hyttegrend')
        self.client.post(reverse('dashboard_plot_create'),
                         {'project': group.pk, 'number': 'T10', 'status': 'available', 'price': '900000'})
        plot = Plot.objects.get()
        self.assertEqual(str(plot), 'Ulven hyttegrend – tomt T10')
        self.client.post(reverse('dashboard_plot_edit', args=[plot.pk]),
                         {'project': group.pk, 'number': 'T10', 'status': 'reserved', 'price': '950000'})
        plot.refresh_from_db()
        self.assertEqual(plot.price, 950000)
        self.client.post(reverse('dashboard_plot_delete', args=[plot.pk]))
        self.assertFalse(Plot.objects.exists())

    def test_quick_status_change_is_logged(self):
        plot = Plot.objects.create(number='7')
        self.client.post(reverse('dashboard_plot_status', args=[plot.pk]), {'status': 'sold'})
        plot.refresh_from_db()
        self.assertEqual(plot.status, 'sold')
        self.assertTrue(ActivityLog.objects.filter(action='Endret tomt til «Solgt»').exists())

    def test_only_cabin_groups_can_hold_plots(self):
        make_project(title='En hytte', category='hytte')
        group = make_project(title='Et felt', category='hyttegrend')
        choices = self.client.get(reverse('dashboard_plot_create')).context['form'].fields['project'].queryset
        self.assertEqual(list(choices), [group])


# ------------------------------------------------------------------
# News
# ------------------------------------------------------------------

class BlogTests(DashboardTestCase):
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
        self.assertContains(self.client.get(reverse('dashboard_inquiry_detail', args=[inquiry.pk])), 'tomt 21')
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
