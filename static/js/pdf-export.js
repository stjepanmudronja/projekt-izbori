// The "Izvezi PDF" button: the page on show as an A4 PDF.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- PDF export of the page on show ----
// The page is captured as an image (html2canvas): jsPDF's built-in fonts have
// no č, ć or đ, and an image keeps the charts too. Search forms, buttons and
// the map are left out; a title block and the source line are laid in for the
// capture; the image is cut into A4 pages between cards, never through one.
const PDF_SKIP_MODULES = new Set(['home', 'sabor-analysis', 'results-eu']);
const PDF_HIDE = '.search-card, .spinner-wrapper, #stationMapCard, .chart-scroll-arrows, .bar-drag-hint, .bar-reset-btn, .home-arrows, .no-pdf';
const PDF_BREAKS = '.card, .chart-card, .result-card, .home-section, h5, h6, table, .compare-grid > *';

function pdfSelectionLabel(panel) {
    // What the page is about, from the choices made in its own dropdowns and
    // year pickers (both sit in the search area the PDF leaves out).
    const picks = Array.from(panel.querySelectorAll('select'))
        .filter(sel => sel.value && sel.offsetParent !== null && sel.selectedIndex >= 0)
        .map(sel => sel.options[sel.selectedIndex].text.trim())
        .filter(t => t && !/^(odaberi|sve|-)/i.test(t));
    const years = Array.from(panel.querySelectorAll('button.active[data-year]'))
        .filter(b => b.offsetParent !== null).map(b => b.dataset.year + '.');
    return [...picks, ...new Set(years)].join(' · ');
}

async function exportPagePDF() {
    const panel = document.querySelector('.module-panel.active');
    const btn = document.getElementById('pdfExportBtn');
    if (!panel || btn.disabled) return;
    const title = moduleTitle.textContent.trim();
    const selection = pdfSelectionLabel(panel);
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Izrađujem PDF...';

    const hidden = [];
    const head = document.createElement('div');
    head.className = 'pdf-export-head';
    head.innerHTML = `<h3>${escapeHtml(title)}</h3>
        ${selection ? `<div>${escapeHtml(selection)}</div>` : ''}
        <div>Projekt Izbori · ${new Date().toLocaleDateString('hr-HR', { day: 'numeric', month: 'long', year: 'numeric' })}</div>`;
    const foot = document.createElement('div');
    foot.className = 'pdf-export-foot';
    foot.innerHTML = document.querySelector('.site-footer').innerHTML;
    try {
        panel.querySelectorAll(PDF_HIDE).forEach(el => {
            if (el.style.display !== 'none') { hidden.push([el, el.style.display]); el.style.display = 'none'; }
        });
        panel.prepend(head);
        panel.append(foot);
        const top = panel.getBoundingClientRect().top;
        const heightPx = panel.scrollHeight;
        // Browsers cap a canvas near 32,000 px tall: scale down a very long page.
        const scale = Math.max(0.75, Math.min(2, 30000 / Math.max(heightPx, 1)));
        // Card tops are where a page may end.
        const breaks = Array.from(panel.querySelectorAll(PDF_BREAKS))
            .filter(el => el.offsetParent !== null)
            .map(el => Math.round((el.getBoundingClientRect().top - top) * scale))
            .filter(y => y > 0).sort((a, b) => a - b);
        const canvas = await html2canvas(panel, { scale, backgroundColor: '#ffffff', logging: false, useCORS: true });

        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        const margin = 10;
        const contentW = pdf.internal.pageSize.getWidth() - margin * 2;
        const contentH = pdf.internal.pageSize.getHeight() - margin * 2;
        const pagePx = Math.floor(canvas.width * contentH / contentW);
        let y = 0, first = true;
        while (y < canvas.height - 2) {
            let end = Math.min(y + pagePx, canvas.height);
            if (end < canvas.height) {
                // The last card top that still fits, if it leaves the page at least a third full.
                const fit = breaks.filter(b => b > y + pagePx / 3 && b <= end);
                if (fit.length) end = fit[fit.length - 1];
            }
            const slice = document.createElement('canvas');
            slice.width = canvas.width;
            slice.height = end - y;
            slice.getContext('2d').drawImage(canvas, 0, y, canvas.width, end - y, 0, 0, canvas.width, end - y);
            if (!first) pdf.addPage();
            pdf.addImage(slice.toDataURL('image/jpeg', 0.92), 'JPEG', margin, margin, contentW, (end - y) * contentW / canvas.width);
            first = false;
            y = end;
        }
        const name = urlSlug([title, selection].filter(Boolean).join(' ')) || 'projekt-izbori';
        pdf.save(`${name}.pdf`);
    } catch (err) {
        console.error('PDF export failed', err);
        btn.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>Izvoz nije uspio';
        setTimeout(() => { btn.innerHTML = original; }, 3000);
        return;
    } finally {
        head.remove();
        foot.remove();
        hidden.forEach(([el, display]) => { el.style.display = display; });
        btn.disabled = false;
    }
    btn.innerHTML = original;
}
