"""Page titles, descriptions and link previews.

Every page is the same SPA shell, so the server fills in the <title>, the
description and the Open Graph / Twitter tags from the URL: a crawler that
reads a shared link (Facebook, WhatsApp, Slack…) runs no script and sees only
these. Deep links name the politician, town or party. The SPA keeps
document.title in step as you move around (core.js, updateDocTitle).
"""
from webapp.core import db

SITE = 'Projekt Izbori'
SITE_DESC = ('Hrvatski izborni podaci od 1990.: rezultati svih izbora po županijama, gradovima '
             'i biračkim mjestima, političari, stranke, izlaznost i simulacije Sabora.')

# slug -> (title, description). Keep the titles in step with moduleTitles in core.js.
PAGE_META = {
    '': (SITE, SITE_DESC),
    'politicar': ('Političari', 'Svi kandidati na hrvatskim izborima od 1990.: kandidature, rezultati, osvojene dužnosti i usporedba političara na istom grafu.'),
    'prema-lokaciji': ('Prema lokaciji', 'Rezultati svih izbora za jednu županiju, grad, općinu, biračko mjesto ili ulicu, s pobjednicima kroz vrijeme.'),
    'mjesto': ('Općine i gradovi', 'Izborna povijest grada ili općine: načelnici i gradonačelnici redom, vodeće liste u vijeću, izlaznost i pobjednici na svim izborima.'),
    'usporedba': ('Usporedi biračka mjesta', 'Usporedi do tri biračka mjesta jedno uz drugo na svim izborima.'),
    'stranke': ('Stranke', 'Registar političkih stranaka Republike Hrvatske povezan s izbornim listama: podaci iz registra i rezultati svake stranke.'),
    'predsjednicki-izbori': ('Predsjednički izbori', 'Rezultati predsjedničkih izbora od 1992. po županijama, gradovima i biračkim mjestima, uz simulaciju drugog kruga.'),
    'eu-parlamentarni-izbori': ('EU parlamentarni izbori', 'Izbori za Europski parlament 2013.–2024.: glasovi lista, raspodjela mandata i preferencijski glasovi kandidata.'),
    'lokalni-izbori': ('Lokalni izbori', 'Lokalni izbori od 1993.: vijeća, županijske skupštine, načelnici, gradonačelnici i župani, s drugim krugovima.'),
    'rezultati-koalicije-sabor': ('Sabor: rezultati i koalicije', 'Izbori za Hrvatski sabor od 1990.: raspodjela mandata, složi svoju koaliciju, napravi svoju predikciju i "Što ako?" s drugim izbornim pravilima.'),
    'zupanijski-dom': ('Županijski dom', 'Izbori za Županijski dom Hrvatskog sabora.'),
    'izlaznost': ('Izlaznost', 'Izlaznost birača na svim izborima od 1990., za cijelu Hrvatsku, županiju, grad ili biračko mjesto.'),
    'karta': ('Karta općina', 'Karta svih hrvatskih općina i gradova: pobjednici, izlaznost i snaga stranaka na svakim izborima.'),
    'snaga-stranaka': ('Snaga stranaka kroz vrijeme', 'Udio glasova svake stranke na izborima za Sabor, Europski parlament, vijeća i skupštine kroz godine.'),
    'zene-u-politici': ('Žene u politici', 'Koliko je žena među kandidatima i izabranima na hrvatskim izborima: Sabor, Europski parlament, predsjednik, gradonačelnici i župani, po godinama i strankama.'),
    'ponovni-izbor': ('Ponovni izbor', 'Dobivaju li načelnici, gradonačelnici i župani ponovno izbore? Svi lokalni izbori od 2009.: tko je ponovno izabran, tko je izgubio i tko je na dužnosti od 2009.'),
    'prelasci': ('Prelasci između stranaka', 'Političari koji su na izborima za Sabor i Europski parlament nastupili za jednu stranku, a zatim za drugu: tko je prešao, iz koje stranke u koju i kada.'),
}

_SMALL = {'i', 'u', 'na', 'za', 'od', 'do', 's', 'sa', 'iz', 'po', 'pri', 'de', 'di', 'la', 'del'}


