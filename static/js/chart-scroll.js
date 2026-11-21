// Horizontal scrolling for wide line charts (izlaznost, politician, station).
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// Wraps a chart's canvas in a horizontally scrollable container (idempotent),
// then sizes the inner wrapper based on label count so x-tick labels don't
// crowd together as more elections are added. Adds floating left/right scroll
// buttons in the top-right corner; they auto-hide when the chart fits.
//
// IMPORTANT: call this BEFORE `new Chart(ctx, …)` for the canvas. Chart.js
// measures the parent element on creation, so the inner wrapper must already
// be at its final width — otherwise the chart stays at the old width even
// after a resize() call.
//
// Reused across the izlaznost / station-winner / politician charts so adding
// new elections gives every chart consistent breathing room + scroll affordance.
function applyChartScroll(canvas, labelCount, opts) {
    if (!canvas) return;
    opts = opts || {};
    const pxPerPoint = opts.pxPerPoint || 95;
    const edgePadding = opts.edgePadding || 40;
    const height = opts.height || 320;
    const { scrollEl, innerEl, btnsEl } = ensureChartScrollWrap(canvas, height);
    const containerWidth = scrollEl.clientWidth;
    const needed = (labelCount || 0) * pxPerPoint + edgePadding * 2;
    if (needed > containerWidth) {
        innerEl.style.minWidth = needed + 'px';
        btnsEl.style.display = '';
    } else {
        innerEl.style.minWidth = '100%';
        btnsEl.style.display = 'none';
        scrollEl.scrollLeft = 0;
    }
    if (!btnsEl.dataset.wired) {
        const step = () => Math.max(160, scrollEl.clientWidth * 0.7);
        btnsEl.querySelectorAll('[data-dir]').forEach(btn => {
            btn.addEventListener('click', () => {
                const dir = parseInt(btn.dataset.dir, 10);
                scrollEl.scrollBy({ left: dir * step(), behavior: 'smooth' });
            });
        });
        btnsEl.dataset.wired = '1';
    }
}

// Wraps `canvas` the first time it's called; on subsequent calls returns the
// existing refs. The arrow buttons live in a wrapper outside the scrolling
// area so they stay pinned to the visible top-right corner (they would scroll
// out of view if placed inside the overflow-x:auto container).
//
//   host
//   └─ chart-scroll-wrap (position:relative)        ← arrows positioned to this
//      ├─ chart-scroll-outer (overflow-x:auto)      ← horizontal scrollbar
//      │  └─ chart-scroll-inner (min-width: …)      ← widens with data
//      │     └─ canvas
//      └─ chart-scroll-arrows (position:absolute)   ← stays in viewport
function ensureChartScrollWrap(canvas, height) {
    if (canvas.parentNode.classList.contains('chart-scroll-inner')) {
        const innerEl = canvas.parentNode;
        const scrollEl = innerEl.parentNode;
        const wrapEl = scrollEl.parentNode;
        return { scrollEl, innerEl, btnsEl: wrapEl.querySelector('.chart-scroll-arrows') };
    }
    const host = canvas.parentNode;
    const wrapEl = document.createElement('div');
    wrapEl.className = 'chart-scroll-wrap';
    wrapEl.style.cssText = 'position:relative;';
    const scrollEl = document.createElement('div');
    scrollEl.className = 'chart-scroll-outer';
    scrollEl.style.cssText = `overflow-x:auto; overflow-y:hidden; height:${height}px;`;
    const innerEl = document.createElement('div');
    innerEl.className = 'chart-scroll-inner';
    innerEl.style.cssText = 'position:relative; height:100%; min-width:100%;';
    const btnsEl = document.createElement('div');
    btnsEl.className = 'btn-group btn-group-sm chart-scroll-arrows';
    btnsEl.style.cssText = 'position:absolute; top:6px; right:6px; z-index:5; display:none;';
    btnsEl.innerHTML = `
        <button type="button" class="btn btn-outline-secondary" data-dir="-1" title="Pomakni lijevo"><i class="bi bi-chevron-left"></i></button>
        <button type="button" class="btn btn-outline-secondary" data-dir="1" title="Pomakni desno"><i class="bi bi-chevron-right"></i></button>`;
    host.insertBefore(wrapEl, canvas);
    wrapEl.appendChild(scrollEl);
    scrollEl.appendChild(innerEl);
    innerEl.appendChild(canvas);
    wrapEl.appendChild(btnsEl);
    return { scrollEl, innerEl, btnsEl };
}
