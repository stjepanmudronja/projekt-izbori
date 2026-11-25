"""Build the PNG icons and the link-preview image from HTML/SVG.

    python tools/build_social_images.py

Writes static/favicon-32.png, static/apple-touch-icon.png (180×180) and
static/og-image.png (1200×630, what Facebook, WhatsApp, Slack… show for a
shared link; they do not read SVG). Rendered by Playwright with the installed
Chrome (requirements-dev.txt), so nothing new is needed. The images are
committed; re-run only after changing static/favicon.svg or the card below.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

STATIC = Path(__file__).resolve().parent.parent / 'static'
FAVICON = (STATIC / 'favicon.svg').read_text()

# The link preview: the site's sidebar colours, its icon, name and what it holds.
# Stays general on purpose (no figures), so it never goes stale.
OG_HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
  html, body {{ margin: 0; width: 1200px; height: 630px; }}
  body {{ font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #fff;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
          position: relative; overflow: hidden; }}
  .wrap {{ position: absolute; left: 84px; top: 92px; right: 84px; }}
  .brand {{ display: flex; align-items: center; gap: 28px; }}
  .brand svg {{ width: 112px; height: 112px; }}
  h1 {{ font-size: 88px; margin: 0; letter-spacing: -1.5px; font-weight: 800; }}
  .sub {{ font-size: 38px; margin: 34px 0 0; color: #d0d7e2; font-weight: 500; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 14px; margin-top: 46px; max-width: 760px; }}
  .chip {{ font-size: 25px; padding: 10px 20px; border-radius: 999px; background: rgba(255,255,255,.12);
           border: 1px solid rgba(255,255,255,.18); }}
  .bars {{ position: absolute; right: 70px; bottom: 0; display: flex; align-items: flex-end; gap: 22px; opacity: .9; }}
  .bars div {{ width: 54px; border-radius: 10px 10px 0 0; background: rgba(255,255,255,.16); }}
  .bars div.hi {{ background: #e03131; }}
  .foot {{ position: absolute; left: 84px; bottom: 52px; font-size: 24px; color: #9fb0c8; }}
</style></head><body>
  <div class="bars"><div style="height:150px"></div><div style="height:250px"></div><div style="height:200px"></div><div class="hi" style="height:320px"></div></div>
  <div class="wrap">
    <div class="brand">{FAVICON}<h1>Projekt Izbori</h1></div>
    <p class="sub">Hrvatski izborni podaci od 1990. do danas</p>
    <div class="chips">
      <span class="chip">Predsjednički</span><span class="chip">Sabor</span><span class="chip">Europski parlament</span>
      <span class="chip">Lokalni</span><span class="chip">Političari</span><span class="chip">Stranke</span>
      <span class="chip">Izlaznost</span><span class="chip">Simulacije</span>
    </div>
  </div>
  <div class="foot">Rezultati po županijama, gradovima i biračkim mjestima</div>
</body></html>"""


def icon_html(size):
    return (f'<!doctype html><html><head><style>html,body{{margin:0;background:transparent}}'
            f'svg{{width:{size}px;height:{size}px;display:block}}</style></head><body>{FAVICON}</body></html>')


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome')
        for name, size in (('favicon-32.png', 32), ('apple-touch-icon.png', 180)):
            page = browser.new_page(viewport={'width': size, 'height': size})
            page.set_content(icon_html(size))
            page.screenshot(path=str(STATIC / name), omit_background=True)
            page.close()
        page = browser.new_page(viewport={'width': 1200, 'height': 630})
        page.set_content(OG_HTML)
        page.screenshot(path=str(STATIC / 'og-image.png'))
        browser.close()
    for name in ('favicon-32.png', 'apple-touch-icon.png', 'og-image.png'):
        print(name, (STATIC / name).stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
