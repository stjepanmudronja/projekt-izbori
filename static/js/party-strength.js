// Snaga stranaka: each party's share across elections.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Snaga stranaka: each party's share across elections (/api/analytics/party-strength) ----
const PS_KIND_STYLE = { sabor: 'circle', eu: 'rectRot', vijeca: 'triangle', skupstine: 'rect' };
const _ps = { ready: false, kind: 'sabor', data: {}, on: new Set(), chart: null, colors: {}, partners: true };

async function initPartyStrength() {
    if (_ps.ready) return;
    _ps.ready = true;
    await loadPartyStrength('sabor');
}

async function loadPartyStrength(kind) {
    const spinner = document.getElementById('psSpinner');
    spinner.classList.add('show');
    try {
        if (!_ps.data[kind]) _ps.data[kind] = await fetch(`/api/analytics/party-strength?kind=${kind}`).then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    const d = _ps.data[kind];
    if (d.error) return;
    _ps.kind = kind;
    // The strongest six, or whatever is still shown that this kind has.
    // A line is its `id`: a registration, or a renamed one's old name ("45:Hrvatska narodna stranka").
    const regs = new Set(d.parties.map(p => p.id));
    const kept = [..._ps.on].filter(r => regs.has(r));
    _ps.on = new Set(kept.length ? kept : d.parties.slice(0, 6).map(p => p.id));
    let next = 0;
    d.parties.forEach(p => {
        if (!_ps.colors[p.id])
            _ps.colors[p.id] = MAP_PARTY_COLORS[psLabel(p).toUpperCase()] || MAP_PALETTE[next++ % MAP_PALETTE.length];
    });
    document.getElementById('psKindGroup').innerHTML = [...d.kinds, { key: 'sve', label: 'Svi zajedno' }].map(k =>
        `<button type="button" class="btn btn-outline-primary${k.key === kind ? ' active' : ''}" data-ps-kind="${k.key}">${k.label}</button>`).join('');
    renderPartyStrength();
}

const psLabel = p => p.short_name || p.name;

function renderPartyStrength() {
    const d = _ps.data[_ps.kind];
    document.getElementById('psChips').innerHTML = d.parties.slice(0, 25).map(p =>
        `<button type="button" class="ps-chip${_ps.on.has(p.id) ? ' on' : ''}${p.active ? '' : ' ceased'}"
            data-ps-id="${escapeHtml(p.id)}" title="${escapeHtml(p.name)}${p.old_name_of ? ` (raniji naziv; poslije ${escapeHtml(p.old_name_of)})` : ''}${p.active ? '' : ' (prestala postojati)'} · najbolje ${formatPct(p.peak, 2)}">
            <i style="background:${_ps.colors[p.id]}"></i>${escapeHtml(psLabel(p))}</button>`).join('');
    const kindLabel = Object.fromEntries(d.kinds.map(k => [k.key, k.label]));
    const all = _ps.kind === 'sve';
    const shown = d.parties.filter(p => _ps.on.has(p.id));
    const years = d.elections.map(e => e.year);
    const datasets = shown.filter(p => p.points.length).map(p => {
        const c = _ps.colors[p.id];
        return {
            label: psLabel(p), reg: p.registry_number, party: p,
            // An election in between that the party led no list in breaks the line.
            data: all ? p.points.map(pt => ({ x: pt.year, y: pt.share, pt }))
                : [...new Set(years)].filter(y => y >= p.points[0].year && y <= p.points[p.points.length - 1].year)
                    .map(y => { const pt = p.points.find(q => q.year === y); return { x: y, y: pt ? pt.share : null, pt }; }),
            // Across election types a line would zigzag between ballots; points only.
            borderColor: c, backgroundColor: c, borderWidth: 2.5, showLine: !all,
            cubicInterpolationMode: 'monotone', pointRadius: 5, pointHoverRadius: 8,
            pointStyle: ctx => (ctx.raw && ctx.raw.pt && PS_KIND_STYLE[ctx.raw.pt.kind]) || 'circle',
            pointBorderColor: '#fff', pointBorderWidth: 1.5,
        };
    });
    // Elections where the party led no list but joined a coalition: a hollow
    // point at the coalition's share, never joined to the party's own line.
    // It sits on the leader's own point, so it is drawn as a ring around it,
    // each further partner's a little wider.
    if (_ps.partners) shown.filter(p => p.partner_points.length).forEach((p, i) => {
        const c = _ps.colors[p.id];
        datasets.push({
            label: psLabel(p), reg: p.registry_number, party: p, partner: true,
            data: p.partner_points.map(pt => ({ x: pt.year, y: pt.share, pt })),
            showLine: false, borderColor: c, backgroundColor: 'transparent', pointBackgroundColor: 'transparent',
            pointBorderColor: c, pointBorderWidth: 2.5, pointRadius: 9 + 4 * i, pointHoverRadius: 11 + 4 * i,
            order: -1,
            pointStyle: ctx => (ctx.raw && ctx.raw.pt && PS_KIND_STYLE[ctx.raw.pt.kind]) || 'circle',
        });
    });
    if (_ps.chart) _ps.chart.destroy();
    _ps.chart = new Chart(document.getElementById('psChart').getContext('2d'), {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'nearest', intersect: true },
            onClick: (evt, items) => {
                if (!items.length) return;
                const reg = datasets[items[0].datasetIndex].reg;
                activateModule('parties', { pushState: false, focusInput: false });
                openParty(reg, { push: true });
            },
            onHover: (evt, items) => { if (evt.native) evt.native.target.style.cursor = items.length ? 'pointer' : 'default'; },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)', padding: 10, cornerRadius: 6,
                    callbacks: {
                        title: items => {
                            const pt = items[0].raw.pt;
                            return `${kindLabel[pt.kind]} ${pt.year}.`;
                        },
                        label: ctx => {
                            const pt = ctx.raw.pt;
                            if (ctx.dataset.partner)
                                return `${ctx.dataset.label}: partner u koaliciji koju predvodi ${pt.leader} - koalicija ${formatPct(pt.share, 2)}`;
                            return `${ctx.dataset.label}: ${formatPct(pt.share, 2)} (${pt.votes.toLocaleString('hr-HR')} glasova)`;
                        },
                        afterLabel: ctx => {
                            const name = ctx.raw.pt.top_list || '';
                            return name && name.toUpperCase() !== (ctx.dataset.party.name || '').toUpperCase()
                                ? `Lista: ${name.replace(/\s*\n\s*/g, ', ').slice(0, 90)}` : '';
                        },
                        footer: () => 'Klikni za stranicu stranke.',
                    }
                },
            },
            scales: {
                x: { type: 'linear', min: Math.min(...years) - 0.5, max: Math.max(...years) + 0.5,
                     afterBuildTicks: axis => { axis.ticks = [...new Set(years)].map(v => ({ value: v })); },
                     ticks: { callback: v => `${v}.`, autoSkip: true, maxRotation: 0, font: { size: 11 } },
                     grid: { color: 'rgba(0,0,0,0.05)' } },
                y: { beginAtZero: true, ticks: { callback: v => v + ' %' }, grid: { color: 'rgba(0,0,0,0.05)' },
                     title: { display: true, text: 'Udio glasova', color: '#6c757d', font: { weight: 'bold' } } },
            },
            animation: { duration: 500 },
        },
    });
    document.getElementById('psNote').innerHTML =
        (all ? 'Oblik točke: ● Sabor · ◆ Europski parlament · ▲ gradska i općinska vijeća · ■ županijske skupštine. ' : '')
        + 'Udio = glasovi lista koje je stranka predvodila (prva navedena u koaliciji) od svih glasova za liste na tim izborima. '
        + 'Na izborima za Sabor i Europski parlament ista koalicija ima jednog predvodnika u svim jedinicama (onog koji je predvodi s najviše glasova), '
        + 'u lokalnim izborima predvodnik je prva navedena stranka u svakoj općini. Šuplja točka: stranka tada nije predvodila nijednu listu, '
        + 'nego je bila partner, pa je prikazan udio koalicije (lokalno: svih lista u kojima je bila partner). Vijeća i skupštine zbrajaju sve općine i gradove u državi. '
        + 'Sabor 1992. i 1995. računa samo državnu listu, 2000. samo I.–X. izbornu jedinicu; manjinske jedinice nisu uključene.';
}

document.addEventListener('change', e => {
    if (e.target.id !== 'psPartners') return;
    _ps.partners = e.target.checked;
    renderPartyStrength();
});
document.addEventListener('click', e => {
    const k = e.target.closest && e.target.closest('[data-ps-kind]');
    if (k) { loadPartyStrength(k.dataset.psKind); return; }
    const c = e.target.closest && e.target.closest('[data-ps-id]');
    if (c) {
        const id = c.dataset.psId;
        if (_ps.on.has(id)) _ps.on.delete(id); else _ps.on.add(id);
        renderPartyStrength();
    }
});
