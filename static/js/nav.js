// Mobile menu: the "Meny" button opens and closes the link list.
// Escape closes it, and the page behind can't scroll while it is open.

document.addEventListener('DOMContentLoaded', function(){
    const toggle = document.querySelector('.menu-toggle');
    const links = document.getElementById('nav-links');
    if (!toggle || !links) return;

    function setOpen(open){
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        links.classList.toggle('is-open', open);
        document.body.classList.toggle('menu-open', open);
    }

    toggle.addEventListener('click', function(){
        setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });

    document.addEventListener('keydown', function(e){
        if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true'){
            setOpen(false);
            toggle.focus();
        }
    });

    links.querySelectorAll('a').forEach(function(link){
        link.addEventListener('click', function(){
            setOpen(false);
        });
    });
});
