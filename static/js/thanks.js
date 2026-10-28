// The thank-you popup after the contact form (core/thanks-dialog.html): rendered open so it shows
// even without JavaScript; here it becomes a proper modal (dimmed page, Escape and «Lukk» close
// it, focus stays inside) and gets a short burst of confetti (confetti.js).

document.addEventListener('DOMContentLoaded', function(){
    const dialog = document.querySelector('[data-thanks-dialog]');
    if (!dialog || typeof dialog.showModal !== 'function') return;

    dialog.close();
    dialog.showModal();
    document.documentElement.classList.add('dialog-open');
    dialog.addEventListener('close', function(){
        document.documentElement.classList.remove('dialog-open');
    });
    // A click on the dimmed page around the box closes it as well
    dialog.addEventListener('click', function(e){
        if (e.target === dialog) dialog.close();
    });

    // A moment after the box has appeared, so the eye is already on it
    setTimeout(function(){
        if (typeof window.confetti === 'function') window.confetti(dialog);
    }, 250);
});