def name_case(s):
    """'ZORAN MILANOVIĆ' -> 'Zoran Milanović', 'DUGO SELO' -> 'Dugo Selo',
    'ANA-MARIJA' -> 'Ana-Marija'; small words stay lower inside a name."""
    words = []
    for i, w in enumerate((s or '').split()):
        lw = w.lower()
        words.append(lw if i and lw in _SMALL else '-'.join(p[:1].upper() + p[1:] for p in lw.split('-')))
    return ' '.join(words)


def party_case(s):
    """Register names are in capitals: 'HRVATSKA DEMOKRATSKA ZAJEDNICA' ->
    'Hrvatska demokratska zajednica'; Hrvatska / Republika keep their capital."""
    out = []
    for i, w in enumerate((s or '').lower().split()):
        if i == 0 or w.startswith(('hrvatsk', 'republik', 'europ', 'zagreb', 'dalmacij', 'istr', 'slavonij')):
            w = w[:1].upper() + w[1:]
        out.append(w)
    return ' '.join(out)


def _lead_id(seg):
    num = ''
    for ch in seg:
        if not ch.isdigit():
            break
        num += ch
    return int(num) if num else None


def _person_meta(segments):
    ids = [i for i in (_lead_id(s) for s in segments) if i][:4]
    if not ids:
        return None
    rows = dict((r[0], r[1:]) for r in db.session.execute(db.text(
        'select id, first_name, last_name from elections_person where id = any(:ids)'), {'ids': ids}))
    names = [name_case(f'{rows[i][0]} {rows[i][1]}') for i in ids if i in rows]
    if not names:
        return None
    if len(names) == 1:
        return (names[0], f'{names[0]}: sve kandidature na hrvatskim izborima, rezultati, udio glasova kroz vrijeme '
                          'i osvojene dužnosti.')
    joined = ', '.join(names[:-1]) + ' i ' + names[-1]
    return (joined, f'Usporedba političara: {joined}. Kandidature, rezultati i udio glasova na istom grafu.')


def _place_meta(segments):
    pid = _lead_id(segments[0]) if segments else None
    row = pid and db.session.execute(db.text(
        'select m.name, m.type, c.name from elections_municipality m '
        'left join elections_county c on c.id = m.county_id where m.id = :id'), {'id': pid}).first()
    if not row:
        return None
    name = name_case(row[0])
    kind = 'Grad' if row[1] == 'grad' else 'Općina'
    county = f', {party_case(row[2])}' if row[2] else ''
    head = 'gradonačelnici' if row[1] == 'grad' else 'načelnici'
    return (name, f'{kind} {name}{county}: izborna povijest, {head} redom, vodeće liste u vijeću, '
                  'izlaznost i pobjednici na svim izborima od 1990.')


def _party_meta(segments):
    n = _lead_id(segments[0]) if segments else None
    row = n and db.session.execute(db.text(
        'select name, short_name from elections_registeredparty where registry_number = :n'), {'n': n}).first()
    if not row:
        return None
    full = party_case(row[0])
    title = f'{full} ({row[1]})' if row[1] else full
    return (title, f'{title}: podaci iz Registra političkih stranaka i rezultati lista koje je stranka '
                   'predvodila ili u kojima je nastupila, na svim izborima.')


def page_meta(path):
    """{'title', 'description'} for a site path ('/mjesto/439-klis')."""
    parts = [p for p in (path or '/').split('/') if p]
    found = None
    try:
        if len(parts) > 1 and parts[0] == 'politicar':
            found = _person_meta(parts[1:])
        elif len(parts) > 1 and parts[0] == 'mjesto':
            found = _place_meta(parts[1:])
        elif len(parts) > 1 and parts[0] == 'stranke':
            found = _party_meta(parts[1:])
    except Exception:          # a bad id must still render the page
        db.session.rollback()
    if not found:
        found = PAGE_META.get(parts[0] if parts else '', PAGE_META[''])
    title, desc = found
    return {'title': title if title == SITE else f'{title} · {SITE}', 'description': desc, 'name': title}
