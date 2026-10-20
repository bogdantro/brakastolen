"""The client's dashboard at /dashboard/: inquiries (a small sales CRM), projects with
photo galleries, plots for sale, news posts and an activity log."""
import csv
import json
import os
import re
from datetime import timedelta
from functools import wraps
from urllib.parse import quote

from django import forms as django_forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.files.base import ContentFile
from django.db.models import Count, Max, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog.models import Blog
from apps.core.models import Inquiry, InquiryNote, Plot, Project, ProjectImage
from apps.core.seo import BUSINESS

from .forms import BlogForm, DashboardLoginForm, InquiryNoteForm, PlotForm, ProjectForm
from .models import ActivityLog, LoginAttempt

# Login rate limiting: this many failed attempts from one IP address
# within the window locks that address out until the window has passed.
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW = timedelta(minutes=15)

CHART_WEEKS = 12
ACTIVITY_PAGE_SIZE = 300


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect(reverse('dashboard_login'))
        return view_func(request, *args, **kwargs)
    return wrapper


def log_activity(request, action, target='', url=''):
    user = request.user if request.user.is_authenticated else None
    ActivityLog.objects.create(user=user, action=action, target=str(target)[:200], url=url)


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def next_order(model):
    return (model.objects.aggregate(m=Max('order'))['m'] or 0) + 1


# ------------------------------------------------------------------
# Login
# ------------------------------------------------------------------

