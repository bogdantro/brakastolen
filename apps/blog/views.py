import math

from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache

from apps.core.seo import site_url
from apps.core.views import plot_picker_context

from .models import Blog

WORDS_PER_MINUTE = 200


def reading_minutes(text):
    """A 450-word post -> 3."""
    words = len(strip_tags(text or '').split())
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def nyheter(request):
    posts = Blog.objects.public()
    return render(request, 'blog/nyheter.html', {'posts': posts})


def image_is_portrait(image):
    """Tall images (e.g. printed ads) are shown whole beside the text instead of cropped wide."""
    if not image:
        return False
    try:
        return image.height > image.width
    except (OSError, ValueError):  # missing or unreadable file: treat as a normal photo
        return False


@never_cache  # the plot picker's viewing form carries a CSRF token, which must never be stale
def nyhet_detail(request, pk, slug):
    is_staff = request.user.is_authenticated and request.user.is_staff
    # Staff can preview drafts; visitors only ever see published posts.
    posts = Blog.objects.all() if is_staff else Blog.objects.public()
    post = get_object_or_404(posts, pk=pk)
    if post.slug != slug:
        return redirect(post.get_absolute_url(), permanent=True)
    return render(request, 'blog/nyhet-detail.html', {
        'post': post,
        'post_image': post.image.url if post.image else '',
        'is_draft': not post.is_published,
        'more_posts': Blog.objects.public().exclude(pk=post.pk)[:3],
        'minutes': reading_minutes(post.text),
        'image_portrait': image_is_portrait(post.image),
        # From SITE_URL, never the request host, so a shared link always points at the real domain
        'share_url': site_url() + post.get_absolute_url(),
        **plot_picker_context(),
    })
