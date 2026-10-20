"""Content the client manages in the dashboard: inquiries, projects (cabin groups and
cabins) with photo galleries, and the individual plots for sale."""
from django.conf import settings
from django.db import models

from .text import format_nok, format_number, norwegian_slugify


def unique_slug(model, instance, value):
    """'Ulven hyttegrend' -> 'ulven-hyttegrend', or 'ulven-hyttegrend-2' if taken."""
    base_slug = norwegian_slugify(value) or 'side'
    slug, counter = base_slug, 1
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        counter += 1
        slug = f'{base_slug}-{counter}'
    return slug


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
# Projects: cabin groups (hyttegrender) and cabins
# ------------------------------------------------------------------

class ProjectQuerySet(models.QuerySet):
    def active(self):
        """Everything not in the trash (drafts included) – for the dashboard."""
        return self.filter(deleted_at__isnull=True)

    def public(self):
        """Only what visitors may see on the website."""
        return self.filter(deleted_at__isnull=True, is_published=True)


class Project(models.Model):
    CATEGORY_CHOICES = [
        ('hyttegrend', 'Hyttegrend'),
        ('hytte', 'Hytte'),
        ('annet', 'Annet'),
    ]
    STATUS_CHOICES = [
        ('for_sale', 'Til salgs'),
        # A cabin model from a supplier that can be built on any plot
        ('to_order', 'Kan bestilles'),
        ('planned', 'Under planlegging'),
        ('sold', 'Solgt'),
    ]
    # Boolean "Ekstra" fields, in display order: (field name, label, icon)
    EXTRAS = [
        ('has_view', 'Utsikt', 'fa-mountain-sun'),
        ('has_fireplace', 'Peis', 'fa-fireplace'),
        ('has_sauna', 'Badstue', 'fa-hot-tub-person'),
        ('has_annex', 'Anneks', 'fa-house-chimney-window'),
        ('has_loft', 'Hems', 'fa-stairs'),
        ('has_road', 'Bilvei frem', 'fa-road'),
        ('has_water_sewer', 'Offentlig vann og avløp', 'fa-faucet-drip'),
        ('has_ski_trail', 'Langrennsløype ved feltet', 'fa-person-skiing-nordic'),
    ]

    title = models.CharField('Tittel', max_length=150)
    slug = models.SlugField('URL-navn', max_length=170, unique=True, blank=True)
    category = models.CharField('Kategori', max_length=20, choices=CATEGORY_CHOICES, default='hyttegrend')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='for_sale')
    location = models.CharField('Sted', max_length=100, blank=True)
    excerpt = models.CharField('Kort beskrivelse', max_length=300, blank=True)
    description = models.TextField('Beskrivelse', blank=True)
    description_2 = models.TextField('Beskrivelse 2', blank=True)
    image = models.ImageField('Hovedbilde', upload_to='projects/')
    image_credit = models.CharField('Fotograf', max_length=150, blank=True)
    is_featured = models.BooleanField('Vis på forsiden', default=False)
    is_published = models.BooleanField('Publisert', default=True)
    order = models.PositiveIntegerField('Rekkefølge', default=0)
    view_count = models.PositiveIntegerField('Visninger', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField('Slettet', null=True, blank=True)

    # Structured facts shown on the project page
    supplier = models.CharField('Hytteleverandør', max_length=100, blank=True)
    price = models.PositiveIntegerField('Pris (kr)', null=True, blank=True)
    area_m2 = models.PositiveIntegerField('Bruksareal (m²)', null=True, blank=True)
    plot_m2 = models.PositiveIntegerField('Tomteareal (m²)', null=True, blank=True)
    bedrooms = models.PositiveSmallIntegerField('Soverom', null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField('Bad', null=True, blank=True)
    year_built = models.PositiveSmallIntegerField('Byggeår', null=True, blank=True)
    altitude = models.CharField('Høyde over havet', max_length=40, blank=True)
    plot_count = models.PositiveSmallIntegerField('Antall tomter i feltet', null=True, blank=True)
    access = models.CharField('Adkomst', max_length=200, blank=True)
    finn_url = models.URLField('Lenke til Finn-annonse', blank=True)
    has_view = models.BooleanField('Utsikt', default=False)
    has_fireplace = models.BooleanField('Peis', default=False)
    has_sauna = models.BooleanField('Badstue', default=False)
    has_annex = models.BooleanField('Anneks', default=False)
    has_loft = models.BooleanField('Hems', default=False)
    has_road = models.BooleanField('Bilvei frem', default=False)
    has_water_sewer = models.BooleanField('Offentlig vann og avløp', default=False)
    has_ski_trail = models.BooleanField('Langrennsløype ved feltet', default=False)

    # SEO
    meta_title = models.CharField('SEO-tittel', max_length=70, blank=True)
    meta_description = models.CharField('SEO-beskrivelse', max_length=160, blank=True)
    og_image = models.ImageField('Delingsbilde', upload_to='projects/og/', blank=True)

    FACT_FIELDS = [
        'supplier', 'price', 'area_m2', 'plot_m2', 'bedrooms', 'bathrooms', 'year_built',
        'altitude', 'plot_count', 'access', 'finn_url',
    ] + [name for name, _, _ in EXTRAS]

    objects = ProjectQuerySet.as_manager()

    class Meta:
        verbose_name = 'Prosjekt'
        verbose_name_plural = 'Prosjekter'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Project, self, self.title)
        super().save(*args, **kwargs)

    @property
    def extras(self):
        """Labels of the ticked Ekstra fields, e.g. ['Utsikt', 'Peis']."""
        return [label for name, label, _ in self.EXTRAS if getattr(self, name)]

    @property
    def price_display(self):
        """5350000 -> '5 350 000 kr'."""
        return format_nok(self.price)

    @property
    def plots_left(self):
        """Plots in this cabin group that are still for sale."""
        return self.plots.filter(status='available').count()


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='gallery_images', on_delete=models.CASCADE)
    image = models.ImageField('Bilde', upload_to='projects/gallery/')
    caption = models.CharField('Bildetekst', max_length=200, blank=True)
    order = models.PositiveIntegerField('Rekkefølge', default=0)

    class Meta:
        verbose_name = 'Prosjektbilde'
        verbose_name_plural = 'Prosjektbilder'
        ordering = ['order', 'id']

    def __str__(self):
        return f'Bilde for {self.project.title}'