def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(reverse('dashboard_home'))

    form = DashboardLoginForm(request.POST or None)
    error = None
    ip = client_ip(request)

    if request.method == 'POST':
        since = timezone.now() - LOGIN_WINDOW
        recent_failures = LoginAttempt.objects.filter(ip=ip, success=False, created_at__gte=since)
        if recent_failures.count() >= LOGIN_MAX_FAILURES:
            oldest = recent_failures.order_by('created_at').first()
            wait = max(1, int((oldest.created_at + LOGIN_WINDOW - timezone.now()).total_seconds() // 60) + 1)
            error = f'For mange mislykkede forsøk. Prøv igjen om {wait} minutter.'
        elif form.is_valid():
            username = form.cleaned_data['username']
            user = authenticate(request, username=username, password=form.cleaned_data['password'])
            if user is not None and user.is_staff:
                LoginAttempt.objects.create(ip=ip, username=username, success=True)
                login(request, user)
                log_activity(request, 'Logget inn')
                return redirect(reverse('dashboard_home'))

            LoginAttempt.objects.create(ip=ip, username=username, success=False)
            if recent_failures.count() >= LOGIN_MAX_FAILURES:
                ActivityLog.objects.create(action='Innlogging sperret etter for mange forsøk', target=f'{username} ({ip})')
                error = 'For mange mislykkede forsøk. Prøv igjen om 15 minutter.'
            else:
                error = 'Feil brukernavn eller passord.'

    return render(request, 'dashboard/login.html', {'form': form, 'error': error})


@require_POST
def dashboard_logout(request):
    logout(request)
    return redirect(reverse('dashboard_login'))


# ------------------------------------------------------------------
# Overview
# ------------------------------------------------------------------

def weekly_inquiry_chart(weeks=CHART_WEEKS):
    """Inquiries per week for the last `weeks` weeks, as bars for a plain HTML/CSS chart."""
    today = timezone.localdate()
    this_monday = today - timedelta(days=today.weekday())
    first_monday = this_monday - timedelta(weeks=weeks - 1)

    counts = [0] * weeks
    dates = Inquiry.objects.filter(is_spam=False, created_at__date__gte=first_monday).values_list('created_at', flat=True)
    for created in dates:
        index = (timezone.localtime(created).date() - first_monday).days // 7
        if 0 <= index < weeks:
            counts[index] += 1

    peak = max(counts) or 1
    bars = []
    for i, count in enumerate(counts):
        start = first_monday + timedelta(weeks=i)
        bars.append({
            'week': start.isocalendar()[1],
            'start': start,
            'end': start + timedelta(days=6),
            'count': count,
            'height': round(count / peak * 100),
            'current': i == weeks - 1,
        })
    return {'bars': bars, 'peak': max(counts), 'total': sum(counts)}


def status_breakdown():
    raw = dict(Inquiry.objects.filter(is_spam=False).values_list('status').annotate(n=Count('id')))
    peak = max(raw.values(), default=0) or 1
    return [
        {'key': key, 'label': label, 'count': raw.get(key, 0), 'width': round(raw.get(key, 0) / peak * 100)}
        for key, label in Inquiry.STATUS_CHOICES
    ]


@staff_required
def dashboard_home(request):
    inbox = Inquiry.objects.filter(is_spam=False, is_archived=False)
    projects = Project.objects.active()
    plot_counts = dict(Plot.objects.values_list('status').annotate(n=Count('id')))
    return render(request, 'dashboard/home.html', {
        'inquiry_count': inbox.count(),
        'unread_count': inbox.filter(is_read=False).count(),
        'open_count': inbox.filter(status__in=['new', 'contacted', 'viewing', 'prospectus_sent']).count(),
        'project_count': projects.filter(is_published=True).count(),
        'draft_count': projects.filter(is_published=False).count(),
        'plots': [{'label': label, 'count': plot_counts.get(key, 0)} for key, label in Plot.STATUS_CHOICES],
        'latest_inquiries': inbox[:5],
        'weekly': weekly_inquiry_chart(),
        'statuses': status_breakdown(),
        'top_projects': projects.filter(view_count__gt=0).order_by('-view_count')[:5],
        'recent_activity': ActivityLog.objects.select_related('user')[:6],
    })


# ------------------------------------------------------------------
# Inquiries
# ------------------------------------------------------------------

INQUIRY_BOXES = {
    'inbox': ('Innboks', Q(is_spam=False, is_archived=False)),
    'archive': ('Arkiv', Q(is_spam=False, is_archived=True)),
    'spam': ('Spam', Q(is_spam=True)),
}


@staff_required
def dashboard_inquiries(request):
    box = request.GET.get('box', 'inbox')
    if box not in INQUIRY_BOXES:
        box = 'inbox'
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()

    inquiries = Inquiry.objects.filter(INQUIRY_BOXES[box][1])
    status_counts = dict(inquiries.values_list('status').annotate(n=Count('id')))
    if status in dict(Inquiry.STATUS_CHOICES):
        inquiries = inquiries.filter(status=status)
    else:
        status = ''
    if q:
        inquiries = inquiries.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(message__icontains=q)
        )

    if request.GET.get('export') == 'csv':
        return export_inquiries_csv(inquiries)

    boxes = [
        {'key': key, 'label': label, 'count': Inquiry.objects.filter(cond).count()}
        for key, (label, cond) in INQUIRY_BOXES.items()
    ]
    pipeline = [
        {'key': key, 'label': label, 'count': status_counts.get(key, 0)}
        for key, label in Inquiry.STATUS_CHOICES
    ]
    params = request.GET.copy()
    params.pop('export', None)
    return render(request, 'dashboard/inquiries.html', {
        'inquiries': inquiries,
        'box': box,
        'boxes': boxes,
        'pipeline': pipeline,
        'status': status,
        'q': q,
        'export_query': params.urlencode(),
    })


def export_inquiries_csv(inquiries):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'henvendelser-{timezone.localdate():%Y-%m-%d}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('﻿')  # BOM so Excel opens æøå correctly
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Dato', 'Navn', 'E-post', 'Telefon', 'Interessert i', 'Tomt', 'Status', 'Arkivert', 'Spam', 'Beskjed'])
    for inquiry in inquiries.select_related('plot'):
        writer.writerow([
            timezone.localtime(inquiry.created_at).strftime('%d.%m.%Y %H:%M'),
            inquiry.name,
            inquiry.email,
            inquiry.phone,
            inquiry.get_interest_display(),
            inquiry.plot.number if inquiry.plot else '',
            inquiry.get_status_display(),
            'Ja' if inquiry.is_archived else 'Nei',
            'Ja' if inquiry.is_spam else 'Nei',
            inquiry.message,
        ])
    return response


INQUIRY_TOGGLES = {
    'archive': ('is_archived', True, 'Arkiverte henvendelse', 'Henvendelsen ble arkivert.'),
    'unarchive': ('is_archived', False, 'Flyttet henvendelse til innboks', 'Henvendelsen ble flyttet til innboksen.'),
    'spam': ('is_spam', True, 'Merket henvendelse som spam', 'Henvendelsen ble merket som spam.'),
    'not_spam': ('is_spam', False, 'Fjernet spam-merking', 'Henvendelsen er ikke lenger merket som spam.'),
}


@staff_required
def dashboard_inquiry_detail(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    detail_url = reverse('dashboard_inquiry_detail', args=[inquiry.pk])

    if not inquiry.is_read:
        inquiry.is_read = True
        inquiry.save(update_fields=['is_read'])

    note_form = InquiryNoteForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete':
            log_activity(request, 'Slettet henvendelse', inquiry.name)
            inquiry.delete()
            messages.success(request, 'Henvendelsen ble slettet.')
            return redirect(reverse('dashboard_inquiries'))

        if action == 'status':
            new_status = request.POST.get('status')
            if new_status in dict(Inquiry.STATUS_CHOICES) and new_status != inquiry.status:
                inquiry.status = new_status
                inquiry.save(update_fields=['status'])
                log_activity(request, f'Endret status til «{inquiry.get_status_display()}»', inquiry.name, detail_url)
                messages.success(request, f'Status endret til «{inquiry.get_status_display()}».')
            return redirect(detail_url)

        if action in INQUIRY_TOGGLES:
            field, value, log_text, message = INQUIRY_TOGGLES[action]
            setattr(inquiry, field, value)
            update = [field]
            if action == 'not_spam':
                inquiry.spam_reason = ''
                update.append('spam_reason')
            inquiry.save(update_fields=update)
            log_activity(request, log_text, inquiry.name, detail_url)
            messages.success(request, message)
            return redirect(detail_url)

        if action == 'add_note':
            note_form = InquiryNoteForm(request.POST)
            if note_form.is_valid():
                InquiryNote.objects.create(inquiry=inquiry, author=request.user, text=note_form.cleaned_data['text'])
                log_activity(request, 'La til notat', inquiry.name, detail_url)
                messages.success(request, 'Notatet ble lagret.')
                return redirect(detail_url)

        if action == 'delete_note':
            InquiryNote.objects.filter(inquiry=inquiry, pk=request.POST.get('note_id')).delete()
            messages.success(request, 'Notatet ble slettet.')
            return redirect(detail_url)

    first_name = inquiry.name.split()[0] if inquiry.name.strip() else ''
    signature = request.user.get_full_name() or request.user.username
    subject = f"Din henvendelse om {BUSINESS['name']}"
    body = (
        f'Hei {first_name},\n\nTakk for henvendelsen din.\n\n\n\n'
        f"Med vennlig hilsen\n{signature}\n{BUSINESS['company']}\nTlf. {BUSINESS['phone_display']}"
    )
    return render(request, 'dashboard/inquiry_detail.html', {
        'inquiry': inquiry,
        'mailto_url': f'mailto:{inquiry.email}?subject={quote(subject)}&body={quote(body)}',
        'phone_clean': re.sub(r'[^\d+]', '', inquiry.phone),
        'notes': inquiry.notes.select_related('author'),
        'note_form': note_form,
        'statuses': Inquiry.STATUS_CHOICES,
    })


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------

@staff_required
def dashboard_projects(request):
    projects = Project.objects.active()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')

    if q:
        projects = projects.filter(Q(title__icontains=q) | Q(location__icontains=q))
    if category in dict(Project.CATEGORY_CHOICES):
        projects = projects.filter(category=category)
    if status == 'published':
        projects = projects.filter(is_published=True)
    elif status == 'draft':
        projects = projects.filter(is_published=False)

    return render(request, 'dashboard/projects.html', {
        'projects': projects,
        'filtered': any([q, category, status]),
        'total': Project.objects.active().count(),
        'trash_count': Project.objects.filter(deleted_at__isnull=False).count(),
        'categories': Project.CATEGORY_CHOICES,
        'f': {'q': q, 'category': category, 'status': status},
    })


@staff_required
@require_POST
def dashboard_projects_reorder(request):
    try:
        ids = [int(i) for i in json.loads(request.body).get('ids', [])]
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'error': 'Kunne ikke lese den nye rekkefølgen. Last siden på nytt og prøv igjen.'}, status=400)

    projects = {p.pk: p for p in Project.objects.active().filter(pk__in=ids)}
    changed = []
    for position, pk in enumerate(ids, start=1):
        project = projects.get(pk)
        if project and project.order != position:
            project.order = position
            changed.append(project)
    Project.objects.bulk_update(changed, ['order'])
    if changed:
        log_activity(request, 'Endret rekkefølgen på prosjekter')
    return JsonResponse({'ok': True})


