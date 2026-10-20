// Dashboard helpers: confirm before deleting, auto-save selects, SEO character counters,
// a small rich-text editor, drag-and-drop ordering and one-by-one gallery upload.

document.addEventListener('DOMContentLoaded', function(){

    function csrfToken(scope){
        const input = (scope || document).querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : '';
    }

    // ------------------------------------------------------------
    // Ask before anything is deleted (forms with data-confirm="...")
    // ------------------------------------------------------------
    document.querySelectorAll('form[data-confirm]').forEach(function(form){
        form.addEventListener('submit', function(e){
            if (!window.confirm(form.dataset.confirm)) e.preventDefault();
        });
    });

    // Quick status changes (plots list) save as soon as a new value is picked
    document.querySelectorAll('select[data-autosubmit]').forEach(function(select){
        select.addEventListener('change', function(){
            select.form.submit();
        });
    });

    // ------------------------------------------------------------
    // Character counters on SEO fields (data-counter + maxlength)
    // ------------------------------------------------------------
    document.querySelectorAll('[data-counter]').forEach(function(field){
        const max = parseInt(field.getAttribute('maxlength'), 10);
        const counter = document.createElement('small');
        counter.className = 'counter';
        counter.setAttribute('aria-live', 'polite');
        field.insertAdjacentElement('afterend', counter);
        function update(){
            counter.textContent = field.value.length + ' / ' + max + ' tegn';
        }
        field.addEventListener('input', update);
        update();
    });

    // ------------------------------------------------------------
    // Rich-text editor: a textarea with data-rich="true" gets a toolbar and an
    // editable area. The HTML is copied back on submit; the server sanitises it.
    // ------------------------------------------------------------
    const TOOLS = [
        ['bold', 'Fet', 'B'],
        ['italic', 'Kursiv', 'I'],
        ['insertUnorderedList', 'Punktliste', '• Liste'],
        ['insertOrderedList', 'Nummerert liste', '1. Liste'],
        ['createLink', 'Lenke', 'Lenke'],
    ];
    const HEADING_TOOLS = [['h2', 'Overskrift', 'H2'], ['h3', 'Underoverskrift', 'H3'], ['p', 'Vanlig tekst', '¶']];

    document.querySelectorAll('textarea[data-rich="true"]').forEach(function(textarea){
        const toolbar = document.createElement('div');
        toolbar.className = 'rich-toolbar';
        const editor = document.createElement('div');
        editor.className = 'rich-editor input';
        editor.contentEditable = 'true';
        editor.setAttribute('role', 'textbox');
        editor.setAttribute('aria-multiline', 'true');
        editor.setAttribute('aria-label', textarea.getAttribute('placeholder') || 'Tekst');
        // The textarea holds sanitised HTML from the server (or old plain text)
        editor.innerHTML = textarea.value;

        function addButton(label, text, onClick){
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = text;
            button.setAttribute('aria-label', label);
            button.addEventListener('click', function(){
                editor.focus();
                onClick();
            });
            toolbar.appendChild(button);
        }

        TOOLS.forEach(function(tool){
            addButton(tool[1], tool[2], function(){
                if (tool[0] === 'createLink'){
                    const url = window.prompt('Lim inn lenken (https://...)');
                    if (url) document.execCommand('createLink', false, url);
                } else {
                    document.execCommand(tool[0], false, null);
                }
            });
        });
        if (textarea.dataset.headings === 'true'){
            HEADING_TOOLS.forEach(function(tool){
                addButton(tool[1], tool[2], function(){
                    document.execCommand('formatBlock', false, tool[0]);
                });
            });
        }

        textarea.hidden = true;
        textarea.insertAdjacentElement('beforebegin', toolbar);
        textarea.insertAdjacentElement('beforebegin', editor);
        textarea.form.addEventListener('submit', function(){
            textarea.value = editor.innerHTML;
        });
    });

    // ------------------------------------------------------------
    // Drag-and-drop ordering of projects (sends the new id order as JSON)
    // ------------------------------------------------------------
    const sortable = document.querySelector('.sortable[data-reorder-url]');
    if (sortable){
        let dragged = null;
        sortable.addEventListener('dragstart', function(e){
            dragged = e.target.closest('li[data-id]');
            if (dragged) dragged.classList.add('is-dragging');
        });
        sortable.addEventListener('dragover', function(e){
            e.preventDefault();
            const over = e.target.closest('li[data-id]');
            if (!dragged || !over || over === dragged) return;
            const after = e.clientY > over.getBoundingClientRect().top + over.offsetHeight / 2;
            over.insertAdjacentElement(after ? 'afterend' : 'beforebegin', dragged);
        });
        sortable.addEventListener('dragend', function(){
            if (!dragged) return;
            dragged.classList.remove('is-dragging');
            dragged = null;
            const ids = Array.from(sortable.querySelectorAll('li[data-id]')).map(function(li){ return li.dataset.id; });
            fetch(sortable.dataset.reorderUrl, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(sortable)},
                body: JSON.stringify({ids: ids}),
            }).then(function(response){
                return response.json();
            }).then(function(data){
                if (data.error) window.alert(data.error);
            }).catch(function(){
                window.alert('Rekkefølgen ble ikke lagret. Sjekk nettforbindelsen og prøv igjen.');
            });
        });
    }

    // ------------------------------------------------------------
    // Plot placement – click in the map to set where the plot sits in the
    // homepage plot picker (map_x / map_y in the 960 × 760 drawing)
    // ------------------------------------------------------------
    const placer = document.querySelector('[data-plot-placer]');
    if (placer){
        const SVG_NS = 'http://www.w3.org/2000/svg';
        const svg = placer.querySelector('svg');
        const layer = svg.querySelector('[data-plot-layer]');
        const form = placer.closest('form');
        const inputX = form.elements.map_x;
        const inputY = form.elements.map_y;
        const inputRotation = form.elements.map_rotation;
        const inputNumber = form.elements.number;
        const status = placer.querySelector('[data-placer-status]');
        const otherPlots = JSON.parse(document.getElementById('placer-other-plots').textContent);

        function parcel(x, y, rotation, label, className){
            const group = document.createElementNS(SVG_NS, 'g');
            group.setAttribute('class', className);
            group.setAttribute('transform', 'translate(' + x + ' ' + y + ') rotate(' + rotation + ')');
            const shape = document.createElementNS(SVG_NS, 'path');
            shape.setAttribute('d', 'M-26 -19 L19 -19 L26 14 L-21 19 Z');
            const text = document.createElementNS(SVG_NS, 'text');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'middle');
            text.textContent = label;
            group.appendChild(shape);
            group.appendChild(text);
            return group;
        }

        function draw(){
            layer.replaceChildren();
            otherPlots.forEach(function(plot){
                layer.appendChild(parcel(plot.x, plot.y, plot.rotation, plot.number, 'placer-other'));
            });
            if (inputX.value && inputY.value){
                const rotation = Number(inputRotation.value || -20);
                layer.appendChild(parcel(Number(inputX.value), Number(inputY.value), rotation, inputNumber.value || '?', 'placer-current'));
                status.textContent = 'Plassert i kartet. Husk å lagre.';
            } else {
                status.textContent = 'Ikke plassert ennå – trykk i kartet.';
            }
        }

        svg.addEventListener('click', function(e){
            const point = svg.createSVGPoint();
            point.x = e.clientX;
            point.y = e.clientY;
            const inSvg = point.matrixTransform(svg.getScreenCTM().inverse());
            inputX.value = Math.round(inSvg.x);
            inputY.value = Math.round(inSvg.y);
            draw();
        });
        inputRotation.addEventListener('input', draw);
        inputNumber.addEventListener('input', draw);
        placer.querySelector('[data-placer-clear]').addEventListener('click', function(){
            inputX.value = '';
            inputY.value = '';
            draw();
        });
        draw();
    }

    // ------------------------------------------------------------
    // Gallery upload – one file per request, so a big gallery never makes
    // one request too large or too slow for the server
    // ------------------------------------------------------------
    const upload = document.getElementById('gallery-upload');
    if (upload){
        const input = upload.querySelector('input[type="file"]');
        const status = upload.querySelector('.upload-status');
        upload.addEventListener('submit', function(e){
            e.preventDefault();
            const files = Array.from(input.files);
            if (!files.length){
                status.textContent = 'Velg ett eller flere bilder først.';
                return;
            }
            let done = 0;
            const failed = [];
            const token = csrfToken(upload);

            function next(index){
                if (index >= files.length){
                    const body = new FormData();
                    body.append('images', done);
                    failed.forEach(function(name){ body.append('failed', name); });
                    fetch(upload.dataset.doneUrl, {method: 'POST', headers: {'X-CSRFToken': token}, body: body})
                        .then(function(response){ return response.json(); })
                        .then(function(data){ window.location = data.redirect; });
                    return;
                }
                status.textContent = 'Laster opp ' + (index + 1) + ' av ' + files.length + '...';
                const body = new FormData();
                body.append('file', files[index]);
                fetch(upload.dataset.uploadUrl, {method: 'POST', headers: {'X-CSRFToken': token}, body: body})
                    .then(function(response){ return response.json(); })
                    .then(function(data){
                        if (data.ok) done += 1; else failed.push(files[index].name);
                    })
                    .catch(function(){ failed.push(files[index].name); })
                    .then(function(){ next(index + 1); });
            }
            next(0);
        });
    }
});
