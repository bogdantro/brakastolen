// Contact form: check the required fields in the browser before sending, so a small
// mistake never reloads the page. Error markup mirrors Django's (ul.errorlist), so
// server-side and browser errors look the same.

document.addEventListener('DOMContentLoaded', function(){
    const form = document.getElementById('inquiry-form');
    if (!form) return;

    const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const PHONE_RE = /^[\d\s+().-]+$/;

    // (field name, check, message) – same rules and wording as forms.py
    const rules = [
        ['name', function(v){ return v.trim() !== ''; }, 'Skriv inn navnet ditt.'],
        ['email', function(v){ return EMAIL_RE.test(v.trim()); }, 'Skriv inn en gyldig e-postadresse.'],
        ['phone', function(v){
            const digits = v.replace(/\D/g, '');
            return v.trim() === '' || (PHONE_RE.test(v.trim()) && digits.length >= 8 && digits.length <= 15);
        }, 'Skriv inn et gyldig telefonnummer, f.eks. 482 58 000.'],
    ];

    function clearError(input){
        input.removeAttribute('aria-invalid');
        const list = input.parentNode.querySelector('ul.errorlist.js');
        if (list) list.remove();
    }

    function showError(input, message){
        clearError(input);
        input.setAttribute('aria-invalid', 'true');
        const list = document.createElement('ul');
        list.className = 'errorlist js';
        const item = document.createElement('li');
        item.textContent = message;
        list.appendChild(item);
        input.parentNode.appendChild(list);
    }

    form.addEventListener('submit', function(e){
        let firstInvalid = null;
        rules.forEach(function(rule){
            const input = form.elements[rule[0]];
            if (!input) return;
            if (rule[1](input.value)){
                clearError(input);
            } else {
                showError(input, rule[2]);
                firstInvalid = firstInvalid || input;
            }
        });
        const consent = form.elements['consent'];
        if (consent && !consent.checked){
            showError(consent, 'Du må godta personvernerklæringen for å sende skjemaet.');
            firstInvalid = firstInvalid || consent;
        } else if (consent){
            clearError(consent);
        }
        if (firstInvalid){
            e.preventDefault();
            firstInvalid.focus();
        }
    });
});
