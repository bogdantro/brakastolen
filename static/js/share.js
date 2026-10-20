// "Kopier lenke" on news posts: copies the post's address and says so.

document.addEventListener('DOMContentLoaded', function(){
    const button = document.querySelector('[data-copy-link]');
    const status = document.querySelector('[data-copy-status]');
    if (!button || !status) return;

    const MESSAGE_SECONDS = 3;

    button.addEventListener('click', function(){
        const url = button.dataset.copyLink;
        function done(message){
            status.textContent = message;
            setTimeout(function(){ status.textContent = ''; }, MESSAGE_SECONDS * 1000);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(function(){
                done('Lenken er kopiert.');
            }).catch(function(){
                done('Kunne ikke kopiere. Lenken er: ' + url);
            });
        } else {
            done('Kunne ikke kopiere. Lenken er: ' + url);
        }
    });
});
