"""The 1993 Županijski dom election, transcribed from the DIP report.

Source: `files/rezultati_sabor/1993/1993_2_Rezultati_Sabor_zupanijski_dom.pdf`
— the bundle of Izborna komisija RH decisions declaring the result county by
county, Klasa 013-91/92-01/08, Urbroj 56605/93-317-1…21, Zagreb, February 1993.

This was the **first** election to the upper house, held **7 February 1993**.
Four counties (II Krapinsko-zagorska, III Sisačko-moslavačka, XIII
Zadarsko-kninska, XVIII Istarska) carry the later date 21 February and cite
"izbori provedeni dana 21. veljače" — repeat voting at stations where the first
round was annulled — so their decisions are dated 24 February rather than 11.

Like the 1997 report this PDF is a **pure scan**: 44 pages, each a single CCITT
Group 4 image with no text layer. Pages were rendered with
`tools/extract_scanned_pdf.py` and transcribed by hand, which is why the data
lives here as a literal. Layout is two pages per county — section I/II (turnout
and the county lists) then section III (seats and members) — except Primorsko-
goranska, Splitsko-dalmatinska and Grad Zagreb, whose list tables spill onto
the second page above the members.

**County names are the 1993 ones, and two no longer exist**: XIII is
*Zadarsko-kninska* (split in 1997 into Zadarska and Šibensko-kninska) and XV is
*Šibenska*. `code` is still the document's own Roman numeral as a 2-char
string, which lines up with today's county codes everywhere else.

Checked on every county: the list votes sum to `valid_total`, `valid_total +
invalid == voted`, and each county returns its 3 seats with 3 named members —
63 in all. Nationally that is 3,580,396 registered, 2,303,782 voted (64.34%),
2,227,763 valid and 76,019 invalid.

Seats **per list**, grouped by the list's first-named party: HDZ 37, HSLS 18,
HSS 5, IDS 3.

**Cross-checked against the published national table, and every row matches to
the vote** — HDZ 1,013,365 (45.5%), HSLS 486,210, HSS 258,953, IDS 76,273,
HSLS-HNS 45,657, SDP 41,955, HSLS-HNS-SDP 35,937, HSLS-HNS-HKDU-SDP 33,246,
HKDU 27,584, Dalmatinska akcija 26,303, RiDS-IDS 22,801, neovisne županijske
liste 22,562, HSLS-SDP 21,478, SDP-SSH 18,312, SDU 17,413, HNS 15,363 — on
2,227,763 valid of 2,303,782 cast. The published "ostale stranke i koalicije"
residual of **64,351** falls out exactly as the remainder over some twenty
small lists, which is the tightest check in the table. Three notes on it:

  * The HSLS-HNS-SDP figure is the sum of **two orderings** the report prints
    differently — Krapinsko-zagorska writes HSLS, HNS, SDP (16,957) and
    Koprivničko-križevačka HSLS, SDP, HNS (18,980). They are one ticket; the
    list names here preserve each county's own order, so the two are separate
    keys in this file and only merge when grouped by party set.
  * The published table labels the 18,312-vote ticket **"SDP-HSS"**. It is
    not: the report names Socijalistička stranka Hrvatske - **SSH** on both
    counties that ran it (Zadarsko-kninska and Splitsko-dalmatinska). Same
    number, wrong partner.
  * **Seats are counted differently there**, the same way they are for 1997:
    HDZ 37, HSLS 16, HSS 5, IDS 3, SDS 1, HNS 1 = 63, which is seats by each
    member's *own* party. The two that move out of HSLS's 18 are Zdravko Tomac
    — SDP, and the nositelj of the HSLS-SDP ticket that elected him in
    Brodsko-posavska — and one HNS member elected on an HSLS-HNS ticket. The
    report records no personal affiliations, so which of the six members
    elected on HSLS-HNS tickets that is cannot be told from this source, and
    only the per-list figure is derivable here.

The President could appoint **up to** five further members (the 1990
Constitution's cap), for a 68-seat house. The report covers the election only
and names none of them.
"""

