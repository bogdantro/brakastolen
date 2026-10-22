// Plot picker (tomtevelger) on the homepage: filter the plots, pick one in the list or on the
// map, and send a viewing request. Plot data comes from the database as JSON in the page
// (#plot-picker-data); the request posts to the normal contact form in the background.

document.addEventListener('DOMContentLoaded', function(){
    const root = document.querySelector('[data-plot-picker]');
    const dataScript = document.getElementById('plot-picker-data');
    if (!root || !dataScript) return;

    const PRICE_STEP = 50000;
    const ZOOM_MIN = 0.85;
    const ZOOM_MAX = 2.4;
    const ZOOM_STEP = 0.25;
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const canHover = window.matchMedia('(hover: hover)').matches;

    const plots = JSON.parse(dataScript.textContent);
    const byId = new Map(plots.map(function(plot){ return [plot.id, plot]; }));
    const numberFormat = new Intl.NumberFormat('nb-NO', {maximumFractionDigits: 0});

    const filters = root.querySelector('[data-picker-filters]');
    const priceMin = root.querySelector('[data-price-min]');
    const priceMax = root.querySelector('[data-price-max]');
    const cardsBox = root.querySelector('[data-cards]');
    const countLabel = root.querySelector('[data-count]');
    const listHint = root.querySelector('[data-list-hint]');
    const viewport = root.querySelector('[data-map-viewport]');
    const svg = viewport.querySelector('svg');
    const plotLayer = svg.querySelector('[data-plot-layer]');
    const tooltip = root.querySelector('[data-tooltip]');
    const selectedCard = root.querySelector('[data-selected-card]');
    const dialog = root.querySelector('[data-picker-dialog]');
    const form = root.querySelector('[data-picker-form]');

    let selectedId = null;
    let zoom = 1;
    let panX = 0;
    let panY = 0;

    function formatPrice(value){
        return numberFormat.format(value) + ' kr';
    }

    function formatArea(value){
        return numberFormat.format(value) + ' m²';
    }

    function plotLabel(plot){
        return 'Tomt ' + plot.number;
    }

    // ------------------------------------------------------------
    // Price range – the slider covers the prices of the plots that have one
    // ------------------------------------------------------------
    const prices = plots.map(function(plot){ return plot.price; }).filter(Boolean);
    const lowestPrice = prices.length ? Math.floor(Math.min.apply(null, prices) / PRICE_STEP) * PRICE_STEP : 0;
    const highestPrice = prices.length ? Math.ceil(Math.max.apply(null, prices) / PRICE_STEP) * PRICE_STEP : 0;
    const priceField = root.querySelector('.price-field');

    if (prices.length < 2 || lowestPrice === highestPrice) {
        priceField.hidden = true;
    }
    [priceMin, priceMax].forEach(function(input){
        input.min = lowestPrice;
        input.max = highestPrice;
    });
    priceMin.value = lowestPrice;
    priceMax.value = highestPrice;

    function updatePriceRange(changed){
        let low = Number(priceMin.value);
        let high = Number(priceMax.value);
        if (low > high - PRICE_STEP) {
            if (changed === 'min') {
                priceMin.value = high - PRICE_STEP;
            } else {
                priceMax.value = low + PRICE_STEP;
            }
            low = Number(priceMin.value);
            high = Number(priceMax.value);
        }
        root.querySelector('[data-price-min-label]').textContent = formatPrice(low);
        root.querySelector('[data-price-max-label]').textContent = formatPrice(high);
        const span = (highestPrice - lowestPrice) || 1;
        const fill = root.querySelector('[data-range-fill]');
        fill.style.left = ((low - lowestPrice) / span * 100) + '%';
        fill.style.right = (100 - (high - lowestPrice) / span * 100) + '%';
    }

    // ------------------------------------------------------------
    // Filtering and sorting
    // ------------------------------------------------------------
    function filteredPlots(){
        const low = Number(priceMin.value);
        const high = Number(priceMax.value);
        const minArea = Number(filters.elements.area.value);
        const query = filters.elements.search.value.trim().toLowerCase();
        const onlyAvailable = filters.elements.only_available.checked;

        const result = plots.filter(function(plot){
            if (onlyAvailable && plot.status !== 'available') return false;
            if (minArea && !(plot.area >= minArea)) return false;
            // Plots without a price ("ta kontakt") are never hidden by the price filter
            if (!priceField.hidden && plot.price && (plot.price < low || plot.price > high)) return false;
            if (query && String(plot.number).toLowerCase().indexOf(query) === -1) return false;
            return true;
        });

        const NO_PRICE = Number.MAX_SAFE_INTEGER;
        const sorters = {
            number: function(a, b){ return String(a.number).localeCompare(String(b.number), 'nb', {numeric: true}); },
            priceAsc: function(a, b){ return (a.price || NO_PRICE) - (b.price || NO_PRICE); },
            priceDesc: function(a, b){ return (b.price || 0) - (a.price || 0); },
            areaDesc: function(a, b){ return (b.area || 0) - (a.area || 0); },
        };
        result.sort(sorters[filters.elements.sort.value] || sorters.number);
        return result;
    }

    // ------------------------------------------------------------
    // The list
    // ------------------------------------------------------------
    function el(tag, className, text){
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function renderCards(list){
        cardsBox.replaceChildren();
        countLabel.textContent = list.length + (list.length === 1 ? ' tomt' : ' tomter');
        listHint.textContent = list.length ? 'Trykk på en tomt for detaljer' : 'Ingen treff med disse filtrene';

        if (!list.length) {
            const empty = el('div', 'empty');
            empty.appendChild(el('strong', '', plots.length ? 'Ingen tomter funnet' : 'Tomtene legges inn snart'));
            empty.appendChild(el('p', '', plots.length
                ? 'Prøv en annen prisklasse, eller fjern noen av filtrene.'
                : 'Ta kontakt for prospekt og pris på de ledige tomtene.'));
            if (plots.length) {
                const clear = el('button', 'text-reset', 'Nullstill filtrene');
                clear.type = 'button';
                clear.addEventListener('click', resetFilters);
                empty.appendChild(clear);
            }
            cardsBox.appendChild(empty);
            return;
        }

        list.forEach(function(plot){
            const card = el('div', 'lot-card status-' + plot.status + (plot.id === selectedId ? ' is-selected' : ''));
            card.dataset.id = plot.id;

            const pick = el('button', 'lot-pick');
            pick.type = 'button';
            pick.setAttribute('aria-pressed', plot.id === selectedId ? 'true' : 'false');

            const top = el('span', 'lot-top');
            top.appendChild(el('span', 'lot-title', plotLabel(plot)));
            top.appendChild(el('span', 'status status-' + plot.status, plot.statusLabel));
            pick.appendChild(top);

            const meta = [];
            if (plot.area) meta.push(formatArea(plot.area));
            meta.push(plot.group || 'Brakastølen');
            pick.appendChild(el('span', 'lot-meta', meta.join(' · ')));

            let priceText = 'Ta kontakt for pris';
            if (plot.status === 'sold') {
                priceText = 'Solgt';
            } else if (plot.price) {
                priceText = formatPrice(plot.price);
            }
            pick.appendChild(el('span', 'lot-price', priceText));
            pick.addEventListener('click', function(){ choose(plot.id, false); });
            card.appendChild(pick);
            cardsBox.appendChild(card);
        });
    }

    // ------------------------------------------------------------
    // The map – one shape per plot that has a position: its real outline from
    // the site plan, or a standard parcel turned to the road
    // ------------------------------------------------------------
    function buildMap(){
        plots.forEach(function(plot, index){
            if (plot.x === null || plot.y === null) return;

            const group = document.createElementNS(SVG_NS, 'g');
            group.setAttribute('class', 'plot');
            group.setAttribute('role', 'button');
            group.setAttribute('tabindex', '0');
            group.setAttribute('aria-label', plotLabel(plot) + ', ' + plot.statusLabel.toLowerCase());
            group.dataset.id = plot.id;

            const shape = document.createElementNS(SVG_NS, 'path');
            shape.setAttribute('class', 'parcel');
            const label = document.createElementNS(SVG_NS, 'text');
            label.setAttribute('class', 'parcel-number');
            label.textContent = plot.number;

            if (plot.shape) {
                shape.setAttribute('d', plot.shape);
                label.setAttribute('x', plot.x);
                label.setAttribute('y', plot.y + 1);
                group.appendChild(shape);
                group.appendChild(label);
            } else {
                // Slightly different sizes so the plots don't look stamped out
                const width = 52 + (index % 3) * 2;
                const height = 38 + (index % 2) * 2;
                const placed = document.createElementNS(SVG_NS, 'g');
                placed.setAttribute('transform', 'translate(' + plot.x + ' ' + plot.y + ') rotate(' + plot.rotation + ')');
                shape.setAttribute('d', 'M' + (-width / 2) + ' ' + (-height / 2) + ' L' + (width / 2 - 7) + ' ' + (-height / 2) +
                    ' L' + (width / 2) + ' ' + (height / 2 - 5) + ' L' + (-width / 2 + 5) + ' ' + (height / 2) + ' Z');
                label.setAttribute('y', '1');
                placed.appendChild(shape);
                placed.appendChild(label);
                group.appendChild(placed);
            }

            group.addEventListener('click', function(){ choose(plot.id, true); });
            group.addEventListener('keydown', function(e){
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    choose(plot.id, true);
                }
            });
            // The hover tooltip is for mice only – on a phone a tap selects the plot instead
            group.addEventListener('mouseenter', function(){ if (canHover) showTooltip(plot); });
            group.addEventListener('mousemove', moveTooltip);
            group.addEventListener('mouseleave', function(){ tooltip.hidden = true; });
            plotLayer.appendChild(group);
        });
    }

    function showTooltip(plot){
        tooltip.replaceChildren();
        tooltip.appendChild(el('strong', '', plotLabel(plot)));
        const parts = [];
        if (plot.area) parts.push(formatArea(plot.area));
        parts.push(plot.status === 'available' && plot.price ? formatPrice(plot.price) : plot.statusLabel);
        tooltip.appendChild(el('span', '', parts.join(' · ')));
        // Height and view, when the client has filled them in (Dashboard → Tomter)
        const place = [];
        if (plot.altitude) place.push('ca. ' + numberFormat.format(plot.altitude) + ' moh.');
        if (plot.view) place.push('Utsikt ' + plot.view.toLowerCase());
        if (place.length) tooltip.appendChild(el('span', 'tooltip-place', place.join(' · ')));
        tooltip.hidden = false;
    }

    function moveTooltip(e){
        const box = viewport.getBoundingClientRect();
        tooltip.style.left = Math.min(e.clientX - box.left + 14, box.width - 170) + 'px';
        tooltip.style.top = Math.max(12, e.clientY - box.top - 52) + 'px';
    }

    function renderMap(list){
        const visible = new Set(list.map(function(plot){ return plot.id; }));
        plotLayer.querySelectorAll('.plot').forEach(function(group){
            const plot = byId.get(Number(group.dataset.id));
            const selected = plot.id === selectedId;
            group.setAttribute('class', 'plot status-' + plot.status +
                (selected ? ' is-selected' : '') + (!visible.has(plot.id) && !selected ? ' is-filtered' : ''));
            group.setAttribute('aria-pressed', selected ? 'true' : 'false');
        });
        renderSelectedCard();
    }

    // ------------------------------------------------------------
    // The card for the chosen plot
    // ------------------------------------------------------------
    function renderSelectedCard(){
        const plot = byId.get(selectedId);
        selectedCard.replaceChildren();
        if (!plot) {
            selectedCard.hidden = true;
            return;
        }
        selectedCard.hidden = false;

        const top = el('div', 'card-top');
        const heading = el('div');
        heading.appendChild(el('strong', '', plotLabel(plot)));
        heading.appendChild(el('span', 'status status-' + plot.status, plot.statusLabel));
        top.appendChild(heading);
        const close = el('button', 'card-close', '×');
        close.type = 'button';
        close.setAttribute('aria-label', 'Lukk detaljene');
        close.addEventListener('click', function(){
            selectedId = null;
            render();
        });
        top.appendChild(close);
        selectedCard.appendChild(top);

        const price = el('p', 'card-price');
        if (plot.status === 'sold') {
            price.textContent = 'Solgt';
        } else if (plot.price) {
            price.textContent = formatPrice(plot.price);
            // The asterisk leads to the one place the costs are listed
            const costs = el('small', '', ' + ');
            const costsLink = el('a', '', 'omk.*');
            costsLink.href = '#omkostninger';
            costsLink.setAttribute('aria-label', 'pluss omkostninger – se oversikten');
            costs.appendChild(costsLink);
            price.appendChild(costs);
        } else {
            price.textContent = 'Ta kontakt for pris';
        }
        selectedCard.appendChild(price);

        // The facts the client fills in for each plot (Dashboard → Tomter)
        const facts = el('dl', 'card-facts');
        [
            ['Størrelse', plot.area ? formatArea(plot.area) : ''],
            ['Høyde over havet', plot.altitude ? 'ca. ' + numberFormat.format(plot.altitude) + ' moh.' : ''],
            ['Utsikt', plot.view],
            ['Område', plot.group],
        ].forEach(function(row){
            if (!row[1]) return;
            const item = el('div');
            item.appendChild(el('dt', '', row[0]));
            item.appendChild(el('dd', '', row[1]));
            facts.appendChild(item);
        });
        if (facts.children.length) selectedCard.appendChild(facts);
        if (plot.note) selectedCard.appendChild(el('p', 'card-note', plot.note));

        const action = el('button', 'button');
        action.type = 'button';
        if (plot.status === 'available') {
            action.textContent = 'Avtal visning av tomten';
            action.addEventListener('click', function(){ openDialog(plot); });
        } else {
            action.textContent = plot.status === 'reserved' ? 'Tomten er reservert' : 'Tomten er solgt';
            action.disabled = true;
        }
        selectedCard.appendChild(action);

        // Links out: the plot's FINN ad, and the sun's path over the plot through the day
        const links = el('div', 'card-links');
        [[plot.finnUrl, 'Se annonsen på FINN'], [plot.sunUrl, 'Se solforhold på tomten']].forEach(function(link){
            if (!link[0]) return;
            const a = el('a', 'card-link', link[1]);
            a.href = link[0];
            a.target = '_blank';
            a.rel = 'noopener';
            a.appendChild(el('span', 'visually-hidden', ' (åpnes i ny fane)'));
            links.appendChild(a);
        });
        if (links.children.length) selectedCard.appendChild(links);
    }

    function choose(id, fromMap){
        selectedId = id;
        render();
        const card = cardsBox.querySelector('.lot-card[data-id="' + id + '"]');
        if (card && fromMap) {
            card.scrollIntoView({block: 'nearest', behavior: 'smooth'});
        }
    }

    function render(){
        const list = filteredPlots();
        renderCards(list);
        renderMap(list);
    }

    function resetFilters(){
        filters.reset();
        priceMin.value = lowestPrice;
        priceMax.value = highestPrice;
        updatePriceRange();
        render();
    }

    // ------------------------------------------------------------
    // Zoom and drag the map
    // ------------------------------------------------------------
    function applyTransform(){
        svg.style.transform = 'translate(' + panX + 'px, ' + panY + 'px) scale(' + zoom + ')';
    }

    // The whole drawing, as the map's SVG declares it (720 × 1000, standing). Below desktop
    // width the map frames the area where the plots are instead, so they come out larger.
    const FULL_VIEW = svg.getAttribute('viewBox').split(' ').map(Number);
    const NARROW_SCREEN = 1140;
    const FRAME_PADDING = 55;

    function fitMapToScreen(){
        const placed = plots.filter(function(plot){ return plot.x !== null && plot.y !== null; });
        if (window.innerWidth >= NARROW_SCREEN || !placed.length) {
            svg.setAttribute('viewBox', FULL_VIEW.join(' '));
            return;
        }
        const xs = placed.map(function(plot){ return plot.x; });
        const ys = placed.map(function(plot){ return plot.y; });
        let minX = Math.min.apply(null, xs) - FRAME_PADDING;
        let maxX = Math.max.apply(null, xs) + FRAME_PADDING;
        let minY = Math.min.apply(null, ys) - FRAME_PADDING;
        let maxY = Math.max.apply(null, ys) + FRAME_PADDING;
        // Grow the frame to the map box's shape, so nothing is stretched
        const box = viewport.getBoundingClientRect();
        const ratio = box.width / (box.height || 1);
        let width = maxX - minX;
        let height = maxY - minY;
        if (width / height < ratio) {
            const extra = height * ratio - width;
            minX -= extra / 2;
            width += extra;
        } else {
            const extra = width / ratio - height;
            minY -= extra / 2;
            height += extra;
        }
        svg.setAttribute('viewBox', [minX, minY, width, height].map(Math.round).join(' '));
    }

    root.querySelectorAll('[data-zoom]').forEach(function(button){
        button.addEventListener('click', function(){
            const action = button.dataset.zoom;
            if (action === 'in') zoom = Math.min(ZOOM_MAX, zoom + ZOOM_STEP);
            if (action === 'out') zoom = Math.max(ZOOM_MIN, zoom - ZOOM_STEP);
            if (action === 'reset') {
                zoom = 1;
                panX = 0;
                panY = 0;
                fitMapToScreen();
            }
            applyTransform();
        });
    });

    // Ctrl/⌘ + scroll zooms; a plain scroll still scrolls the page
    viewport.addEventListener('wheel', function(e){
        if (!e.ctrlKey && !e.metaKey) return;
        e.preventDefault();
        zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom + (e.deltaY < 0 ? 0.12 : -0.12)));
        applyTransform();
    }, {passive: false});

    let drag = null;
    viewport.addEventListener('pointerdown', function(e){
        if (e.button !== 0 || e.target.closest('.plot')) return;
        drag = {x: e.clientX, y: e.clientY, panX: panX, panY: panY};
        viewport.classList.add('is-dragging');
        viewport.setPointerCapture(e.pointerId);
    });
    viewport.addEventListener('pointermove', function(e){
        if (!drag) return;
        panX = drag.panX + (e.clientX - drag.x);
        panY = drag.panY + (e.clientY - drag.y);
        applyTransform();
    });
    function stopDrag(){
        drag = null;
        viewport.classList.remove('is-dragging');
    }
    viewport.addEventListener('pointerup', stopDrag);
    viewport.addEventListener('pointercancel', stopDrag);

    // ------------------------------------------------------------
    // Viewing request – posted to the contact form in the background
    // ------------------------------------------------------------
    const status = form.querySelector('[data-form-status]');
    const submit = form.querySelector('button[type="submit"]');

    function clearErrors(){
        form.querySelectorAll('ul.errorlist').forEach(function(list){ list.remove(); });
        form.querySelectorAll('[aria-invalid]').forEach(function(input){ input.removeAttribute('aria-invalid'); });
    }

    function showFieldError(name, message){
        const input = form.elements[name];
        if (!input || input.type === 'hidden') return false;
        input.setAttribute('aria-invalid', 'true');
        const list = el('ul', 'errorlist');
        list.appendChild(el('li', '', message));
        input.closest('.field').appendChild(list);
        return true;
    }

    function showStatus(message, isError){
        status.textContent = message;
        status.classList.toggle('is-error', Boolean(isError));
        status.hidden = false;
    }

    // The chosen plot, cut out of the site plan and zoomed in, for the dialog's side panel
    const MINI_MAP_SIZE = [240, 170];
    const planImage = svg.querySelector('image');

    function drawMiniMap(plot){
        const box = root.querySelector('[data-dialog-map]');
        box.replaceChildren();
        if (plot.x === null || plot.y === null || !planImage) {
            box.hidden = true;
            return;
        }
        box.hidden = false;
        const mini = document.createElementNS(SVG_NS, 'svg');
        mini.setAttribute('viewBox', [plot.x - MINI_MAP_SIZE[0] / 2, plot.y - MINI_MAP_SIZE[1] / 2,
            MINI_MAP_SIZE[0], MINI_MAP_SIZE[1]].join(' '));
        const image = document.createElementNS(SVG_NS, 'image');
        image.setAttribute('href', planImage.getAttribute('href'));
        image.setAttribute('width', planImage.getAttribute('width'));
        image.setAttribute('height', planImage.getAttribute('height'));
        mini.appendChild(image);
        // The other plots, faintly, so the chosen one is seen among its neighbours
        plots.forEach(function(other){
            if (!other.shape || other.id === plot.id) return;
            const path = document.createElementNS(SVG_NS, 'path');
            path.setAttribute('d', other.shape);
            path.setAttribute('class', 'mini-other status-' + other.status);
            mini.appendChild(path);
        });
        const chosen = document.createElementNS(SVG_NS, 'path');
        chosen.setAttribute('class', 'mini-chosen');
        chosen.setAttribute('d', plot.shape || ('M' + (plot.x - 24) + ' ' + (plot.y - 18) + ' h48 v36 h-48 Z'));
        mini.appendChild(chosen);
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', plot.x);
        label.setAttribute('y', plot.y + 1);
        label.textContent = plot.number;
        mini.appendChild(label);
        box.appendChild(mini);
    }

    function fillPlotPanel(plot){
        root.querySelector('[data-dialog-plot-name]').textContent = plotLabel(plot);
        const facts = root.querySelector('[data-dialog-facts]');
        facts.replaceChildren();
        const rows = [];
        if (plot.group) rows.push(['Område', plot.group]);
        if (plot.area) rows.push(['Størrelse', formatArea(plot.area)]);
        if (plot.altitude) rows.push(['Høyde', 'ca. ' + numberFormat.format(plot.altitude) + ' moh.']);
        if (plot.view) rows.push(['Utsikt', plot.view]);
        rows.push(['Pris', plot.price ? formatPrice(plot.price) + ' + omk.*' : 'Ta kontakt']);
        rows.forEach(function(row){
            const item = el('div');
            item.appendChild(el('dt', '', row[0]));
            item.appendChild(el('dd', '', row[1]));
            facts.appendChild(item);
        });
        drawMiniMap(plot);
    }

    const doneView = root.querySelector('[data-dialog-done]');

    function openDialog(plot){
        clearErrors();
        status.hidden = true;
        submit.disabled = false;
        form.hidden = false;
        doneView.hidden = true;
        form.elements.plot.value = plot.id;
        fillPlotPanel(plot);
        root.querySelector('[data-dialog-intro]').textContent =
            'Uforpliktende visning av ' + plotLabel(plot).toLowerCase() + '. Vi tar kontakt for å finne et tidspunkt som passer.';
        const suggestion = 'Hei! Jeg ønsker mer informasjon og gjerne en visning av ' + plotLabel(plot).toLowerCase() + '.';
        // Keep what the visitor wrote themselves; only swap our own suggestion for the new plot
        const message = form.elements.message;
        if (!message.value || message.value === message.dataset.suggested) {
            message.value = suggestion;
            message.dataset.suggested = suggestion;
        }
        document.documentElement.classList.add('dialog-open');
        if (typeof dialog.showModal === 'function') {
            dialog.showModal();
        } else {
            dialog.setAttribute('open', '');
        }
        // Start at the top, with the heading in view, even if the form was scrolled last time
        dialog.querySelector('.dialog-main').scrollTop = 0;
        form.elements.name.focus({preventScroll: true});
    }

    function closeDialog(){
        if (typeof dialog.close === 'function') {
            dialog.close();
        } else {
            dialog.removeAttribute('open');
            document.documentElement.classList.remove('dialog-open');
        }
    }

    // Escape, the close buttons and «Se flere tomter» all end here
    dialog.addEventListener('close', function(){
        document.documentElement.classList.remove('dialog-open');
    });
    root.querySelectorAll('[data-dialog-close]').forEach(function(button){
        button.addEventListener('click', closeDialog);
    });
    // A click on the dimmed background (outside the dialog's box) closes it
    dialog.addEventListener('click', function(e){
        if (e.target === dialog) closeDialog();
    });

    function showDone(name, plotName){
        const firstName = name.trim().split(/\s+/)[0];
        root.querySelector('[data-done-title]').textContent = firstName ? 'Takk, ' + firstName + '!' : 'Takk!';
        root.querySelector('[data-done-text]').textContent =
            'Forespørselen om visning av ' + plotName.toLowerCase() + ' er sendt. Vi tar kontakt med deg så snart som mulig for å avtale tid.';
        form.hidden = true;
        doneView.hidden = false;
        doneView.focus();
    }

    form.addEventListener('submit', function(e){
        e.preventDefault();
        clearErrors();

        // Same rules as the server, so a typo never costs a round trip
        let firstInvalid = null;
        if (!form.elements.name.value.trim()) {
            showFieldError('name', 'Skriv inn navnet ditt.');
            firstInvalid = form.elements.name;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.elements.email.value.trim())) {
            showFieldError('email', 'Skriv inn en gyldig e-postadresse.');
            firstInvalid = firstInvalid || form.elements.email;
        }
        if (!form.elements.consent.checked) {
            showFieldError('consent', 'Du må godta personvernerklæringen for å sende skjemaet.');
            firstInvalid = firstInvalid || form.elements.consent;
        }
        if (firstInvalid) {
            firstInvalid.focus();
            return;
        }

        submit.disabled = true;
        showStatus('Sender ...', false);

        // «Når passer det best?» goes into the message, so it reaches the inquiry as plain text
        const body = new FormData(form);
        const when = body.get('when');
        body.delete('when');
        if (when) body.set('message', (body.get('message') + '\n\nPasser best: ' + when).trim());
        const sentName = form.elements.name.value;
        const sentPlot = root.querySelector('[data-dialog-plot-name]').textContent;

        fetch(form.action, {
            method: 'POST',
            body: body,
            headers: {'Accept': 'application/json', 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value},
            credentials: 'same-origin',
        }).then(function(response){
            if (response.status === 403) {
                throw new Error('Skjemaet hadde ligget åpent for lenge. Last inn siden på nytt og prøv igjen – forespørselen ble ikke sendt.');
            }
            return response.json().then(function(data){ return {ok: response.ok, data: data}; });
        }).then(function(result){
            if (result.ok && result.data.ok) {
                status.hidden = true;
                form.elements.message.value = '';
                form.querySelectorAll('input[name="when"]').forEach(function(input){ input.checked = false; });
                showDone(sentName, sentPlot);
                return;
            }
            const fields = result.data.fields || {};
            let shown = false;
            Object.keys(fields).forEach(function(name){
                shown = showFieldError(name, fields[name][0]) || shown;
            });
            showStatus(result.data.error || 'Noe gikk galt. Prøv igjen, eller ring oss.', true);
            submit.disabled = false;
        }).catch(function(error){
            showStatus(error.message && error.message.indexOf('Skjemaet') === 0
                ? error.message
                : 'Fikk ikke kontakt med serveren. Sjekk nettforbindelsen og prøv igjen.', true);
            submit.disabled = false;
        });
    });

    // ------------------------------------------------------------
    // Wire up and draw
    // ------------------------------------------------------------
    priceMin.addEventListener('input', function(){ updatePriceRange('min'); render(); });
    priceMax.addEventListener('input', function(){ updatePriceRange('max'); render(); });
    filters.querySelectorAll('[data-filter]').forEach(function(input){
        input.addEventListener(input.type === 'search' ? 'input' : 'change', render);
    });
    filters.addEventListener('submit', function(e){ e.preventDefault(); });
    root.querySelector('[data-reset]').addEventListener('click', function(e){
        e.preventDefault();
        resetFilters();
    });

    // Start with the first free plot chosen, so the card shows what the picker does
    const firstFree = plots.find(function(plot){ return plot.status === 'available' && plot.x !== null; });
    selectedId = firstFree ? firstFree.id : null;

    buildMap();
    fitMapToScreen();
    updatePriceRange();
    render();

    let resizeTimer = null;
    window.addEventListener('resize', function(){
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(fitMapToScreen, 150);
    });
});
