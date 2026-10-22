// Dashboard helpers: the mobile menu, confirm before deleting, auto-submitting filters,
// the plots list (autosave, bulk changes, sales map), SEO character counters, a small
// rich-text editor and plot placement.

document.addEventListener('DOMContentLoaded', function(){
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const TOAST_TIME = 4200;

    function csrfToken(scope){
        const input = (scope || document).querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : '';
    }

    // A short confirmation in the corner, e.g. «Markerte tomt 11 som solgt.»
    const toast = document.querySelector('[data-toast]');
    let toastTimer = null;
    function showToast(message, isError){
        if (!toast) return;
        toast.textContent = message;
        toast.classList.toggle('is-error', Boolean(isError));
        toast.hidden = false;
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(function(){ toast.hidden = true; }, TOAST_TIME);
    }

    // ------------------------------------------------------------
    // Mobile menu
    // ------------------------------------------------------------
    const menuButton = document.querySelector('[data-menu-button]');
    if (menuButton){
        menuButton.addEventListener('click', function(){
            const open = menuButton.getAttribute('aria-expanded') !== 'true';
            menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
            document.body.classList.toggle('menu-open', open);
        });
        document.addEventListener('keydown', function(e){
            if (e.key === 'Escape' && document.body.classList.contains('menu-open')){
                menuButton.click();
                menuButton.focus();
            }
        });
    }

    // ------------------------------------------------------------
    // Ask before anything is deleted (forms with data-confirm, buttons with data-confirm-click)
    // ------------------------------------------------------------
    document.querySelectorAll('form[data-confirm]').forEach(function(form){
        form.addEventListener('submit', function(e){
            if (!window.confirm(form.dataset.confirm)) e.preventDefault();
        });
    });
    document.querySelectorAll('[data-confirm-click]').forEach(function(button){
        button.addEventListener('click', function(e){
            if (!window.confirm(button.dataset.confirmClick)) e.preventDefault();
        });
    });

    // Filters that apply as soon as a new value is picked
    document.querySelectorAll('select[data-autosubmit]').forEach(function(select){
        select.addEventListener('change', function(){
            select.form.submit();
        });
    });

    // ------------------------------------------------------------
    // The sales map: plots on the site plan, coloured by status
    // ------------------------------------------------------------
    function drawParcel(layer, plot, className){
        const group = document.createElementNS(SVG_NS, 'g');
        group.setAttribute('class', className);
        const shape = document.createElementNS(SVG_NS, 'path');
        const label = document.createElementNS(SVG_NS, 'text');
        label.textContent = plot.number;
        if (plot.shape){
            shape.setAttribute('d', plot.shape);
            label.setAttribute('x', plot.x);
            label.setAttribute('y', plot.y + 1);
            group.appendChild(shape);
            group.appendChild(label);
        } else {
            const placed = document.createElementNS(SVG_NS, 'g');
            placed.setAttribute('transform', 'translate(' + plot.x + ' ' + plot.y + ') rotate(' + plot.rotation + ')');
            shape.setAttribute('d', 'M-26 -19 L19 -19 L26 14 L-21 19 Z');
            label.setAttribute('y', '1');
            placed.appendChild(shape);
            placed.appendChild(label);
            group.appendChild(placed);
        }
        layer.appendChild(group);
        return group;
    }

    const salesMap = document.querySelector('[data-sales-map]');
    const salesData = document.getElementById('sales-map-data');
    const mapParcels = new Map();
    const mapPlots = salesData ? JSON.parse(salesData.textContent) : [];

    if (salesMap && salesData){
        const layer = salesMap.querySelector('[data-plot-layer]');
        const tip = salesMap.querySelector('[data-map-tip]');
        const frame = salesMap.querySelector('.sales-map-frame');

        mapPlots.forEach(function(plot){
            const group = drawParcel(layer, plot, 'parcel status-' + plot.status);
            group.setAttribute('role', 'link');
            group.setAttribute('tabindex', '0');
            group.setAttribute('aria-label', 'Tomt ' + plot.number + ', ' + plot.statusLabel.toLowerCase());
            mapParcels.set(plot.id, group);

            function open(){
                const row = document.getElementById('tomt-' + plot.id);
                if (row){
                    row.scrollIntoView({block: 'center', behavior: 'smooth'});
                    flashRow(row);
                    const field = row.querySelector('input[data-price]');
                    if (field) field.focus({preventScroll: true});
                } else {
                    window.location = plot.url;
                }
            }
            group.addEventListener('click', open);
            group.addEventListener('keydown', function(e){
                if (e.key === 'Enter' || e.key === ' '){
                    e.preventDefault();
                    open();
                }
            });
            group.addEventListener('mouseenter', function(){
                const current = mapPlots.find(function(p){ return p.id === plot.id; });
                tip.replaceChildren();
                const title = document.createElement('strong');
                title.textContent = 'Tomt ' + current.number + ' · ' + current.statusLabel;
                const facts = document.createElement('span');
                facts.textContent = [current.area, current.price || 'Ingen pris', current.category].filter(Boolean).join(' · ');
                tip.appendChild(title);
                tip.appendChild(facts);
                tip.hidden = false;
                highlightRow(plot.id, true);
            });
            group.addEventListener('mousemove', function(e){
                const box = frame.getBoundingClientRect();
                tip.style.left = Math.min(e.clientX - box.left + 14, box.width - 200) + 'px';
                tip.style.top = Math.max(8, e.clientY - box.top - 56) + 'px';
            });
            group.addEventListener('mouseleave', function(){
                tip.hidden = true;
                highlightRow(plot.id, false);
            });
        });
    }

    function setMapStatus(id, status, statusLabel){
        const group = mapParcels.get(id);
        if (!group) return;
        const keep = group.classList.contains('is-hover') ? ' is-hover' : '';
        group.setAttribute('class', 'parcel status-' + status + keep);
        const plot = mapPlots.find(function(p){ return p.id === id; });
        if (plot){
            plot.status = status;
            plot.statusLabel = statusLabel;
        }
    }

    function highlightRow(id, on){
        const row = document.getElementById('tomt-' + id);
        if (row) row.classList.toggle('is-hover', on);
    }

    function flashRow(row){
        row.classList.remove('is-flash');
        void row.offsetWidth;  // restart the animation
        row.classList.add('is-flash');
    }

    // ------------------------------------------------------------
    // The plots list: every change saves at once (one field per request)
    // ------------------------------------------------------------
    const numberFormat = new Intl.NumberFormat('nb-NO', {maximumFractionDigits: 0});
    function groupThousands(value){
        return value === null || value === '' ? '' : numberFormat.format(value).replace(/\s/g, ' ');
    }

    document.querySelectorAll('[data-row-form]').forEach(function(form){
        const id = Number(form.dataset.rowForm);
        const row = document.getElementById('tomt-' + id);
        if (!row) return;
        const state = row.querySelector('[data-row-state]');
        const fields = Array.from(document.querySelectorAll('[form="row-' + id + '"][data-quick]'));

        function remember(field){
            field.dataset.saved = field.type === 'radio' ? String(field.checked) : field.value;
        }
        function restore(name){
            fields.forEach(function(field){
                if (field.name !== name) return;
                if (field.type === 'radio') field.checked = field.dataset.saved === 'true';
                else field.value = field.dataset.saved;
            });
        }
        fields.forEach(remember);

        function setState(text, kind){
            state.textContent = text;
            state.className = 'row-state' + (kind ? ' is-' + kind : '');
        }

        function save(field){
            const body = new FormData();
            body.append('csrfmiddlewaretoken', csrfToken(form));
            body.append(field.name, field.value);
            setState('Lagrer…', 'busy');
            row.classList.add('is-saving');
            fetch(form.action, {
                method: 'POST',
                headers: {'Accept': 'application/json'},
                body: body,
            }).then(function(response){
                return response.json().then(function(data){ return {ok: response.ok, data: data}; });
            }).then(function(result){
                const data = result.data;
                if (!result.ok || !data.ok){
                    restore(field.name);
                    setState('Ikke lagret', 'error');
                    showToast('Tomten ble ikke lagret: ' + (data.error || 'ukjent feil.'), true);
                    return;
                }
                const plot = data.plot;
                if (field.name === 'price') field.value = groupThousands(plot.price);
                if (field.name === 'area_m2') field.value = plot.area === null ? '' : plot.area;
                fields.forEach(remember);
                row.className = row.className.replace(/status-\w+/, 'status-' + plot.status);
                setMapStatus(id, plot.status, plot.statusLabel);
                const mapPlot = mapPlots.find(function(p){ return p.id === id; });
                if (mapPlot){
                    mapPlot.price = plot.priceDisplay;
                    mapPlot.category = plot.categoryName;
                }
                updateFigures(data.summary);
                if (data.changed.length){
                    setState('Lagret', 'saved');
                    showToast(data.message);
                } else {
                    setState('', '');
                }
            }).catch(function(){
                restore(field.name);
                setState('Ikke lagret', 'error');
                showToast('Fikk ikke kontakt med serveren. Sjekk nettet og prøv igjen.', true);
            }).then(function(){
                row.classList.remove('is-saving');
            });
        }

        fields.forEach(function(field){
            field.addEventListener('change', function(){
                if (field.type === 'radio' && !field.checked) return;
                if (field.dataset.price !== undefined){
                    // Allow «1 500 000», «1.500.000», «1500000 kr»; anything else is a typo,
                    // never a reason to wipe the price
                    if (/[^\d\s.,\-]/.test(field.value.replace(/kr/gi, ''))){
                        restore(field.name);
                        setState('Ikke lagret', 'error');
                        showToast('Skriv prisen med tall, for eksempel 1 500 000. La feltet stå tomt for «Ta kontakt for pris».', true);
                        return;
                    }
                    const digits = field.value.replace(/[^\d]/g, '');
                    field.value = digits ? groupThousands(Number(digits)) : '';
                }
                if (field.type !== 'radio' && field.value === field.dataset.saved) return;
                save(field);
            });
            // Enter in a text field saves it without submitting anything else
            if (field.tagName === 'INPUT' && field.type !== 'radio'){
                field.addEventListener('keydown', function(e){
                    if (e.key === 'Enter'){
                        e.preventDefault();
                        field.blur();
                    }
                    if (e.key === 'Escape'){
                        field.value = field.dataset.saved;
                        field.blur();
                    }
                });
            }
        });

        row.addEventListener('mouseenter', function(){
            const group = mapParcels.get(id);
            if (group) group.classList.add('is-hover');
        });
        row.addEventListener('mouseleave', function(){
            const group = mapParcels.get(id);
            if (group) group.classList.remove('is-hover');
        });
    });

    function updateFigures(summary){
        if (!summary) return;
        Object.keys(summary).forEach(function(key){
            const number = document.querySelector('[data-count="' + key + '"]');
            if (number) number.textContent = summary[key];
            const share = document.querySelector('[data-share="' + key + '"]');
            if (share) share.style.flexGrow = summary[key];
        });
    }

    // If the page was opened at a plot (…#tomt-12), point it out
    if (window.location.hash.indexOf('#tomt-') === 0){
        const row = document.querySelector(window.location.hash);
        if (row) flashRow(row);
    }

    // ------------------------------------------------------------
    // Bulk changes: tick plots, then «Merk som …» or «Flytt til …»
    // ------------------------------------------------------------
    const bulkForm = document.querySelector('[data-bulk-form]');
    if (bulkForm){
        const boxes = Array.from(bulkForm.querySelectorAll('input[name="plots"]'));
        const checkAll = bulkForm.querySelector('[data-check-all]');
        const bar = bulkForm.querySelector('[data-bulk-bar]');
        const count = bulkForm.querySelector('[data-bulk-count]');

        function refresh(){
            const chosen = boxes.filter(function(box){ return box.checked; });
            if (bar) bar.classList.toggle('is-active', chosen.length > 0);
            if (count){
                count.textContent = chosen.length
                    ? chosen.length + (chosen.length === 1 ? ' tomt valgt' : ' tomter valgt')
                    : 'Kryss av tomter i listen for å endre flere samtidig.';
            }
            boxes.forEach(function(box){
                box.closest('tr').classList.toggle('is-checked', box.checked);
            });
            if (checkAll){
                checkAll.checked = chosen.length > 0 && chosen.length === boxes.length;
                checkAll.indeterminate = chosen.length > 0 && chosen.length < boxes.length;
            }
        }

        if (checkAll){
            checkAll.hidden = false;
            checkAll.addEventListener('change', function(){
                boxes.forEach(function(box){ box.checked = checkAll.checked; });
                refresh();
            });
        }
        // Shift-click ticks every plot between this one and the last one ticked
        let lastIndex = null;
        boxes.forEach(function(box, index){
            box.addEventListener('click', function(e){
                if (e.shiftKey && lastIndex !== null){
                    const from = Math.min(lastIndex, index);
                    const to = Math.max(lastIndex, index);
                    for (let i = from; i <= to; i++) boxes[i].checked = box.checked;
                }
                lastIndex = index;
                refresh();
            });
        });
        bulkForm.addEventListener('submit', function(e){
            const chosen = boxes.filter(function(box){ return box.checked; }).length;
            if (!chosen){
                e.preventDefault();
                showToast('Kryss av minst én tomt i listen først.', true);
                return;
            }
            const button = e.submitter;
            if (button && button.name === 'status' && button.value === 'sold'){
                const noun = chosen === 1 ? 'tomt' : 'tomter';
                if (!window.confirm('Markere ' + chosen + ' ' + noun + ' som solgt?')) e.preventDefault();
            }
        });
        if (bar) bar.classList.add('is-enhanced');
        refresh();
    }

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
    // Plot placement – click in the map to set where the plot sits in the
    // plot picker (map_x / map_y in the 720 × 1000 drawing). A plot with its real
    // outline from the site plan keeps it until it is moved by hand.
    // ------------------------------------------------------------
    const placer = document.querySelector('[data-plot-placer]');
    if (placer){
        const svg = placer.querySelector('svg');
        const layer = svg.querySelector('[data-plot-layer]');
        const form = placer.closest('form');
        const inputX = form.elements.map_x;
        const inputY = form.elements.map_y;
        const inputShape = form.elements.map_shape;
        const inputRotation = form.elements.map_rotation;
        const inputNumber = form.elements.number;
        const rotationField = placer.querySelector('[data-rotation-field]');
        const status = placer.querySelector('[data-placer-status]');
        const otherPlots = JSON.parse(document.getElementById('placer-other-plots').textContent);
        const originalShape = inputShape.value;
        const resetShape = placer.querySelector('[data-placer-reset]');

        function draw(){
            layer.replaceChildren();
            otherPlots.forEach(function(plot){
                drawParcel(layer, plot, 'placer-other');
            });
            const hasShape = Boolean(inputShape.value);
            if (rotationField) rotationField.hidden = hasShape;
            if (resetShape) resetShape.hidden = !originalShape || inputShape.value === originalShape;
            if (inputX.value && inputY.value){
                drawParcel(layer, {
                    number: inputNumber.value || '?',
                    x: Number(inputX.value),
                    y: Number(inputY.value),
                    rotation: Number(inputRotation.value || -20),
                    shape: inputShape.value,
                }, 'placer-current');
                status.textContent = hasShape
                    ? 'Tomten har omrisset fra tomtekartet. Trykk et annet sted i kartet for å flytte den.'
                    : 'Plassert i kartet. Husk å lagre.';
            } else {
                status.textContent = 'Ikke plassert ennå – trykk i kartet der tomten ligger.';
            }
        }

        svg.addEventListener('click', function(e){
            const point = svg.createSVGPoint();
            point.x = e.clientX;
            point.y = e.clientY;
            const inSvg = point.matrixTransform(svg.getScreenCTM().inverse());
            if (inputShape.value && !window.confirm('Flytte tomten hit? Omrisset fra tomtekartet byttes da ut med en standard tomteform.')){
                return;
            }
            inputShape.value = '';
            inputX.value = Math.round(inSvg.x);
            inputY.value = Math.round(inSvg.y);
            draw();
        });
        inputRotation.addEventListener('input', draw);
        inputNumber.addEventListener('input', draw);
        placer.querySelector('[data-placer-clear]').addEventListener('click', function(){
            inputX.value = '';
            inputY.value = '';
            inputShape.value = '';
            draw();
        });
        if (resetShape){
            resetShape.addEventListener('click', function(){
                inputShape.value = originalShape;
                inputX.value = resetShape.dataset.x;
                inputY.value = resetShape.dataset.y;
                draw();
            });
        }
        draw();
    }
});
