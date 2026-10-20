import re

from django import forms

from .models import Inquiry
from .spam import make_form_token, spam_reason


class InquiryForm(forms.ModelForm):
    # Honeypot: hidden from people, but bots fill in every field they find.
    # Deliberately not called "website"/"url": browser autofill fills those in for real visitors.
    hp_check = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'autocomplete': 'one-time-code', 'tabindex': '-1',
    }))
    # Signed time the form was shown; checked in spam.spam_reason()
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Inquiry
        fields = ['name', 'email', 'phone', 'interest', 'message', 'consent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'F.eks. Kari Nordmann', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'class': 'input', 'placeholder': 'F.eks. kari@epost.no', 'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={
                'class': 'input', 'placeholder': 'F.eks. 482 58 000', 'autocomplete': 'tel', 'inputmode': 'tel', 'type': 'tel',
            }),
            'interest': forms.Select(attrs={'class': 'input'}),
            'message': forms.Textarea(attrs={
                'class': 'input', 'rows': 5,
                'placeholder': 'F.eks. Vi er interessert i en tomt med utsikt og vil gjerne komme på visning i juni.',
            }),
        }
        error_messages = {
            'name': {'required': 'Skriv inn navnet ditt.'},
            'email': {'required': 'Skriv inn e-postadressen din.', 'invalid': 'Skriv inn en gyldig e-postadresse.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['consent'].required = True
        self.fields['consent'].error_messages['required'] = 'Du må godta personvernerklæringen for å sende skjemaet.'
        # A bound form shown again with errors keeps the posted token
        self.initial['form_ts'] = make_form_token()

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not phone:
            return ''
        digits = re.sub(r'\D', '', phone)
        if not re.fullmatch(r'[\d\s+().-]+', phone) or not 8 <= len(digits) <= 15:
            raise forms.ValidationError('Skriv inn et gyldig telefonnummer, f.eks. 482 58 000.')
        return phone

    def spam_reason(self, extra_signals=()):
        return spam_reason(self.cleaned_data, self.cleaned_data.get('form_ts'), extra_signals)
