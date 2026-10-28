// A short, quiet burst of confetti in the site's colours – after an inquiry is sent, so it is
// clear it went through. No library: a canvas over the page for about two seconds, then gone.
// Nothing at all for people who prefer reduced motion.
//
//     window.confetti();          // over the page
//     window.confetti(dialog);    // inside a <dialog> (the top layer would hide a canvas on <body>)

(function(){
    const PIECES = 110;
    const DURATION_MS = 2400;
    const FADE_MS = 700;
    const GRAVITY = 0.16;
    const DRAG = 0.985;
    // Brand green, frost blue, fjord blue, the sun's yellow and a light grey
    const COLOURS = ['#002223', '#9CC3D0', '#2C6278', '#F2B632', '#E6ECEF'];

    window.confetti = function(container){
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const canvas = document.createElement('canvas');
        canvas.setAttribute('aria-hidden', 'true');
        canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:2147483000';
        (container || document.body).appendChild(canvas);

        const ratio = window.devicePixelRatio || 1;
        const width = window.innerWidth;
        const height = window.innerHeight;
        canvas.width = width * ratio;
        canvas.height = height * ratio;
        const ctx = canvas.getContext('2d');
        ctx.scale(ratio, ratio);

        // Two soft cannons from the lower corners, aimed up and in towards the middle
        const pieces = [];
        for (let i = 0; i < PIECES; i++) {
            const fromLeft = i % 2 === 0;
            const angle = (fromLeft ? -60 : -120) + (Math.random() - 0.5) * 40;
            const speed = 9 + Math.random() * 8 * Math.min(1, height / 700);
            pieces.push({
                x: fromLeft ? width * 0.08 : width * 0.92,
                y: height * 0.95,
                vx: Math.cos(angle * Math.PI / 180) * speed,
                vy: Math.sin(angle * Math.PI / 180) * speed,
                size: 5 + Math.random() * 6,
                spin: Math.random() * Math.PI,
                spinSpeed: (Math.random() - 0.5) * 0.3,
                round: Math.random() < 0.25,
                colour: COLOURS[i % COLOURS.length],
            });
        }

        const start = performance.now();
        function frame(now){
            const elapsed = now - start;
            if (elapsed > DURATION_MS) {
                canvas.remove();
                return;
            }
            ctx.clearRect(0, 0, width, height);
            ctx.globalAlpha = Math.min(1, (DURATION_MS - elapsed) / FADE_MS);
            pieces.forEach(function(piece){
                piece.vx *= DRAG;
                piece.vy = piece.vy * DRAG + GRAVITY;
                piece.x += piece.vx;
                piece.y += piece.vy;
                piece.spin += piece.spinSpeed;
                ctx.save();
                ctx.translate(piece.x, piece.y);
                ctx.rotate(piece.spin);
                ctx.fillStyle = piece.colour;
                if (piece.round) {
                    ctx.beginPath();
                    ctx.arc(0, 0, piece.size / 2.6, 0, Math.PI * 2);
                    ctx.fill();
                } else {
                    // Flat paper strips: scaling one side by the spin makes them seem to turn over
                    ctx.scale(1, Math.cos(piece.spin * 2));
                    ctx.fillRect(-piece.size / 2, -piece.size / 4, piece.size, piece.size / 2);
                }
                ctx.restore();
            });
            requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
    };
})();
