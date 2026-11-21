// Početna: headline numbers, highlight sliders and the mini career charts.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Home page: headline numbers + sliders of highlights (/api/home) ----
let _homeData = null;
async function initHome() {
    if (_homeData) return;
    const spinner = document.getElementById('homeSpinner');
    spinner.classList.add('show');
    try {
        const res = await fetch('/api/home');
        _homeData = await res.json();
        renderHome(_homeData);
    } catch (err) {
        document.getElementById('homeSections').innerHTML =
            '<div class="alert alert-warning">Pregled trenutačno nije dostupan.</div>';
    } finally {
        spinner.classList.remove('show');
    }
}

const homePct = v => (v ?? 0).toLocaleString('hr-HR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %';
const homeNum = v => (v ?? 0).toLocaleString('hr-HR');
const homeVotes = v => `${homeNum(v)} ${v % 10 === 1 && v % 100 !== 11 ? 'glas' : ([2, 3, 4].includes(v % 10) && ![12, 13, 14].includes(v % 100) ? 'glasa' : 'glasova')}`;
const homeRound = r => r.round > 1 ? ` · ${r.round}. krug` : '';

function homeSection(id, title, subtitle, cards) {
    if (!cards.length) return '';
    return `<section class="home-section">
        <div class="home-section-head">
            <div><h5>${title}</h5>${subtitle ? `<small>${subtitle}</small>` : ''}</div>
            <div class="home-arrows">
                <button type="button" data-scroll="${id}" data-dir="-1" title="Natrag"><i class="bi bi-chevron-left"></i></button>
                <button type="button" data-scroll="${id}" data-dir="1" title="Dalje"><i class="bi bi-chevron-right"></i></button>
            </div>
        </div>
        <div class="home-track" id="${id}">${cards.join('')}</div>
    </section>`;
}

function renderHome(d) {
    const st = d.stats || {};
    document.getElementById('homeStats').innerHTML = [
        [`${st.first_year}.–${st.last_year}.`, 'razdoblje'],
        [homeNum(st.elections), 'izbora'],
        [homeNum(st.persons), 'kandidata i političara'],
        [homeNum(st.candidacies), 'kandidatura'],
        [homeNum(st.places), 'općina i gradova'],
    ].map(([v, l]) => `<div class="home-stat"><b>${v}</b><span>${l}</span></div>`).join('');

    const where = r => r.place_id ? placeLinkHtml(r.place_id, r.name) : escapeHtml(r.name || '');
    const sections = [];

    const pres = d.presidential || { elections: [], records: [] };
    const resultsLink = year => `<a href="#" class="home-results mt-auto small" data-cat="predsjednicki" data-year="${year}">Rezultati izbora <i class="bi bi-arrow-right"></i></a>`;
    // One card per president (newest first), holding every election they won.
    const presidents = [];
    for (const e of pres.elections) {
        let p = presidents.find(x => x.person_id === e.winner.person_id);
        if (!p) presidents.push(p = { person_id: e.winner.person_id, name: e.winner.name, wins: [] });
        p.wins.unshift(e);
    }
    const winLinks = p => p.wins.map(e => `<a href="#" class="home-results" data-cat="predsjednicki" data-year="${e.year}">${e.year}.</a>`).join(' · ');
    sections.push(homeSection('homePresidents', 'Predsjednici Republike Hrvatske',
        'Udio glasova svakog predsjednika na svim izborima na kojima se kandidirao; istaknute su točke njegovih pobjeda.',
        presidents.map((p, i) => `<div class="home-card hc-wide">
            <div class="hc-kicker">${p.wins.length > 1 ? `${p.wins.length} mandata` : '1 mandat'}</div>
            <div class="hc-title">${personLinkHtml(p.name, p.person_id)}</div>
            <div class="hc-chart"><canvas id="homePresChart${i}"></canvas></div>
            <div class="small mt-auto">Rezultati izbora: ${winLinks(p)}</div>
        </div>`)));
    // Famous outside politics: the same career chart, nothing highlighted.
    const figures = d.public_figures || [];
    const ranIn = f => {
        const seen = [];
        f.career.forEach(c => {
            const t = `${c.type.replace(' izbori', '').replace('Parlamentarni', 'Sabor')} ${c.year}.`;
            if (!seen.includes(t)) seen.push(t);
        });
        return seen.join(' · ');
    };
    sections.push(homeSection('homeFigures', 'Poznata lica na izbornim listama',
        'Glazbenici, sportaši, glumci i poduzetnici koji su se kandidirali: njihov udio glasova na svim izborima.',
        figures.map((f, i) => `<div class="home-card hc-wide">
            <div class="hc-kicker">${escapeHtml(f.known_as)}</div>
            <div class="hc-title">${personLinkHtml(f.name, f.person_id)}</div>
            <div class="hc-chart"><canvas id="homeFigureChart${i}"></canvas></div>
            <div class="hc-muted mt-auto">${escapeHtml(ranIn(f))}</div>
        </div>`)));
    sections.push(homeSection('homePresRecords', 'Rekordi predsjedničkih izbora', '',
        pres.records.map(r => `<div class="home-card">
            <div class="hc-kicker">${escapeHtml(r.kind)}</div>
            <div class="hc-big">${escapeHtml(r.value)}</div>
            ${r.person_id ? `<div class="fw-semibold">${personLinkHtml(r.name, r.person_id)}</div>` : ''}
            <div class="hc-muted">${escapeHtml(r.text)}</div>
            ${resultsLink(r.year)}
        </div>`)));

    const streaks = d.streaks || { items: [] };
    sections.push(homeSection('homeStreaks', `Na vlasti bez prekida od ${streaks.since}.`,
        `${homeNum(streaks.count)} načelnika, gradonačelnika i župana pobijedilo je na svim neposrednim izborima od ${streaks.since}.`,
        streaks.items.map(s => `<div class="home-card">
            <div class="hc-kicker">${escapeHtml(s.office)}</div>
            <div class="hc-title">${personLinkHtml(s.name, s.person_id)}</div>
            <div>${s.place_id ? placeLinkHtml(s.place_id, s.place) : escapeHtml(s.place || '')}</div>
            <span class="hc-badge">${s.wins} pobjeda zaredom</span>
            <div class="hc-muted mt-auto">Zadnji izbori: ${homePct(s.share)}</div>
        </div>`)));

    sections.push(homeSection('homeClosest', 'Najtješnje utrke',
        'Izbori za načelnika, gradonačelnika i župana odlučeni s najmanje glasova razlike.',
        (d.closest || []).map(r => `<div class="home-card">
            <div class="hc-kicker">${escapeHtml(r.office)} · ${r.year}.${homeRound(r)}</div>
            <div class="hc-title">${where(r)}</div>
            <span class="hc-badge${r.tie ? ' tie' : ''}">${r.tie ? 'Izjednačeno' : `Razlika: ${homeVotes(r.margin)}`}</span>
            <div class="hc-row"><span>${personLinkHtml(r.first.name, r.first.person_id)}</span><span>${homeNum(r.first.votes)}</span></div>
            <div class="hc-row"><span>${personLinkHtml(r.second.name, r.second.person_id)}</span><span>${homeNum(r.second.votes)}</span></div>
        </div>`)));

    sections.push(homeSection('homeLandslides', 'Najuvjerljivije pobjede',
        'Najveći udio glasova u utrci s barem dva kandidata.',
        (d.landslides || []).map(r => `<div class="home-card">
            <div class="hc-kicker">${escapeHtml(r.office)} · ${r.year}.${homeRound(r)}</div>
            <div class="hc-big">${homePct(r.share)}</div>
            <div class="hc-title">${personLinkHtml(r.first.name, r.first.person_id)}</div>
            <div>${where(r)}</div>
            <div class="hc-muted mt-auto">${homeVotes(r.first.votes)} · ${r.candidates} kandidata</div>
        </div>`)));

    for (const [key, label] of [['sabor', 'Sabor'], ['eu', 'Europski parlament']]) {
        const p = (d.preferences || {})[key];
        if (!p) continue;
        sections.push(homeSection(`homePref${key}`, `Najviše preferencijskih glasova - ${label} ${p.year}.`,
            'Osobni glasovi koje su birači dali kandidatu unutar njegove liste.',
            p.items.map((x, i) => `<div class="home-card">
                <div class="hc-rank">#${i + 1}</div>
                <div class="hc-title">${personLinkHtml(x.name, x.person_id)}</div>
                <div class="hc-muted">${escapeHtml(x.list || '')}</div>
                <div class="hc-big mt-auto">${homeNum(x.votes)}</div>
            </div>`)));
    }

    sections.push(homeSection('homeCareers', 'Najduže izborne karijere',
        'Političari koji su se kandidirali na najviše izbora.',
        (d.careers || []).map(c => `<div class="home-card">
            <div class="hc-title">${personLinkHtml(c.name, c.person_id)}</div>
            <div class="hc-big">${c.elections}</div>
            <div class="hc-muted">izbora, ${c.from}.–${c.to}.</div>
            <div class="hc-muted mt-auto">${c.kinds > 1 ? `${c.kinds} vrste izbora` : 'jedna vrsta izbora'}</div>
        </div>`)));

    const t = d.turnout || { top: [] };
    sections.push(homeSection('homeTurnout', `Najveća izlaznost - lokalni izbori ${t.year}.`,
        'Općine i gradovi s najviše birača koji su glasali (vijeće, 1. krug; mjesta s barem 300 birača).',
        t.top.map((x, i) => `<div class="home-card">
            <div class="hc-rank">#${i + 1}</div>
            <div class="hc-title">${placeLinkHtml(x.place_id, x.name)}</div>
            <div class="hc-big">${homePct(x.pct)}</div>
            <div class="hc-muted mt-auto">${homeNum(x.cast)} od ${homeNum(x.registered)} birača</div>
        </div>`)));

    const un = d.unopposed || [];
    if (un.length) {
        const max = Math.max(...un.map(u => u.count), 1);
        sections.push(`<section class="home-section">
            <div class="home-section-head"><div><h5>Sve više izbora bez protukandidata</h5>
                <small>Utrke za načelnika, gradonačelnika i župana u kojima se kandidirala samo jedna osoba.</small></div></div>
            <div class="home-card" style="max-width: 32rem;">
                <div class="home-bars">${un.map(u => `<div><b>${u.count}</b><i style="height:${Math.round(u.count / max * 100)}%"></i>${u.year}.</div>`).join('')}</div>
            </div>
        </section>`);
    }
    document.getElementById('homeSections').innerHTML = sections.join('');
    presidents.forEach((p, i) => renderHomePresChart(
        document.getElementById(`homePresChart${i}`), (pres.careers || {})[p.person_id] || [], p.wins));
    figures.forEach((f, i) => renderHomePresChart(document.getElementById(`homeFigureChart${i}`), f.career, []));
}

// A president's career in miniature: the politician page's vote-share line
// (points coloured by election type, a click opens that election), with each
// presidential win (its deciding round) drawn larger.
const _homeCharts = [];
function renderHomePresChart(canvas, career, wins) {
    if (!canvas || !career.length) { if (canvas) canvas.parentElement.style.display = 'none'; return; }
    const isThis = c => /predsjedni/i.test(c.type) && wins.some(e => c.year === e.year && c.round === e.rounds);
    const shares = career.map(c => c.share);
    const colors = career.map(c => getElectionColor(c.type).border);
    const targets = career.map(c => {
        const cat = electionTypeToCategory(c.type);
        if (!cat) return null;
        return cat === 'lokalni'
            ? { cat, year: c.year, kind: c.lokalni_kind, countyId: c.county_id, municipalityId: c.municipality_id }
            : { cat, year: c.year };
    });
    const old = _homeCharts.findIndex(ch => ch.canvas === canvas);
    if (old >= 0) _homeCharts.splice(old, 1)[0].destroy();
    _homeCharts.push(new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: career.map(c => c.year),
            datasets: [{
                data: shares,
                borderColor: 'rgb(15, 52, 96)',
                backgroundColor: 'rgba(15, 52, 96, 0.08)',
                fill: true, tension: 0.3, borderWidth: 2,
                pointBackgroundColor: colors,
                pointBorderColor: career.map(c => isThis(c) ? '#C9A227' : '#fff'),
                pointBorderWidth: career.map(c => isThis(c) ? 3 : 1.5),
                pointRadius: career.map(c => isThis(c) ? 6.5 : 3.5),
                pointHoverRadius: 7,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            layout: { padding: { top: 8, right: 6 } },
            onClick: (evt, items) => {
                const t = items && items.length && targets[items[0].index];
                if (t) izlNavigateTo(t.cat, t.year, t);
            },
            onHover: (evt, items) => {
                const hit = items && items.length && targets[items[0].index];
                if (evt && evt.native) evt.native.target.style.cursor = hit ? 'pointer' : 'default';
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)', padding: 8, cornerRadius: 6, displayColors: false,
                    titleFont: { size: 11 }, bodyFont: { size: 11 },
                    callbacks: {
                        title: items => {
                            const c = career[items[0].dataIndex];
                            return `${c.type.replace('izbori', '').trim()} ${c.year}.${c.round > 1 ? ` (${c.round}. krug)` : ''}`
                                + (c.district ? `\n${c.district}` : '');
                        },
                        label: ctx => {
                            const c = career[ctx.dataIndex];
                            return [`Udio: ${formatPct(c.share, 2)}`, `Glasovi: ${c.votes.toLocaleString('hr-HR')}`];
                        },
                    }
                },
            },
            scales: {
                // A round top that fits: a 0.7 % candidate is not a flat line at the bottom.
                y: { beginAtZero: true, max: [1, 2, 5, 10, 25, 50, 75, 100].find(v => v >= Math.max(...shares) * 1.15) || 100,
                     grid: { color: 'rgba(0,0,0,0.05)' },
                     ticks: { maxTicksLimit: 5, font: { size: 9 }, callback: v => formatPct(v, v % 1 ? 1 : 0) } },
                x: { grid: { display: false }, ticks: { font: { size: 9 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 6 } }
            },
            animation: { duration: 600 }
        }
    }));
}
document.addEventListener('click', e => {
    const a = e.target.closest && e.target.closest('.home-results');
    if (!a) return;
    e.preventDefault();
    izlNavigateTo(a.dataset.cat, Number(a.dataset.year));
});
document.addEventListener('click', e => {
    const btn = e.target.closest && e.target.closest('[data-scroll]');
    if (!btn) return;
    const track = document.getElementById(btn.dataset.scroll);
    if (track) track.scrollBy({ left: Number(btn.dataset.dir) * track.clientWidth * 0.85 });
});
