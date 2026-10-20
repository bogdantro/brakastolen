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
    const FAVORITES_KEY = 'brakastolen-favoritt-tomter';
    const SVG_NS = 'http://www.w3.org/2000/svg';

    const plots = JSON.parse(dataScript.textContent);
    const byId = new Map(plots.map(function(plot){ return [plot.id, plot]; }));
    const numberFormat = new Intl.NumberFormat('nb-NO', {maximumFractionDigits: 0});

    const filters = root.querySelector('[data-picker-filters]');
    const priceMin = root.querySelector('[data-price-min]');
    const priceMax = root.querySelector('[data-price-max]');
    const cardsBox = root.querySelector('[data-cards]');
    const countLabel = root.querySelector('[data-count]');
    const listHint = root.querySelector('[data-list-hint]');
    const favoritesToggle = root.querySelector('[data-favorites-toggle]');
    const viewport = root.querySelector('[data-map-viewport]');
    const svg = viewport.querySelector('svg');
    const plotLayer = svg.querySelector('[data-plot-layer]');
    const tooltip = root.querySelector('[data-tooltip]');
    const selectedCard = root.querySelector('[data-selected-card]');
    const dialog = root.querySelector('[data-picker-dialog]');
    const form = root.querySelector('[data-picker-form]');

    let selectedId = null;
    let favoritesOnly = false;
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
    // Favourites – remembered in this browser only
    // ------------------------------------------------------------
    let favorites = new Set();
    try {
        favorites = new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]'));
    } catch (error) {
        favorites = new Set();
    }

    function saveFavorites(){
        try {
            localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(favorites)));
        } catch (error) {
            // Private browsing or blocked storage: favourites just last until the page is closed
        }
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
            if (favoritesOnly && !favorites.has(plot.id)) return false;
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

    function heartIcon(filled){
        const icon = document.createElementNS(SVG_NS, 'svg');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('aria-hidden', 'true');
        const path = document.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', 'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z');
        path.setAttribute('fill', filled ? 'currentColor' : 'none');
        path.setAttribute('stroke', 'currentColor');
        path.setAttribute('stroke-width', '1.7');
        icon.appendChild(path);
        return icon;
    }

    function renderCards(list){
        cardsBox.replaceChildren();
        countLabel.textContent = list.length + (list.length === 1 ? ' tomt' : ' tomter');
        listHint.textContent = list.length ? 'Trykk på en tomt for detaljer' : 'Ingen treff med disse filtrene';
        favoritesToggle.setAttribute('aria-pressed', favoritesOnly ? 'true' : 'false');

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

            const fav = el('button', 'fav' + (favorites.has(plot.id) ? ' is-active' : ''));
            fav.type = 'button';
            fav.setAttribute('aria-pressed', favorites.has(plot.id) ? 'true' : 'false');
            fav.setAttribute('aria-label', (favorites.has(plot.id) ? 'Fjern ' : 'Legg til ') + plotLabel(plot).toLowerCase() + (favorites.has(plot.id) ? ' fra favoritter' : ' i favoritter'));
            fav.appendChild(heartIcon(favorites.has(plot.id)));
            fav.addEventListener('click', function(){
                if (favorites.has(plot.id)) {
                    favorites.delete(plot.id);
                } else {
                    favorites.add(plot.id);
                }
                saveFavorites();
                render();
            });
            card.appendChild(fav);
            cardsBox.appendChild(card);
        });
    }

    // ------------------------------------------------------------
    // The map – one shape per plot that has a position
    // ------------------------------------------------------------
    function buildMap(){
        plots.forEach(function(plot, index){
            if (plot.x === null || plot.y === null) return;
            // Slightly different sizes so the plots don't look stamped out
            const width = 52 + (index % 3) * 2;
            const height = 38 + (index % 2) * 2;

            const group = document.createElementNS(SVG_NS, 'g');
            group.setAttribute('class', 'plot');
            group.setAttribute('role', 'button');
            group.setAttribute('tabindex', '0');
            group.setAttribute('aria-label', plotLabel(plot) + ', ' + plot.statusLabel.toLowerCase());
            group.dataset.id = plot.id;

            const placed = document.createElementNS(SVG_NS, 'g');
            placed.setAttribute('transform', 'translate(' + plot.x + ' ' + plot.y + ') rotate(' + plot.rotation + ')');

            const shape = document.createElementNS(SVG_NS, 'path');
            shape.setAttribute('class', 'parcel');
            shape.setAttribute('d', 'M' + (-width / 2) + ' ' + (-height / 2) + ' L' + (width / 2 - 7) + ' ' + (-height / 2) +
                ' L' + (width / 2) + ' ' + (height / 2 - 5) + ' L' + (-width / 2 + 5) + ' ' + (height / 2) + ' Z');

            const label = document.createElementNS(SVG_NS, 'text');
            label.setAttribute('class', 'parcel-number');
            label.setAttribute('y', '1');
            label.textContent = plot.number;

            placed.appendChild(shape);
            placed.appendChild(label);
            group.appendChild(placed);

            group.addEventListener('click', function(){ choose(plot.id, true); });
            group.addEventListener('keydown', function(e){
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    choose(plot.id, true);
                }
            });
            group.addEventListener('mouseenter', function(){ showTooltip(plot); });
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
        top.appendChild(el('strong', '', plotLabel(plot)));
        const close = el('button', 'card-close', '×');
        close.type = 'button';
        close.setAttribute('aria-label', 'Lukk detaljene');
        close.addEventListener('click', function(){
            selectedId = null;
            render();
        });
        top.appendChild(close);
        selectedCard.appendChild(top);

        const facts = [plot.statusLabel];
        if (plot.area) facts.push(formatArea(plot.area));
        if (plot.altitude) facts.push(plot.altitude + ' moh.');
        if (plot.group) facts.push(plot.group);
        selectedCard.appendChild(el('p', 'card-meta', facts.join(' · ')));
        if (plot.note) selectedCard.appendChild(el('p', 'card-note', plot.note));

        const price = el('p', 'card-price');
        if (plot.status === 'sold') {
            price.textContent = 'Solgt';
        } else if (plot.price) {
            price.textContent = formatPrice(plot.price);
            price.appendChild(el('small', '', ' + omk.'));
        } else {
            price.textContent = 'Ta kontakt for pris';
        }
        selectedCard.appendChild(price);

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
        favoritesOnly = false;
        updatePriceRange();
        render();
    }

    // ------------------------------------------------------------
    // Zoom and drag the map
    // ------------------------------------------------------------
    function applyTransform(){
        svg.style.transform = 'translate(' + panX + 'px, ' + panY + 'px) scale(' + zoom + ')';
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

    function openDialog(plot){
        clearErrors();
        status.hidden = true;
        submit.disabled = false;
        form.elements.plot.value = plot.id;
        root.querySelector('[data-dialog-intro]').textContent =
            'Send en uforpliktende forespørsel om visning av ' + plotLabel(plot).toLowerCase() +
            (plot.area ? ' (' + formatArea(plot.area) + ')' : '') + '.';
        if (!form.elements.message.value) {
            form.elements.message.value = 'Hei! Jeg ønsker mer informasjon og gjerne en visning av ' + plotLabel(plot).toLowerCase() + '.';
        }
        if (typeof dialog.showModal === 'function') {
            dialog.showModal();
        } else {
            dialog.setAttribute('open', '');
        }
        form.elements.name.focus();
    }

    function closeDialog(){
        if (typeof dialog.close === 'function') {
            dialog.close();
        } else {
            dialog.removeAttribute('open');
        }
    }

    root.querySelector('[data-dialog-close]').addEventListener('click', closeDialog);
    // A click on the dimmed background (outside the form) closes the dialog
    dialog.addEventListener('click', function(e){
        if (e.target === dialog) closeDialog();
    });

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

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {'Accept': 'application/json', 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value},
            credentials: 'same-origin',
        }).then(function(response){
            if (response.status === 403) {
                throw new Error('Skjemaet hadde ligget åpent for lenge. Last inn siden på nytt og prøv igjen – forespørselen ble ikke sendt.');
            }
            return response.json().then(function(data){ return {ok: response.ok, data: data}; });
        }).then(function(result){
            if (result.ok && result.data.ok) {
                showStatus(result.data.message, false);
                form.elements.message.value = '';
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
    favoritesToggle.addEventListener('click', function(){
        favoritesOnly = !favoritesOnly;
        render();
    });

    // Start with the first free plot chosen, so the card shows what the picker does
    const firstFree = plots.find(function(plot){ return plot.status === 'available' && plot.x !== null; });
    selectedId = firstFree ? firstFree.id : null;

    buildMap();
    updatePriceRange();
    render();
});
