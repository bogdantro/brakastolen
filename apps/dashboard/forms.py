from django import forms

from apps.blog.models import Blog
from apps.core.models import Plot, Project
from apps.core.richtext import sanitize_html

RICH_FIELDS = ('description', 'description_2')


class RichTextarea(forms.Textarea):
    """A textarea that dashboard.js upgrades to a small formatting editor."""

    def __init__(self, attrs=None):
        base = {'class': 'input', 'rows': 6, 'data-rich': 'true'}
        base.update(attrs or {})
        super().__init__(base)


def counted(max_length, rows=None):
    """A text field with a live character counter (dashboard.js), for SEO fields."""
    attrs = {'class': 'input', 'maxlength': max_length, 'data-counter': 'true'}
    if rows:
        return forms.Textarea(attrs={**attrs, 'rows': rows})
    return forms.TextInput(attrs=attrs)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 'category', 'status', 'location', 'excerpt',
            'description', 'description_2',
            'image', 'image_credit', 'is_featured', 'is_published',
            *Project.FACT_FIELDS,
            'meta_title', 'meta_description', 'og_image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Ulven hyttegrend'}),
            'category': forms.Select(attrs={'class': 'input'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'location': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Brakastølen, Vaset'}),
            'excerpt': forms.Textarea(attrs={'class': 'input', 'rows': 2, 'maxlength': 300,
                                             'placeholder': 'Én eller to setninger som vises i oversikten'}),
            'description': RichTextarea(attrs={'placeholder': 'Fortell om feltet eller hytta...'}),
            'description_2': RichTextarea(attrs={'placeholder': 'Mer tekst (valgfritt)...'}),
            'image_credit': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Pål Harald Uthus'}),
            'supplier': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Tinde Hytter'}),
            'price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 900000', 'min': 0}),
            'area_m2': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 109', 'min': 0}),
            'plot_m2': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 1400', 'min': 0}),
            'bedrooms': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 4', 'min': 0}),
            'bathrooms': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 2', 'min': 0}),
            'year_built': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 2025', 'min': 1900}),
            'altitude': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. 950–1050 moh.'}),
            'plot_count': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 10', 'min': 0}),
            'access': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Via Nye Øyevegen og Ulsetbekkvegen'}),
            'finn_url': forms.URLInput(attrs={'class': 'input', 'placeholder': 'https://www.finn.no/...'}),
            'meta_title': counted(70),
            'meta_description': counted(160, rows=3),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # New projects start as drafts so they can be finished before going live.
        if not self.instance.pk:
            self.initial.setdefault('is_published', False)
        self.fields['meta_title'].widget.attrs['placeholder'] = 'Standard: prosjekttittelen'
        self.fields['meta_description'].widget.attrs['placeholder'] = 'Standard: den korte beskrivelsen'

    @property
    def extra_fields(self):
        return [self[name] for name, _, _ in Project.EXTRAS]

    @property
    def fact_fields(self):
        extras = {name for name, _, _ in Project.EXTRAS}
        return [self[name] for name in Project.FACT_FIELDS if name not in extras]

    def clean(self):
        cleaned = super().clean()
        for name in RICH_FIELDS:
            if name in cleaned:
                cleaned[name] = sanitize_html(cleaned[name])
        return cleaned


class PlotForm(forms.ModelForm):
    class Meta:
        model = Plot
        fields = ['project', 'number', 'status', 'area_m2', 'price', 'altitude', 'note']
        widgets = {
            'project': forms.Select(attrs={'class': 'input'}),
            'number': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. 7'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'area_m2': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 1400', 'min': 0}),
            'price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 900000', 'min': 0}),
            'altitude': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 980', 'min': 0}),
            'note': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Rett ved langrennssporet'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].empty_label = 'Ikke i en hyttegrend'


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'author', 'excerpt', 'text', 'image', 'image_alt', 'is_published', 'meta_title', 'meta_description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Nye tomter i Ulven hyttegrend'}),
            'author': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Haakon Edland'}),
            'excerpt': forms.Textarea(attrs={'class': 'input', 'rows': 2, 'maxlength': 300,
                                             'placeholder': 'Kort oppsummering som vises i listen og i Google'}),
            'text': RichTextarea(attrs={'rows': 14, 'data-headings': 'true', 'placeholder': 'Skriv nyheten her...'}),
            'image_alt': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Tomtekart over Brakastølen'}),
            'meta_title': counted(70),
            'meta_description': counted(160, rows=3),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault('is_published', False)

    def clean_text(self):
        text = sanitize_html(self.cleaned_data.get('text', ''))
        if not text:
            raise forms.ValidationError('Nyheten kan ikke være tom.')
        return text


class InquiryNoteForm(forms.Form):
    text = forms.CharField(
        label='Nytt notat',
        widget=forms.Textarea(attrs={'class': 'input', 'rows': 3,
                                     'placeholder': 'F.eks. Ringte tirsdag – ønsker visning av tomt 7 i juni'}),
    )


class DashboardLoginForm(forms.Form):
    username = forms.CharField(
        label='Brukernavn',
        widget=forms.TextInput(attrs={'class': 'input', 'autocomplete': 'username', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Passord',
        widget=forms.PasswordInput(attrs={'class': 'input', 'autocomplete': 'current-password'}),
    )
