from apps.core.models import Inquiry


def dashboard(request):
    """Unread-inquiry count for the sidebar badge (dashboard pages only)."""
    if not request.path.startswith('/dashboard/') or not getattr(request, 'user', None):
        return {}
    if not (request.user.is_authenticated and request.user.is_staff):
        return {}
    return {
        'sidebar_unread': Inquiry.objects.filter(is_read=False, is_spam=False, is_archived=False).count(),
    }
