"""E-mail heads-up to the client when a new inquiry arrives.

Off unless both EMAIL_HOST and INQUIRY_NOTIFY_EMAILS are set in .env. The inquiry is
already saved in the dashboard before this runs, so a mail server problem never loses it.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db import close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone

from .seo import site_url

log = logging.getLogger(__name__)


def is_configured():
    return bool(settings.EMAIL_HOST and settings.INQUIRY_NOTIFY_EMAILS)


def inquiry_text(inquiry):
    """Plain-text e-mail body: every field by name, plus a link straight to the dashboard."""
    received = timezone.localtime(inquiry.created_at).strftime('%d.%m.%Y kl. %H:%M')
    dashboard_url = site_url() + reverse('dashboard_inquiry_detail', args=[inquiry.pk])
    return '\n'.join([
        'Ny henvendelse fra nettsiden til Brakastølen',
        '',
        f'Navn: {inquiry.name}',
        f'E-post: {inquiry.email}',
        f'Telefon: {inquiry.phone or "–"}',
        f'Interessert i: {inquiry.get_interest_display()}',
        f'Tomt: {inquiry.plot}' if inquiry.plot else 'Tomt: –',
        f'Mottatt: {received}',
        '',
        inquiry.message or '(ingen beskjed)',
        '',
        f'Åpne i dashbordet: {dashboard_url}',
    ])


def send_now(inquiry_id):
    from .models import Inquiry
    try:
        inquiry = Inquiry.objects.filter(pk=inquiry_id).first()
        if inquiry is None:
            return
        send_mail(
            subject=f'Ny henvendelse: {inquiry.name} ({inquiry.get_interest_display().lower()})',
            message=inquiry_text(inquiry),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.INQUIRY_NOTIFY_EMAILS,
        )
    except Exception:  # a broken mail server must never reach the visitor; the inquiry is saved
        log.exception('Could not send e-mail for inquiry %s', inquiry_id)
    finally:
        close_old_connections()


def send_inquiry(inquiry):
    """Send after the inquiry is committed, in the background so the visitor never waits."""
    if not is_configured():
        return
    transaction.on_commit(
        lambda: threading.Thread(target=send_now, args=(inquiry.pk,), daemon=True).start()
    )
