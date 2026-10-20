// Hero slideshow: slow cross-fade between the photos in static/images/hero,
// with the "01 / 03" counter following along. Stays on the first photo for
// people who prefer reduced motion.

document.addEventListener('DOMContentLoaded', function(){
    const hero = document.querySelector('[data-slideshow]');
    if (!hero) return;
    const slides = hero.querySelectorAll('.slide');
    const current = hero.querySelector('[data-slide-current]');
    if (slides.length < 2) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const SLIDE_SECONDS = 7;
    let index = 0;

    setInterval(function(){
        slides[index].classList.remove('is-active');
        index = (index + 1) % slides.length;
        slides[index].classList.add('is-active');
        if (current) current.textContent = String(index + 1).padStart(2, '0');
    }, SLIDE_SECONDS * 1000);
});
