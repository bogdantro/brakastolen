"""Content the client manages in the dashboard: inquiries and the plots for sale."""
from django.conf import settings
from django.db import models

from .text import format_nok, format_number


# ------------------------------------------------------------------
# Inquiries from the contact form
# ------------------------------------------------------------------

class Inquiry(models.Model):
    # A sale of a plot or cabin goes through these steps
    STATUS_CHOICES = [
        ('new', 'Ny'),
        ('contacted', 'Kontaktet'),
        ('viewing', 'Visning avtalt'),
        ('prospectus_sent', 'Prospekt sendt'),
        ('won', 'Solgt'),
        ('lost', 'Tapt'),
    ]
    INTEREST_CHOICES = [
        ('plot', 'Tomt'),
        ('plot_and_cabin', 'Tomt med nøkkelferdig hytte'),
        ('viewing', 'Visning'),
        ('prospectus', 'Prospekt'),
        ('other', 'Annet'),
    ]

    name = models.CharField('Navn', max_length=150)
    email = models.EmailField('E-post')
    phone = models.CharField('Telefon', max_length=30, blank=True)
    interest = models.CharField('Interessert i', max_length=20, choices=INTEREST_CHOICES, default='plot')
    message = models.TextField('Beskjed', blank=True)
    consent = models.BooleanField('Godtok personvernerklæringen', default=False)
    # Set when the inquiry was sent from a plot in the plot picker on the homepage
    plot = models.ForeignKey('Plot', verbose_name='Tomt', related_name='inquiries',
                             null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='new')
    is_read = models.BooleanField('Lest', default=False)
    is_archived = models.BooleanField('Arkivert', default=False)
    is_spam = models.BooleanField('Spam', default=False)
    # Why the spam check flagged it, so a wrongly flagged customer is easy to spot
    spam_reason = models.CharField('Spam-grunn', max_length=200, blank=True)
    created_at = models.DateTimeField('Mottatt', auto_now_add=True)

    class Meta:
        verbose_name = 'Henvendelse'
        verbose_name_plural = 'Henvendelser'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.created_at:%d.%m.%Y})'


class InquiryNote(models.Model):
    inquiry = models.ForeignKey(Inquiry, related_name='notes', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    text = models.TextField('Notat')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notat'
        verbose_name_plural = 'Notater'
        ordering = ['-created_at']

    def __str__(self):
        return f'Notat for {self.inquiry.name}'

    @property
    def author_name(self):
        """'Haakon Edland', 'haakon', or 'Ukjent' when the author's user has been deleted."""
        if self.author is None:
            return 'Ukjent'
        return self.author.get_full_name() or self.author.username


# ------------------------------------------------------------------
# Plots (tomter)
# ------------------------------------------------------------------

class PlotQuerySet(models.QuerySet):
    def public(self):
        """The plots visitors see – all of them, sold ones included, so the map stays complete."""
        return self.all()

    def available(self):
        return self.filter(status='available')


class PlotCategory(models.Model):
    """A grouping of plots the client chooses, e.g. «Byggetrinn 1» – shown with each plot."""
    name = models.CharField('Navn', max_length=80, unique=True)
    order = models.PositiveIntegerField('Rekkefølge', default=0)

    class Meta:
        verbose_name = 'Tomtekategori'
        verbose_name_plural = 'Tomtekategorier'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Plot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Ledig'),
        ('reserved', 'Reservert'),
        ('sold', 'Solgt'),
    ]

    category = models.ForeignKey(
        PlotCategory, related_name='plots', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Kategori',
    )
    number = models.CharField('Tomtenummer', max_length=20)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='available')
    area_m2 = models.PositiveIntegerField('Tomteareal (m²)', null=True, blank=True)
    price = models.PositiveIntegerField('Pris (kr)', null=True, blank=True)
    altitude = models.PositiveSmallIntegerField('Høyde (moh.)', null=True, blank=True)
    note = models.CharField('Merknad', max_length=200, blank=True)
    # Where the plot sits in the plot picker's map (units of its 960 × 760 drawing).
    # Set by clicking on the map in the dashboard; plots without a position are only listed.
    map_x = models.FloatField('Plassering i kartet (x)', null=True, blank=True)
    map_y = models.FloatField('Plassering i kartet (y)', null=True, blank=True)
    map_rotation = models.FloatField('Rotasjon i kartet (grader)', default=-20)
    # The plot's real outline from the site plan, as SVG path data in the same units.
    # Plots without one are drawn as a standard parcel at map_x / map_y.
    map_shape = models.TextField('Omriss i kartet', blank=True)
    order = models.PositiveIntegerField('Rekkefølge', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PlotQuerySet.as_manager()

    class Meta:
        verbose_name = 'Tomt'
        verbose_name_plural = 'Tomter'
        ordering = ['order', 'number']

    def __str__(self):
        return f'Tomt {self.number}'

    @property
    def group_name(self):
        """'Byggetrinn 1', or '' for a plot without a category."""
        return self.category.name if self.category else ''

    @property
    def price_display(self):
        """900000 -> '900 000 kr'."""
        return format_nok(self.price)

    @property
    def area_display(self):
        """1400 -> '1 400 m²'."""
        return f'{format_number(self.area_m2)} m²' if self.area_m2 else ''

    @property
    def is_on_map(self):
        return self.map_x is not None and self.map_y is not None

    def as_picker_data(self):
        """What the plot picker on the homepage needs, as plain JSON-friendly values."""
        return {
            'id': self.pk,
            'number': self.number,
            'group': self.group_name,
            'status': self.status,
            'statusLabel': self.get_status_display(),
            'area': self.area_m2,
            'price': self.price,
            'altitude': self.altitude,
            'note': self.note,
            'x': self.map_x,
            'y': self.map_y,
            'rotation': self.map_rotation,
            'shape': self.map_shape,
        }
