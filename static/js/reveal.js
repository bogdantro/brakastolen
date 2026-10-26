// Photos glide up into place as you scroll down to them – on every page (the client's wish,
// 26.10.2026). Mark a photo with data-reveal; the styles are in base.scss. Runs at once (not
// on DOMContentLoaded), so photos already on screen never flash before being hidden.

(function(){
    if (!('IntersectionObserver' in window)) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    // Only now are [data-reveal] photos hidden (base.scss) – without JavaScript they just show
    document.documentElement.classList.add('reveal-ready');

    document.addEventListener('DOMContentLoaded', function(){
        const observer = new IntersectionObserver(function(entries){
            entries.forEach(function(entry){
                if (!entry.isIntersecting) return;
                entry.target.classList.add('is-revealed');
                observer.unobserve(entry.target);
            });
        }, {rootMargin: '0px 0px -10% 0px'});

        document.querySelectorAll('[data-reveal]').forEach(function(item){
            observer.observe(item);
        });
    });
})();

