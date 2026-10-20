// Dashboard login: a "Vis/Skjul" button for the password, and a busy state on submit
// so a slow connection never invites a double click.

document.addEventListener('DOMContentLoaded', function(){
    const toggle = document.querySelector('[data-show-password]');
    const form = document.querySelector('.login-form');
    if (!form) return;

    if (toggle){
        const input = document.getElementById(toggle.getAttribute('aria-controls'));
        // Shown only when JavaScript runs, since it does nothing without it
        toggle.hidden = false;
        toggle.addEventListener('click', function(){
            const showing = input.type === 'text';
            input.type = showing ? 'password' : 'text';
            toggle.textContent = showing ? 'Vis' : 'Skjul';
            toggle.setAttribute('aria-pressed', showing ? 'false' : 'true');
            input.focus();
        });
    }

    form.addEventListener('submit', function(){
        const button = form.querySelector('.login-button');
        button.disabled = true;
        button.classList.add('is-busy');
    });
});