# ------------------------------------------------------------------
# Plots (tomter)
# ------------------------------------------------------------------

class PlotQuerySet(models.QuerySet):
    def public(self):
        """Plots in published cabin groups (or not in a group at all)."""
        return self.filter(
            models.Q(project__isnull=True) | models.Q(project__is_published=True, project__deleted_at__isnull=True)
        )

    def available(self):
        return self.filter(status='available')


class Plot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Ledig'),
        ('reserved', 'Reservert'),
        ('sold', 'Solgt'),
    ]

    project = models.ForeignKey(
        Project, related_name='plots', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Hyttegrend', limit_choices_to={'category': 'hyttegrend', 'deleted_at__isnull': True},
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
    order = models.PositiveIntegerField('Rekkefølge', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PlotQuerySet.as_manager()

    class Meta:
        verbose_name = 'Tomt'
        verbose_name_plural = 'Tomter'
        ordering = ['project__order', 'order', 'number']

    def __str__(self):
        group = f'{self.project.title} – ' if self.project else ''
        return f'{group}tomt {self.number}'

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
            'group': self.project.title if self.project else '',
            'status': self.status,
            'statusLabel': self.get_status_display(),
            'area': self.area_m2,
            'price': self.price,
            'altitude': self.altitude,
            'note': self.note,
            'x': self.map_x,
            'y': self.map_y,
            'rotation': self.map_rotation,
        }
