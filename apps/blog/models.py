from django.db import models
from django.urls import reverse

from apps.core.text import norwegian_slugify


class BlogQuerySet(models.QuerySet):
    def public(self):
        """Only what visitors may see on the website."""
        return self.filter(is_published=True)


class Blog(models.Model):
    title = models.CharField('Tittel', max_length=300)
    # Rebuilt from the title on every save; the URL also has the id, so an old
    # link with the previous slug is redirected instead of breaking.
    slug = models.SlugField('URL-navn', max_length=350, blank=True)
    excerpt = models.CharField('Ingress', max_length=300, blank=True)
    text = models.TextField('Tekst')
    image = models.ImageField('Bilde', upload_to='blog/', blank=True)
    image_alt = models.CharField('Bildebeskrivelse', max_length=200, blank=True)
    author = models.CharField('Forfatter', max_length=70, blank=True)
    is_published = models.BooleanField('Publisert', default=True)
    meta_title = models.CharField('SEO-tittel', max_length=70, blank=True)
    meta_description = models.CharField('SEO-beskrivelse', max_length=160, blank=True)
    created_at = models.DateTimeField('Opprettet', auto_now_add=True)
    updated_at = models.DateTimeField('Sist endret', auto_now=True)

    objects = BlogQuerySet.as_manager()

    class Meta:
        verbose_name = 'Nyhet'
        verbose_name_plural = 'Nyheter'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = norwegian_slugify(self.title)[:350] or 'nyhet'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('nyhet_detail', args=[self.pk, self.slug])