COUNTIES = [
 {'code': '01', 'name': 'Zagrebačka županija',
  'registered': 129913, 'voted': 101758, 'invalid': 3469, 'valid_total': 98289,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 47280, 'pct': 48.10},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 29009, 'pct': 29.51},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 18697, 'pct': 19.02},
    {'n': 4, 'parties': ['Hrvatska stranka naravnog zakona'],
     'holder': 'Drago Antoniazzo', 'votes': 366, 'pct': 0.37},
    {'n': 5, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Dr. Milivoj Kramarić', 'votes': 2174, 'pct': 2.21},
    {'n': 6, 'parties': ['Socijalno-demokratska unija Hrvatske - SDU'],
     'holder': 'Dr. Branko Horvat', 'votes': 763, 'pct': 0.78}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Ivan Lacković', 'deputy': 'Ivan Penić'},
      {'name': 'Tomislav Ivčić', 'deputy': 'dipl.vet. Zvonimir Teklić'}]},
    {'list': 'Hrvatska seljačka stranka - HSS', 'n': 1, 'elected': [
      {'name': 'Ivan Tretinjak', 'deputy': 'Ančica Šipuljak'}]}]},
 {'code': '02', 'name': 'Krapinsko-zagorska županija',
  'registered': 116256, 'voted': 80525, 'invalid': 2977, 'valid_total': 77548,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 45385, 'pct': 58.53},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 15206, 'pct': 19.61},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS',
                         'Hrvatska narodna stranka - HNS',
                         'Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Dražen Budiša', 'votes': 16957, 'pct': 21.87}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'dr. Ivan Valent', 'deputy': 'Josip Horjan'},
      {'name': 'Branko Horvat', 'deputy': 'Vidislav Kiš'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS, Hrvatska narodna stranka - HNS i '
             'Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP',
     'n': 1, 'elected': [
      {'name': 'dr. Stanko Belina', 'deputy': 'dr. Ivan Šimatović'}]}]},
 {'code': '03', 'name': 'Sisačko-moslavačka županija',
  'registered': 205189, 'voted': 104405, 'invalid': 3422, 'valid_total': 100983,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 55883, 'pct': 55.34},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Stjepan Marić', 'votes': 13406, 'pct': 13.28},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 30342, 'pct': 30.05},
    {'n': 4, 'parties': ['Hrvatska stranka naravnog zakona'],
     'holder': 'Edgar Horvat', 'votes': 1352, 'pct': 1.34}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Josip Brajković', 'deputy': 'prof.dr. Ilija Škrinjarić'},
      {'name': 'Božidar Pugelnik', 'deputy': 'Antonio Matoc'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Krunoslav Orešković', 'deputy': 'Zorko Kostanjšek'}]}]},
 {'code': '04', 'name': 'Karlovačka županija',
  'registered': 130210, 'voted': 72749, 'invalid': 2313, 'valid_total': 70436,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 42562, 'pct': 60.43},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Željko Sučec', 'votes': 4717, 'pct': 6.70},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS',
                         'Hrvatska narodna stranka - HNS'],
     'holder': 'Dražen Budiša', 'votes': 19401, 'pct': 27.54},
    {'n': 4, 'parties': ['Socijalno-demokratska unija Hrvatske - SDU'],
     'holder': 'Dr. Branko Horvat', 'votes': 3756, 'pct': 5.33}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Ante Jozo Ramić', 'deputy': 'Ivan Benić'},
      {'name': 'Ivan Novosel', 'deputy': 'Marijan Srdarev'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS, Hrvatska narodna stranka - HNS',
     'n': 1, 'elected': [
      {'name': 'Prof. dr. Mirko Butković', 'deputy': 'Dražen Cukina'}]}]},
 {'code': '05', 'name': 'Varaždinska županija',
  'registered': 144529, 'voted': 102917, 'invalid': 3623, 'valid_total': 99294,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 39013, 'pct': 39.29},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Stjepan Rodeš', 'votes': 25955, 'pct': 26.14},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS',
                         'Hrvatska narodna stranka - HNS',
                         'Hrvatska kršćanska demokratska unija - HKDU',
                         'Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Dražen Budiša', 'votes': 33246, 'pct': 33.48},
    {'n': 4, 'parties': ['Hrvatska stranka naravnog zakona'],
     'holder': 'Inga Poje', 'votes': 1080, 'pct': 1.09}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 1, 'elected': [
      {'name': 'Marijan Mlinarić', 'deputy': 'Ratimir Čavlović'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS, Hrvatska narodna stranka - HNS, '
             'Hrvatska kršćanska demokratska unija - HKDU, Socijaldemokratska partija Hrvatske - '
             'Stranka demokratskih promjena - SDP', 'n': 1, 'elected': [
      {'name': 'Marko Lapaine', 'deputy': 'Hrvoj Vančik, dr.'}]},
    {'list': 'Hrvatska seljačka stranka - HSS', 'n': 1, 'elected': [
      {'name': 'Stjepan Rodeš', 'deputy': 'Franjo Turek'}]}]},
 {'code': '06', 'name': 'Koprivničko-križevačka županija',
  'registered': 100425, 'voted': 74063, 'invalid': 2474, 'valid_total': 71589,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 28324, 'pct': 39.56},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska stranka - HKDS'],
     'holder': 'Dr. Vinko Pavlović', 'votes': 1632, 'pct': 2.28},
    {'n': 3, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 22653, 'pct': 31.64},
    {'n': 4, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS',
                         'Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP',
                         'Hrvatska narodna stranka - HNS'],
     'holder': 'Dražen Budiša', 'votes': 18980, 'pct': 26.51}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 1, 'elected': [
      {'name': 'Zlatan Sremec', 'deputy': 'Ivan Mikulić'}]},
    {'list': 'Hrvatska seljačka stranka - HSS', 'n': 1, 'elected': [
      {'name': 'Dr. Valentin Puževski', 'deputy': 'Ivan Vuk'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS, Socijaldemokratska partija Hrvatske - '
             'Stranka demokratskih promjena - SDP, Hrvatska narodna stranka - HNS',
     'n': 1, 'elected': [
      {'name': 'Mladen Godek', 'deputy': 'Ana Ivančević'}]}]},
 {'code': '07', 'name': 'Bjelovarsko-bilogorska županija',
  'registered': 99828, 'voted': 80057, 'invalid': 3171, 'valid_total': 76886,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 33873, 'pct': 44.06},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Josip Balja, dipl. vet.', 'votes': 2407, 'pct': 3.13},
    {'n': 3, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 20422, 'pct': 26.56},
    {'n': 4, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 20184, 'pct': 26.25}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 1, 'elected': [
      {'name': 'Đuro Panjan', 'deputy': 'Zvonimir Novoselec'}]},
    {'list': 'Hrvatska seljačka stranka - HSS', 'n': 1, 'elected': [
      {'name': 'Petar Jurušić', 'deputy': 'Elizabeta Maretić'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Mr. Damir Zorić', 'deputy': 'prof. Goran Jakovljević'}]}]},
 {'code': '08', 'name': 'Primorsko-goranska županija',
  'registered': 261158, 'voted': 174335, 'invalid': 5596, 'valid_total': 168739,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 59735, 'pct': 35.40},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Zvonimir Sablić, dipl. oecc.', 'votes': 3856, 'pct': 2.29},
    {'n': 3, 'parties': ['Hrvatska narodna stranka - HNS'],
     'holder': 'Franjo Starčević, prof.', 'votes': 4037, 'pct': 2.39},
    {'n': 4, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Prof.dr. Juraj Plenković', 'votes': 3967, 'pct': 2.35},
    {'n': 5, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 49209, 'pct': 29.16},
    {'n': 6, 'parties': ['Riječki demokratski savez - RiDS',
                         'Istarski demokratski sabor - IDS'],
     'holder': 'Dr. Bernardo Di Lenardo-Zamlić', 'votes': 22801, 'pct': 13.51},
    {'n': 7, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Slavko Linić, dipl. oecc.', 'votes': 20700, 'pct': 12.27},
    {'n': 8, 'parties': ['Socijalno-demokratska unija Hrvatske - SDU'],
     'holder': 'Dr. Branko Horvat', 'votes': 1921, 'pct': 1.14},
    {'n': 9, 'parties': ['Srpska narodna stranka'],
     'holder': 'Borislav Arsenijević', 'votes': 2513, 'pct': 1.49}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Prof. dr. Katica Ivanišević', 'deputy': 'doc.dr. Žarko Tomljanović'},
      {'name': 'Antun Rački', 'deputy': 'Marija Maja Stipančić'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Dr. Marko Ivanović', 'deputy': 'Ivan Blažina'}]}]},
 {'code': '09', 'name': 'Ličko-senjska županija',
  'registered': 47761, 'voted': 31302, 'invalid': 1124, 'valid_total': 30178,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 22541, 'pct': 74.69},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Pajo Šimić', 'votes': 1952, 'pct': 6.47},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 5685, 'pct': 18.84}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 3, 'elected': [
      {'name': 'Dražen Bobinac', 'deputy': 'Blaženka Častek'},
      {'name': 'Robert Peranić', 'deputy': 'Miran Ivanišević'},
      {'name': 'Josip Vukelić - Piki', 'deputy': 'Milan Galić'}]}]},
 {'code': '10', 'name': 'Virovitičko-podravska županija',
  'registered': 70945, 'voted': 57283, 'invalid': 2642, 'valid_total': 54641,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 26965, 'pct': 49.35},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 15076, 'pct': 27.59},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Martin Špegelj', 'votes': 12600, 'pct': 23.06}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Dragutin Dečak', 'deputy': 'Petar Budiša'},
      {'name': 'Jozo Medved', 'deputy': 'Karlo Crnčić'}]},
    {'list': 'Hrvatska seljačka stranka - HSS', 'n': 1, 'elected': [
      {'name': 'Josip Dent', 'deputy': 'Josip Hrala'}]}]},
 {'code': '11', 'name': 'Požeško-slavonska županija',
  'registered': 86946, 'voted': 66131, 'invalid': 2102, 'valid_total': 64029,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 34921, 'pct': 54.54},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Dr. Anto Kovačević', 'votes': 4188, 'pct': 6.54},
    {'n': 3, 'parties': ['Hrvatska narodna stranka - HNS'],
     'holder': 'Mr. Antun Lovrić', 'votes': 2241, 'pct': 3.50},
    {'n': 4, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Mr.dr. Josip Fajdić', 'votes': 5504, 'pct': 8.60},
    {'n': 5, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 15712, 'pct': 24.54},
    {'n': 6, 'parties': ['Srpska narodna stranka'],
     'holder': 'Stevo Došen', 'votes': 1463, 'pct': 2.28}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Mario Včelik, dipl. pravnik', 'deputy': 'Željko Glavić'},
      {'name': 'Vladimir Delač, ing.', 'deputy': 'Franjo Širac'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Milan Markanjević', 'deputy': 'Ivan Grbić'}]}]},
 {'code': '12', 'name': 'Brodsko-posavska županija',
  'registered': 120804, 'voted': 83876, 'invalid': 3322, 'valid_total': 80554,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 40865, 'pct': 50.73},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska stranka - HKDS',
                         'Hrvatska narodna stranka - HNS'],
     'holder': 'Dr. Davorin Đanić', 'votes': 2895, 'pct': 3.59},
    {'n': 3, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Anđelko Gabrić, dipl. ing. polj.', 'votes': 6970, 'pct': 8.65},
    {'n': 4, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS',
                         'Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Dr. Zdravko Tomac', 'votes': 21478, 'pct': 26.66},
    {'n': 5, 'parties': ['Nezavisna županijska lista'],
     'holder': 'Ivan Schumacher', 'votes': 8346, 'pct': 10.36}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Akademik Stjepan Babić', 'deputy': 'prof. Ante Lasić'},
      {'name': 'Dragica Vidmar', 'deputy': 'Marko Maričević'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS, Socijaldemokratska partija Hrvatske - '
             'Stranka demokratskih promjena - SDP', 'n': 1, 'elected': [
      {'name': 'Dr. Zdravko Tomac', 'deputy': 'Tomislav Ninčević'}]}]},
 {'code': '13', 'name': 'Zadarsko-kninska županija',
  'registered': 197369, 'voted': 61716, 'invalid': 1912, 'valid_total': 59804,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 36850, 'pct': 61.62},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Prof.dr. Pavao Živković', 'votes': 791, 'pct': 1.32},
    {'n': 3, 'parties': ['Hrvatska narodna stranka - HNS'],
     'holder': 'Stanislav Antić', 'votes': 4552, 'pct': 7.61},
    {'n': 4, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 14050, 'pct': 23.49},
    {'n': 5, 'parties': ['Nezavisna županijska lista'],
     'holder': 'Prim.dr. Božo Zdrilić', 'votes': 1443, 'pct': 2.41},
    {'n': 6, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP',
                         'Socijalistička stranka Hrvatske - SSH'],
     'holder': 'Josip Sviličić', 'votes': 1829, 'pct': 3.06},
    {'n': 7, 'parties': ['Stranka demokratske akcije - ogranak za Hrvatsku'],
     'holder': 'Šefik Nadarević', 'votes': 289, 'pct': 0.48}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Julije Derossi', 'deputy': 'Pavao Račić'},
      {'name': 'Davor Aras', 'deputy': 'Živko Kolega'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'dr. Tereza Ganza-Aras', 'deputy': 'doc.dr.sc. Zlatko Matulić'}]}]},
 {'code': '14', 'name': 'Osječko-baranjska županija',
  'registered': 256075, 'voted': 140604, 'invalid': 4613, 'valid_total': 135991,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 69897, 'pct': 51.40},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Josip Franc, dipl.ing.građ.', 'votes': 2081, 'pct': 1.53},
    {'n': 3, 'parties': ['Hrvatska narodna stranka - HNS'],
     'holder': 'Ivan Vrkić, prof.filozofije i dipl.pravnik', 'votes': 4533, 'pct': 3.33},
    {'n': 4, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Dr. Damir Klasiček', 'votes': 7756, 'pct': 5.70},
    {'n': 5, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 48157, 'pct': 35.41},
    {'n': 6, 'parties': ['Srpska narodna stranka'],
     'holder': 'Branislav Vorkapić', 'votes': 2880, 'pct': 2.12},
    {'n': 7, 'parties': ['Stranka srednjoeuropske akcije - SEA'],
     'holder': 'Damir Milić, prof.', 'votes': 687, 'pct': 0.51}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Branimir Glavaš', 'deputy': 'Ivo Markotić'},
      {'name': 'Stjepan Čamagajevac', 'deputy': 'Mate Zorić'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Ivica Šutalo', 'deputy': 'Zdenko Mužević'}]}]},
 {'code': '15', 'name': 'Šibenska županija',
  'registered': 79954, 'voted': 47082, 'invalid': 1970, 'valid_total': 45112,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 23727, 'pct': 52.60},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska stranka - HKDS',
                         'Hrvatska demokratska stranka - HDS',
                         'Kršćanska narodna stranka - KNS'],
     'holder': 'Dr. Antun Carić', 'votes': 1414, 'pct': 3.13},
    {'n': 3, 'parties': ['Hrvatska narodna stranka - HNS',
                         'Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Dr. Ante Romac', 'votes': 4660, 'pct': 10.33},
    {'n': 4, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Drago Stipac', 'votes': 1716, 'pct': 3.80},
    {'n': 5, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 13595, 'pct': 30.14}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Jadranko Markov', 'deputy': 'Duje Stančić'},
      {'name': 'Ante Đelalija', 'deputy': 'dr. Vladimir Lučev'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Dr. Mate Meštrović', 'deputy': 'Ivo Glavaš'}]}]},
 {'code': '16', 'name': 'Vukovarsko-srijemska županija',
  'registered': 110743, 'voted': 67021, 'invalid': 2129, 'valid_total': 64892,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 40585, 'pct': 62.54},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 6519, 'pct': 10.05},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 16514, 'pct': 25.45},
    {'n': 4, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Petar Bošnjaković', 'votes': 1274, 'pct': 1.96}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Tomislav Merčep', 'deputy': 'Martin Sablić'},
      {'name': 'Tihomir Zovak', 'deputy': 'Ante Gilja'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Željko Štanfel, dr. med.', 'deputy': 'Željko Rapčan'}]}]},
 {'code': '17', 'name': 'Splitsko-dalmatinska županija',
  'registered': 360752, 'voted': 225806, 'invalid': 8294, 'valid_total': 217512,
  'lists': [
    {'n': 1, 'parties': ['Dalmatinska akcija'],
     'holder': 'Dr. Mira Ljubić-Lorger', 'votes': 22175, 'pct': 10.19},
    {'n': 2, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 96062, 'pct': 44.16},
    {'n': 3, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU',
                         'Hrvatska republikanska zajednica - HRZ',
                         'Kršćanska narodna stranka - KNS'],
     'holder': 'Arsen Mužić', 'votes': 4220, 'pct': 1.94},
    {'n': 4, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Dipl.ing. Joško Kovač', 'votes': 13954, 'pct': 6.42},
    {'n': 5, 'parties': ['Hrvatska stranka'],
     'holder': 'Frano Čačija', 'votes': 1409, 'pct': 0.65},
    {'n': 6, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 62090, 'pct': 28.55},
    {'n': 7, 'parties': ['Hrvatska stranka naravnog zakona'],
     'holder': 'Dragutin Kopić', 'votes': 1119, 'pct': 0.51},
    {'n': 8, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP',
                         'Socijalistička stranka Hrvatske - SSH'],
     'holder': 'Prof. Vinko Bajrović', 'votes': 16483, 'pct': 7.58}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Dipl. oecc. Nadan Vidošević', 'deputy': 'dipl.ing. Zvonimir Puljić'},
      {'name': 'Marijan Milinović', 'deputy': 'Ante Delić'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Prof. Ivica Škarić', 'deputy': 'Tihomir Rađa'}]}]},
 {'code': '18', 'name': 'Istarska županija',
  'registered': 159502, 'voted': 118823, 'invalid': 3980, 'valid_total': 114843,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 18782, 'pct': 16.35},
    {'n': 2, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Dr. Ivan Prodan', 'votes': 1396, 'pct': 1.22},
    {'n': 3, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 11658, 'pct': 10.15},
    {'n': 4, 'parties': ['Hrvatska stranka naravnog zakona'],
     'holder': 'Mr. Josip-Anton Rupnik', 'votes': 554, 'pct': 0.48},
    {'n': 5, 'parties': ['Istarski demokratski sabor - IDS'],
     'holder': 'Ivan Jakovčić', 'votes': 76273, 'pct': 66.42},
    {'n': 6, 'parties': ['Istarska liberalna stranka'],
     'holder': 'Boris Rotar, prof.', 'votes': 2296, 'pct': 2.00},
    {'n': 7, 'parties': ['Istarska pučka stranka', 'Istarska nezavisna stranka',
                         'Kršćanska narodna stranka - KNS'],
     'holder': 'Dipl.ing. Nevio Milotić', 'votes': 1690, 'pct': 1.47},
    {'n': 8, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP',
                         'Socijalistička stranka Hrvatske - SSH',
                         'Socijaldemokratska stranka Hrvatske - SDH'],
     'holder': 'Dario Forza', 'votes': 2194, 'pct': 1.91}],
  'seats': [
    {'list': 'Istarski demokratski sabor - IDS', 'n': 3, 'elected': [
      {'name': 'Branko Ružić', 'deputy': 'Bruno Poropat'},
      {'name': 'Denis Jelenković', 'deputy': 'Marino Folo'},
      {'name': 'Ivan Pauletta', 'deputy': 'Emil Soldatić'}]}]},
 {'code': '19', 'name': 'Dubrovačko-neretvanska županija',
  'registered': 96387, 'voted': 64423, 'invalid': 2307, 'valid_total': 62116,
  'lists': [
    {'n': 1, 'parties': ['Dalmatinska akcija'],
     'holder': 'Dr. Mira Ljubić-Lorger', 'votes': 4128, 'pct': 6.65},
    {'n': 2, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 28585, 'pct': 46.02},
    {'n': 3, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU',
                         'Hrvatska kršćanska demokratska stranka - HKDS',
                         'Hrvatska demokratska stranka - HDS'],
     'holder': 'Ivo Jelić, dipl.ing.', 'votes': 3511, 'pct': 5.65},
    {'n': 4, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Joško Kovač', 'votes': 3565, 'pct': 5.74},
    {'n': 5, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 15913, 'pct': 25.62},
    {'n': 6, 'parties': ['Nezavisna županijska lista'],
     'holder': 'Dr. Niko Visković', 'votes': 2207, 'pct': 3.55},
    {'n': 7, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Marko Vlašić Čiče', 'votes': 4207, 'pct': 6.77}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Mato-Matko Medo', 'deputy': 'dr. Petar Čumbelić'},
      {'name': 'Dr. Petar Đukan', 'deputy': 'Miho Valjalo'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Dr. Boris Franušić', 'deputy': 'mr. Luko Milić'}]}]},
 {'code': '20', 'name': 'Međimurska županija',
  'registered': 89878, 'voted': 64590, 'invalid': 2321, 'valid_total': 62269,
  'lists': [
    {'n': 1, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 20591, 'pct': 33.07},
    {'n': 2, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Ivan Radek', 'votes': 1956, 'pct': 3.14},
    {'n': 3, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Josip Pankretić', 'votes': 10594, 'pct': 17.01},
    {'n': 4, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS',
                         'Hrvatska narodna stranka - HNS'],
     'holder': 'Dražen Budiša', 'votes': 26256, 'pct': 42.17},
    {'n': 5, 'parties': ['Kršćanska narodna stranka - KNS'],
     'holder': 'Dr.vet.med. Vladimir Mesarić', 'votes': 2872, 'pct': 4.61}],
  'seats': [
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS, Hrvatska narodna stranka - HNS',
     'n': 2, 'elected': [
      {'name': 'Branko Levačić', 'deputy': 'Žarko Katić'},
      {'name': 'Krešimir Lovrenčić', 'deputy': 'Alojzije Šestan'}]},
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 1, 'elected': [
      {'name': 'Prof. dr. Zvonimir Bartolić', 'deputy': 'Antun Jurinec'}]}]},
 {'code': '21', 'name': 'Grad Zagreb',
  'registered': 715772, 'voted': 484316, 'invalid': 12258, 'valid_total': 472058,
  'lists': [
    {'n': 1, 'parties': ['Domovinska građanska stranka'],
     'holder': 'Drago Mintas', 'votes': 3105, 'pct': 0.66},
    {'n': 2, 'parties': ['Hrvatska demokratska stranka prava - HDSP'],
     'holder': 'Krešimir Pavelić, dipl.pravnik', 'votes': 6973, 'pct': 1.48},
    {'n': 3, 'parties': ['Hrvatska demokratska zajednica - HDZ'],
     'holder': 'Dr. Franjo Tuđman', 'votes': 200939, 'pct': 42.57},
    {'n': 4, 'parties': ['Hrvatska kršćanska demokratska unija - HKDU'],
     'holder': 'Željko Olujić, dipl. pravnik', 'votes': 12305, 'pct': 2.61},
    {'n': 5, 'parties': ['Hrvatska seljačka stranka - HSS'],
     'holder': 'Drago Stipac', 'votes': 48616, 'pct': 10.30},
    {'n': 6, 'parties': ['Hrvatska socijalno liberalna stranka - HSLS'],
     'holder': 'Dražen Budiša', 'votes': 151804, 'pct': 32.16},
    {'n': 7, 'parties': ['Hrvatska stranka'],
     'holder': 'Dr. Vlatko Mićković', 'votes': 1269, 'pct': 0.27},
    {'n': 8, 'parties': ['Hrvatska stranka naravnog zakona'],
     'holder': 'Zlatko Žagmešter', 'votes': 2555, 'pct': 0.54},
    {'n': 9, 'parties': ['Nezavisna županijska lista'],
     'holder': 'Božidar Alić', 'votes': 7270, 'pct': 1.54},
    {'n': 10, 'parties': ['Nezavisna županijska lista'],
     'holder': 'Domagoj Margetić', 'votes': 1786, 'pct': 0.38},
    {'n': 11, 'parties': ['Nezavisna županijska lista'],
     'holder': 'Vladimir Pavetić', 'votes': 1510, 'pct': 0.32},
    {'n': 12, 'parties': ['Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena - SDP'],
     'holder': 'Vesna Vešligaj', 'votes': 13600, 'pct': 2.88},
    {'n': 13, 'parties': ['Socijalno-demokratska unija Hrvatske - SDU'],
     'holder': 'Dr. Branko Horvat', 'votes': 10973, 'pct': 2.32},
    {'n': 14, 'parties': ['Srpska narodna stranka'],
     'holder': 'Veljko Miljević', 'votes': 7383, 'pct': 1.56},
    {'n': 15, 'parties': ['Stranka demokratske akcije - ogranak za Hrvatsku'],
     'holder': 'Doc.dr. Šemso Tanković', 'votes': 1970, 'pct': 0.42}],
  'seats': [
    {'list': 'Hrvatska demokratska zajednica - HDZ', 'n': 2, 'elected': [
      {'name': 'Ivan Aralica', 'deputy': 'dr. Branko Jeren'},
      {'name': 'Zlatko Novak', 'deputy': 'Ante Šango'}]},
    {'list': 'Hrvatska socijalno liberalna stranka - HSLS', 'n': 1, 'elected': [
      {'name': 'Relja Bašić', 'deputy': 'Vesna Cvjetković-Kurelec'}]}]},
]
