// Homepage: the hero slideshow and the activity carousel. (Photos gliding into view is
// reveal.js, shared by every page.)

// ------------------------------------------------------------
// Hero slideshow: slow cross-fade between the photos in static/images/hero.
// Stays on the first photo for people who prefer reduced motion.
// ------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function(){
    const hero = document.querySelector('[data-slideshow]');
    if (!hero) return;
    const slides = hero.querySelectorAll('.slide');
    if (slides.length < 2) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const SLIDE_SECONDS = 7;
    let index = 0;

    setInterval(function(){
        slides[index].classList.remove('is-active');
        index = (index + 1) % slides.length;
        slides[index].classList.add('is-active');
    }, SLIDE_SECONDS * 1000);
});

// ------------------------------------------------------------
// Activity carousel – the row scrolls by itself (swipe, trackpad, arrow keys); the
// buttons move one photo at a time, and the counter follows along
// ------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function(){
    const carousel = document.querySelector('[data-carousel]');
    if (!carousel) return;
    const track = carousel.querySelector('[data-carousel-track]');
    const slides = track.children;
    const prev = carousel.querySelector('[data-carousel-prev]');
    const next = carousel.querySelector('[data-carousel-next]');
    const current = carousel.querySelector('[data-carousel-current]');
    if (!slides.length) return;

    function currentIndex(){
        // The slide whose left edge is closest to where the first one starts
        const start = slides[0].offsetLeft;
        let best = 0;
        for (let i = 1; i < slides.length; i++) {
            if (Math.abs(slides[i].offsetLeft - start - track.scrollLeft) <
                Math.abs(slides[best].offsetLeft - start - track.scrollLeft)) best = i;
        }
        return best;
    }

    function goTo(index){
        const target = slides[Math.max(0, Math.min(slides.length - 1, index))];
        track.scrollTo({left: target.offsetLeft - slides[0].offsetLeft, behavior: 'smooth'});
    }

    function update(){
        current.textContent = currentIndex() + 1;
        // A little slack, since browsers round the scroll position
        prev.disabled = track.scrollLeft <= 2;
        next.disabled = track.scrollLeft >= track.scrollWidth - track.clientWidth - 2;
    }

    prev.addEventListener('click', function(){ goTo(currentIndex() - 1); });
    next.addEventListener('click', function(){ goTo(currentIndex() + 1); });

    let scrollTimer = null;
    track.addEventListener('scroll', function(){
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(update, 60);
    }, {passive: true});
    window.addEventListener('resize', update);
    update();
});
