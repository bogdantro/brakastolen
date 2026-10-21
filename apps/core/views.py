import logging
import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.cache import never_cache

from apps.blog.models import Blog

from . import notify
from .forms import InquiryForm
from .models import Inquiry, Plot
from .seo import BUSINESS, FAQ, PARTNERS, site_url

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Error pages
# ------------------------------------------------------------------

def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    # The full page needs the nav, footer and context processors. If any of that is
    # what broke, fall back to a standalone page so visitors still get a phone number.
    try:
        return render(request, '500.html', status=500)
    except Exception:
        log.exception('500 page failed, showing the standalone fallback')
        return HttpResponseServerError(render_to_string('500-fallback.html', {'business': BUSINESS}))


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------

HERO_EXTENSIONS = ('.webp', '.jpg', '.jpeg', '.png')


def natural_key(name):
    """'hero-10.jpg' sorts after 'hero-2.jpg'."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', name)]


def hero_images():
    """Every image in static/images/hero, in natural order (hero-2 before hero-10), so the
    client adds a hero photo by dropping a file in the folder. The ?v= part changes when a
    file is replaced, so browsers never show an old cached photo."""
    folder = finders.find('images/hero')
    if not folder:
        return []
    files = sorted((f for f in os.listdir(folder) if f.lower().endswith(HERO_EXTENSIONS)), key=natural_key)
    return [
        f"{static('images/hero/' + name)}?v={int(os.path.getmtime(os.path.join(folder, name)))}"
        for name in files
    ]


def plot_picker_context():
    """What core/plot-picker.html needs. Pages that include it must be @never_cache,
    because its viewing form carries a CSRF token."""
    plots = Plot.objects.public().select_related('category')
    return {
        'picker_plots': [plot.as_picker_data() for plot in plots],
        'picker_form': InquiryForm(initial={'interest': 'viewing'}, auto_id='picker_%s'),
    }


@never_cache  # the plot picker's viewing form carries a CSRF token, which must never be stale
def hjemme(request):
    return render(request, 'core/index.html', {
        'hero_images': hero_images(),
        'latest_posts': Blog.objects.public()[:3],
        'faq': FAQ,
        **plot_picker_context(),
    })


@never_cache  # the plot picker's viewing form carries a CSRF token, which must never be stale
def tomter(request):
    plots = Plot.objects.public().select_related('category')
    return render(request, 'core/tomter.html', {
        'plots': plots,
        'available_plots': plots.filter(status='available').count(),
        'faq': FAQ[:4],
        **plot_picker_context(),
    })


def hytter(request):
    return render(request, 'core/hytter.html', {'partners': PARTNERS})


def om_vaset(request):
    return render(request, 'core/om-vaset.html')


def aktiviteter(request):
    return render(request, 'core/aktiviteter.html')


def om_oss(request):
    return render(request, 'core/om-oss.html', {'partners': PARTNERS})


def personvern(request):
    return render(request, 'core/personvern.html')


# ------------------------------------------------------------------
# Contact form
# ------------------------------------------------------------------

INQUIRY_RATE_LIMIT = 10       # inquiries per IP ...
INQUIRY_RATE_WINDOW = 60 * 60  # ... per hour; more than that counts as one spam signal


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or ''


def over_rate_limit(request):
    key = f'inquiry-rate:{client_ip(request)}'
    cache.add(key, 0, INQUIRY_RATE_WINDOW)
    try:
        count = cache.incr(key)
    except ValueError:  # the key expired between add() and incr()
        count = 1
    return count > INQUIRY_RATE_LIMIT


def wants_json(request):
    """The plot picker sends the viewing form in the background and asks for JSON."""
    return 'application/json' in request.headers.get('Accept', '')


@never_cache  # an old cached copy would carry a stale CSRF token and fail on submit
def kontakt(request):
    if request.method == 'POST':
        form = InquiryForm(request.POST)
        if not form.is_valid() and wants_json(request):
            errors = {name: [str(e) for e in errs] for name, errs in form.errors.items()}
            return JsonResponse({'error': 'Noe må rettes før forespørselen kan sendes.', 'fields': errors}, status=400)
        if form.is_valid():
            inquiry = form.save(commit=False)
            # Spam is kept out of the inbox, but the bot still sees the normal thank-you.
            # It lands in the dashboard's Spam folder, so a wrongly flagged customer is never lost.
            extra = ['many inquiries from same address'] if over_rate_limit(request) else []
            reason = form.spam_reason(extra)
            inquiry.is_spam = bool(reason)
            inquiry.spam_reason = reason[:200]
            inquiry.save()
            if reason:
                log.warning('Inquiry %s marked as spam: %s', inquiry.pk, reason)
            else:
                notify.send_inquiry(inquiry)
            thanks = 'Takk for henvendelsen! Vi tar kontakt med deg så snart som mulig.'
            if wants_json(request):
                return JsonResponse({'ok': True, 'message': thanks})
            messages.success(request, thanks)
            return redirect(reverse('kontakt'))
    else:
        # "Avtal visning" links to /kontakt/?interesse=viewing so the right choice is ready
        interest = request.GET.get('interesse', '')
        initial = {'interest': interest} if interest in dict(Inquiry.INTEREST_CHOICES) else {}
        form = InquiryForm(initial=initial)
    return render_kontakt(request, form)


def render_kontakt(request, form, status=200, csrf_expired=False):
    response = render(request, 'core/kontakt.html', {
        'form': form,
        'csrf_expired': csrf_expired,
        **plot_picker_context(),
    }, status=status)
    add_never_cache_headers(response)
    return response


def csrf_failure(request, reason=''):
    """The contact form's token no longer matches the cookie – usually an old tab, the back
    button, or a dashboard login in another tab. Instead of a bare 403, give the visitor the
    form back with what they typed and a fresh token, so one more click sends it."""
    if request.method == 'POST' and request.path == reverse('kontakt'):
        fields = InquiryForm._meta.fields
        form = InquiryForm(initial={name: request.POST.get(name, '') for name in fields})
        return render_kontakt(request, form, status=403, csrf_expired=True)
    return default_csrf_failure(request, reason)


# ------------------------------------------------------------------
# SEO files: robots.txt and llms.txt
# ------------------------------------------------------------------

AI_CRAWLERS = [
    'GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-User', 'Claude-SearchBot',
    'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'CCBot', 'Bingbot',
]

LLMS_FULL_CACHE_SECONDS = 60 * 60


def favicon(request):
    """Browsers ask for /favicon.ico by themselves (e.g. on the sitemap), whatever the page links to.
    static() gives the live file name, with its content hash."""
    return redirect(static('images/favicon/favicon.ico'), permanent=True)


def robots_txt(request):
    if not settings.ALLOW_INDEXING:
        # Test/staging domain: keep every search engine and AI crawler out
        return HttpResponse('User-agent: *\nDisallow: /\n', content_type='text/plain; charset=utf-8')
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /dashboard/',
        'Disallow: /admin/',
        '',
        '# AI assistants and AI search are welcome to read and cite the site',
    ]
    for bot in AI_CRAWLERS:
        lines += [f'User-agent: {bot}', 'Allow: /', 'Disallow: /dashboard/', 'Disallow: /admin/', '']
    lines += [f'Sitemap: {site_url()}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


def llms_txt(request):
    """A plain-text summary for AI assistants (https://llmstxt.org)."""
    from .llms import build_llms_summary
    return HttpResponse(build_llms_summary(), content_type='text/plain; charset=utf-8')


def llms_full_txt(request):
    """Full text of every public page for AI assistants. Cached for an hour."""
    from .llms import build_llms_full
    text = cache.get('llms_full_txt')
    if text is None:
        text = build_llms_full()
        cache.set('llms_full_txt', text, LLMS_FULL_CACHE_SECONDS)
    return HttpResponse(text, content_type='text/plain; charset=utf-8')
