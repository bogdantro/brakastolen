"""The client's dashboard at /dashboard/: inquiries (a small sales CRM), the plots for
sale with their sales map, the field info under the plot map (costs, FINN ads, documents),
news posts and an activity log."""
import csv
import re
from datetime import timedelta
from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Max, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.blog.models import Blog
from apps.core.models import PLOT_STREETS, CostItem, FieldDocument, FinnAd, Inquiry, InquiryNote, Plot, PlotCategory
from apps.core.seo import BUSINESS
from apps.core.views import wants_json

from .forms import (
    BlogForm, CostItemForm, DashboardLoginForm, FieldDocumentForm, FinnAdForm, InquiryNoteForm, PlotBulkForm,
    PlotCategoryForm, PlotForm, PlotQuickForm,
)
from .models import ActivityLog, LoginAttempt
from .templatetags.dashboard_tags import millions

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


def unlink_activity(url):
    """After something is deleted, its old log entries keep their text but stop linking to a page that is gone."""
    ActivityLog.objects.filter(url=url).update(url='')


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
    hour = timezone.localtime().hour
    if 5 <= hour < 10:
        greeting = 'God morgen'
    elif 10 <= hour < 18:
        greeting = 'God dag'
    else:
        greeting = 'God kveld'  # also late at night, never "God dag" at 02:00
    return render(request, 'dashboard/home.html', {
        'greeting': greeting,
        'today': timezone.localdate(),
        'inquiry_count': inbox.count(),
        'unread_count': inbox.filter(is_read=False).count(),
        'open_count': inbox.filter(status__in=['new', 'contacted', 'viewing', 'prospectus_sent']).count(),
        'plot_summary': plot_summary(),
        'map_plots': plot_map_data(Plot.objects.select_related('category')),
        'latest_inquiries': inbox[:5],
        'weekly': weekly_inquiry_chart(),
        'statuses': status_breakdown(),
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
            unlink_activity(detail_url)
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
# Plots
# ------------------------------------------------------------------

PLOT_SORTS = {
    'number': 'Tomtenummer',
    'price': 'Pris, lavest først',
    'price_desc': 'Pris, høyest først',
    'area_desc': 'Størst først',
    'updated': 'Sist endret',
}


PLOT_STATUS_PLURALS = {'available': 'Ledige', 'reserved': 'Reserverte', 'sold': 'Solgte'}


def plot_number_key(plot):
    """'7' < '11' < 'T3': numbers in numeric order, then the rest alphabetically."""
    digits = re.match(r'\d+', plot.number)
    return (0, int(digits.group()), plot.number) if digits else (1, 0, plot.number)


def sort_plots(plots, sort):
    plots = sorted(plots, key=plot_number_key)
    if sort == 'price':
        plots.sort(key=lambda p: (p.price is None, p.price or 0))
    elif sort == 'price_desc':
        plots.sort(key=lambda p: p.price or 0, reverse=True)
    elif sort == 'area_desc':
        plots.sort(key=lambda p: p.area_m2 or 0, reverse=True)
    elif sort == 'updated':
        plots.sort(key=lambda p: p.updated_at, reverse=True)
    return plots


def plot_summary():
    """Counts per status and what the plots still for sale are worth, for the overview and the list."""
    counts = dict(Plot.objects.values_list('status').annotate(n=Count('id')))
    prices = list(Plot.objects.filter(status='available', price__isnull=False).values_list('price', flat=True))
    total = sum(counts.values())
    return {
        'total': total,
        'statuses': [
            {'key': key, 'label': label, 'plural': PLOT_STATUS_PLURALS[key], 'count': counts.get(key, 0),
             'share': round(counts.get(key, 0) / total * 100) if total else 0}
            for key, label in Plot.STATUS_CHOICES
        ],
        'available': counts.get('available', 0),
        'sold': counts.get('sold', 0),
        'available_value': sum(prices),
        'price_from': min(prices, default=None),
        'price_to': max(prices, default=None),
    }


def plot_map_data(plots):
    """The plots for the dashboard's sales map (dashboard.js), as plain JSON-friendly values."""
    return [{
        'id': plot.pk,
        'number': plot.number,
        'status': plot.status,
        'statusLabel': plot.get_status_display(),
        'price': plot.price_display,
        'area': plot.area_display,
        'category': plot.category.name if plot.category else '',
        'x': plot.map_x,
        'y': plot.map_y,
        'rotation': plot.map_rotation,
        'shape': plot.map_shape,
        'url': reverse('dashboard_plot_edit', args=[plot.pk]),
    } for plot in plots if plot.is_on_map]


def back_to_plots(request):
    """Where to return after a change from the list: the same filtered list, else the plain one."""
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return reverse('dashboard_plots')


@staff_required
def dashboard_plots(request):
    all_plots = Plot.objects.select_related('category')
    plots = all_plots
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'number')

    if status in dict(Plot.STATUS_CHOICES):
        plots = plots.filter(status=status)
    else:
        status = ''
    if category == 'none':
        plots = plots.filter(category__isnull=True)
    elif category.isdigit():
        plots = plots.filter(category_id=int(category))
    else:
        category = ''
    if q:
        plots = plots.filter(Q(number__icontains=q) | Q(note__icontains=q))
    if sort not in PLOT_SORTS:
        sort = 'number'

    return render(request, 'dashboard/plots.html', {
        'plots': sort_plots(plots, sort),
        'summary': plot_summary(),
        'map_plots': plot_map_data(all_plots),
        'categories': PlotCategory.objects.annotate(plot_count=Count('plots')),
        'uncategorised': all_plots.filter(category__isnull=True).count(),
        'statuses': Plot.STATUS_CHOICES,
        'sorts': PLOT_SORTS,
        'f': {'status': status, 'category': category, 'q': q, 'sort': sort},
        'filtered': any([status, category, q]),
        'this_url': request.get_full_path(),
    })


def plot_change_text(plot, name):
    """The activity log line for one changed field."""
    if name == 'status':
        return f'Markerte tomt {plot.number} som {plot.get_status_display().lower()}'
    if name == 'price':
        return f'Endret prisen på tomt {plot.number} til {plot.price_display or "ingen pris"}'
    if name == 'area_m2':
        return f'Endret størrelsen på tomt {plot.number} til {plot.area_display or "ukjent"}'
    if name == 'category':
        if plot.category:
            return f'Flyttet tomt {plot.number} til «{plot.category.name}»'
        return f'Fjernet kategorien på tomt {plot.number}'
    return f'Oppdaterte tomt {plot.number}'


def form_error_text(form):
    return ' '.join(str(error) for errors in form.errors.values() for error in errors)


@staff_required
@require_POST
def dashboard_plot_quick(request, pk):
    """Change one or more of status, price, size and category straight from the list.
    Answers with JSON for the list's autosave, or redirects back for a plain form post."""
    plot = get_object_or_404(Plot.objects.select_related('category'), pk=pk)
    names = [name for name in PlotQuickForm.EDITABLE if name in request.POST]
    as_json = wants_json(request)
    if not names:
        if as_json:
            return JsonResponse({'ok': False, 'error': 'Ingenting å lagre.'}, status=400)
        return redirect(back_to_plots(request))

    form = PlotQuickForm.for_fields(names, request.POST, instance=plot)
    if not form.is_valid():
        error = form_error_text(form)
        if as_json:
            return JsonResponse({'ok': False, 'error': error, 'fields': list(form.errors)}, status=400)
        messages.error(request, f'Tomt {plot.number} ble ikke lagret: {error}')
        return redirect(back_to_plots(request))

    changed = form.changed_data
    if changed:
        form.save()
        edit_url = reverse('dashboard_plot_edit', args=[plot.pk])
        for name in changed:
            log_activity(request, plot_change_text(plot, name), str(plot), edit_url)

    texts = [plot_change_text(plot, name) + '.' for name in changed]
    if as_json:
        summary = plot_summary()
        return JsonResponse({
            'ok': True,
            'changed': changed,
            'message': ' '.join(texts) or 'Ingen endring.',
            'plot': {
                'status': plot.status,
                'statusLabel': plot.get_status_display(),
                'price': plot.price,
                'priceDisplay': plot.price_display,
                'area': plot.area_m2,
                'category': plot.category_id,
                'categoryName': plot.category.name if plot.category else '',
            },
            # The figures above the list follow along without a reload
            'summary': {
                **{item['key']: item['count'] for item in summary['statuses']},
                'value': millions(summary['available_value']),
            },
        })
    if texts:
        messages.success(request, ' '.join(texts))
    return redirect(back_to_plots(request))


@staff_required
@require_POST
def dashboard_plots_bulk(request):
    """Mark several plots sold (or another status), or move them to a category, in one go."""
    data = request.POST.copy()
    # «Merk som Solgt» etc. are buttons named status; «Flytt» sends action=category
    data.setdefault('action', 'status')
    form = PlotBulkForm(data)
    if not form.is_valid():
        messages.error(request, form_error_text(form))
        return redirect(back_to_plots(request))

    plots = sorted(form.cleaned_data['plots'], key=plot_number_key)
    numbers = ', '.join(p.number for p in plots)
    count = len(plots)
    noun = 'tomt' if count == 1 else 'tomter'
    selected = Plot.objects.filter(pk__in=[p.pk for p in plots])

    if form.cleaned_data['action'] == 'status':
        new_status = form.cleaned_data['status']
        if not new_status:
            messages.error(request, 'Velg hvilken status tomtene skal få.')
            return redirect(back_to_plots(request))
        selected.update(status=new_status, updated_at=timezone.now())
        text = f'Markerte {count} {noun} som {dict(Plot.STATUS_CHOICES)[new_status].lower()}'
    else:
        category = form.cleaned_data['category']
        selected.update(category=category, updated_at=timezone.now())
        if category:
            text = f'Flyttet {count} {noun} til «{category.name}»'
        else:
            text = f'Fjernet kategorien på {count} {noun}'

    log_activity(request, text, f'tomt {numbers}', reverse('dashboard_plots'))
    messages.success(request, f'{text} ({numbers}).')
    return redirect(back_to_plots(request))


@staff_required
@require_POST
def dashboard_plot_categories(request):
    """Add, rename or delete a plot category. Deleting keeps the plots, just without a category."""
    action = request.POST.get('action')
    target = reverse('dashboard_plots') + '#kategorier'

    if action == 'add':
        form = PlotCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.order = next_order(PlotCategory)
            category.save()
            log_activity(request, 'La til tomtekategori', category.name, target)
            messages.success(request, f'Kategorien «{category.name}» ble lagt til.')
        else:
            messages.error(request, form_error_text(form))
        return redirect(target)

    category_id = request.POST.get('category_id', '')
    # A tampered or stale form must give a 404, not a crash on a non-number
    category = get_object_or_404(PlotCategory, pk=int(category_id) if category_id.isdigit() else 0)
    if action == 'rename':
        old_name = category.name
        form = PlotCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            if category.name != old_name:
                log_activity(request, f'Endret navn på tomtekategori fra «{old_name}»', category.name, target)
                messages.success(request, f'«{old_name}» heter nå «{category.name}».')
        else:
            messages.error(request, form_error_text(form))
    elif action == 'delete':
        name = category.name
        count = category.plots.count()
        category.delete()
        log_activity(request, 'Slettet tomtekategori', name, target)
        left = f' {count} {"tomt står" if count == 1 else "tomter står"} nå uten kategori.' if count else ''
        messages.success(request, f'«{name}» ble slettet.{left}')
    return redirect(target)


def street_names():
    """The streets offered in the plot form: the field's own, plus any typed in by hand."""
    typed = Plot.objects.exclude(street='').values_list('street', flat=True)
    return sorted(set(street for _, _, street in PLOT_STREETS) | set(typed))


def other_plots_on_map(plot=None):
    """The other plots, drawn faintly in the plot form's map so a new one can be placed beside them."""
    plots = Plot.objects.filter(map_x__isnull=False, map_y__isnull=False)
    if plot is not None:
        plots = plots.exclude(pk=plot.pk)
    return [{'number': p.number, 'x': p.map_x, 'y': p.map_y, 'rotation': p.map_rotation, 'shape': p.map_shape}
            for p in plots]


@staff_required
def dashboard_plot_create(request):
    form = PlotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plot = form.save(commit=False)
        plot.order = next_order(Plot)
        plot.save()
        log_activity(request, 'La til tomt', str(plot), reverse('dashboard_plot_edit', args=[plot.pk]))
        messages.success(request, f'Tomt {plot.number} ble lagt til.')
        return redirect(reverse('dashboard_plots'))
    return render(request, 'dashboard/plot_form.html', {'form': form, 'plot': None, 'map_plots': other_plots_on_map(),
                                                        'plot_streets': street_names()})


@staff_required
def dashboard_plot_edit(request, pk):
    plot = get_object_or_404(Plot, pk=pk)
    edit_url = reverse('dashboard_plot_edit', args=[plot.pk])
    form = PlotForm(request.POST or None, instance=plot)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_activity(request, 'Oppdaterte tomt', str(plot), edit_url)
        messages.success(request, f'Tomt {plot.number} ble oppdatert.')
        return redirect(reverse('dashboard_plots'))
    return render(request, 'dashboard/plot_form.html', {
        'form': form,
        'plot': plot,
        'map_plots': other_plots_on_map(plot),
        'plot_streets': street_names(),
        'inquiries': Inquiry.objects.filter(plot=plot, is_spam=False)[:10],
        'history': ActivityLog.objects.select_related('user').filter(url=edit_url)[:8],
    })


@staff_required
@require_POST
def dashboard_plot_delete(request, pk):
    plot = get_object_or_404(Plot, pk=pk)
    name = str(plot)
    unlink_activity(reverse('dashboard_plot_edit', args=[plot.pk]))
    plot.delete()
    log_activity(request, 'Slettet tomt', name)
    messages.success(request, f'«{name}» ble slettet.')
    return redirect(reverse('dashboard_plots'))


# ------------------------------------------------------------------
# The field: costs, FINN ads and documents shown under the plot map
# ------------------------------------------------------------------

def field_page(request, cost_forms=None, ad_forms=None, doc_forms=None, new_cost=None, new_ad=None, new_doc=None):
    """The page, with any form that just failed shown again with its errors."""
    cost_forms = cost_forms or {}
    ad_forms = ad_forms or {}
    doc_forms = doc_forms or {}
    costs = list(CostItem.objects.all())
    ads = list(FinnAd.objects.order_by('-category', 'order', '-created_at'))  # plots first, as on the website
    documents = list(FieldDocument.objects.all())
    fixed_total = sum(c.amount or 0 for c in costs if c.percent is None)
    return render(request, 'dashboard/field.html', {
        'costs': [(c, cost_forms.get(c.pk) or CostItemForm(instance=c, prefix=f'cost-{c.pk}')) for c in costs],
        'fixed_total': fixed_total,
        'new_cost': new_cost or CostItemForm(prefix='cost-new'),
        'ads': [(a, ad_forms.get(a.pk) or FinnAdForm(instance=a, prefix=f'ad-{a.pk}')) for a in ads],
        'new_ad': new_ad or FinnAdForm(prefix='ad-new', initial={'is_active': True}),
        'plot_ads': Plot.objects.exclude(finn_url='').select_related('category'),
        'documents': [(d, doc_forms.get(d.pk) or FieldDocumentForm(instance=d, prefix=f'doc-{d.pk}')) for d in documents],
        'new_doc': new_doc or FieldDocumentForm(prefix='doc-new', initial={'is_published': True}),
    })


# «cost_add», «ad_save», «doc_delete» … -> (model, form, form prefix, noun for the log, section on the page)
FIELD_ITEMS = {
    'cost': (CostItem, CostItemForm, 'cost', 'omkostning', 'omkostninger'),
    'ad': (FinnAd, FinnAdForm, 'ad', 'Finn-annonse', 'finn'),
    'doc': (FieldDocument, FieldDocumentForm, 'doc', 'dokument', 'dokumenter'),
}


@staff_required
def dashboard_field(request):
    if request.method != 'POST':
        return field_page(request)

    action = request.POST.get('action', '')
    kind, _, verb = action.partition('_')
    if kind not in FIELD_ITEMS or verb not in ('add', 'save', 'delete'):
        return redirect(reverse('dashboard_field'))
    model, form_class, prefix, noun, section = FIELD_ITEMS[kind]
    target = reverse('dashboard_field') + f'#{section}'

    if verb == 'add':
        form = form_class(request.POST, request.FILES, prefix=f'{prefix}-new')
        if not form.is_valid():
            messages.error(request, 'Noe må rettes – se feltet som er merket.')
            return field_page(request, **{f'new_{kind}': form})
        item = form.save(commit=False)
        item.order = next_order(model)
        item.save()
        log_activity(request, f'La til {noun}', str(item), target)
        messages.success(request, f'«{item}» ble lagt til.')
        return redirect(target)

    pk = request.POST.get('pk', '')
    item = get_object_or_404(model, pk=int(pk) if pk.isdigit() else 0)
    if verb == 'delete':
        name = str(item)
        if kind == 'doc':
            item.file.delete(save=False)
        item.delete()
        log_activity(request, f'Slettet {noun}', name, target)
        messages.success(request, f'«{name}» ble slettet.')
        return redirect(target)

    form = form_class(request.POST, request.FILES, instance=item, prefix=f'{prefix}-{item.pk}')
    if not form.is_valid():
        messages.error(request, 'Noe må rettes – se feltet som er merket.')
        return field_page(request, **{f'{kind}_forms': {item.pk: form}})
    if form.has_changed():
        old_file = item.file.name if kind == 'doc' else None
        form.save()
        if kind == 'doc' and old_file and old_file != item.file.name:
            item.file.storage.delete(old_file)  # a replaced document doesn't linger in media/
        log_activity(request, f'Oppdaterte {noun}', str(item), target)
        messages.success(request, f'«{item}» ble lagret.')
    return redirect(target)


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
    unlink_activity(reverse('dashboard_blog_edit', args=[post.pk]))
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
