// Navigation: the mobile menu, and a nav that hides while you scroll down and slides back in
// as soon as you scroll up (so it's always one small scroll away, but never in the way).

document.addEventListener('DOMContentLoaded', function(){
    const header = document.querySelector('.site-header');
    const toggle = document.querySelector('.menu-toggle');
    const links = document.getElementById('nav-links');
    if (!header || !toggle || !links) return;

    // Below this many pixels the nav sits in its normal place at the top of the page
    const STICKY_FROM = 320;
    // Ignore tiny scroll jitters (trackpads, momentum scrolling)
    const SCROLL_TOLERANCE = 6;

    // ------------------------------------------------------------
    // Mobile menu – Escape closes it, the page can't scroll while open
    // ------------------------------------------------------------
    function isOpen(){
        return toggle.getAttribute('aria-expanded') === 'true';
    }

    function setOpen(open){
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        links.classList.toggle('is-open', open);
        document.body.classList.toggle('menu-open', open);
    }

    toggle.addEventListener('click', function(){
        setOpen(!isOpen());
    });

    document.addEventListener('keydown', function(e){
        if (e.key === 'Escape' && isOpen()){
            setOpen(false);
            toggle.focus();
        }
    });

    links.querySelectorAll('a').forEach(function(link){
        link.addEventListener('click', function(){
            setOpen(false);
        });
    });

    // ------------------------------------------------------------
    // Sticky on scroll up
    // ------------------------------------------------------------
    let lastY = window.scrollY;
    let ticking = false;

    // Switching between the normal and the sticky nav happens without animation,
    // so the bar never visibly slides around while it changes mode
    function switchQuietly(sticky){
        header.classList.add('no-transition');
        header.classList.toggle('is-sticky', sticky);
        if (!sticky) header.classList.remove('is-shown');
        window.requestAnimationFrame(function(){
            window.requestAnimationFrame(function(){
                header.classList.remove('no-transition');
            });
        });
    }

    function update(){
        ticking = false;
        const y = window.scrollY;
        const sticky = header.classList.contains('is-sticky');
        if (y <= SCROLL_TOLERANCE){
            // Back at the very top: the normal nav, in its normal place
            if (sticky) switchQuietly(false);
        } else if (sticky || y >= STICKY_FROM){
            if (!sticky) switchQuietly(true);
            if (y < lastY - SCROLL_TOLERANCE || isOpen()){
                header.classList.add('is-shown');
            } else if (y > lastY + SCROLL_TOLERANCE){
                header.classList.remove('is-shown');
            }
        }
        if (Math.abs(y - lastY) > SCROLL_TOLERANCE){
            lastY = y;
        }
    }

    window.addEventListener('scroll', function(){
        if (!ticking){
            ticking = true;
            window.requestAnimationFrame(update);
        }
    }, {passive: true});

    // A keyboard user tabbing into the hidden nav must be able to see it
    header.addEventListener('focusin', function(){
        header.classList.add('is-shown');
    });

    update();
});
