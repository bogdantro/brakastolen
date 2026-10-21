import re

from django import forms

from apps.blog.models import Blog
from apps.core.models import Plot, PlotCategory
from apps.core.richtext import sanitize_html
from apps.core.text import format_number

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


class NokField(forms.IntegerField):
    """A price typed the Norwegian way: '1 500 000', '1.500.000 kr' or '1500000' -> 1500000.
    Shown back with spaces between the thousands."""

    widget = forms.TextInput

    def to_python(self, value):
        if isinstance(value, str):
            value = re.sub(r'(?i)\s|\.|,-|kr', '', value)  # \s also covers non-breaking spaces
        return super().to_python(value)

    def prepare_value(self, value):
        if isinstance(value, int):
            return format_number(value)
        return value

    def widget_attrs(self, widget):
        # Text input, so no min/max/step from IntegerField – just a numeric keyboard on phones
        return {'inputmode': 'numeric', 'autocomplete': 'off'}


class PlotForm(forms.ModelForm):
    price = NokField(label='Pris (kr)', required=False, min_value=0)

    class Meta:
        model = Plot
        fields = ['number', 'category', 'status', 'area_m2', 'price', 'altitude', 'note',
                  'map_x', 'map_y', 'map_rotation', 'map_shape']
        widgets = {
            'number': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. 67'}),
            'category': forms.Select(attrs={'class': 'input'}),
            'status': forms.RadioSelect,
            'area_m2': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 1400', 'min': 0}),
            'altitude': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'F.eks. 980', 'min': 0}),
            'note': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Rett ved langrennssporet'}),
            # Set by clicking on the map in the plot form (dashboard.js)
            'map_x': forms.HiddenInput,
            'map_y': forms.HiddenInput,
            'map_shape': forms.HiddenInput,
            'map_rotation': forms.NumberInput(attrs={'class': 'input', 'step': 1, 'min': -180, 'max': 180}),
        }
        labels = {'area_m2': 'Størrelse (m²)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price'].widget.attrs.update({'class': 'input', 'placeholder': 'F.eks. 1 500 000'})
        self.fields['price'].help_text = 'Tomt uten pris vises som «Ta kontakt for pris».'
        self.fields['category'].empty_label = 'Uten kategori'
        self.fields['map_rotation'].required = False

    def clean_map_rotation(self):
        """Empty -> the default angle, so a plot can always be saved without touching the map."""
        value = self.cleaned_data.get('map_rotation')
        return Plot._meta.get_field('map_rotation').default if value is None else value


class PlotQuickForm(forms.ModelForm):
    """One or more of a plot's sales fields, changed straight from the plots list.
    Only the fields actually sent are validated and saved (see `for_fields`)."""

    price = NokField(label='Pris (kr)', required=False, min_value=0)

    EDITABLE = ('status', 'price', 'area_m2', 'category')

    class Meta:
        model = Plot
        fields = ['status', 'price', 'area_m2', 'category']

    @classmethod
    def for_fields(cls, names, *args, **kwargs):
        form = cls(*args, **kwargs)
        for name in list(form.fields):
            if name not in names:
                del form.fields[name]
        return form


class PlotBulkForm(forms.Form):
    """The same change for several plots at once, from the plots list."""

    ACTIONS = [
        ('status', 'Endre status'),
        ('category', 'Endre kategori'),
    ]

    plots = forms.ModelMultipleChoiceField(queryset=Plot.objects.all(), error_messages={
        'required': 'Velg minst én tomt i listen først.',
    })
    action = forms.ChoiceField(choices=ACTIONS)
    status = forms.ChoiceField(choices=Plot.STATUS_CHOICES, required=False)
    category = forms.ModelChoiceField(queryset=PlotCategory.objects.all(), required=False,
                                      empty_label='Uten kategori')


class PlotCategoryForm(forms.ModelForm):
    class Meta:
        model = PlotCategory
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Byggetrinn 3'})}
        error_messages = {'name': {'unique': 'Det finnes allerede en kategori med dette navnet.'}}


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
