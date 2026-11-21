// Županijski dom and the 1990, 1992 and 1995 Sabor views.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Županijski dom (upper house, 1997) ---------------------------------
//
// Its own module rather than a year of the Sabor page: a different chamber,
// counties for districts, three seats each however large, and seats that the
// DIP report states outright instead of an allocation to compute.
function renderZupanijskiDom(d, area) {
    const t = d.totals || {};
    const turnoutPct = t.registered ? (t.cast / t.registered * 100) : 0;
    const colors = {};
    (d.parties || []).forEach((p, i) => { colors[p.name] = hemicycleColors[i % hemicycleColors.length]; });

    const dateLabel = d.date
        ? new Date(d.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'long', year: 'numeric' })
        : d.year;

    const partyRows = (d.parties || []).map(p => `
        <div class="d-flex align-items-center gap-2" style="font-size:0.86rem; padding:3px 0;">
            <span style="width:13px;height:13px;border-radius:50%;background:${colors[p.name]};display:inline-block;flex-shrink:0;border:1px solid rgba(0,0,0,0.15);"></span>
            <span class="fw-semibold flex-grow-1">${escapeHtml(p.name)}</span>
            <span class="text-muted">${p.seats}</span>
        </div>`).join('');

    const counties = (d.counties || []).map(c => {
        const lists = c.lists.map(l => `
            <tr${l.seats ? '' : ' class="text-muted"'}>
                <td>${l.seats ? `<span class="badge bg-success" style="font-size:0.7rem;">${l.seats}</span>` : ''}</td>
                <td style="font-size:0.85rem;">${escapeHtml(l.name)}</td>
                <td class="text-end" style="font-size:0.85rem;">${formatNumber(l.votes)}</td>
                <td class="text-end" style="font-size:0.85rem;">${formatPct(l.pct, 2)}</td>
            </tr>`).join('');
        const members = c.members.map(m => `
            <div style="font-size:0.85rem;">
                ${personLinkHtml(m.name, m.person_id)}
                ${m.deputy ? `<small class="text-muted"> - zamjenik: ${escapeHtml(m.deputy)}</small>` : ''}
            </div>`).join('');
        return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div>
                    <span class="fw-bold">${escapeHtml(c.name)}</span>
                    <span class="badge bg-dark ms-2" style="font-size:0.72rem;">${c.seats} mandata</span>
                </div>
                <small class="text-muted">
                    ${formatNumber(c.registered)} upisanih · ${formatNumber(c.cast)} glasovalo ·
                    ${formatPct(c.registered ? c.cast / c.registered * 100 : 0)} izlaznost
                </small>
            </div>
            <div class="table-responsive mt-2">
                <table class="table table-sm table-hover mb-2">
                    <thead><tr><th style="width:34px;"></th><th>Lista</th><th class="text-end">Glasovi</th><th class="text-end">%</th></tr></thead>
                    <tbody>${lists}</tbody>
                </table>
            </div>
            <div class="mt-1"><small class="text-muted fw-semibold">Izabrani zastupnici</small>${members}</div>
        </div>`;
    }).join('');

    area.innerHTML = `
        <div class="card p-3 mb-3">
            <h5 class="fw-bold mb-1">Županijski dom Sabora - ${dateLabel}</h5>
            <p class="text-muted mb-3" style="font-size:0.86rem;">
                Gornji dom Sabora, 1993.–2001. Svaka od 21 županije birala je po
                ${d.seats_per_county} zastupnika, neovisno o veličini, pa je izabrano
                ${d.elected_seats}. Dom je ukinut ustavnim promjenama 2001.
            </p>
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Mandati po listama</div>
                    ${partyRows}
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Ukupno ${d.elected_seats} izabranih; uz njih je predsjednik Republike
                        mogao imenovati do ${d.appointed_seats} zastupnika, koje izvješće DIP-a
                        ne navodi.
                        <br>Mandati su prikazani po <em>listi</em> - kako ih izvješće navodi - a ne po
                        stranačkoj pripadnosti pojedinog zastupnika; zajedničke liste zato stoje pod
                        prvom navedenom strankom.
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Izlaznost</div>
                    <div style="font-size:0.86rem;">
                        <div class="d-flex justify-content-between"><span class="text-muted">Upisanih birača</span><strong>${formatNumber(t.registered || 0)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Glasovalo</span><strong>${formatNumber(t.cast || 0)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Važećih listića</span><strong>${formatNumber(t.valid || 0)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Nevažećih listića</span><strong>${formatNumber(t.invalid || 0)}</strong></div>
                        <div class="d-flex justify-content-between mt-1 pt-1" style="border-top:1px solid rgba(0,0,0,0.08);"><span class="text-muted">Izlaznost</span><strong>${formatPct(turnoutPct)}</strong></div>
                    </div>
                </div>
            </div>
        </div>
        <h6 class="fw-bold mb-2"><i class="bi bi-geo-alt me-2"></i>Rezultati po županijama</h6>
        ${counties}`;
}

// Shared by the 1992 and 1995 views, the two mixed-system Sabor years.
const mixedPersonLink = (n, id) => personLinkHtml(n, id);
// District coalitions are printed as "HSS,HSLS,HNS" in the 1995 report and are
// stored that way; breathe on them for display only.
const mixedListLabel = t => escapeHtml(t).replace(/,(?=\S)/g, ', ');

function mixedDateLabel(d) {
    return d.date
        ? new Date(d.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'long', year: 'numeric' })
        : d.year;
}

function mixedPartyRows(d) {
    const colors = {};
    (d.parties || []).forEach((p, i) => { colors[p.name] = hemicycleColors[i % hemicycleColors.length]; });
    return (d.parties || []).map(p => `
        <div class="d-flex align-items-center gap-2" style="font-size:0.86rem; padding:3px 0;">
            <span style="width:13px;height:13px;border-radius:50%;background:${colors[p.name]};display:inline-block;flex-shrink:0;border:1px solid rgba(0,0,0,0.15);"></span>
            <span class="fw-semibold flex-grow-1">${escapeHtml(p.name)}</span>
            <span class="text-muted">${p.seats}</span>
        </div>`).join('');
}

// A candidate contest: the top candidate takes the seat outright. `r.list_vote`
// (1992 only) adds how the same unit voted on the countrywide list.
function mixedRaceCard(r) {
    const rows = (r.candidates || []).map(c => `
        <tr${c.won ? '' : ' class="text-muted"'}>
            <td>${c.won ? '<i class="bi bi-check-circle-fill text-success"></i>' : ''}</td>
            <td style="font-size:0.85rem;">${mixedPersonLink(c.name, c.person_id)}</td>
            <td style="font-size:0.8rem;" class="text-muted">${mixedListLabel(c.list)}</td>
            <td class="text-end" style="font-size:0.85rem;">${formatNumber(c.votes)}</td>
            <td class="text-end" style="font-size:0.85rem;">${formatPct(c.pct, 2)}</td>
        </tr>`).join('');
    const listVote = (r.list_vote || []).length ? `
        <div class="text-muted mt-2" style="font-size:0.78rem;">Državna lista u ovoj jedinici:
            ${r.list_vote.map(l => `${escapeHtml(l.name.split(' - ').pop())} ${formatPct(l.pct, 1)}`).join(' · ')}</div>` : '';
    return `
    <div class="card result-card mb-3 p-3">
        <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
            <div>
                <span class="fw-bold">${escapeHtml(r.label)}</span>
                ${r.minority ? `<span class="badge bg-secondary ms-2" style="font-size:0.7rem;">${escapeHtml(r.minority)}</span>` : ''}
                ${r.seats && r.seats > 1 ? `<span class="badge bg-dark ms-1" style="font-size:0.7rem;">${r.seats} mandata</span>` : ''}
            </div>
            <small class="text-muted">
                ${formatNumber(r.registered)} upisanih · ${formatNumber(r.cast)} glasovalo ·
                ${formatPct(r.turnout_pct, 2)} izlaznost · ${formatNumber(r.invalid)} nevažećih
            </small>
        </div>
        ${r.multi_vote ? `<div class="text-muted mt-1" style="font-size:0.78rem;">
            Bira ${r.seats} zastupnika, pa jedan listić nosi do ${r.seats} glasa - zbroj glasova je
            zato veći od broja važećih listića, a postoci se računaju od ukupnog broja glasova.</div>` : ''}
        <div class="table-responsive mt-2">
            <table class="table table-sm table-hover mb-0">
                <thead><tr><th style="width:28px;"></th><th>Kandidat</th><th>Stranka</th><th class="text-end">Glasovi</th><th class="text-end">%</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        ${listVote}
    </div>`;
}

function renderSabor1995(d, area) {
    const dateLabel = mixedDateLabel(d);
    const personLink = mixedPersonLink;
    const partyRows = mixedPartyRows(d);

    // A proportional contest: list table on the left, elected members grouped
    // under the list that returned them. No personal votes existed — the
    // ballot was for the list — so no per-member figure is shown.
    const proportional = (sec, id, note) => {
        const rows = (sec.lists || []).map(l => `
            <tr${l.seats ? '' : ' class="text-muted"'}>
                <td>${l.seats ? `<span class="badge bg-success" style="font-size:0.7rem;">${l.seats}</span>` : ''}</td>
                <td style="font-size:0.85rem;">${escapeHtml(l.name)}</td>
                <td class="text-end" style="font-size:0.85rem;">${formatNumber(l.votes)}</td>
                <td class="text-end" style="font-size:0.85rem;">${formatPct(l.pct, 2)}</td>
            </tr>`).join('');
        const members = (sec.members_by_list || []).map(g => `
            <div class="mb-2">
                <div class="fw-semibold" style="font-size:0.82rem;">${escapeHtml(g.list)}
                    <span class="badge bg-dark ms-1" style="font-size:0.68rem;">${g.seats}</span></div>
                <div style="font-size:0.85rem;">${g.names.map(personLink).join(' · ')}</div>
            </div>`).join('');
        return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div>
                    <span class="fw-bold">${escapeHtml(sec.label)}</span>
                    <span class="badge bg-dark ms-2" style="font-size:0.72rem;">${sec.seats} mandata</span>
                </div>
                <small class="text-muted">
                    ${formatNumber(sec.registered)} upisanih · ${formatNumber(sec.cast)} glasovalo ·
                    ${formatPct(sec.registered ? sec.cast / sec.registered * 100 : 0)} izlaznost ·
                    ${formatNumber(sec.invalid)} nevažećih
                </small>
            </div>
            ${note ? `<div class="text-muted mt-1" style="font-size:0.8rem;">${note}</div>` : ''}
            <div class="table-responsive mt-2">
                <table class="table table-sm table-hover mb-2">
                    <thead><tr><th style="width:34px;"></th><th>Lista</th><th class="text-end">Glasovi</th><th class="text-end">%</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
            <div class="mt-1"><small class="text-muted fw-semibold d-block mb-1">Izabrani zastupnici</small>${members}</div>
        </div>`;
    };

    const race = mixedRaceCard;

    const nat = d.national || {}, dia = d.diaspora || {};
    const totalReg = (nat.registered || 0) + (dia.registered || 0);
    const totalCast = (nat.cast || 0) + (dia.cast || 0);

    area.innerHTML = `
        <div class="card p-3 mb-3">
            <h5 class="fw-bold mb-1">Zastupnički dom Sabora - ${dateLabel}</h5>
            <p class="text-muted mb-3" style="font-size:0.86rem;">
                ${d.total_seats} zastupnika izabrano je u četiri odvojena izbora istoga dana:
                ${nat.seats} s jedne državne liste (razmjerno, prag 5%),
                ${dia.seats} s posebnih lista dijaspore,
                ${(d.districts || []).length} u jednomandatnim izbornim jedinicama (pobjeđuje kandidat
                s najviše glasova, bez drugog kruga) i
                ${(d.minorities || []).reduce((a, m) => a + (m.seats || 0), 0)} u posebnim jedinicama
                za nacionalne manjine. Zato ovdje nema D'Hondtove raspodjele - mandati su onakvi
                kakvima ih izvješće Izborne komisije navodi.
            </p>
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Mandati po strankama</div>
                    ${partyRows}
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Zajedničke liste stoje pod prvom navedenom strankom, kao i drugdje na
                        stranici. IDS je 1995. bio i dio državne liste predvođene HSS-om, pa se
                        njegova 2 mandata u izbornim jedinicama u nekim pregledima pribrajaju
                        toj koaliciji (16 + 2 = 18).
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Izlaznost</div>
                    <div style="font-size:0.86rem;">
                        <div class="d-flex justify-content-between"><span class="text-muted">Upisanih birača</span><strong>${formatNumber(totalReg)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Glasovalo</span><strong>${formatNumber(totalCast)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">- u Hrvatskoj</span><span>${formatNumber(nat.cast || 0)} (${formatPct(nat.registered ? nat.cast / nat.registered * 100 : 0)})</span></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">- u inozemstvu</span><span>${formatNumber(dia.cast || 0)} (${formatPct(dia.registered ? dia.cast / dia.registered * 100 : 0)})</span></div>
                        <div class="d-flex justify-content-between mt-1 pt-1" style="border-top:1px solid rgba(0,0,0,0.08);"><span class="text-muted">Izlaznost</span><strong>${formatPct(totalReg ? totalCast / totalReg * 100 : 0)}</strong></div>
                    </div>
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Brojke su s državne liste i lista dijaspore - one zajedno pokrivaju cijeli
                        birački popis točno jednom. Izborne jedinice broje iste birače ponovno, pa se
                        njihove brojke prikazuju uz svaku jedinicu, ali se ne zbrajaju u ukupnu izlaznost.
                    </div>
                </div>
            </div>
        </div>

        <h6 class="fw-bold mb-2"><i class="bi bi-list-ol me-2"></i>Državna lista</h6>
        ${proportional(nat, 'nat', 'Jedna lista za cijelu Hrvatsku, mandati razmjerno uz izborni prag od 5%.')}

        <h6 class="fw-bold mb-2"><i class="bi bi-globe-americas me-2"></i>Posebne liste - dijaspora</h6>
        ${proportional(dia, 'dia', 'Birači izvan Hrvatske; 1995. je dijaspori pripadao utvrđen broj od 12 mandata.')}

        <h6 class="fw-bold mb-2"><i class="bi bi-geo-alt me-2"></i>Izborne jedinice I.–XXVIII.</h6>
        ${(d.districts || []).map(race).join('')}

        <h6 class="fw-bold mb-2"><i class="bi bi-people me-2"></i>Posebne izborne jedinice - nacionalne manjine</h6>
        ${(d.minorities || []).map(race).join('')}`;
}

function renderSabor1992(d, area) {
    const nat = d.national || {};
    const short = name => name.split(' - ').pop();
    const listSeats = l => (l.seats || 0) + (l.minority_seats || 0);

    const listRows = (nat.lists || []).map(l => `
        <tr${listSeats(l) ? '' : ' class="text-muted"'}>
            <td>${l.seats ? `<span class="badge bg-success" style="font-size:0.7rem;">${l.seats}</span>` : ''}
                ${l.minority_seats ? `<span class="badge bg-secondary" style="font-size:0.7rem;" title="Mandati pripadnika manjina proglašeni s ove liste">+${l.minority_seats}</span>` : ''}</td>
            <td style="font-size:0.85rem;">${escapeHtml(l.name)}</td>
            <td class="text-end" style="font-size:0.85rem;">${formatNumber(l.votes)}</td>
            <td class="text-end" style="font-size:0.85rem;">${formatPct(l.pct, 2)}</td>
        </tr>`).join('');
    const memberGroup = (title, names, badge) => `
        <div class="mb-2">
            <div class="fw-semibold" style="font-size:0.82rem;">${escapeHtml(title)}
                ${badge ? `<span class="badge bg-dark ms-1" style="font-size:0.68rem;">${badge}</span>` : ''}</div>
            <div style="font-size:0.85rem;">${names.map(mixedPersonLink).join(' · ')}</div>
        </div>`;
    const members = (nat.members_by_list || []).map(g => memberGroup(g.list, g.names, g.seats)).join('');
    const serbs = (d.serb_seats || []).map(g => memberGroup(g.list, g.names, g.names.length)).join('');
    const extra = d.extra_minority_seat;

    // The list vote per unit, against the six largest lists nationally. The
    // abroad and residual rows close the table so its columns sum to the
    // national result.
    const top = (nat.lists || []).slice(0, 6).map(l => d.lists.indexOf(l.name));
    const unitRows = (d.units || []).map(u => {
        const valid = u.valid || 1;
        const shown = top.reduce((a, i) => a + u.votes[i], 0);
        return `<tr>
            <td style="font-size:0.8rem; white-space:nowrap;">${escapeHtml(u.label)}</td>
            ${top.map(i => `<td class="text-end" style="font-size:0.8rem;">${formatPct(u.votes[i] / valid * 100, 1)}</td>`).join('')}
            <td class="text-end text-muted" style="font-size:0.8rem;">${formatPct((valid - shown) / valid * 100, 1)}</td>
        </tr>`;
    }).join('');

    area.innerHTML = `
        <div class="card p-3 mb-3">
            <h5 class="fw-bold mb-1">Zastupnički dom Sabora - ${mixedDateLabel(d)}</h5>
            <p class="text-muted mb-3" style="font-size:0.86rem;">
                ${d.total_seats} zastupnika: ${nat.seats} s jedne državne liste (razmjerno, prag 3%),
                ${(d.districts || []).length} u jednomandatnim izbornim jedinicama (pobjeđuje kandidat s
                najviše glasova, bez drugog kruga), ${(d.minorities || []).length} u posebnim jedinicama za
                manje manjine te ${(d.serb_seats || []).reduce((a, g) => a + g.names.length, 0) + (extra ? 1 : 0)}
                proglašena s državnih lista kako bi manjine dobile zajamčena mjesta. Zato ovdje nema
                D'Hondtove raspodjele - mandati su onakvi kakvima ih izvješće Izborne komisije navodi.
            </p>
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Mandati po strankama</div>
                    ${mixedPartyRows(d)}
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Kandidati u izbornim jedinicama pribrojeni su državnoj listi svoje stranke; DA, IDS i
                        RDS imali su zajedničku državnu listu, a zasebne kandidate u jedinicama. Zajednički
                        kandidati stoje pod prvom navedenom strankom.
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Izlaznost (državna lista)</div>
                    <div style="font-size:0.86rem;">
                        <div class="d-flex justify-content-between"><span class="text-muted">Upisanih birača</span><strong>${formatNumber(nat.registered)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Glasovalo</span><strong>${formatNumber(nat.cast)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Nevažećih listića</span><span>${formatNumber(nat.invalid)}</span></div>
                        <div class="d-flex justify-content-between mt-1 pt-1" style="border-top:1px solid rgba(0,0,0,0.08);"><span class="text-muted">Izlaznost</span><strong>${formatPct(nat.registered ? nat.cast / nat.registered * 100 : 0)}</strong></div>
                    </div>
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Izborne jedinice broje iste birače ponovno, pa se njihove brojke prikazuju uz svaku
                        jedinicu, ali se ne zbrajaju u ukupnu izlaznost.
                    </div>
                </div>
            </div>
        </div>

        <h6 class="fw-bold mb-2"><i class="bi bi-list-ol me-2"></i>Državna lista</h6>
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div><span class="fw-bold">${escapeHtml(nat.label || 'Državna lista')}</span>
                    <span class="badge bg-dark ms-2" style="font-size:0.72rem;">${nat.seats} mandata</span></div>
                <small class="text-muted">${formatNumber(nat.valid)} važećih glasova</small>
            </div>
            <div class="table-responsive mt-2">
                <table class="table table-sm table-hover mb-2">
                    <thead><tr><th style="width:70px;"></th><th>Lista</th><th class="text-end">Glasovi</th><th class="text-end">%</th></tr></thead>
                    <tbody>${listRows}</tbody>
                </table>
            </div>
            <div class="mt-1"><small class="text-muted fw-semibold d-block mb-1">Izabrani zastupnici</small>${members}</div>
            <div class="mt-2"><small class="text-muted fw-semibold d-block mb-1">Srpska nacionalna zajednica - 13 mandata (11,5% stanovništva 1981.), proglašeni s državnih lista</small>${serbs}</div>
            ${extra ? `<div class="mt-2"><small class="text-muted fw-semibold d-block mb-1">Peti mandat manjih manjina - ${escapeHtml(extra.community)} zajednica</small>
                ${memberGroup(extra.list, [extra.name], 1)}</div>` : ''}
            <details class="mt-2">
                <summary class="text-muted" style="font-size:0.85rem; cursor:pointer;">Glasovi za državne liste po izbornim jedinicama</summary>
                <div class="text-muted mt-2" style="font-size:0.78rem;">
                    Redovito biračko tijelo po jedinicama, uz inozemstvo. Posljednji redak su listići izvan
                    redovitog biračkog tijela koje izvješće ne raščlanjuje po jedinicama - s njime stupci
                    daju točno državni rezultat. Jedinice 1. i 3. posebne glasovale su za državne liste u
                    jedinicama u kojima leže, pa nemaju zaseban redak.
                </div>
                <div class="table-responsive mt-2" style="max-height:480px; overflow-y:auto;">
                    <table class="table table-sm table-hover mb-0">
                        <thead style="position:sticky; top:0; background:var(--bs-body-bg);"><tr>
                            <th style="font-size:0.8rem;">Jedinica</th>
                            ${top.map(i => `<th class="text-end" style="font-size:0.8rem;">${escapeHtml(short(d.lists[i]))}</th>`).join('')}
                            <th class="text-end" style="font-size:0.8rem;">Ostali</th>
                        </tr></thead>
                        <tbody>${unitRows}</tbody>
                    </table>
                </div>
            </details>
        </div>

        <h6 class="fw-bold mb-2"><i class="bi bi-geo-alt me-2"></i>Izborne jedinice I.–LX.</h6>
        ${(d.districts || []).map(mixedRaceCard).join('')}

        <h6 class="fw-bold mb-2"><i class="bi bi-people me-2"></i>Posebne izborne jedinice - nacionalne manjine</h6>
        ${(d.minorities || []).map(mixedRaceCard).join('')}`;
}

// Per-chamber intro for the 1990 view: what the chamber was and who voted.
const SABOR_1990_INTRO = {
    dpv: d => `Sabor iz ${d.year}. imao je tri vijeća, birana odvojeno; ovo je Društveno-političko vijeće,
        za koje su glasovali svi birači. ${d.total_seats} zastupnika izabrano je u isto toliko
        jednomandatnih jedinica`,
    vo: d => `Sabor iz ${d.year}. imao je tri vijeća, birana odvojeno; ovo je Vijeće općina, u koje je
        svaka općina birala po jednog zastupnika, a Zagreb još jednog za Gradsku zajednicu općina.
        ${d.total_seats} zastupnika izabrano je u isto toliko jednomandatnih jedinica`,
    vur: d => `Sabor iz ${d.year}. imao je tri vijeća, birana odvojeno; ovo je Vijeće udruženog rada,
        koje su birali zaposleni prema mjestu rada, a ne prebivališta. ${d.total_seats} zastupnika
        izabrano je u isto toliko jednomandatnih jedinica`,
};

function renderSabor1990(d, area) {
    const t1 = (d.round_totals || {})['1'] || {};
    const pills = (d.chambers || []).map(c => `
        <button type="button" class="btn btn-sm ${c.key === d.chamber_key ? 'btn-secondary' : 'btn-outline-secondary'}"
                data-chamber="${c.key}">${escapeHtml(c.title)}</button>`).join('');
    const overlapping = (d.units || []).filter(u => u.rounds.some(r => r.overlapping));
    const fmtDate = iso => iso
        ? new Date(iso).toLocaleDateString('hr-HR', { day: 'numeric', month: 'long', year: 'numeric' })
        : '';
    const roundTable = r => `
        <div class="mt-2">
            ${r.round === 2 ? `<div class="fw-semibold" style="font-size:0.82rem;">2. krug${r.date ? ' - ' + fmtDate(r.date) : ''}</div>` : ''}
            <div class="table-responsive">
                <table class="table table-sm table-hover mb-1">
                    <thead><tr><th style="width:28px;"></th><th>Kandidat</th><th>Predlagatelj</th><th class="text-end">Glasovi</th><th class="text-end">%</th></tr></thead>
                    <tbody>${r.candidates.map(c => `
                        <tr${c.won ? '' : ' class="text-muted"'}>
                            <td>${c.won ? '<i class="bi bi-check-circle-fill text-success"></i>' : ''}</td>
                            <td style="font-size:0.85rem;">${mixedPersonLink(c.name, c.person_id)} <span class="text-muted" style="font-size:0.75rem;">${escapeHtml(c.residence || '')}</span></td>
                            <td style="font-size:0.8rem;" class="text-muted">${escapeHtml(c.list)}</td>
                            <td class="text-end" style="font-size:0.85rem;">${c.votes === null ? '-' : formatNumber(c.votes)}</td>
                            <td class="text-end" style="font-size:0.85rem;">${formatPct(c.pct, 2)}</td>
                        </tr>`).join('')}</tbody>
                </table>
            </div>
            <small class="text-muted">${formatNumber(r.registered)} upisanih · ${formatNumber(r.cast)} glasovalo ·
                ${formatPct(r.turnout_pct, 2)} izlaznost · ${formatNumber(r.invalid)} nevažećih</small>
            ${r.overlapping ? `<div class="text-muted" style="font-size:0.75rem;">Birači ove jedinice glasovali su
                i u svojim općinama, pa nisu uključeni u ukupnu izlaznost.</div>` : ''}
            ${r.votes_known === false ? `<div class="text-muted" style="font-size:0.75rem;">Glasovi kandidata u
                sačuvanom primjerku izvješća nisu čitljivi (stranica je odrezana uz desni rub).</div>` : ''}
        </div>`;
    const unitCard = u => `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <span class="fw-bold">${escapeHtml(u.label)}</span>
                ${u.decided_in_round === 2 ? '<span class="badge bg-secondary" style="font-size:0.7rem;">odlučeno u 2. krugu</span>' : ''}
            </div>
            ${u.rounds.map(roundTable).join('')}
        </div>`;

    area.innerHTML = `
        <div class="d-flex flex-wrap gap-2 mb-3">${pills}</div>
        <div class="card p-3 mb-3">
            <h5 class="fw-bold mb-1">${escapeHtml(d.chamber)} Sabora - ${d.year}.</h5>
            <p class="text-muted mb-3" style="font-size:0.86rem;">
                ${(SABOR_1990_INTRO[d.chamber_key] || SABOR_1990_INTRO.dpv)(d)}: kandidat s većinom glasova
                izabran je u 1. krugu, a ondje gdje ga nije bilo glasovanje je ponovljeno i izabran je prvi
                u 2. krugu (${d.runoffs} jedinica).
            </p>
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Mandati po strankama</div>
                    ${mixedPartyRows(d)}
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Zajednički kandidat stoji pod prvom navedenom strankom; kandidati Koalicije narodnog
                        sporazuma pod koalicijom.
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="fw-semibold mb-1" style="font-size:0.9rem;">Izlaznost (1. krug)</div>
                    <div style="font-size:0.86rem;">
                        <div class="d-flex justify-content-between"><span class="text-muted">Upisanih birača</span><strong>${formatNumber(t1.registered)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Glasovalo</span><strong>${formatNumber(t1.cast)}</strong></div>
                        <div class="d-flex justify-content-between"><span class="text-muted">Nevažećih listića</span><span>${formatNumber(t1.invalid)}</span></div>
                        <div class="d-flex justify-content-between mt-1 pt-1" style="border-top:1px solid rgba(0,0,0,0.08);"><span class="text-muted">Izlaznost</span><strong>${formatPct(t1.registered ? t1.cast / t1.registered * 100 : 0)}</strong></div>
                    </div>
                    ${overlapping.length ? `<div class="text-muted mt-2" style="font-size:0.8rem;">
                        Bez jedinice ${overlapping.map(u => escapeHtml(u.name)).join(', ')}: njezini birači
                        glasovali su i u svojim općinama, pa bi se inače brojali dvaput.
                    </div>` : ''}
                    <div class="text-muted mt-2" style="font-size:0.8rem;">
                        Glasovi kandidata u izvješću ponegdje su nešto manji od broja glasovalih umanjenog za
                        nevažeće listiće; razlika je u samom izvješću, pa se važećim glasovima smatra zbroj
                        glasova kandidata.
                    </div>
                </div>
            </div>
        </div>
        <h6 class="fw-bold mb-2"><i class="bi bi-geo-alt me-2"></i>Izborne jedinice (${d.total_seats})</h6>
        ${(d.missing_units || []).length ? `<div class="text-muted mb-2" style="font-size:0.8rem;">
            Izvješće ne sadrži jedinice ${d.missing_units.join('., ')}.</div>` : ''}
        ${(d.units || []).map(unitCard).join('')}`;
}
