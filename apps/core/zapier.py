"""New inquiries to Zapier, which e-mails them (or texts, or posts to Slack) – the site itself
sends no e-mail.

Contract with the Zap: every real inquiry from the contact page or the plot picker is POSTed as
JSON to ZAPIER_WEBHOOK_URL (.env), right after it is saved. The keys are flat and readable, so
they show up by name in Zapier ("name", "phone_display", "plot", …), plus ready-made pieces:

    email_subject   "Ny henvendelse: Kari Nordmann – visning av tomt 21"
    email_html      the whole e-mail body (the Zap's "Body" field, type HTML)
    reply_to        the customer's address, so «Svar» in the mail client answers them
    summary_text    a few lines for an SMS or a Slack message

Spam is not sent: it stays in the dashboard's Spam folder. Without a URL nothing is sent and
nothing breaks. The post runs in a background thread after the database commit, so the visitor
never waits for Zapier, and a Zapier outage only costs the notice – the inquiry is always saved.
"""
import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.db import close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format as format_date
from django.utils.html import escape, linebreaks

from .models import Inquiry
from .seo import BUSINESS, site_url
from .text import format_phone

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10

# The white deer logo, as the live site serves it. A fixed address rather than one built from
# SITE_URL: mail clients load it days later, from wherever the mail is read, and the address
# must keep working even while a domain still points at the old website.
EMAIL_LOGO_URL = 'https://brakastolen.no/static/images/logo/tranberg-hjort-hvit.77960ac87d7f.png'

# E-mail colours: the site's brand green, frost-blue details and cool greys (inline styles only –
# mail clients ignore stylesheets)
GREEN = '#002223'
ACCENT = '#9CC3D0'
TEXT = '#111A1D'
MUTED = '#4B5A61'
LINE = '#E1E7EA'
PAGE = '#F3F6F7'


def is_configured():
    return bool(getattr(settings, 'ZAPIER_WEBHOOK_URL', ''))


def send_inquiry(inquiry):
    """Queue the notice for a saved inquiry. Call it from the view; returns at once."""
    if inquiry.is_spam or not is_configured():
        return
    pk = inquiry.pk
    transaction.on_commit(lambda: threading.Thread(target=post_inquiry, args=(pk,), daemon=True).start())


