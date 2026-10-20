"""Spam rules for the contact form: block bots, never hide a real customer.

Bot checks (honeypot, signed timestamp, too fast) are certain, so each one alone marks spam.
Content checks are guesses, so it takes two or more of them together. Spam is never
thrown away – it is stored in the dashboard's Spam folder with the reason.
"""
import re
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.core import signing

# People need several seconds to fill in the form; bots post almost instantly.
# Kept low because browser autofill can fill everything but the message in a moment.
MIN_FILL_SECONDS = 2
FORM_TOKEN_SALT = 'kontakt-form-ts'
# Only real links count: "https://…", "www.…" or HTML/BBCode. A missing space after a full stop
# ("tomt.Har dere visning?") or an initial ("Ola N.Nordmann") must never look like a link.
LINK_RE = re.compile(r'(?:https?://|www\.)[^\s<>"\']+', re.I)
MARKUP_LINK_RE = re.compile(r'\[url|<a\s', re.I)
# Buyers often paste a Finn ad or a cabin supplier's page; those never count.
TRUSTED_LINK_DOMAINS = (
    'finn.no', 'brakastolen.no', 'xn--brakastlen-6cb.no', 'tindehytter.no', 'levehytter.no',
)
# Cyrillic or CJK text: common in spam, but a real buyer may write e.g. Ukrainian,
# so on its own it is only one signal.
FOREIGN_SCRIPT_RE = re.compile(r'[Ѐ-ӿ぀-ヿ一-鿿가-힯]')
SPAM_WORDS = re.compile(
    r'\b(seo|backlinks?|crypto|bitcoin|casino|viagra|cialis|loan offer|guest post|'
    r'rank(ing)? (your|on) google|web ?design services|lead generation|whatsapp me)\b', re.I)
SOFT_SIGNALS_FOR_SPAM = 2


def trusted_domains():
    own = urlsplit(getattr(settings, 'SITE_URL', '') or '').hostname or ''
    return tuple(d for d in (own.removeprefix('www.'), *TRUSTED_LINK_DOMAINS) if d)


def is_trusted(link):
    if not re.match(r'https?://', link, re.I):
        link = 'http://' + link
    host = (urlsplit(link).hostname or '').lower()
    # endswith('.' + d), not endswith(d): "evilfinn.no" must not pass as finn.no
    return any(host == d or host.endswith('.' + d) for d in trusted_domains())


def untrusted_link_count(text):
    """Links in the text that point anywhere but our own site, Finn or the cabin suppliers."""
    untrusted = [link for link in LINK_RE.findall(text or '') if not is_trusted(link)]
    # HTML/BBCode links are spam whatever they point to
    return len(untrusted) + len(MARKUP_LINK_RE.findall(text or ''))


def make_form_token():
    return signing.dumps(time.time(), salt=FORM_TOKEN_SALT)


def bot_reason(data, token):
    """Certain signs of a bot, or ''."""
    if data.get('hp_check'):
        return 'honeypot'
    try:
        started = signing.loads(token or '', salt=FORM_TOKEN_SALT)
    except signing.BadSignature:
        return 'missing token'
    if time.time() - float(started) < MIN_FILL_SECONDS:
        return 'too fast'
    return ''


def content_signals(data):
    """Things real spam usually has. Each one alone is fine."""
    name, message = data.get('name', ''), data.get('message', '')
    signals = []
    if untrusted_link_count(name):
        signals.append('link in name')
    if untrusted_link_count(message) >= 2:
        signals.append('links in message')
    if FOREIGN_SCRIPT_RE.search(name + message):
        signals.append('foreign script')
    if SPAM_WORDS.search(message):
        signals.append('spam words')
    return signals


def spam_reason(data, token, extra_signals=()):
    """Why a submission looks like spam, or '' if it should reach the inbox."""
    reason = bot_reason(data, token)
    if reason:
        return reason
    signals = content_signals(data) + list(extra_signals)
    if len(signals) >= SOFT_SIGNALS_FOR_SPAM:
        return ', '.join(signals)
    return ''
