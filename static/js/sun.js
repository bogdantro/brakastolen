// Solforhold for a plot, worked out in the browser – a simpler answer than suncalc.org, which
// the client found hard to use (27.10.2026). For a point (lat, lon) it gives sunrise, sunset and
// hours of sun today, at midsummer, at the equinox and at midwinter, and a picture of the sun's
// path across the sky (east on the left, south in the middle, west on the right).
//
// The sun's position uses the same astronomy as suncalc.org (accurate to a minute or so). It is
// for open, flat terrain: mountains and trees on the horizon shorten the day a little.
//
// Used by plot-picker.js: window.sunPanel(lat, lon) returns a DOM element.

(function(){
    const RAD = Math.PI / 180;
    const DAY_MS = 24 * 60 * 60 * 1000;
    const OBLIQUITY = 23.4397 * RAD;
    // The sun counts as up when its top edge clears the horizon (refraction included)
    const SUNRISE_ALTITUDE = -0.833;
    // Minutes between samples when looking for sunrise and sunset, and when drawing the path
    const STEP_MINUTES = 2;

    const SVG_NS = 'http://www.w3.org/2000/svg';
    const CHART = {width: 320, height: 150, top: 14, bottom: 26, maxAltitude: 60};
    const timeFormat = new Intl.DateTimeFormat('nb-NO', {hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Oslo'});
    // The calendar date in Norway as '2026-10-27', whatever time zone the visitor's device is in
    const dateFormat = new Intl.DateTimeFormat('en-CA', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Europe/Oslo'});

    // ------------------------------------------------------------
    // The sun's position: altitude above the horizon and compass direction, in degrees
    // ------------------------------------------------------------
    function sunPosition(time, lat, lon){
        const days = time / DAY_MS - 10957.5;  // days since 1 January 2000, 12:00 UTC
        const anomaly = RAD * (357.5291 + 0.98560028 * days);
        const centre = RAD * (1.9148 * Math.sin(anomaly) + 0.02 * Math.sin(2 * anomaly) + 0.0003 * Math.sin(3 * anomaly));
        const longitude = anomaly + centre + RAD * 102.9372 + Math.PI;
        const declination = Math.asin(Math.sin(longitude) * Math.sin(OBLIQUITY));
        const ascension = Math.atan2(Math.sin(longitude) * Math.cos(OBLIQUITY), Math.cos(longitude));
        const hourAngle = RAD * (280.16 + 360.9856235 * days) + RAD * lon - ascension;
        const phi = RAD * lat;

        const altitude = Math.asin(Math.sin(phi) * Math.sin(declination) +
            Math.cos(phi) * Math.cos(declination) * Math.cos(hourAngle));
        const fromSouth = Math.atan2(Math.sin(hourAngle),
            Math.cos(hourAngle) * Math.sin(phi) - Math.tan(declination) * Math.cos(phi));
        return {altitude: altitude / RAD, azimuth: (fromSouth / RAD + 180 + 360) % 360};
    }

    // ------------------------------------------------------------
    // One day: sunrise, sunset, hours of sun and the path, sampled every few minutes
    // ------------------------------------------------------------
    // dateKey: the day in Norway as '2026-06-21'
    function sunDay(dateKey, lat, lon){
        // A window a few hours wider than the day, so it covers Norwegian midnight to midnight
        // in both summer and winter time; samples from other days are skipped
        const parts = dateKey.split('-').map(Number);
        const start = Date.UTC(parts[0], parts[1] - 1, parts[2]) - 3 * 60 * 60 * 1000;
        const end = start + DAY_MS + 6 * 60 * 60 * 1000;
        let rise = null;
        let set = null;
        let minutesUp = 0;
        const path = [];
        let previous = null;

        for (let time = start; time <= end; time += STEP_MINUTES * 60 * 1000) {
            const sameDay = dateFormat.format(time) === dateKey;
            const position = sunPosition(time, lat, lon);
            const up = position.altitude > SUNRISE_ALTITUDE;
            if (sameDay) {
                if (up) {
                    minutesUp += STEP_MINUTES;
                    path.push(position);
                }
                if (previous !== null && up && !previous) rise = time;
                if (previous !== null && !up && previous) set = time;
            }
            previous = up;
        }
        return {rise: rise, set: set, minutesUp: minutesUp, path: path};
    }

    // 1158 -> '19 t 18 m' – short, so the table fits a narrow column
    function duration(minutes){
        const hours = Math.floor(minutes / 60);
        const rest = Math.round(minutes % 60);
        return rest ? hours + ' t ' + rest + ' m' : hours + ' t';
    }

    // ------------------------------------------------------------
    // The panel
    // ------------------------------------------------------------
    function el(tag, className, text){
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function svg(tag, attributes){
        const node = document.createElementNS(SVG_NS, tag);
        Object.keys(attributes).forEach(function(name){ node.setAttribute(name, attributes[name]); });
        return node;
    }

    // East (90°) on the left, south (180°) in the middle, west (270°) on the right – as when you
    // stand on the plot facing south. Summer sun rises and sets further north, past the edges.
    function chartX(azimuth){
        const from = 30;
        const to = 330;
        return Math.max(0, Math.min(1, (azimuth - from) / (to - from))) * CHART.width;
    }

    function chartY(altitude){
        const usable = CHART.height - CHART.top - CHART.bottom;
        return CHART.height - CHART.bottom - Math.max(0, altitude) / CHART.maxAltitude * usable;
    }

    function drawChart(days){
        const chart = svg('svg', {viewBox: '0 0 ' + CHART.width + ' ' + CHART.height, class: 'sun-chart', 'aria-hidden': 'true'});
        const horizon = CHART.height - CHART.bottom;
        chart.appendChild(svg('line', {x1: 0, y1: horizon, x2: CHART.width, y2: horizon, class: 'sun-horizon'}));

        [['Ø', 90], ['SØ', 135], ['S', 180], ['SV', 225], ['V', 270]].forEach(function(mark){
            const x = chartX(mark[1]);
            chart.appendChild(svg('line', {x1: x, y1: horizon, x2: x, y2: horizon + 5, class: 'sun-tick'}));
            const label = svg('text', {x: x, y: CHART.height - 6, class: 'sun-compass'});
            label.textContent = mark[0];
            chart.appendChild(label);
        });

        days.forEach(function(day){
            if (!day.data.path.length) return;
            const points = day.data.path
                .filter(function(position){ return position.azimuth >= 30 && position.azimuth <= 330; })
                .map(function(position){ return chartX(position.azimuth).toFixed(1) + ',' + chartY(position.altitude).toFixed(1); });
            if (points.length < 2) return;
            chart.appendChild(svg('polyline', {points: points.join(' '), class: 'sun-path ' + day.key}));
        });
        return chart;
    }

    window.sunPanel = function(lat, lon){
        const today = dateFormat.format(Date.now());
        const year = today.slice(0, 4);
        const days = [
            {key: 'is-today', label: 'I dag', date: today},
            // Short names, so the table fits the narrow plot card on desktop
            {key: 'is-summer', label: 'Sommer', title: 'Midtsommer, 21. juni', date: year + '-06-21'},
            {key: 'is-equinox', label: 'Vår/høst', title: 'Vår- og høstjevndøgn, 20. mars', date: year + '-03-20'},
            {key: 'is-winter', label: 'Vinter', title: 'Midtvinter, 21. desember', date: year + '-12-21'},
        ];
        days.forEach(function(day){
            day.data = sunDay(day.date, lat, lon);
        });

        const panel = el('div', 'sun-panel');
        panel.appendChild(drawChart(days));

        const legend = el('p', 'sun-legend');
        [['is-summer', 'Sommer'], ['is-equinox', 'Vår/høst'], ['is-winter', 'Vinter'], ['is-today', 'I dag']].forEach(function(item){
            const entry = el('span', 'sun-key ' + item[0]);
            entry.appendChild(el('i'));
            entry.appendChild(document.createTextNode(item[1]));
            legend.appendChild(entry);
        });
        panel.appendChild(legend);

        const table = el('table', 'sun-table');
        const head = el('tr');
        // Short headers so the table fits the plot card; the title gives the full words
        [['', ''], ['Opp', 'Sola står opp'], ['Ned', 'Sola går ned'], ['Sol', 'Timer med sol']].forEach(function(header){
            const cell = el('th', '', header[0]);
            if (header[1]) cell.title = header[1];
            head.appendChild(cell);
        });
        table.appendChild(head);
        days.forEach(function(day){
            const row = el('tr', day.key);
            const name = el('th', '', day.label);
            if (day.title) name.title = day.title;
            row.appendChild(name);
            const data = day.data;
            if (data.rise === null && data.set === null) {
                // Midnight sun or polar night – not at 61° N, but never show nonsense
                const cell = el('td', '', data.minutesUp ? 'Sol hele døgnet' : 'Sola er ikke oppe');
                cell.colSpan = 3;
                row.appendChild(cell);
            } else {
                row.appendChild(el('td', '', data.rise ? timeFormat.format(data.rise) : '–'));
                row.appendChild(el('td', '', data.set ? timeFormat.format(data.set) : '–'));
                row.appendChild(el('td', '', duration(data.minutesUp)));
            }
            table.appendChild(row);
        });
        panel.appendChild(table);

        panel.appendChild(el('p', 'sun-note',
            'Beregnet for tomtens plassering i åpent terreng. Fjell og trær i horisonten kan gi litt kortere soltid.'));
        return panel;
    };
})();