@staff_required
def dashboard_project_create(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        project = form.save(commit=False)
        project.order = next_order(Project)
        project.save()
        state = 'publisert' if project.is_published else 'lagret som utkast'
        log_activity(request, f'Opprettet prosjekt ({state})', project.title,
                     reverse('dashboard_project_edit', args=[project.pk]))
        messages.success(request, f'Prosjektet ble {state}. Nå kan du legge til bilder i galleriet.')
        return redirect(reverse('dashboard_project_edit', args=[project.pk]))
    return render(request, 'dashboard/project_form.html', {'form': form, 'project': None})


@staff_required
def dashboard_project_edit(request, pk):
    project = get_object_or_404(Project.objects.active(), pk=pk)
    edit_url = reverse('dashboard_project_edit', args=[project.pk])
    was_published = project.is_published

    form = ProjectForm(request.POST or None, request.FILES or None, instance=project)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if project.is_published and not was_published:
            log_activity(request, 'Publiserte prosjekt', project.title, edit_url)
        elif was_published and not project.is_published:
            log_activity(request, 'Gjorde prosjekt om til utkast', project.title, edit_url)
        else:
            log_activity(request, 'Oppdaterte prosjekt', project.title, edit_url)
        messages.success(request, 'Prosjektet ble oppdatert.')
        return redirect(edit_url)

    return render(request, 'dashboard/project_form.html', {
        'form': form,
        'project': project,
        'gallery': project.gallery_images.all(),
    })


@staff_required
@require_POST
def dashboard_project_image_upload(request, pk):
    """One gallery photo per request. The browser sends a large gallery one file at a
    time, so no single request gets too big or too slow for nginx and gunicorn."""
    project = get_object_or_404(Project.objects.active(), pk=pk)
    upload = request.FILES.get('file')
    if upload is None:
        return JsonResponse({'error': 'Ingen fil mottatt.'}, status=400)
    try:
        # Checks that it really is an image Pillow can open, whatever the browser claimed
        django_forms.ImageField().clean(upload)
    except django_forms.ValidationError:
        return JsonResponse({'error': f'«{upload.name}» er ikke et bilde som kan leses.'}, status=400)
    ProjectImage.objects.create(project=project, image=upload, order=next_order(ProjectImage))
    return JsonResponse({'ok': True})


@staff_required
@require_POST
def dashboard_project_images_done(request, pk):
    """Called once after a batch upload: one message and one activity entry for the lot."""
    project = get_object_or_404(Project.objects.active(), pk=pk)
    try:
        count = int(request.POST.get('images') or 0)
    except ValueError:
        count = 0
    failed = [name for name in request.POST.getlist('failed') if name][:20]
    edit_url = reverse('dashboard_project_edit', args=[project.pk])
    if count:
        messages.success(request, f'Lastet opp {count} bilde(r).')
        log_activity(request, f'Lastet opp {count} bilde(r)', project.title, edit_url)
    if failed:
        messages.warning(request, 'Disse filene ble ikke lastet opp: ' + ', '.join(failed))
    return JsonResponse({'ok': True, 'redirect': edit_url})


def copy_file(field_file, target_field):
    """Save a physical copy so the two projects never share (and later delete) one file."""
    field_file.open('rb')
    try:
        target_field.save(os.path.basename(field_file.name), ContentFile(field_file.read()), save=False)
    finally:
        field_file.close()


@staff_required
@require_POST
def dashboard_project_duplicate(request, pk):
    original = get_object_or_404(Project.objects.active(), pk=pk)
    copy = Project(
        title=f'{original.title} (kopi)',
        category=original.category,
        status=original.status,
        location=original.location,
        excerpt=original.excerpt,
        description=original.description,
        description_2=original.description_2,
        image_credit=original.image_credit,
        is_published=False,
        is_featured=False,
        order=next_order(Project),
    )
    for name in Project.FACT_FIELDS:
        setattr(copy, name, getattr(original, name))
    if original.image:
        copy_file(original.image, copy.image)
    copy.save()
    for image in original.gallery_images.all():
        gallery_copy = ProjectImage(project=copy, caption=image.caption, order=image.order)
        copy_file(image.image, gallery_copy.image)
        gallery_copy.save()
    log_activity(request, 'Dupliserte prosjekt', original.title, reverse('dashboard_project_edit', args=[copy.pk]))
    messages.success(request, f'Kopi av «{original.title}» ble opprettet som utkast.')
    return redirect(reverse('dashboard_project_edit', args=[copy.pk]))


@staff_required
@require_POST
def dashboard_project_delete(request, pk):
    project = get_object_or_404(Project.objects.active(), pk=pk)
    project.deleted_at = timezone.now()
    project.save(update_fields=['deleted_at'])
    log_activity(request, 'Flyttet prosjekt til papirkurven', project.title, reverse('dashboard_project_trash'))
    messages.success(request, f'«{project.title}» ble flyttet til papirkurven. Du kan gjenopprette det derfra.')
    return redirect(reverse('dashboard_projects'))


@staff_required
def dashboard_project_trash(request):
    projects = Project.objects.filter(deleted_at__isnull=False).order_by('-deleted_at')
    return render(request, 'dashboard/project_trash.html', {'projects': projects})


@staff_required
@require_POST
def dashboard_project_restore(request, pk):
    project = get_object_or_404(Project, pk=pk, deleted_at__isnull=False)
    project.deleted_at = None
    project.save(update_fields=['deleted_at'])
    log_activity(request, 'Gjenopprettet prosjekt', project.title, reverse('dashboard_project_edit', args=[project.pk]))
    messages.success(request, f'«{project.title}» ble gjenopprettet.')
    return redirect(reverse('dashboard_project_trash'))


def delete_project_files(project):
    files = [project.image, project.og_image] + [img.image for img in project.gallery_images.all()]
    for field_file in files:
        if field_file:
            field_file.delete(save=False)


@staff_required
@require_POST
def dashboard_project_purge(request, pk):
    project = get_object_or_404(Project, pk=pk, deleted_at__isnull=False)
    title = project.title
    delete_project_files(project)
    project.delete()
    log_activity(request, 'Slettet prosjekt permanent', title)
    messages.success(request, f'«{title}» ble slettet permanent.')
    return redirect(reverse('dashboard_project_trash'))


@staff_required
@require_POST
def dashboard_project_image_delete(request, pk):
    image = get_object_or_404(ProjectImage, pk=pk)
    project = image.project
    image.image.delete(save=False)
    image.delete()
    log_activity(request, 'Slettet bilde fra galleriet', project.title, reverse('dashboard_project_edit', args=[project.pk]))
    messages.success(request, 'Bildet ble slettet.')
    return redirect(reverse('dashboard_project_edit', args=[project.pk]))


# ------------------------------------------------------------------
# Plots
# ------------------------------------------------------------------

@staff_required
def dashboard_plots(request):
    plots = Plot.objects.select_related('project')
    status = request.GET.get('status', '')
    if status in dict(Plot.STATUS_CHOICES):
        plots = plots.filter(status=status)
    else:
        status = ''
    return render(request, 'dashboard/plots.html', {
        'plots': plots,
        'status': status,
        'statuses': Plot.STATUS_CHOICES,
    })


def other_plots_on_map(plot=None):
    """The other plots, drawn faintly in the plot form's map so a new one can be placed beside them."""
    plots = Plot.objects.filter(map_x__isnull=False, map_y__isnull=False)
    if plot is not None:
        plots = plots.exclude(pk=plot.pk)
    return [{'number': p.number, 'x': p.map_x, 'y': p.map_y, 'rotation': p.map_rotation} for p in plots]


@staff_required
def dashboard_plot_create(request):
    form = PlotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plot = form.save(commit=False)
        plot.order = next_order(Plot)
        plot.save()
        log_activity(request, 'La til tomt', str(plot), reverse('dashboard_plot_edit', args=[plot.pk]))
        messages.success(request, f'«{plot}» ble lagt til.')
        return redirect(reverse('dashboard_plots'))
    return render(request, 'dashboard/plot_form.html', {'form': form, 'plot': None, 'map_plots': other_plots_on_map()})


@staff_required
def dashboard_plot_edit(request, pk):
    plot = get_object_or_404(Plot, pk=pk)
    form = PlotForm(request.POST or None, instance=plot)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_activity(request, 'Oppdaterte tomt', str(plot), reverse('dashboard_plot_edit', args=[plot.pk]))
        messages.success(request, f'«{plot}» ble oppdatert.')
        return redirect(reverse('dashboard_plots'))
    return render(request, 'dashboard/plot_form.html', {'form': form, 'plot': plot, 'map_plots': other_plots_on_map(plot)})


@staff_required
@require_POST
def dashboard_plot_status(request, pk):
    """Quick status change from the list: Ledig / Reservert / Solgt."""
    plot = get_object_or_404(Plot, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Plot.STATUS_CHOICES) and new_status != plot.status:
        plot.status = new_status
        plot.save(update_fields=['status', 'updated_at'])
        log_activity(request, f'Endret tomt til «{plot.get_status_display()}»', str(plot),
                     reverse('dashboard_plot_edit', args=[plot.pk]))
        messages.success(request, f'«{plot}» er nå {plot.get_status_display().lower()}.')
    return redirect(reverse('dashboard_plots'))


@staff_required
@require_POST
def dashboard_plot_delete(request, pk):
    plot = get_object_or_404(Plot, pk=pk)
    name = str(plot)
    plot.delete()
    log_activity(request, 'Slettet tomt', name)
    messages.success(request, f'«{name}» ble slettet.')
    return redirect(reverse('dashboard_plots'))


# ------------------------------------------------------------------
# News (blog)
# ------------------------------------------------------------------

@staff_required
def dashboard_blog(request):
    return render(request, 'dashboard/blog.html', {'posts': Blog.objects.all()})


@staff_required
def dashboard_blog_create(request):
    form = BlogForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save()
        state = 'publisert' if post.is_published else 'lagret som utkast'
        log_activity(request, f'Opprettet nyhet ({state})', post.title, reverse('dashboard_blog_edit', args=[post.pk]))
        messages.success(request, f'Nyheten ble {state}.')
        return redirect(reverse('dashboard_blog_edit', args=[post.pk]))
    return render(request, 'dashboard/blog_form.html', {'form': form, 'post': None})


@staff_required
def dashboard_blog_edit(request, pk):
    post = get_object_or_404(Blog, pk=pk)
    form = BlogForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_activity(request, 'Oppdaterte nyhet', post.title, reverse('dashboard_blog_edit', args=[post.pk]))
        messages.success(request, 'Nyheten ble oppdatert.')
        return redirect(reverse('dashboard_blog_edit', args=[post.pk]))
    return render(request, 'dashboard/blog_form.html', {'form': form, 'post': post})


@staff_required
@require_POST
def dashboard_blog_delete(request, pk):
    post = get_object_or_404(Blog, pk=pk)
    title = post.title
    if post.image:
        post.image.delete(save=False)
    post.delete()
    log_activity(request, 'Slettet nyhet', title)
    messages.success(request, f'«{title}» ble slettet.')
    return redirect(reverse('dashboard_blog'))


# ------------------------------------------------------------------
# Activity log
# ------------------------------------------------------------------

@staff_required
def dashboard_activity(request):
    since = timezone.now() - timedelta(days=7)
    return render(request, 'dashboard/activity.html', {
        'entries': ActivityLog.objects.select_related('user')[:ACTIVITY_PAGE_SIZE],
        'failed_logins': LoginAttempt.objects.filter(success=False, created_at__gte=since).count(),
    })