def post_inquiry(pk):
    """Build the payload for inquiry `pk` and POST it. Runs in the background thread."""
    try:
        inquiry = Inquiry.objects.select_related('plot').get(pk=pk)
        body = json.dumps(payload(inquiry)).encode('utf-8')
        request = urllib.request.Request(settings.ZAPIER_WEBHOOK_URL, data=body, method='POST',
                                         headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            log.info('Inquiry %s sent to Zapier (%s)', pk, response.status)
    except (urllib.error.URLError, OSError, ValueError):
        # urlopen raises HTTPError (a URLError) for 4xx/5xx – the inquiry itself is saved
        log.exception('Could not send inquiry %s to Zapier', pk)
    except Exception:  # a background thread must never die silently – log whatever it was
        log.exception('Unexpected error sending inquiry %s to Zapier', pk)
    finally:
        close_old_connections()


# ------------------------------------------------------------------
# The payload
# ------------------------------------------------------------------

def payload(inquiry):
    """Everything the Zap needs, as flat, readable keys. Values are plain text; email_html is
    the only HTML, and every value in it is escaped."""
    first_name = inquiry.name.split()[0] if inquiry.name.split() else inquiry.name
    phone_display, phone_link = format_phone(inquiry.phone) if inquiry.phone else ('', '')
    received = timezone.localtime(inquiry.created_at)
    plot = inquiry.plot
    interest = inquiry.get_interest_display()

    subject_topic = f'{interest.lower()} av {str(plot).lower()}' if plot and inquiry.interest == 'viewing' \
        else (f'{interest.lower()}, {str(plot).lower()}' if plot else interest.lower())
    reply_body = (f'Hei {first_name},\n\nTakk for henvendelsen til Brakastølen!\n\n\n\n'
                  f'Med vennlig hilsen\n{BUSINESS["contact_name"]}\n{BUSINESS["company"]}\n{BUSINESS["phone_display"]}')

    data = {
        'id': inquiry.pk,
        'received': f'{format_date(received, "j. F Y")} kl. {received:%H:%M}',
        'received_iso': received.isoformat(),
        'source': 'Tomtevelgeren på forsiden' if plot else 'Kontaktskjemaet',
        'name': inquiry.name,
        'first_name': first_name,
        'email': inquiry.email,
        'phone': inquiry.phone,
        'phone_display': phone_display,
        'interest': interest,
        'message': inquiry.message,
        'plot': str(plot) if plot else '',
        'plot_street': plot.street if plot else '',
        'plot_area': plot.area_display if plot else '',
        'plot_price': plot.price_display if plot else '',
        'plot_status': plot.get_status_display() if plot else '',
        'plot_map_url': (f'https://www.google.com/maps/search/?api=1&query={plot.latlon[0]}%2C{plot.latlon[1]}'
                         if plot and plot.is_on_map else ''),
        # One tap to call, text or answer
        'tel_link': f'tel:{phone_link}' if phone_link else '',
        'sms_link': f'sms:{phone_link}' if phone_link else '',
        'mailto_link': 'mailto:{}?{}'.format(inquiry.email, urllib.parse.urlencode(
            {'subject': 'Din henvendelse til Brakastølen', 'body': reply_body}, quote_via=urllib.parse.quote)),
        'dashboard_url': site_url() + reverse('dashboard_inquiry_detail', args=[inquiry.pk]),
        'email_subject': f'Ny henvendelse: {inquiry.name} – {subject_topic}',
        'reply_to': inquiry.email,
    }
    data['summary_text'] = summary_text(data)
    data['email_html'] = email_html(data)
    return data


def summary_text(data):
    """'Ny henvendelse fra Kari Nordmann (912 34 567) – Visning, Tomt 21. Se: https://…'"""
    who = data['name'] + (f' ({data["phone_display"]})' if data['phone_display'] else '')
    what = ', '.join(filter(None, [data['interest'], data['plot']]))
    return f'Ny henvendelse fra {who} – {what}. Se: {data["dashboard_url"]}'


# ------------------------------------------------------------------
# The e-mail body: table layout and inline styles, so it looks the same in Outlook, Gmail and
# on the phone. Every value from the form goes through escape().
# ------------------------------------------------------------------

def email_html(data):
    logo = EMAIL_LOGO_URL
    rows = [
        ('Navn', escape(data['name'])),
        ('E-post', f'<a href="mailto:{escape(data["email"])}" style="color:{GREEN};">{escape(data["email"])}</a>'),
        ('Telefon', f'<a href="{escape(data["tel_link"])}" style="color:{GREEN};">{escape(data["phone_display"])}</a>'
         if data['tel_link'] else '<span style="color:#7A868C;">Ikke oppgitt</span>'),
        ('Gjelder', escape(data['interest'])),
    ]
    if data['plot']:
        # Non-breaking spaces inside each fact, so «1 800 000 kr» never splits on a phone
        facts = ' · '.join(escape(value).replace(' ', '&nbsp;') for value in
                           [data['plot_street'], data['plot_area'], data['plot_price'], data['plot_status']] if value)
        plot = f'<strong>{escape(data["plot"])}</strong>' + (f'<br><span style="color:{MUTED};">{facts}</span>' if facts else '')
        if data['plot_map_url']:
            plot += f'<br><a href="{escape(data["plot_map_url"])}" style="color:{GREEN};">Se tomten i kart</a>'
        rows.append(('Tomt', plot))
    rows.append(('Mottatt', escape(data['received'])))

    table = ''.join(
        f'<tr><td style="padding:10px 0;border-top:1px solid {LINE};width:110px;vertical-align:top;'
        f'color:{MUTED};font-size:14px;">{label}</td>'
        f'<td style="padding:10px 0;border-top:1px solid {LINE};vertical-align:top;color:{TEXT};font-size:15px;">{value}</td></tr>'
        for label, value in rows
    )
    message = (linebreaks(escape(data['message'])).replace('<p>', '<p style="margin:0 0 12px;">')
               if data['message'] else f'<p style="margin:0;color:{MUTED};">Ingen beskjed.</p>')

    def button(href, text, solid):
        colours = (f'background:{GREEN};color:#ffffff;border:1px solid {GREEN};' if solid
                   else f'background:#ffffff;color:{GREEN};border:1px solid {GREEN};')
        return (f'<a href="{escape(href)}" style="display:inline-block;margin:0 8px 8px 0;padding:12px 20px;'
                f'{colours}border-radius:2px;font-size:15px;font-weight:600;text-decoration:none;">{text}</a>')

    buttons = button(data['mailto_link'], f'Svar {escape(data["first_name"])}', True)
    if data['tel_link']:
        buttons += button(data['tel_link'], 'Ring', False)
    buttons += button(data['dashboard_url'], 'Åpne i dashbordet', False)

    return f'''<!DOCTYPE html>
<html lang="nb"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(data['email_subject'])}</title></head>
<body style="margin:0;padding:0;background:{PAGE};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;font-family:Georgia,'Times New Roman',serif;">
  <tr><td style="background:{GREEN};padding:22px 28px;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:14px;"><img src="{escape(logo)}" width="44" alt="Brakastølen" style="display:block;width:44px;height:auto;border:0;"></td>
      <td><div style="color:#ffffff;font-size:22px;line-height:1;">{escape(BUSINESS['name'])}</div>
          <div style="color:{ACCENT};font-size:12px;letter-spacing:2px;margin-top:6px;">VASET · VALDRES</div></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:28px 28px 8px;">
    <p style="margin:0 0 6px;color:{MUTED};font-size:13px;letter-spacing:1px;text-transform:uppercase;">{escape(data['source'])}</p>
    <h1 style="margin:0 0 18px;color:{TEXT};font-size:26px;font-weight:normal;line-height:1.2;">Ny henvendelse fra {escape(data['name'])}</h1>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{table}</table>
  </td></tr>
  <tr><td style="padding:12px 28px 8px;">
    <p style="margin:0 0 8px;color:{MUTED};font-size:14px;">Beskjed</p>
    <div style="padding:16px 18px;background:{PAGE};border-left:3px solid {ACCENT};color:{TEXT};font-size:15px;line-height:1.55;">{message}</div>
  </td></tr>
  <tr><td style="padding:20px 28px 20px;">{buttons}</td></tr>
  <tr><td style="padding:18px 28px 24px;border-top:1px solid {LINE};color:#7A868C;font-size:12px;line-height:1.5;">
    Sendt automatisk fra nettsiden. Henvendelsen er også lagret i dashbordet under Henvendelser.
  </td></tr>
</table>
</td></tr>
</table>
</body></html>'''
