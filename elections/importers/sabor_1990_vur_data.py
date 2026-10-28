"""The 1990 Vijeće udruženog rada election, read out of the report's OCR.

Source: `files/rezultati_sabor/1990/1990_1_5_Sabor_Rezultati_Vijece_udruzenog_rada.pdf`
(152 pages) and its supplement `1990_1_6_…_dopunski_izvjestaj.pdf` (14 pages),
CCITT-G4 scans with no text layer. Unlike the other two chambers this one is
not hand-typed: `sabor_1990_vur_parse` reads it from `tools/pdf_ocr` output
and writes `DISTRICTS` below (`--write`); what OCR cannot read is fixed in
`sabor_1990_vur_manual.py`, read off the scan. Correct a value there, not
here, or the next `--write` undoes it.

Chamber C) of the 1990 Sabor, the "council of associated labour", elected by
the employed at their workplaces rather than by residence: 160 single-member
units under the same two-round majority rule as the other two chambers
(Article 58 of the electoral law). The main report prints the units decided
in time for it; the supplement carries those that were not, among them
Zagreb - Centar V (49), Zagreb - Pešćenica V (67), Zagreb - Trešnjevka IV and
V (74, 75), Rijeka VIII (106) and Zadar III (120).

Same shapes as `sabor_1990_dpv_data`: unit -> name, rounds, winner; each round
holds registered, cast, invalid and the candidates as (name, residence, party,
votes), in the report's order, `party` being comma-joined abbreviations from
`PARTIES`.
"""
from .sabor_1990_dpv_data import (  # noqa: F401  (shared helpers)
    PARTIES as _DPV_PARTIES, party_label, person_name,
)

ELECTION_TYPE_SLUG = 'sabor_vur'
ELECTION_TYPE_NAME = 'Vijeće udruženog rada Sabora'

PARTIES = {
    **_DPV_PARTIES,
    'SZH': 'Savez zelenih Hrvatske',
    'USPĐ': 'Udruženje samostalnih privrednika Đurđevac',
    'USPS': 'Udruženje samostalnih privrednika Sisak',
    'SUSPS': 'Savez udruženja samostalnih privrednika Split',
}

DISTRICTS = {
    1: {'name': 'Beli Manastir', 'rounds': [
        {'registered': 15291, 'cast': 12887, 'invalid': 803, 'candidates': [
            ('Svetozar Barbirović', 'Beli Manastir', 'SKH-SDP', 755),
            ('Milan Basrak', 'Osijek', 'SKH-SDP', 850),
            ('Siniša Bjelica', 'Beli Manastir', 'NK', 419),
            ('Marko Brdarić', 'Šumarina', 'SKH-SDP', 1087),
            ('Josip Časar', 'Beli Manastir', 'NK', 1364),
            ('Ivan Čatipović', 'Osijek', 'NK', 813),
            ('Zdravko Damjanović', 'Beli Manastir', 'NK', 324),
            ('Mile Horvat', 'Kneževi Vinogradi', 'NK', 678),
            ('Ilija Knežević', 'Darda', 'NK', 485),
            ('Slavko Marjanović', 'Beli Manastir', 'SKH-SDP', 537),
            ('Milan Medunić', 'Beli Manastir', 'NK', 480),
            ('Dušan Njegovan', 'Osijek', 'SKH-SDP', 304),
            ('Radomir Simić', 'Beli Manastir', 'SKH-SDP', 555),
            ('Veselin Šarić', 'Osijek', 'SKH-SDP', 272),
            ('Josip Tomašek', 'Darda', 'NK', 912),
            ('Milivoj Vuković', 'Beli Manastir', 'SKH-SDP', 2249),
        ]},
        {'registered': 15517, 'cast': 12019, 'invalid': 663, 'candidates': [
            ('Milivoj Vuković', 'Beli Manastir', 'SKH-SDP', 6000),
            ('Josip Časar', 'Beli Manastir', 'NK', 1947),
            ('Marko Brdarić', 'Šumarina', 'SKH-SDP', 1900),
            ('Josip Tomašek', 'Darda', 'NK', 1509),
        ]},
    ], 'winner': 'Milivoj Vuković'},
    2: {'name': 'Osijek I', 'rounds': [
        {'registered': 14900, 'cast': 10341, 'invalid': 378, 'candidates': [
            ('Marko Bartolović', 'Osijek', 'SKH-SDP', 951),
            ('Zlatko Benašić', 'Osijek', 'NK', 183),
            ('Vladimir Dobrić', 'Osijek', 'SKH-SDP', 571),
            ('Ivan Dumančić', 'Osijek', 'NK', 302),
            ('Matija Grajf', 'Ernestinovo', 'NK', 266),
            ('Stjepan Frigan', 'Višnjevac', 'NK', 263),
            ('Slavko Medvidović', 'Višnjevac', 'SKH-SDP', 395),
            ('Mato Obradović', 'Osijek', 'SKH-SDP', 614),
            ('Zoran Ostović', 'Osijek', 'SKH-SDP', 600),
            ('Josip Pavić', 'Osijek', 'NK', 484),
            ('Ivan Pintarić', 'Osijek', 'NK', 208),
            ('Ivan Raguž', 'Osijek', 'NK', 488),
            ('Predrag Rehner', 'Osijek', 'NK', 160),
            ('Petar Tumir', 'Osijek', 'NK', 172),
            ('Josip Valinčić', 'Osijek', 'HDZ', 3845),
            ('Hrvoje Vuksan', 'Osijek', 'NK', 344),
        ]},
        {'registered': 15060, 'cast': 9345, 'invalid': 415, 'candidates': [
            ('Josip Valinčić', 'Osijek', 'HDZ', 5124),
            ('Mato Obradović', 'Osijek', 'SKH-SDP,SSH,SSOH', 3806),
        ]},
    ], 'winner': 'Josip Valinčić'},
    3: {'name': 'Osijek II', 'rounds': [
        {'registered': 9700, 'cast': 7878, 'invalid': 636, 'candidates': [
            ('Zvonko Erak', 'Osijek', 'SKH-SDP', 4290),
            ('Petar Kutleša', 'Osijek', 'NK', 1417),
            ('Milan Lelas', 'Osijek', 'NK', 366),
            ('Dragutin Ruska', 'Osijek', 'NK', 244),
            ('Željko Šplajt', 'Osijek', 'NK', 373),
            ('Pavao Vratarić', 'Osijek', 'NK', 552),
        ]},
    ], 'winner': 'Zvonko Erak'},
    4: {'name': 'Osijek III', 'rounds': [
        {'registered': 13027, 'cast': 10656, 'invalid': 282, 'candidates': [
            ('Zvonko Anderluh', 'Višnjevac', 'NK', 487),
            ('Tihomir Antunović', 'Osijek', 'NK', 352),
            ('Ivan Halas', 'Osijek', 'HDZ', 4258),
            ('Mirko Hefer', 'Čepin', 'NK', 447),
            ('Đorđe Klašnja', 'Osijek', 'NK', 673),
            ('Zdenko Kon', 'Osijek', 'SKH-SDP', 3024),
            ('Ante Krbanja', 'Osijek', 'NK', 275),
            ('Ivan Leko', 'Čepin', 'HDS,KNS', 1036),
        ]},
        {'registered': 13395, 'cast': 10049, 'invalid': 256, 'candidates': [
            ('Ivan Halas', 'Osijek', 'HDZ', 4671),
            ('Zdenko Kon', 'Osijek', 'SKH-SDP', 4323),
            ('Ivan Leko', 'Čepin', 'HDS', 799),
        ]},
    ], 'winner': 'Ivan Halas'},
    5: {'name': 'Osijek IV', 'rounds': [
        {'registered': 12135, 'cast': 9580, 'invalid': 555, 'candidates': [
            ('Pavo Oršolić', 'Osijek', 'NK', 655),
            ('Josip Ostriž', 'Osijek', 'NK', 838),
            ('Nedo Rešetar', 'Osijek', 'NK', 626),
            ('Bogdan Sudić', 'Osijek', 'NK', 813),
            ('Mr Tomislav Šljivac', 'Osijek', 'NK', 663),
            ('Zdenka Vekić', 'Osijek', 'NK', 655),
            ('Mato Vuković', 'Osijek', 'NK', 1408),
            ('Ivan Vuletić', 'Sarvaš', 'HDZ', 3097),
        ]},
        {'registered': 12110, 'cast': 8884, 'invalid': 592, 'candidates': [
            ('Ivan Vuletić', 'Sarvaš', 'HDZ', 4364),
            ('Mato Vuković', 'Osijek', 'NK', 3928),
        ]},
    ], 'winner': 'Ivan Vuletić'},
    6: {'name': 'Osijek V', 'rounds': [
        {'registered': 14115, 'cast': 11696, 'invalid': 212, 'candidates': [
            ('Mr Mato Bijuk', 'Osijek', 'NK', 419),
            ('Beatrica Brčić', 'Osijek', 'NK', 132),
            ('Vesna Brođanac', 'Osijek', 'NK', 236),
            ('Vladimir Bučević', 'Osijek', 'NK', 125),
            ('Dr Mile Čuljat', 'Osijek', 'NK', 215),
            ('Dr Vasilije Duranović', 'Osijek', 'NK', 542),
            ('Branimir Glavaš', 'Osijek', 'HDZ', 3025),
            ('Zvonimir Ivković', 'Osijek', 'NK', 228),
            ('Boro Kaluđer', 'Osijek', 'NK', 132),
            ('Gordana Klinger', 'Osijek', 'SSH', 336),
            ('Dr Ljiljana Kolenić', 'Osijek', 'NK', 83),
            ('Vjekoslava Kosanović-Singer', 'Osijek', 'SKH-SDP', 2048),
            ('Ivan Kuleš', 'Višnjevac', 'NK', 174),
            ('Dr Berislav Mandić', 'Osijek', 'HKDS,KNS', 1093),
            ('Dr Nikola Mandić', 'Osijek', 'SKH-SDP', 1924),
            ('Marijana Mitrović', 'Darda', 'NK', 148),
            ('Svetozar Sarkanjac', 'Osijek', 'NK', 130),
            ('Antun Sandalić', 'Osijek', 'NK', 100),
            ('Ante Tadić', 'Osijek', 'NK', 102),
            ('Dr Josip Vrbošić', 'Osijek', 'NK', 282),
        ]},
        {'registered': 14020, 'cast': 11143, 'invalid': 209, 'candidates': [
            ('Branimir Glavaš', 'Osijek', 'HDZ', 4637),
            ('Vjekoslava Kosanović-Singer', 'Osijek', 'SKH-SDP', 3442),
            ('Dr Nikola Mandić', 'Osijek', 'SKH-SDP', 2855),
        ]},
    ], 'winner': 'Branimir Glavaš'},
    7: {'name': 'Osijek VI', 'rounds': [
        {'registered': 8135, 'cast': 3850, 'invalid': 124, 'candidates': [
            ('Artur Gedike', 'Osijek', 'SSOH', 1911),
            ('Hrvatin Šustić', 'Osijek', 'HDZ', 1815),
        ]},
        {'registered': 7673, 'cast': 3407, 'invalid': 75, 'candidates': [
            ('Artur Gedike', 'Osijek', 'SSOH,SKH-SDP,SSH', 1686),
            ('Hrvatin Šustić', 'Osijek', 'HDZ', 1646),
        ]},
    ], 'winner': 'Artur Gedike'},
    8: {'name': 'Vukovar I', 'rounds': [
        {'registered': 16286, 'cast': 12401, 'invalid': 1126, 'candidates': [
            ('Petar Bošnjaković', 'Borovo', 'SKH-SDP', 5969),
            ('Miroslav Keravica', 'Borovo', 'NK', 1518),
            ('Petko Kosorić', 'Borovo', 'NK', 1143),
            ('Josip Kovač', 'Vukovar', 'NK', 2645),
        ]},
        {'registered': 16478, 'cast': 11687, 'invalid': 1049, 'candidates': [
            ('Petar Bošnjaković', 'Borovo', 'SKH-SDP', 4993),
            ('Josip Kovač', 'Vukovar', 'NK', 2632),
            ('Petko Kosorić', 'Borovo', 'NK', 3013),
        ]},
    ], 'winner': 'Petar Bošnjaković'},
    9: {'name': 'Vukovar II', 'rounds': [
        {'registered': 5567, 'cast': 4524, 'invalid': 376, 'candidates': [
            ('Vlatko Blažek', 'Ilok', 'SKH-SDP', 632),
            ('Aleksandar Ivezić', 'Vukovar', 'NK', 188),
            ('Ivan Juroš', 'Ilok', 'NK', 773),
            ('Tomislav Omrčenović', 'Vukovar', 'NK', 297),
            ('Đorđe Prokić', 'Vukovar', 'SKH-SDP', 981),
            ('Adam Rendulić', 'Lovas', 'SKH-SDP', 338),
            ('Đuro Tutnjević', 'Vukovar', 'SKH-SDP', 502),
            ('Drago Zelenika', 'Ilok', 'NK', 437),
        ]},
        {'registered': 5568, 'cast': 4372, 'invalid': 300, 'candidates': [
            ('Đorđe Prokić', 'Vukovar', 'SKH-SDP', 1685),
            ('Ivan Juroš', 'Ilok', 'NK', 1769),
            ('Vlatko Blažek', 'Ilok', 'SKH-SDP', 618),
        ]},
    ], 'winner': 'Ivan Juroš'},
    10: {'name': 'Vukovar III', 'rounds': [
        {'registered': 8850, 'cast': 6660, 'invalid': 485, 'candidates': [
            ('Hilda Devčić', 'Vukovar', 'SKH-SDP', 1566),
            ('Zvonimir Ivanišević', 'Vukovar', 'NK', 1071),
            ('Obrad Mirosavljević', 'Vukovar', 'NK', 763),
            ('Zlatko Modalek', 'Borovo', 'SKH-SDP', 1927),
            ('Ivan Mratinić', 'Vukovar', 'NK', 529),
            ('Mirko Šrajer', 'Borovo', 'NK', 319),
        ]},
        {'registered': 8866, 'cast': 6108, 'invalid': 495, 'candidates': [
            ('Zlatko Modalek', 'Borovo', 'SKH-SDP', 2449),
            ('Hilda Devčić', 'Vukovar', 'SKH-SDP', 1179),
            ('Zvonimir Ivanišević', 'Vukovar', 'NK', 913),
            ('Obrad Mirosavljević', 'Vukovar', 'NK', 559),
            ('Ivan Mratinić', 'Vukovar', 'NK', 513),
        ]},
    ], 'winner': 'Zlatko Modalek'},
    11: {'name': 'Vinkovci I', 'rounds': [
        {'registered': 11036, 'cast': 8960, 'invalid': 266, 'candidates': [
            ('Vlado Jemrić', 'Vinkovci', 'SSH', 1943),
            ('Bruno Kozina', 'Vinkovci', 'NK', 699),
            ('Željko Kukavčić', 'Vinkovci', 'NK', 477),
            ('Slavko Vištica', 'Vinkovci', 'HDZ', 5575),
        ]},
    ], 'winner': 'Slavko Vištica'},
    12: {'name': 'Vinkovci II', 'rounds': [
        {'registered': 12553, 'cast': 10132, 'invalid': 339, 'candidates': [
            ('Zvonimir Koščević', 'Vinkovci', 'SSH', 3676),
            ('Marijan Vukojević', 'Ivankovo', 'HDZ', 6117),
        ]},
    ], 'winner': 'Marijan Vukojević'},
    13: {'name': 'Slavonski Brod I', 'rounds': [
        {'registered': 11660, 'cast': 8930, 'invalid': 165, 'candidates': [
            ('Tomislav Galović', 'Slavonski Brod', 'NK', 318),
            ('Marija Gasler', 'Slavonski Brod', 'SZH', 450),
            ('Damir Krešo', 'Slavonski Brod', 'SSOH', 379),
            ('Dubravko Lalić', 'Slavonski Brod', 'NK', 147),
            ('Ante Lasić', 'Slavonski Brod', 'HDZ', 4589),
            ('Ivan Milas', 'Slavonski Brod', 'SKH-SDP', 1935),
            ('Ilija Vrljić', 'Stari Slatinik', 'HDS,KNS', 761),
            ('Ante Vukasović', 'Slavonski Brod', 'NK', 177),
        ]},
    ], 'winner': 'Ante Lasić'},
    14: {'name': 'Slavonski Brod II', 'rounds': [
        {'registered': 8820, 'cast': 6869, 'invalid': 340, 'candidates': [
            ('Nino Cirkveni', 'Slavonski Brod', 'SDSH,KNS', 708),
            ('Stjepan Ergović', 'Slavonski Brod', 'SSH', 608),
            ('Branko Janković', 'Slavonski Brod', 'HDZ', 3605),
            ('Ivan Novaković', 'Slavonski Brod', 'SKH-SDP', 1597),
        ]},
    ], 'winner': 'Branko Janković'},
    15: {'name': 'Slavonski Brod III', 'rounds': [
        {'registered': 13573, 'cast': 10901, 'invalid': 294, 'candidates': [
            ('Dr Željko Blažević', 'Slavonski Brod', 'HDS,KNS', 1888),
            ('Marko Čeović', 'Slavonski Brod', 'NK', 247),
            ('Stjepan Filipović', 'Slavonski Brod', 'NK', 397),
            ('Dr Josip Jelić', 'Slavonski Brod', 'NK', 711),
            ('Dr Zdenko Knežević', 'Vrpolje', 'HDZ', 3837),
            ('Stjepan Kokanović', 'Slavonski Brod', 'SSH', 459),
            ('Stanimir Krešić', 'Slavonski Brod', 'HSLS,KNS', 183),
            ('Ivica Miletić', 'Slavonski Brod', 'SKH-SDP', 2631),
            ('Čedomir Sundač', 'Slavonski Brod', 'NK', 226),
        ]},
        {'registered': 13597, 'cast': 9703, 'invalid': 196, 'candidates': [
            ('Dr Zdenko Knežević', 'Vrpolje', 'HDZ', 4302),
            ('Ivica Miletić', 'Slavonski Brod', 'SKH-SDP', 3572),
            ('Dr Željko Blažević', 'Slavonski Brod', 'HDS', 1631),
        ]},
    ], 'winner': 'Dr Zdenko Knežević'},
    16: {'name': 'Đakovo', 'rounds': [
        {'registered': 9280, 'cast': 7825, 'invalid': 158, 'candidates': [
            ('Luka Budić', 'Đakovo', 'KNS', 1247),
            ('Ivan Buljan', 'Đakovo', 'HDZ', 4103),
            ('Ivica Mandić', 'Đakovo', 'SKH-SDP', 1725),
            ('Mijo Tokić', 'Đakovo', 'SSH', 588),
        ]},
    ], 'winner': 'Ivan Buljan'},
    17: {'name': 'Županja', 'rounds': [
        {'registered': 7620, 'cast': 6405, 'invalid': 155, 'candidates': [
            ('Matej Juzbašić', 'Bošnjaci', 'HSS,KNS', 951),
            ('Ratimir Matijević', 'Županja', 'NK', 320),
            ('Niko Popović', 'Županja', 'HDZ', 3270),
            ('Vesna Šnajder', 'Županja', 'SKH-SDP', 1450),
            ('Gabrijel Sokičić', 'Županja', 'NK', 256),
        ]},
    ], 'winner': 'Niko Popović'},
    18: {'name': 'Našice', 'rounds': [
        {'registered': 12930, 'cast': 11064, 'invalid': 236, 'candidates': [
            ('Ivica Čeme', 'Našice', 'HDZ', 5481),
            ('Josip Dundović', 'Našice', 'NK', 672),
            ('Vladimir Gall', 'Našice', 'HKDS,KNS', 612),
            ('Pavle Kovačević', 'Orahovica', 'SKH-SDP', 2130),
            ('Stjepan Patača', 'Đurđenovac', 'SKH-SDP', 1201),
            ('Ivan Škorić', 'Našice', 'HSLS,SDSH,HDS,HKDS,KNS', 732),
        ]},
        {'registered': 13051, 'cast': 10356, 'invalid': 193, 'candidates': [
            ('Ivica Čeme', 'Našice', 'HDZ', 6682),
            ('Pavle Kovačević', 'Orahovica', 'SKH-SDP', 3479),
        ]},
    ], 'winner': 'Ivica Čeme'},
    19: {'name': 'Valpovo', 'rounds': [
        {'registered': 10150, 'cast': 8148, 'invalid': 233, 'candidates': [
            ('Mr Marijan Jakšić', 'Belišće', 'SKH-SDP', 2169),
            ('Ivica Šimić', 'Belišće', 'NK', 1023),
            ('Stjepan Zetović', 'Belišće', 'HDZ', 4716),
        ]},
    ], 'winner': 'Stjepan Zetović'},
    20: {'name': 'Podravska Slatina', 'rounds': [
        {'registered': 13326, 'cast': 11826, 'invalid': 227, 'candidates': [
            ('Vladimir Jurić', 'Podravska Slatina', 'SSH', 846),
            ('Marijan Perić', 'Podravska Slatina', 'SKH-SDP', 3896),
            ('Josip Rastija', 'Podravska Slatina', 'NK', 437),
            ('Ante Šimara', 'Podravska Slatina', 'HDZ', 4870),
            ('Stipan Šimunović', 'Donji Miholjac', 'NK', 787),
            ('Pavo Zvocak', 'Donji Miholjac', 'KNS', 664),
        ]},
        {'registered': 13408, 'cast': 11124, 'invalid': 232, 'candidates': [
            ('Ante Šimara', 'Podravska Slatina', 'HDZ', 5769),
            ('Marijan Perić', 'Podravska Slatina', 'SKH-SDP', 5123),
        ]},
    ], 'winner': 'Ante Šimara'},
    21: {'name': 'Slavonska Požega', 'rounds': [
        {'registered': 17294, 'cast': 13932, 'invalid': 242, 'candidates': [
            ('Ferdo Ćuk', 'Slavonska Požega', 'HDZ', 7429),
            ('Milan Devčić', 'Slavonska Požega', 'SKH-SDP', 3405),
            ('Mato Ećimović', 'Pleternica', 'SSH', 532),
            ('Vinko Kovačević', 'Slavonska Požega', 'NK', 308),
            ('Ivica Kršilović', 'Pleternica', 'NK', 123),
            ('Dragutin Mandić', 'Slavonska Požega', 'NK', 267),
            ('Franjo Pavlović', 'Slavonska Požega', 'HSLS,SDSH,HKDS,HDS,KNS', 1437),
            ('Ivan Petriska', 'Slavonska Požega', 'NK', 189),
        ]},
    ], 'winner': 'Ferdo Ćuk'},
    22: {'name': 'Nova Gradiška', 'rounds': [
        {'registered': 13389, 'cast': 11106, 'invalid': 369, 'candidates': [
            ('Dubravko Brnčić', 'Nova Gradiška', 'NK', 493),
            ('Josip Butković', 'Černik', 'NK', 702),
            ('Ljubica Hanak', 'Nova Gradiška', 'NK', 424),
            ('Slavko Jelinić', 'Nova Gradiška', 'SSH', 1177),
            ('Mijo Šagovac', 'Nova Gradiška', 'NK', 659),
            ('Ninko Vučković', 'Nova Gradiška', 'SSH', 2268),
            ('Vjekoslav Žugaj', 'Nova Gradiška', 'HSLS,HDS,HKDS,KNS', 5014),
        ]},
        {'registered': 13423, 'cast': 9938, 'invalid': 289, 'candidates': [
            ('Vjekoslav Žugaj', 'Nova Gradiška', 'HSLS,HDS,HKDS,KNS', 6087),
            ('Ninko Vučković', 'Nova Gradiška', 'SSH', 3562),
        ]},
    ], 'winner': 'Vjekoslav Žugaj'},
    23: {'name': 'Bjelovar', 'rounds': [
        {'registered': 16722, 'cast': 13935, 'invalid': 308, 'candidates': [
            ('Dane Bjelobaba', 'Bjelovar', 'SKH-SDP', 3496),
            ('Petar Curić', 'Bjelovar', 'NK', 350),
            ('Milan Lebinac', 'Bjelovar', 'SKH-SDP', 1410),
            ('Antun Mirović', 'Višnjevac', 'HDS,KNS', 1141),
            ('Krešimir Pavičić', 'Bjelovar', 'NK', 711),
            ('Zvonko Podlecak', 'Bjelovar', 'NK', 217),
            ('Željko Stojković', 'Kapela', 'HSS,KNS', 626),
            ('Jure Šimić', 'Rovišće', 'HDZ', 4653),
            ('Ivan Stefekov', 'Bjelovar', 'SSH', 1012),
        ]},
        {'registered': 16903, 'cast': 12867, 'invalid': 199, 'candidates': [
            ('Jure Šimić', 'Rovišće', 'HDZ', 5632),
            ('Dane Bjelobaba', 'Bjelovar', 'SKH-SDP', 5715),
            ('Antun Mirović', 'Višnjevac', 'HDS', 1321),
        ]},
    ], 'winner': 'Dane Bjelobaba'},
    24: {'name': 'Križevci', 'rounds': [
        {'registered': 7095, 'cast': 5645, 'invalid': 298, 'candidates': [
            ('Marijan Belani', 'Križevci', 'NK', 342),
            ('Stjepan Čokor', 'Križevci', 'HDZ', 1985),
            ('Vilim Jurić', 'Čubinec', 'NK', 176),
            ('Ivan Knok', 'Križevci', 'SSH', 260),
            ('Petar Milas', 'Križevci', 'HSLS,KNS', 590),
            ('Krunoslav Ružić', 'Križevci', 'SKH-SDP', 1456),
            ('Josip Šikić', 'Križevci', 'NK', 336),
            ('Stjepan Toth', 'Križevci', 'NK', 199),
        ]},
        {'registered': 7098, 'cast': 5219, 'invalid': 122, 'candidates': [
            ('Stjepan Čokor', 'Križevci', 'HDZ', 2276),
            ('Krunoslav Ružić', 'Križevci', 'SKH-SDP', 2012),
            ('Petar Milas', 'Križevci', 'HSLS,KNS', 809),
        ]},
    ], 'winner': 'Stjepan Čokor'},
    25: {'name': 'Daruvar', 'rounds': [
        {'registered': 12616, 'cast': 10650, 'invalid': 543, 'candidates': [
            ('Krunoslav Guberović', 'Daruvar', 'SKH-SDP,SSH', 2718),
            ('Marica Pervan', 'Daruvar', 'SKH-SDP,SSH', 2910),
            ('Momir Plavšić', 'Daruvar', 'NK', 1326),
            ('Luka Starčić', 'Kaniška Iva', 'HDS,KNS', 3153),
        ]},
        {'registered': 12605, 'cast': 9823, 'invalid': 496, 'candidates': [
            ('Luka Starčić', 'Kaniška Iva', 'HDS', 3202),
            ('Marica Pervan', 'Daruvar', 'SKH-SDP,SSH', 4786),
            ('Momir Plavšić', 'Daruvar', 'NK', 1339),
        ]},
    ], 'winner': 'Marica Pervan'},
    26: {'name': 'Virovitica', 'rounds': [
        {'registered': 11610, 'cast': 10054, 'invalid': 210, 'candidates': [
            ('Dr Rudolf Brijačak', 'Gradina', 'HDZ', 5166),
            ('Dr Jakob Čupen', 'Virovitica', 'NK', 502),
            ('Mr Milan Glumac', 'Virovitica', 'NK', 423),
            ('Zdravko Novoselac', 'Suhopolje', 'NK', 189),
            ('Ivan Slamić', 'Virovitica', 'NK', 478),
            ('Tomislav Špoljarić', 'Virovitica', 'NK', 153),
            ('Marijan Tomljanović', 'Virovitica', 'SKH-SDP', 2403),
            ('Dragan Vukušić', 'Virovitica', 'NK', 164),
            ('Mile Zidar', 'Virovitica', 'SSH', 366),
        ]},
    ], 'winner': 'Dr Rudolf Brijačak'},
    27: {'name': 'Koprivnica I', 'rounds': [
        {'registered': 11582, 'cast': 9187, 'invalid': 255, 'candidates': [
            ('Mr Željko Durdina', 'Koprivnica', 'SKH-SDP', 2616),
            ('Marijan Ištvanović', 'Reka', 'SKH-SDP', 1275),
            ('Ante Krajina', 'Koprivnica', 'HDZ', 3897),
            ('Milan Matijević', 'Koprivnica', 'HSLS,KNS', 1144),
        ]},
        {'registered': 11677, 'cast': 8190, 'invalid': 236, 'candidates': [
            ('Ante Krajina', 'Koprivnica', 'HDZ', 4167),
            ('Mr Željko Durdina', 'Koprivnica', 'SKH-SDP', 3787),
        ]},
    ], 'winner': 'Ante Krajina'},
    28: {'name': 'Koprivnica II', 'rounds': [
        {'registered': 9005, 'cast': 7156, 'invalid': 195, 'candidates': [
            ('Ivan Brodnik', 'Koprivnica', 'NK', 297),
            ('Ivan Cimbrišak', 'Koprivnica', 'HSS,KNS', 1004),
            ('Ivan Curić', 'Pitomača', 'NK', 155),
            ('Mato Jukić', 'Koprivnica', 'HDZ', 2328),
            ('Nikola Kancijan', 'Koprivnica', 'SKH-SDP', 1293),
            ('Marijan Lukačić', 'Koprivnica', 'NK', 237),
            ('Mr Neven Petruša', 'Koprivnica', 'SKH-SDP', 1238),
            ('Ivica Zagrajski', 'Koprivnica', 'NK', 409),
        ]},
        {'registered': 9048, 'cast': 6493, 'invalid': 182, 'candidates': [
            ('Mato Jukić', 'Koprivnica', 'HDZ', 3036),
            ('Nikola Kancijan', 'Koprivnica', 'SKH-SDP', 3275),
        ]},
    ], 'winner': 'Nikola Kancijan'},
    29: {'name': 'Đurđevac', 'rounds': [
        {'registered': 7125, 'cast': 6186, 'invalid': 138, 'candidates': [
            ('Mirko Lukić', 'Virje', 'NK', 821),
            ('Marijan Panić', 'Đurđevac', 'NK', 406),
            ('Ivan Prepelec', 'Pitomača', 'SKH-SDP', 1516),
            ('Nikola Slavica', 'Đurđevac', 'NK', 886),
            ('Veljko Turković', 'Đurđevac', 'HDZ', 2419),
        ]},
        {'registered': 7114, 'cast': 5459, 'invalid': 154, 'candidates': [
            ('Veljko Turković', 'Đurđevac', 'HDZ', 2516),
            ('Nikola Slavica', 'Đurđevac', 'NK', 1622),
            ('Mirko Lukić', 'Virje', 'NK', 1167),
        ]},
    ], 'winner': 'Veljko Turković'},
    30: {'name': 'Pakrac', 'rounds': [
        {'registered': 13919, 'cast': 11524, 'invalid': 944, 'candidates': [
            ('Ivan Barbir', 'Čazma', 'NK', 3138),
            ('Đorđe Gunjević', 'Pakrac', 'NK', 2853),
            ('Branko Kovačić', 'Čazma', 'SKH-SDP', 4589),
        ]},
        {'registered': 13902, 'cast': 10778, 'invalid': 882, 'candidates': [
            ('Branko Kovačić', 'Čazma', 'SKH-SDP', 4704),
            ('Ivan Barbir', 'Čazma', 'NK', 2624),
            ('Đorđe Gunjević', 'Pakrac', 'NK', 2568),
        ]},
    ], 'winner': 'Branko Kovačić'},
    31: {'name': 'Čakovec I', 'rounds': [
        {'registered': 16049, 'cast': 13277, 'invalid': 696, 'candidates': [
            ('Slavko Bubek', 'Čakovec', 'NK', 2220),
            ('Alojz Hudiček', 'Čakovec', 'NK', 3087),
            ('Petar Petrović', 'Čakovec', 'NK', 1102),
            ('Ivan Radek', 'Mačkovec', 'HKDS,KNS', 5548),
            ('Alojz Rambrot', 'Čakovec', 'NK', 624),
        ]},
        {'registered': 16013, 'cast': 12243, 'invalid': 629, 'candidates': [
            ('Ivan Radek', 'Mačkovec', 'HKDS,KNS', 6373),
            ('Alojz Hudiček', 'Čakovec', 'NK', 3598),
            ('Petar Petrović', 'Čakovec', 'NK', 1643),
        ]},
    ], 'winner': 'Ivan Radek'},
    32: {'name': 'Čakovec II', 'rounds': [
        {'registered': 14136, 'cast': 9810, 'invalid': 408, 'candidates': [
            ('Ivan Ganzer', 'Dunjkovec', 'HKDS,KNS', 4379),
            ('Pavao Hlapčić', 'Čakovec', 'NK', 1965),
            ('Dragica Kropek', 'Čakovec', 'NK', 3058),
        ]},
        {'registered': 14077, 'cast': 8319, 'invalid': 346, 'candidates': [
            ('Ivan Ganzer', 'Dunjkovec', 'HKDS,KNS', 3968),
            ('Dragica Kropek', 'Čakovec', 'NK', 4005),
        ]},
    ], 'winner': 'Dragica Kropek'},
    33: {'name': 'Varaždin I', 'rounds': [
        {'registered': 16120, 'cast': 11836, 'invalid': 665, 'candidates': [
            ('Slavko Friščić', 'Varaždin', 'NK', 986),
            ('Zdravko Habijan', 'Varaždin', 'NK', 304),
            ('Ivo Horvat', 'Nedelišće', 'NK', 377),
            ('Stjepan Hunjak', 'Varaždin', 'SKH-SDP', 2050),
            ('Ivica Komić', 'Petrijanec', 'SSH', 477),
            ('Boris Kranjec', 'Varaždin', 'NK', 188),
            ('Ambroz Nikolić', 'Varaždin', 'NK', 189),
            ('Boris Santo', 'Varaždin', 'NK', 405),
            ('Ivan Šipek', 'Varaždin', 'HDS,KNS', 5030),
            ('Damir Vitez', 'Varaždin', 'NK', 1165),
        ]},
        {'registered': 16043, 'cast': 10322, 'invalid': 559, 'candidates': [
            ('Ivan Šipek', 'Varaždin', 'HDS', 5304),
            ('Stjepan Hunjak', 'Varaždin', 'SKH-SDP', 2618),
            ('Damir Vitez', 'Varaždin', 'NK', 1838),
        ]},
    ], 'winner': 'Ivan Šipek'},
    34: {'name': 'Varaždin II', 'rounds': [
        {'registered': 14346, 'cast': 10971, 'invalid': 529, 'candidates': [
            ('Branko Bek', 'Varaždin', 'NK', 847),
            ('Mijo Cmrečko', 'Varaždin', 'NK', 322),
            ('Franjo Grdjan', 'Varaždin', 'NK', 539),
            ('Dragutin Lovrenčić', 'Hrašćica', 'SKH-SDP', 1804),
            ('Svjetlana Makaj', 'Varaždin', 'NK', 637),
            ('Dr Josip Sudec', 'Varaždin', 'NK', 1009),
            ('Stjepan Svržnjak', 'Varaždin', 'NK', 431),
            ('Branko Šincek', 'Varaždin', 'HDS,KNS', 4347),
            ('Franjo Tkalec', 'Varaždin', 'NK', 506),
        ]},
        {'registered': 14358, 'cast': 9193, 'invalid': 374, 'candidates': [
            ('Branko Šincek', 'Varaždin', 'HDS', 4815),
            ('Dragutin Lovrenčić', 'Hrašćica', 'SKH-SDP', 2491),
            ('Branko Bek', 'Varaždin', 'NK', 1511),
        ]},
    ], 'winner': 'Branko Šincek'},
    35: {'name': 'Varaždin III', 'rounds': [
        {'registered': 7266, 'cast': 5801, 'invalid': 17, 'candidates': [
            ('Marijan Cesarec', 'Varaždin', 'NK', 689),
            ('Ratimir Čavlović', 'Varaždin', 'HDZ', 1352),
            ('Zdravko Ostroški', 'Beletinec', 'HDS,KNS', 1051),
            ('Branko Tomljenović', 'Varaždin', 'NK', 315),
            ('Božidar Vučetić', 'Varaždin', 'SKH-SDP', 1833),
            ('Dr Boris Zver', 'Varaždin', 'NK', 484),
        ]},
        {'registered': 7226, 'cast': 5097, 'invalid': 100, 'candidates': [
            ('Božidar Vučetić', 'Varaždin', 'SKH-SDP', 2073),
            ('Ratimir Čavlović', 'Varaždin', 'HDZ,HDS', 1798),
            ('Marijan Cesarec', 'Varaždin', 'NK', 616),
            ('Dr Boris Zver', 'Varaždin', 'NK', 506),
        ]},
    ], 'winner': 'Božidar Vučetić'},
    36: {'name': 'Ivanec', 'rounds': [
        {'registered': 8738, 'cast': 7216, 'invalid': 187, 'candidates': [
            ('Željko Brezovec', 'Ivanec', 'HSLS,KNS', 1078),
            ('Stjepan Gašparić', 'Ladanje Donje', 'SKH-SDP', 1826),
            ('Zlatko Koračević', 'Bednja', 'NK', 758),
            ('Ivan Kušen', 'Ivanec', 'HDZ', 3367),
        ]},
        {'registered': 8954, 'cast': 6502, 'invalid': 158, 'candidates': [
            ('Ivan Kušen', 'Ivanec', 'HDZ', 3443),
            ('Stjepan Gašparić', 'Ladanje Donje', 'SKH-SDP', 1704),
            ('Željko Brezovec', 'Ivanec', 'HSLS,KNS', 662),
            ('Zlatko Koračević', 'Bednja', 'NK', 535),
        ]},
    ], 'winner': 'Ivan Kušen'},
    37: {'name': 'Ludbreg', 'rounds': [
        {'registered': 11673, 'cast': 9823, 'invalid': 286, 'candidates': [
            ('Nada Đud', 'Varaždinske Toplice', 'SSH', 801),
            ('Goran Ivec', 'Novi Marof', 'SSOH', 550),
            ('Antun Kos', 'Novi Marof', 'NK', 563),
            ('Slavko Mlinarić', 'Novi Marof', 'SKH-SDP', 1849),
            ('Anđelko Potrebica', 'Varaždinske Toplice', 'HDZ', 4411),
            ('Franjo Repić', 'Ludbreg', 'NK', 1363),
        ]},
        {'registered': 11745, 'cast': 8884, 'invalid': 235, 'candidates': [
            ('Anđelko Potrebica', 'Varaždinske Toplice', 'HDZ', 4832),
            ('Slavko Mlinarić', 'Novi Marof', 'SKH-SDP', 2922),
            ('Nada Đud', 'Varaždinske Toplice', 'SSH', 895),
        ]},
    ], 'winner': 'Anđelko Potrebica'},
    38: {'name': 'Krapina', 'rounds': [
        {'registered': 12126, 'cast': 9365, 'invalid': 2091, 'candidates': [
            ('Žarko Miljan', 'Krapina', 'NK', 3389),
            ('Ivan Prelčec', 'Krapina', 'SKH-SDP', 2537),
            ('Dolfi Šmid', 'Krapina', 'NK', 1348),
        ]},
        {'registered': 12118, 'cast': 7740, 'invalid': 1630, 'candidates': [
            ('Žarko Miljan', 'Krapina', 'NK', 3667),
            ('Ivan Prelčec', 'Krapina', 'SKH-SDP', 2443),
        ]},
    ], 'winner': 'Žarko Miljan'},
    39: {'name': 'Zabok', 'rounds': [
        {'registered': 12470, 'cast': 9984, 'invalid': 311, 'candidates': [
            ('Stjepan Hanžić', 'Zabok', 'NK', 565),
            ('Dr Mijo Hržina', 'Veliko Trgovišće', 'HSLS,KNS', 777),
            ('Danijel Jelenčić', 'Krapinske Toplice', 'SKH-SDP', 2075),
            ('Andrija Jureković', 'Krapinske Toplice', 'NK', 244),
            ('Mr Zvonko Marušić', 'Zabok', 'NK', 325),
            ('Dr Vladimir Sokolić', 'Zabok', 'HDZ', 4471),
            ('Dr Ljudevit Ulaković', 'Zabok', 'NK', 431),
            ('Dr Štefanija Valent', 'Zabok', 'NK', 781),
        ]},
        {'registered': 11780, 'cast': 8027, 'invalid': 205, 'candidates': [
            ('Dr Vladimir Sokolić', 'Zabok', 'HDZ', 4182),
            ('Danijel Jelenčić', 'Krapinske Toplice', 'SKH-SDP', 2218),
            ('Dr Štefanija Valent', 'Zabok', 'NK', 750),
            ('Dr Mijo Hržina', 'Veliko Trgovišće', 'HSLS,KNS', 672),
        ]},
    ], 'winner': 'Dr Vladimir Sokolić'},
    40: {'name': 'Donja Stubica', 'rounds': [
        {'registered': 16881, 'cast': 12530, 'invalid': 1203, 'candidates': [
            ('Daniel Klancir', 'Zlatar Bistrica', 'SKH-SDP', 3778),
            ('Zdravko Kurilj', 'Oroslavlje', 'NK', 7526),
        ]},
    ], 'winner': 'Zdravko Kurilj'},
    41: {'name': 'Ivanić Grad', 'rounds': [
        {'registered': 15039, 'cast': 12123, 'invalid': 690, 'candidates': [
            ('Ivanka Dlaka', 'Dubrava', 'SKH-SDP', 3792),
            ('Vitomir Klasić', 'Križ', 'NK', 1011),
            ('Josip Krklec', 'Žabno', 'NK', 509),
            ('Ivan Lončarić', 'Vrbovec', 'NK', 926),
            ('Ivan Macan', 'Sesvetski Kraljevac', 'NK', 336),
            ('Jadranko Mijalić', 'Vrbovec', 'HSLS,SDSH,HDS,HKDS,HSS,KNS', 4325),
        ]},
        {'registered': 14722, 'cast': 10639, 'invalid': 458, 'candidates': [
            ('Jadranko Mijalić', 'Vrbovec', 'HSLS,SDSH,HDS,HKDS,HSS,KNS', 4222),
            ('Ivanka Dlaka', 'Dubrava', 'SKH-SDP', 3845),
            ('Vitomir Klasić', 'Križ', 'NK', 1179),
            ('Ivan Lončarić', 'Vrbovec', 'NK', 932),
        ]},
    ], 'winner': 'Jadranko Mijalić'},
    42: {'name': 'Dugo Selo', 'rounds': [
        {'registered': 7579, 'cast': 6147, 'invalid': 220, 'candidates': [
            ('Damir Bilić', 'Dugo Selo', 'HDZ', 2882),
            ('Lidija Bošnjaković', 'Kobiljak', 'HSLS,KNS', 528),
            ('Ivan Grgac', 'Dugo Selo', 'NK', 358),
            ('Nikola Hasnek', 'Zelina', 'SSH', 290),
            ('Stjepan Kukovačec', 'Zelina', 'SKH-SDP', 1160),
            ('Predrag Mikulčić', 'Dugo Selo', 'NK', 166),
            ('Vlado Šindler', 'Lukarišće', 'NK', 184),
            ('Boris Trupec', 'Dugo Selo', 'NK', 359),
        ]},
        {'registered': 7543, 'cast': 5167, 'invalid': 165, 'candidates': [
            ('Damir Bilić', 'Dugo Selo', 'HDZ', 2743),
            ('Stjepan Kukovačec', 'Zelina', 'SKH-SDP', 1635),
            ('Lidija Bošnjaković', 'Kobiljak', 'HSLS,KNS', 624),
        ]},
    ], 'winner': 'Damir Bilić'},
    43: {'name': 'Kutina', 'rounds': [
        {'registered': 12725, 'cast': 9947, 'invalid': 146, 'candidates': [
            ('Ivan Jandroković', 'Kutina', 'NK', 401),
            ('Ivo Lenić', 'Kutina', 'HDZ', 4024),
            ('Zdravko Nikšić', 'Kutina', 'HSLS,KNS', 1540),
            ('Ante Pranjić', 'Kutina', 'NK', 302),
            ('Slavko Sokol', 'Kutina', 'SKH-SDP', 3521),
        ]},
        {'registered': 12656, 'cast': 9229, 'invalid': 152, 'candidates': [
            ('Ivo Lenić', 'Kutina', 'HDZ', 4955),
            ('Slavko Sokol', 'Kutina', 'SKH-SDP', 4122),
        ]},
    ], 'winner': 'Ivo Lenić'},
    44: {'name': 'Jastrebarsko', 'rounds': [
        {'registered': 5803, 'cast': 4892, 'invalid': 85, 'candidates': [
            ('Albert Gros', 'Jastrebarsko', 'NK', 438),
            ('Ante Kapac', 'Jastrebarsko', 'SKH-SDP', 1092),
            ('Ivan Penić', 'Jastrebarsko', 'HDZ', 3276),
        ]},
    ], 'winner': 'Ivan Penić'},
    45: {'name': 'Zagreb - Centar I', 'rounds': [
        {'registered': 4599, 'cast': 3579, 'invalid': 49, 'candidates': [
            ('Zvonko Đerek', 'Sesvete', 'HDS,KNS', 517),
            ('Ilija Kuga', 'Zagreb', 'SKH-SDP', 637),
            ('Šime Stopfer', 'Zagreb', 'NK', 278),
            ('Vjekoslav Studen', 'Zagreb', 'HDZ', 2098),
        ]},
    ], 'winner': 'Vjekoslav Studen'},
    46: {'name': 'Zagreb - Centar II', 'rounds': [
        {'registered': 7862, 'cast': 4726, 'invalid': 78, 'candidates': [
            ('Marijan Bolarić', 'Zagreb', 'NK', 270),
            ('Bartol Ivanuša', 'Zagreb', 'SKH-SDP', 1121),
            ('Dr Antun Mikec', 'Zagreb', 'NK', 352),
            ('Ivan Orčik', 'Zagreb', 'HDZ', 2585),
            ('Ilijaz Ramadani', 'Zagreb', 'NK', 116),
            ('Janko Tisanić', 'Zagreb', 'NK', 204),
        ]},
        {'registered': 7794, 'cast': 3744, 'invalid': 50, 'candidates': [
            ('Ivan Orčik', 'Zagreb', 'HDZ', 2174),
            ('Bartol Ivanuša', 'Zagreb', 'SKH-SDP', 1027),
            ('Dr Antun Mikec', 'Zagreb', 'NK', 483),
        ]},
    ], 'winner': 'Ivan Orčik'},
    47: {'name': 'Zagreb - Centar III', 'rounds': [
        {'registered': 3219, 'cast': 2199, 'invalid': 312, 'candidates': [
            ('Vera Babić', 'Zagreb', 'NK', 1159),
            ('Frane Božina', 'Zagreb', 'SKH-SDP', 355),
            ('Vjekoslav Silić', 'Zagreb', 'SKH-SDP', 373),
        ]},
    ], 'winner': 'Vera Babić'},
    48: {'name': 'Zagreb - Centar IV', 'rounds': [
        {'registered': 18448, 'cast': 13543, 'invalid': 158, 'candidates': [
            ('Stjepan Jambrešić', 'Zagreb', 'NK', 488),
            ('Klara Novosel', 'Zagreb', 'HDZ', 7254),
            ('Antun Plenković', 'Zagreb', 'HSLS,KNS', 2110),
            ('Dalibor Srića', 'Zagreb', 'SKH-SDP', 3082),
            ('Željan Surjan', 'Zagreb', 'NK', 177),
            ('Roko Taslak', 'Zagreb', 'NK', 274),
        ]},
    ], 'winner': 'Klara Novosel'},
    49: {'name': 'Zagreb - Centar V', 'rounds': [
        {'registered': 15099, 'cast': 10346, 'invalid': 137, 'candidates': [
            ('Stjepan Androić', 'Zaprešić', 'NK', 252),
            ('Dr Štefica Bahtijarević', 'Zagreb', 'NK', 181),
            ('Josip Copić', 'Zagreb', 'NK', 130),
            ('Dr Adolf Dragičević', 'Zagreb', 'SKH-SDP', 2096),
            ('Dr Ljerka Duić', 'Zagreb', 'NK', 217),
            ('Dr Krešimir Humski', 'Zagreb', 'NK', 229),
            ('Tomislav Ladan', 'Zagreb', 'NK', 530),
            ('Dr Tihomil Maštrović', 'Zagreb', 'HSLS,KNS', 1669),
            ('Damir Mejovšek', 'Zagreb', 'HDZ', 3805),
            ('Anuška Nakić', 'Zagreb', 'NK', 163),
            ('Mate Pavković', 'Zagreb', 'NK', 101),
            ('Vilim Ribić', 'Zagreb', 'SDSH,KNS', 570),
            ('Dr Josip Stipanov', 'Zagreb', 'NK', 156),
            ('Ivica Vuković', 'Zagreb', 'NK', 110),
        ]},
        {'registered': 15125, 'cast': 7799, 'invalid': 94, 'candidates': [
            ('Damir Mejovšek', 'Zagreb', 'HDZ', 4004),
            ('Dr Adolf Dragičević', 'Zagreb', 'SKH-SDP', 1822),
            ('Dr Tihomil Maštrović', 'Zagreb', 'HSLS,KNS', 1879),
        ]},
    ], 'winner': 'Damir Mejovšek'},
    50: {'name': 'Zagreb - Centar VI', 'rounds': [
        {'registered': 13748, 'cast': 8953, 'invalid': 1305, 'candidates': [
            ('Tomislav Bilić', 'Zagreb', 'NK', 2010),
            ('Ljerka Ercegović', 'Zagreb', 'SKH-SDP', 4003),
            ('Jadranka Japunčić', 'Zagreb', 'NK', 762),
            ('Katica Pezo', 'Zagreb', 'NK', 873),
        ]},
        {'registered': 12690, 'cast': 6430, 'invalid': 937, 'candidates': [
            ('Ljerka Ercegović', 'Zagreb', 'SKH-SDP', 2825),
            ('Tomislav Bilić', 'Zagreb', 'NK', 1403),
            ('Katica Pezo', 'Zagreb', 'NK', 614),
            ('Jadranka Japunčić', 'Zagreb', 'NK', 651),
        ]},
    ], 'winner': 'Ljerka Ercegović'},
    51: {'name': 'Zagreb - Črnomerec I', 'rounds': [
        {'registered': 7957, 'cast': 5727, 'invalid': 104, 'candidates': [
            ('Milka Fell-Rudić', 'Zagreb', 'SKH-SDP', 1321),
            ('Zdenko Krpan', 'Zagreb', 'NK', 602),
            ('Ivan Šimunović', 'Zelina', 'HDZ', 3700),
        ]},
    ], 'winner': 'Ivan Šimunović'},
    52: {'name': 'Zagreb - Črnomerec II', 'rounds': [
        {'registered': 8478, 'cast': 6522, 'invalid': 95, 'candidates': [
            ('Dr Nedjeljko Kujundžić', 'Zagreb', 'HDZ', 3759),
            ('Zdravko Tomičić', 'Zagreb', 'SKH-SDP', 1536),
            ('Miroslav Vojvoda', 'Zagreb', 'NK', 296),
            ('Dalibor Žarak', 'Zagreb', 'HSLS,HDS,SDSH,HSS,HKDS,KNS', 826),
        ]},
    ], 'winner': 'Dr Nedjeljko Kujundžić'},
    53: {'name': 'Zagreb - Črnomerec III', 'rounds': [
        {'registered': 12412, 'cast': 9479, 'invalid': 170, 'candidates': [
            ('Anto Dugonjić', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 641),
            ('Mr Marko Ivanović', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 883),
            ('Nada Juzbašić', 'Zagreb', 'NK', 297),
            ('Dr Dragutin Košuta', 'Zagreb', 'HDZ', 4682),
            ('Dr Petar Nola', 'Zagreb', 'NK', 469),
            ('Dr Frane Rušinović', 'Zagreb', 'SKH-SDP', 2052),
            ('Ivan Validžić', 'Zagreb', 'NK', 137),
            ('Agneza Vukelić', 'Zagreb', 'NK', 143),
        ]},
        {'registered': 12306, 'cast': 8321, 'invalid': 132, 'candidates': [
            ('Dr Dragutin Košuta', 'Zagreb', 'HDZ', 4571),
            ('Dr Frane Rušinović', 'Zagreb', 'SKH-SDP', 2283),
            ('Mr Marko Ivanović', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,KNS', 1325),
        ]},
    ], 'winner': 'Dr Dragutin Košuta'},
    54: {'name': 'Zagreb - Dubrava', 'rounds': [
        {'registered': 9768, 'cast': 7402, 'invalid': 9, 'candidates': [
            ('Ivan Perinović', 'Zagreb', 'SKH-SDP', 1833),
            ('Drago Previšić', 'Zagreb', 'HDZ', 4648),
            ('Tomo Šnajder', 'Zagreb', 'NK', 408),
            ('Nenad Zaninović', 'Zagreb', 'NK', 432),
        ]},
    ], 'winner': 'Drago Previšić'},
    55: {'name': 'Zagreb - Maksimir I', 'rounds': [
        {'registered': 14607, 'cast': 11340, 'invalid': 246, 'candidates': [
            ('Slavko Bevanda', 'Zagreb', 'HDZ', 6013),
            ('Zdenko Mahmei', 'Zagreb', 'SKH-SDP', 2233),
            ('Tomislav Mraz', 'Zagreb', 'NK', 423),
            ('Milan Rukavina', 'Zagreb', 'NK', 494),
            ('Zvonko Štetić', 'Zagreb', 'HKDS,KNS', 1364),
            ('Dragutin Štiglić', 'Zagreb', 'NK', 566),
        ]},
    ], 'winner': 'Slavko Bevanda'},
    56: {'name': 'Zagreb - Maksimir II', 'rounds': [
        {'registered': 8223, 'cast': 6082, 'invalid': 87, 'candidates': [
            ('Stjepan Bačić', 'Zagreb', 'NK', 188),
            ('Dr Velimir Borovečki', 'Zagreb', 'NK', 160),
            ('Mr Nikica Car', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 598),
            ('Dr Frane Golem', 'Zagreb', 'HDZ', 2676),
            ('Dr Andrija Hebrang', 'Zagreb', 'NK', 366),
            ('Dr Vlado Jukić', 'Sesvete', 'NK', 77),
            ('Dr Petar Juzbašić', 'Zagreb', 'SKH-SDP', 1237),
            ('Dr Milivoj Kačić', 'Zagreb', 'NK', 134),
            ('Dr Miljenko Primorac', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 415),
            ('Dr Dušan Sabolović', 'Zagreb', 'NK', 143),
        ]},
        {'registered': 8202, 'cast': 5229, 'invalid': 72, 'candidates': [
            ('Dr Frane Golem', 'Zagreb', 'HDZ', 2862),
            ('Dr Petar Juzbašić', 'Zagreb', 'SKH-SDP', 1371),
            ('Mr Nikica Car', 'Zagreb', 'HSLS,SDSH,HKDS,HSS,KNS', 924),
        ]},
    ], 'winner': 'Dr Frane Golem'},
    57: {'name': 'Zagreb - Medveščak I', 'rounds': [
        {'registered': 9320, 'cast': 6684, 'invalid': 202, 'candidates': [
            ('Vera Jukić', 'Zagreb', 'NK', 634),
            ('Stipan Jurčević', 'Split', 'NK', 201),
            ('Franjo Mraz', 'Zagreb', 'NK', 326),
            ('Boris Oremović', 'Zagreb', 'NK', 313),
            ('Branko Požnjak', 'Zagreb', 'HDZ', 3127),
            ('Dušan Rapaić', 'Zagreb', 'NK', 619),
            ('Josip Sečen', 'Zagreb', 'NK', 776),
            ('Marijan Šolić', 'Zagreb', 'NK', 486),
        ]},
        {'registered': 8178, 'cast': 5357, 'invalid': 125, 'candidates': [
            ('Branko Požnjak', 'Zagreb', 'HDZ', 2769),
            ('Josip Sečen', 'Zagreb', 'NK', 1024),
            ('Vera Jukić', 'Zagreb', 'NK', 445),
            ('Dušan Rapaić', 'Zagreb', 'NK', 534),
            ('Marijan Šolić', 'Zagreb', 'NK', 460),
        ]},
    ], 'winner': 'Branko Požnjak'},
    58: {'name': 'Zagreb - Medveščak II', 'rounds': [
        {'registered': 5892, 'cast': 4035, 'invalid': 549, 'candidates': [
            ('Jure Nikulac', 'Zagreb', 'NK', 1761),
            ('Mladen Siketić', 'Zagreb', 'NK', 1725),
        ]},
        {'registered': 5845, 'cast': 3614, 'invalid': 489, 'candidates': [
            ('Jure Nikulac', 'Zagreb', 'NK', 1491),
            ('Mladen Siketić', 'Zagreb', 'NK', 1634),
        ]},
    ], 'winner': 'Mladen Siketić'},
    59: {'name': 'Zagreb - Medveščak III', 'rounds': [
        {'registered': 6087, 'cast': 4635, 'invalid': 80, 'candidates': [
            ('Boris Bernasek', 'Zagreb', 'NK', 241),
            ('Petir Jelaska', 'Zagreb', 'SKH-SDP', 966),
            ('Stjepan Kralj', 'Zagreb', 'NK', 309),
            ('Mladen Šutalo', 'Zagreb', 'HDZ', 2873),
            ('Josip Trogrlić', 'Zagreb', 'NK', 166),
        ]},
    ], 'winner': 'Mladen Šutalo'},
    60: {'name': 'Zagreb - Medveščak IV', 'rounds': [
        {'registered': 17872, 'cast': 14324, 'invalid': 459, 'candidates': [
            ('Miroslav Bolanča', 'Zagreb', 'NK', 998),
            ('Marijan Đerek', 'Zagreb', 'HDS,KNS', 2942),
            ('Ivan Gabrilo', 'Zagreb', 'NK', 362),
            ('Martin Katičić', 'Zagreb', 'NK', 702),
            ('Mate Ljubičić', 'Zagreb', 'NK', 511),
            ('Nediljko Matić', 'Zagreb', 'HDZ', 4938),
            ('Vlatko Mileta', 'Zagreb', 'NK', 383),
            ('Zvonko-Ivica Miljak', 'Zagreb', 'NK', 790),
            ('Stjepan-Stipe Orešković', 'Zagreb', 'NK', 377),
            ('Damir Perišin', 'Zagreb', 'NK', 669),
            ('Krunoslav Pišk', 'Zagreb', 'NK', 677),
            ('Dubravko Tadić', 'Zagreb', 'NK', 385),
        ]},
        {'registered': 17453, 'cast': 11968, 'invalid': 1877, 'candidates': [
            ('Nediljko Matić', 'Zagreb', 'HDZ', 5850),
            ('Marijan Đerek', 'Zagreb', 'HDS', 4241),
        ]},
    ], 'winner': 'Nediljko Matić'},
    61: {'name': 'Zagreb - Novi Zagreb I', 'rounds': [
        {'registered': 6977, 'cast': 4388, 'invalid': 208, 'candidates': [
            ('Srećko Penezić', 'Zagreb', 'HDZ', 3030),
            ('Ante Peša', 'Zagreb', 'NK', 1149),
        ]},
    ], 'winner': 'Srećko Penezić'},
    62: {'name': 'Zagreb - Novi Zagreb II', 'rounds': [
        {'registered': 13370, 'cast': 9699, 'invalid': 135, 'candidates': [
            ('Damir Dasović', 'Zagreb', 'HDZ', 4474),
            ('Ivan Denačić', 'Zagreb', 'NK', 282),
            ('Milan Desnica', 'Zagreb', 'NK', 218),
            ('Joso Ivanda', 'Zagreb', 'SKH-SDP', 1966),
            ('Dr Josip Klarica', 'Zagreb', 'NK', 339),
            ('Ante Ledić', 'Zagreb', 'NK', 576),
            ('Josip Martinec', 'Zagreb', 'NK', 155),
            ('Miron Nevistić', 'Zagreb', 'NK', 113),
            ('Milan Rogić', 'Klinča Selo', 'NK', 196),
            ('Kruno Zakarija', 'Zagreb', 'HSLS,KNS', 1229),
        ]},
        {'registered': 13345, 'cast': 7614, 'invalid': 100, 'candidates': [
            ('Damir Dasović', 'Zagreb', 'HDZ', 4036),
            ('Joso Ivanda', 'Zagreb', 'SKH-SDP', 2190),
            ('Kruno Zakarija', 'Zagreb', 'HSLS,KNS', 1288),
        ]},
    ], 'winner': 'Damir Dasović'},
    63: {'name': 'Zagreb - Peščenica I', 'rounds': [
        {'registered': 15147, 'cast': 11254, 'invalid': 443, 'candidates': [
            ('Rajko Dumančić', 'Zagreb', 'NK', 731),
            ('Vedran Konjevod', 'Zagreb', 'HDZ', 5821),
            ('Krešimir Mikoličić', 'Zagreb', 'NK', 367),
            ('Marko Petrinović', 'Zagreb', 'HSLS,KNS', 984),
            ('Mirko Pribanić', 'Zagreb', 'NK', 429),
            ('Branko Sladetić', 'Zagreb', 'NK', 209),
            ('Stjepan Sučić', 'Zagreb', 'NK', 367),
            ('Stjepan Utrobičić', 'Zagreb', 'HDS,KNS', 1063),
            ('Antun Velicki', 'Zagreb', 'NK', 395),
            ('Božidar Žerjav', 'Zagreb', 'NK', 445),
        ]},
    ], 'winner': 'Vedran Konjevod'},
    64: {'name': 'Zagreb - Peščenica II', 'rounds': [
        {'registered': 12605, 'cast': 9281, 'invalid': 229, 'candidates': [
            ('Vjekoslav Boban', 'Zagreb', 'SKH-SDP', 2264),
            ('Zlatko Brzić', 'Zagreb', 'NK', 277),
            ('Juraj Glavinić', 'Zagreb', 'NK', 123),
            ('Josip Gospodarić', 'Zagreb', 'NK', 243),
            ('Marijan Jurić', 'Novaki', 'HDZ', 4843),
            ('Stanko Perica', 'Zagreb', 'NK', 219),
            ('Andrija Vrdoljak', 'Zagreb', 'HKDS,KNS', 1083),
        ]},
    ], 'winner': 'Marijan Jurić'},
    65: {'name': 'Zagreb - Peščenica III', 'rounds': [
        {'registered': 11908, 'cast': 6752, 'invalid': 120, 'candidates': [
            ('Miljenko Cvjetko', 'Zagreb', 'HDZ', 3996),
            ('Milan Hrnjak', 'Zagreb', 'NK', 940),
            ('Petar Ivanović', 'Zagreb', 'SKH-SDP', 1696),
        ]},
    ], 'winner': 'Miljenko Cvjetko'},
    66: {'name': 'Zagreb - Peščenica IV', 'rounds': [
        {'registered': 10931, 'cast': 8322, 'invalid': 195, 'candidates': [
            ('Davorin Kobak', 'Zagreb', 'NK', 580),
            ('Anđelko Krašić', 'Zagreb', 'HDZ', 4862),
            ('Vitomir Ledić', 'Zagreb', 'NK', 324),
            ('Ivan Stepanić', 'Zagreb', 'NK', 717),
            ('Milan Vojvodić', 'Zagreb', 'SKH-SDP', 1644),
        ]},
    ], 'winner': 'Anđelko Krašić'},
    67: {'name': 'Zagreb - Peščenica V', 'rounds': [
        {'registered': 7906, 'cast': 6172, 'invalid': 109, 'candidates': [
            ('Joso Bičanić', 'Zagreb', 'NK', 227),
            ('Franjo Dubrović', 'Zagreb', 'HSS,KNS', 378),
            ('Stjepan Klenkar', 'Zagreb', 'NK', 150),
            ('Petar Radić', 'Zagreb', 'PZK', 136),
            ('Branko Sabljak', 'Zagreb', 'HDZ', 2834),
            ('Nenad Starc', 'Zagreb', 'SKH-SDP', 1478),
            ('Zvonimir Šain', 'Zagreb', 'HSLS,KNS', 860),
        ]},
        {'registered': 7733, 'cast': 5402, 'invalid': 74, 'candidates': [
            ('Branko Sabljak', 'Zagreb', 'HDZ', 2756),
            ('Nenad Starc', 'Zagreb', 'SKH-SDP', 1483),
            ('Zvonimir Šain', 'Zagreb', 'HSLS,KNS', 1089),
        ]},
    ], 'winner': 'Branko Sabljak'},
    68: {'name': 'Zagreb - Samobor', 'rounds': [
        {'registered': 10904, 'cast': 8234, 'invalid': 206, 'candidates': [
            ('Frane Čačić Arapović', 'Samobor', 'HDZ', 5064),
            ('Franjo Lamot', 'Samobor', 'NK', 1546),
            ('Anđelko Pavić', 'Zagreb', 'SSH', 1383),
        ]},
    ], 'winner': 'Frane Čačić Arapović'},
    69: {'name': 'Zagreb - Sesvete', 'rounds': [
        {'registered': 6078, 'cast': 4667, 'invalid': 93, 'candidates': [
            ('Jakov Alagusić', 'Zagreb', 'NK', 77),
            ('Mihovil Grabovac', 'Sesvete', 'NK', 303),
            ('Slavko Kulić', 'Zagreb', 'SKH-SDP', 458),
            ('Ante Kutle', 'Sesvete', 'HDZ', 2464),
            ('Ivica Lepušić', 'Zagreb', 'SKH-SDP', 478),
            ('Zvonko Novak', 'Zagreb', 'NK', 177),
            ('Igor Stažić', 'Dubrava', 'HSLS,KNS', 428),
            ('Mladen Vinković', 'Zagreb', 'NK', 189),
        ]},
    ], 'winner': 'Ante Kutle'},
    70: {'name': 'Zagreb - Susedgrad', 'rounds': [
        {'registered': 16821, 'cast': 12682, 'invalid': 293, 'candidates': [
            ('Ante Brković', 'Zagreb', 'NK', 283),
            ('Franjo Cvetnić', 'Zagreb', 'NK', 198),
            ('Bernard Grbić', 'Zagreb', 'HDZ', 7050),
            ('Ljubica Herak', 'Zagreb', 'SKH-SDP', 2346),
            ('Ivo Jelenčić', 'Zagreb', 'HSS,KNS', 1284),
            ('Slavko Novokmet', 'Zagreb', 'NK', 233),
            ('Ladislav Prežigalo', 'Zagreb', 'NK', 233),
            ('Branko Rajilić', 'Zagreb', 'NK', 171),
            ('Željko Stubičan', 'Zagreb', 'NK', 240),
            ('Franjo Šušnjar', 'Zagreb', 'NK', 336),
        ]},
    ], 'winner': 'Bernard Grbić'},
    71: {'name': 'Zagreb - Trešnjevka I', 'rounds': [
        {'registered': 12034, 'cast': 9912, 'invalid': 225, 'candidates': [
            ('Dragutin Barić', 'Zagreb', 'HDZ', 5985),
            ('Domagoj Kero', 'Zagreb', 'NK', 525),
            ('Ladislav Novačić', 'Zagreb', 'NK', 563),
            ('Ranko Pecotić', 'Zagreb', 'SKH-SDP', 2614),
        ]},
    ], 'winner': 'Dragutin Barić'},
    72: {'name': 'Zagreb - Trešnjevka II', 'rounds': [
        {'registered': 6696, 'cast': 5184, 'invalid': 130, 'candidates': [
            ('Joso Biondić', 'Zagreb', 'SKH-SDP', 1304),
            ('Zorislav Mihaljević', 'Zagreb', 'NK', 340),
            ('Miroslav Popović', 'Zagreb', 'NK', 210),
            ('Emilija Rajić', 'Zagreb', 'HDZ', 3200),
        ]},
    ], 'winner': 'Emilija Rajić'},
    73: {'name': 'Zagreb - Trešnjevka III', 'rounds': [
        {'registered': 7369, 'cast': 4513, 'invalid': 225, 'candidates': [
            ('Željko Gudan', 'Zagreb', 'HDZ', 2346),
            ('Juraj Jergović', 'Zagreb', 'SKH-SDP', 1148),
            ('Tomislav Madžar', 'Zagreb', 'NK', 464),
            ('Stanko Tratnik', 'Zagreb', 'SSH', 330),
        ]},
        {'registered': 8414, 'cast': 4003, 'invalid': 153, 'candidates': [
            ('Željko Gudan', 'Zagreb', 'HDZ', 2085),
            ('Juraj Jergović', 'Zagreb', 'SKH-SDP', 1188),
            ('Tomislav Madžar', 'Zagreb', 'NK', 368),
            ('Stanko Tratnik', 'Zagreb', 'SSH', 209),
        ]},
    ], 'winner': 'Željko Gudan'},
    74: {'name': 'Zagreb - Trešnjevka IV', 'rounds': [
        {'registered': 10403, 'cast': 7173, 'invalid': 1339, 'candidates': [
            ('Miodrag Petrović', 'Zagreb', 'NK', 2815),
            ('Janko Radić', 'Zagreb', 'SKH-SDP', 3019),
        ]},
        {'registered': 10368, 'cast': 5912, 'invalid': 1380, 'candidates': [
            ('Janko Radić', 'Zagreb', 'SKH-SDP', 2502),
            ('Miodrag Petrović', 'Zagreb', 'NK', 2030),
        ]},
    ], 'winner': 'Janko Radić'},
    75: {'name': 'Zagreb - Trešnjevka V', 'rounds': [
        {'registered': 13739, 'cast': 10658, 'invalid': 262, 'candidates': [
            ('Mirko Crnojević', 'Zagreb', 'SSH', 361),
            ('Ivan Hren', 'Zagreb', 'HDZ', 4679),
            ('Branko Jakopec', 'Zagreb', 'NK', 159),
            ('Vesna Kanižaj', 'Zagreb', 'NK', 243),
            ('Marija Lončar-Matijašević', 'Zagreb', 'NK', 156),
            ('Branko Molan', 'Zagreb', 'SKH-SDP', 2174),
            ('Julijus Pevalek', 'Zagreb', 'NK', 720),
            ('Dr Valentin Puževski', 'Križevci', 'NK', 248),
            ('Vlado Sužnjević', 'Zagreb', 'SDSH,KNS', 1229),
            ('Dr Petar Tocilj', 'Zagreb', 'NK', 427),
        ]},
        {'registered': 13966, 'cast': 9315, 'invalid': 277, 'candidates': [
            ('Ivan Hren', 'Zagreb', 'HDZ', 5589),
            ('Branko Molan', 'Zagreb', 'SKH-SDP', 3449),
        ]},
    ], 'winner': 'Ivan Hren'},
    76: {'name': 'Zagreb - Trnje I', 'rounds': [
        {'registered': 14890, 'cast': 10347, 'invalid': 336, 'candidates': [
            ('Branimir Bilić', 'Zagreb', 'NK', 491),
            ('Velimir Ivanko', 'Zagreb', 'HDZ', 3019),
            ('Ivica Kriletić', 'Zagreb', 'NK', 351),
            ('Miroslav Lilić', 'Zagreb', 'NK', 1373),
            ('Stipan Marović', 'Zagreb', 'NK', 398),
            ('Nikola Petrović', 'Zagreb', 'NK', 289),
            ('Marin Pivčević', 'Zagreb', 'HSLS,KNS', 1371),
            ('Vedran Sinovčić', 'Zagreb', 'NK', 228),
            ('Slaven Srzić', 'Zagreb', 'NK', 290),
            ('Katarina Šošić', 'Zagreb', 'HDZ', 2201),
        ]},
        {'registered': 15855, 'cast': 8508, 'invalid': 492, 'candidates': [
            ('Velimir Ivanko', 'Zagreb', 'HDZ', 4719),
            ('Marin Pivčević', 'Zagreb', 'HSLS,KNS', 3297),
        ]},
    ], 'winner': 'Velimir Ivanko'},
    77: {'name': 'Zagreb - Trnje II', 'rounds': [
        {'registered': 10332, 'cast': 7296, 'invalid': 260, 'candidates': [
            ('Petar Fleković', 'Zagreb', 'NK', 1051),
            ('Goran Granić', 'Zagreb', 'NK', 512),
            ('Marijan Kallay', 'Zagreb', 'NK', 339),
            ('Jerko Latković', 'Zagreb', 'HSLS,KNS', 1096),
            ('Slavomir Madjor', 'Zagreb', 'NK', 236),
            ('Nino Vedriš', 'Zagreb', 'HDZ', 3802),
        ]},
    ], 'winner': 'Nino Vedriš'},
    78: {'name': 'Zagreb - Trnje III', 'rounds': [
        {'registered': 7327, 'cast': 5060, 'invalid': 563, 'candidates': [
            ('Stanko Kovač', 'Zagreb', 'NK', 2452),
            ('Ivica Rilje', 'Zagreb', 'NK', 2045),
        ]},
        {'registered': 7192, 'cast': 4368, 'invalid': 669, 'candidates': [
            ('Stanko Kovač', 'Zagreb', 'NK', 2005),
            ('Ivica Rilje', 'Zagreb', 'NK', 1694),
        ]},
    ], 'winner': 'Stanko Kovač'},
    79: {'name': 'Zagreb - Trnje IV', 'rounds': [
        {'registered': 9597, 'cast': 6472, 'invalid': 877, 'candidates': [
            ('Marijan Bokulić', 'Zagreb', 'NK', 1002),
            ('Walter Dragšić', 'Zagreb', 'NK', 360),
            ('Jadranko Husarić', 'Dugo Selo', 'NK', 405),
            ('Stjepan Križan', 'Zagreb', 'NK', 930),
            ('Ivan Matija', 'Zagreb', 'SKH-SDP', 989),
            ('Marko Runac', 'Samobor', 'NK', 440),
            ('Miljenko Sunić', 'Zagreb', 'NK', 266),
            ('Mijo Trgovčević', 'Zagreb', 'NK', 472),
            ('Milan Vranešević', 'Zagreb', 'SKH-SDP', 731),
        ]},
        {'registered': 9552, 'cast': 5594, 'invalid': 826, 'candidates': [
            ('Marijan Bokulić', 'Zagreb', 'NK', 1627),
            ('Ivan Matija', 'Zagreb', 'SKH-SDP', 1731),
            ('Stjepan Križan', 'Zagreb', 'NK', 1410),
        ]},
    ], 'winner': 'Ivan Matija'},
    80: {'name': 'Zagreb - Trnje V', 'rounds': [
        {'registered': 11341, 'cast': 9510, 'invalid': 167, 'candidates': [
            ('Nikola Cavrić', 'Zagreb', 'NK', 137),
            ('Jovo Cvjetičanin', 'Zagreb', 'NK', 289),
            ('Nedjeljka Despot', 'Zagreb', 'NK', 167),
            ('Mirko Hlupić', 'Zagreb', 'SKH-SDP', 1357),
            ('Ivica Ihas', 'Zagreb', 'HSLS,SDSH,HDS,HKDS,HSS,KNS', 1828),
            ('Branko Jordanić', 'Zagreb', 'NK', 151),
            ('Dr Mr Miroslav Kirinčić', 'Zagreb', 'SSH', 374),
            ('Edo Kosović', 'Zagreb', 'SKH-SDP', 1467),
            ('Ivica Kostelac', 'Zagreb', 'NK', 148),
            ('Zoran Stare', 'Zagreb', 'HDZ', 2774),
            ('Božo Vranješ', 'Zagreb', 'NK', 171),
            ('Joso Zdunić', 'Zagreb', 'NK', 226),
        ]},
        {'registered': 11554, 'cast': 8531, 'invalid': 125, 'candidates': [
            ('Zoran Stare', 'Zagreb', 'HDZ', 2850),
            ('Ivica Ihas', 'Zagreb', 'HSLS,SDSH,HDS,HKDS,HSS,KNS', 1922),
            ('Edo Kosović', 'Zagreb', 'SKH-SDP', 3634),
        ]},
    ], 'winner': 'Edo Kosović'},
    81: {'name': 'Zagreb - Velika Gorica', 'rounds': [
        {'registered': 10307, 'cast': 8267, 'invalid': 323, 'candidates': [
            ('Dragan Blagović', 'Zagreb', 'NK', 360),
            ('Miro Dražić', 'Novi Zagreb', 'NK', 190),
            ('Stjepan Havidić', 'Velika Gorica', 'NK', 431),
            ('Zlatko Kožar', 'Zagreb', 'NK', 220),
            ('Dragutin Popovčić', 'Velika Gorica', 'SKH-SDP', 1861),
            ('Marijan Prgomet', 'Velika Gorica', 'NK', 387),
            ('Jakov Vukelić', 'Velika Gorica', 'NK', 252),
            ('Josip Zagorac', 'Kravarsko', 'HDZ', 4243),
        ]},
    ], 'winner': 'Josip Zagorac'},
    82: {'name': 'Zagreb - Zaprešić', 'rounds': [
        {'registered': 8064, 'cast': 6277, 'invalid': 787, 'candidates': [
            ('Vladimir Dragičević', 'Zagreb', 'NK', 758),
            ('Antun Kadić', 'Zagreb', 'NK', 832),
            ('Zlatko Skledar', 'Zaprešić', 'NK', 2202),
            ('Dr Tomislav Škunca', 'Prigorje', 'SKH-SDP', 1698),
        ]},
        {'registered': 8037, 'cast': 5196, 'invalid': 738, 'candidates': [
            ('Zlatko Skledar', 'Zaprešić', 'NK', 2114),
            ('Dr Tomislav Škunca', 'Prigorje', 'SKH-SDP', 1519),
            ('Antun Kadić', 'Zagreb', 'NK', 550),
            ('Vladimir Dragičević', 'Zagreb', 'NK', 275),
        ]},
    ], 'winner': 'Zlatko Skledar'},
    84: {'name': 'Zagreb II', 'rounds': [
        {'registered': 8944, 'cast': 7231, 'invalid': 240, 'candidates': [
            ('Mile Glumac', 'Zagreb', 'NK', 2866),
            ('Vinko Mrkonja', 'Zagreb', 'NK', 1516),
            ('Djuro Vrandečić', 'Zagreb', 'NK', 2577),
        ]},
        {'registered': 8954, 'cast': 6449, 'invalid': 260, 'candidates': [
            ('Mile Glumac', 'Zagreb', 'NK', 3025),
            ('Djuro Vrandečić', 'Zagreb', 'NK', 2004),
            ('Vinko Mrkonja', 'Zagreb', 'NK', 1160),
        ]},
    ], 'winner': 'Mile Glumac'},
    85: {'name': 'Sisak I', 'rounds': [
        {'registered': 10855, 'cast': 8658, 'invalid': 677, 'candidates': [
            ('Nebojša Jovanović', 'Sisak', 'SSOH', 940),
            ('Miloš Petrović', 'Zagreb', 'SKH-SDP', 6213),
            ('Dušan Rakić', 'Sisak', 'NK', 828),
        ]},
    ], 'winner': 'Miloš Petrović'},
    86: {'name': 'Sisak II', 'rounds': [
        {'registered': 8323, 'cast': 6743, 'invalid': 281, 'candidates': [
            ('Ivan Medarac', 'Sisak', 'SKH-SDP', 3519),
            ('Darko Pavlak', 'Sunja', 'SDSH,KNS', 1906),
            ('Boško Subotić', 'Sisak', 'NK', 1037),
        ]},
    ], 'winner': 'Ivan Medarac'},
    87: {'name': 'Sisak III', 'rounds': [
        {'registered': 12595, 'cast': 10226, 'invalid': 172, 'candidates': [
            ('Vjekoslav Blažević', 'Sisak', 'HDZ', 3400),
            ('Stjepan Bujas', 'Sisak', 'SKH-SDP', 5861),
            ('Marica Kasaić-Božić', 'Sisak', 'NK', 396),
            ('Josip Obrad', 'Sisak', 'NK', 397),
        ]},
    ], 'winner': 'Stjepan Bujas'},
    88: {'name': 'Petrinja', 'rounds': [
        {'registered': 14762, 'cast': 12294, 'invalid': 317, 'candidates': [
            ('Borislav Meandžija', 'Glina', 'SKH-SDP', 2980),
            ('Davor Salopek', 'Petrinja', 'HSLS,KNS', 2236),
            ('Đuro Stojić', 'Glina', 'NK', 932),
            ('Jovo Vukobrat', 'Petrinja', 'SKH-SDP,SSH', 5716),
        ]},
        {'registered': 14579, 'cast': 11204, 'invalid': 257, 'candidates': [
            ('Jovo Vukobrat', 'Petrinja', 'SKH-SDP,SSH', 8471),
            ('Davor Salopek', 'Petrinja', 'HSLS,KNS', 2476),
        ]},
    ], 'winner': 'Jovo Vukobrat'},
    89: {'name': 'Kostajnica', 'rounds': [
        {'registered': 13676, 'cast': 10692, 'invalid': 387, 'candidates': [
            ('Ivan Berić', 'Novska', 'HDZ,HSLS', 2370),
            ('Grga Ivezić', 'Novska', 'NK', 372),
            ('Marijan Juran', 'Lipovljani', 'NK', 361),
            ('Josip Krajči', 'Lipovljani', 'NK', 579),
            ('Mladen Murić', 'Kostajnica', 'NK', 1974),
            ('Branko Štengl', 'Novska', 'NK', 230),
            ('Dušan Trivunčić', 'Jasenovac', 'SKH-SDP', 4419),
        ]},
        {'registered': 13600, 'cast': 9765, 'invalid': 280, 'candidates': [
            ('Dušan Trivunčić', 'Jasenovac', 'SKH-SDP', 5627),
            ('Ivan Berić', 'Novska', 'HDZ,HSLS', 2858),
        ]},
    ], 'winner': 'Dušan Trivunčić'},
    90: {'name': 'Karlovac I', 'rounds': [
        {'registered': 10006, 'cast': 7932, 'invalid': 181, 'candidates': [
            ('Ivica Car', 'Karlovac', 'SKH-SDP', 2455),
            ('Željko Mažuran', 'Karlovac', 'NK', 442),
            ('Ivan Novosel', 'Karlovac', 'HDZ', 3612),
            ('Ivan Rast', 'Karlovac', 'HDS,KNS', 772),
            ('Đuro Rebić', 'Karlovac', 'NK', 470),
        ]},
        {'registered': 9293, 'cast': 7203, 'invalid': 151, 'candidates': [
            ('Ivan Novosel', 'Karlovac', 'HDZ', 3825),
            ('Ivica Car', 'Karlovac', 'SKH-SDP', 2726),
            ('Ivan Rast', 'Karlovac', 'HDS', 501),
        ]},
    ], 'winner': 'Ivan Novosel'},
    91: {'name': 'Karlovac II', 'rounds': [
        {'registered': 9596, 'cast': 7732, 'invalid': 583, 'candidates': [
            ('Ivan Bedeniković', 'Karlovac', 'NK', None),
            ('Dragutin Bešenić', 'Karlovac', 'NK', None),
            ('Nikola Mačešić', 'Karlovac', 'SKH-SDP', None),
            ('Nenad Zlonoga', 'Karlovac', 'SSOH', None),
        ]},
        {'registered': 10246, 'cast': 7686, 'invalid': 681, 'candidates': [
            ('Nikola Mačešić', 'Karlovac', 'SKH-SDP', None),
            ('Ivan Bedeniković', 'Karlovac', 'NK', None),
            ('Nenad Zlonoga', 'Karlovac', 'SSOH', None),
            ('Dragutin Bešenić', 'Karlovac', 'NK', None),
        ]},
    ], 'winner': 'Nikola Mačešić'},
    92: {'name': 'Karlovac III', 'rounds': [
        {'registered': 13509, 'cast': 10766, 'invalid': 709, 'candidates': [
            ('Vitomir Majoli', 'Karlovac', 'NK', 2201),
            ('Boris Sušanj', 'Karlovac', 'SKH-SDP', 1629),
            ('Božidar Tyrolt', 'Karlovac', 'SKH-SDP', 3518),
            ('Marko Vuković', 'Karlovac', 'NK', 1210),
            ('Vinko Žigo', 'Karlovac', 'SKH-SDP', 1499),
        ]},
        {'registered': 13458, 'cast': 9504, 'invalid': 785, 'candidates': [
            ('Božidar Tyrolt', 'Karlovac', 'SKH-SDP', 4465),
            ('Vitomir Majoli', 'Karlovac', 'NK', 1830),
            ('Boris Sušanj', 'Karlovac', 'SKH-SDP', 1283),
            ('Marko Vuković', 'Karlovac', 'NK', 1136),
        ]},
    ], 'winner': 'Božidar Tyrolt'},
    93: {'name': 'Duga Resa', 'rounds': [
        {'registered': 6526, 'cast': 5397, 'invalid': 329, 'candidates': [
            ('Vlado Jakšić', 'Duga Resa', 'HDS,KNS', 3303),
            ('Andrija Prus', 'Duga Resa', 'SKH-SDP', 1052),
            ('Ivan Saftić', 'Karlovac', 'NK', 713),
        ]},
    ], 'winner': 'Vlado Jakšić'},
    94: {'name': 'Slunj', 'rounds': [
        {'registered': 9495, 'cast': 8121, 'invalid': 700, 'candidates': [
            ('Milorad Bekić', 'Topusko', 'SKH-SDP,SSH', 2828),
            ('Bogdan Bojanić', 'Vrginmost', 'NK', 469),
            ('Josip Ivanušec', 'Ozalj', 'NK', 1271),
            ('Dušan Šaša', 'Vrginmost', 'NK', 561),
            ('Mile Turkalj', 'Slunj', 'SKH-SDP', 1497),
            ('Ivan Žabčić', 'Ozalj', 'SKH-SDP', 795),
        ]},
        {'registered': 9150, 'cast': 7301, 'invalid': 1186, 'candidates': [
            ('Milorad Bekić', 'Topusko', 'SKH-SDP,SSH', 3835),
            ('Mile Turkalj', 'Slunj', 'SKH-SDP', 2280),
        ]},
    ], 'winner': 'Milorad Bekić'},
    95: {'name': 'Otočac', 'rounds': [
        {'registered': 11332, 'cast': 9369, 'invalid': 472, 'candidates': [
            ('Juro Cubel', 'Otočac', 'SKH-SDP,SSH', 2244),
            ('Ivan Furlan', 'Prozor', 'HDZ', 2436),
            ('Anđelko Kružičević', 'Plitvička Jezera', 'SKH-SDP', 4217),
        ]},
        {'registered': 11263, 'cast': 8722, 'invalid': 363, 'candidates': [
            ('Anđelko Kružičević', 'Plitvička Jezera', 'SKH-SDP', 5776),
            ('Ivan Furlan', 'Prozor', 'HDZ', 2582),
        ]},
    ], 'winner': 'Anđelko Kružičević'},
    96: {'name': 'Gospić', 'rounds': [
        {'registered': 10371, 'cast': 8368, 'invalid': 459, 'candidates': [
            ('Miloš Begović', 'Gospić', 'NK', 454),
            ('Ankica Blažević', 'Gospić', 'NK', 2029),
            ('Branko Čuić', 'Gospić', 'NK', 156),
            ('Milan Dešić', 'Gospić', 'NK', 270),
            ('Đuro Kricković', 'Lički Osik', 'NK', 935),
            ('Branka Kuprešanin', 'Gračac', 'SKH-SDP', 3146),
            ('Milan Peić', 'Gospić', 'NK', 312),
            ('Branko Pupavac', 'Gospić', 'NK', 348),
            ('Branka Stanisavljević', 'Gospić', 'NK', 258),
        ]},
        {'registered': 10366, 'cast': 7627, 'invalid': 312, 'candidates': [
            ('Branka Kuprešanin', 'Gračac', 'SKH-SDP', 3977),
            ('Ankica Blažević', 'Gospić', 'NK', 2502),
            ('Đuro Kricković', 'Lički Osik', 'NK', 836),
        ]},
    ], 'winner': 'Branka Kuprešanin'},
    97: {'name': 'Ogulin', 'rounds': [
        {'registered': 11778, 'cast': 9587, 'invalid': 304, 'candidates': [
            ('Bosiljka Dolušić', 'Ogulin', 'NK', 987),
            ('Željko Denić', 'Plaški', 'NK', 1011),
            ('Tomislav Heski', 'Vrbovsko', 'NK', 652),
            ('Đorđe Matić', 'Vrbovsko', 'NK', 345),
            ('Miloš Vujnović', 'Ogulin', 'SKH-SDP', 2642),
            ('Josip Zubčić', 'Ogulin', 'HDZ', 3782),
        ]},
        {'registered': 11807, 'cast': 9083, 'invalid': 103, 'candidates': [
            ('Josip Zubčić', 'Ogulin', 'HDZ', 4086),
            ('Miloš Vujnović', 'Ogulin', 'SKH-SDP', 4882),
        ]},
    ], 'winner': 'Miloš Vujnović'},
    98: {'name': 'Delnice', 'rounds': [
        {'registered': 8254, 'cast': 6782, 'invalid': 439, 'candidates': [
            ('Marjan Majnarić', 'Delnice', 'NK', 1820),
            ('Sigfrid Nikola', 'Delnice', 'SKH-SDP', 2648),
            ('Božidar Pleše', 'Lokve', 'NK', 1857),
        ]},
        {'registered': 8235, 'cast': 6300, 'invalid': 449, 'candidates': [
            ('Sigfrid Nikola', 'Delnice', 'SKH-SDP', 2777),
            ('Božidar Pleše', 'Lokve', 'NK', 1743),
            ('Marjan Majnarić', 'Delnice', 'NK', 1331),
        ]},
    ], 'winner': 'Sigfrid Nikola'},
    99: {'name': 'Rijeka I', 'rounds': [
        {'registered': 12076, 'cast': 9314, 'invalid': 317, 'candidates': [
            ('Josip Anić', 'Rijeka', 'NK', 585),
            ('Petar Ečimović', 'Rijeka', 'HDS,KNS', 1502),
            ('Milutin Maračić', 'Rijeka', 'HDZ', 2449),
            ('Mladen Škorić', 'Rijeka', 'SKH-SDP', 2465),
            ('Branko Škrobonja', 'Rijeka', 'SKH-SDP', 1981),
        ]},
        {'registered': 11560, 'cast': 8674, 'invalid': 255, 'candidates': [
            ('Mladen Škorić', 'Rijeka', 'SKH-SDP', 4780),
            ('Milutin Maračić', 'Rijeka', 'HDZ', 3639),
        ]},
    ], 'winner': 'Mladen Škorić'},
    100: {'name': 'Rijeka II', 'rounds': [
        {'registered': 9233, 'cast': 7866, 'invalid': 249, 'candidates': [
            ('Mirko Došen', 'Kastav', 'HDS,SDSH,HSLS,HKDS,HSS,KNS', 1324),
            ('Milan Janjanin', 'Rijeka', 'NK', 668),
            ('Damjan Prtenjača', 'Rijeka', 'HDZ', 2450),
            ('Damir Vrhovnik', 'Rijeka', 'SKH-SDP', 3175),
        ]},
        {'registered': 9089, 'cast': 7372, 'invalid': 221, 'candidates': [
            ('Damir Vrhovnik', 'Rijeka', 'SKH-SDP', 3878),
            ('Damjan Prtenjača', 'Rijeka', 'HDZ', 3273),
        ]},
    ], 'winner': 'Damir Vrhovnik'},
    101: {'name': 'Rijeka III', 'rounds': [
        {'registered': 9688, 'cast': 6815, 'invalid': 602, 'candidates': [
            ('Ivica Franolić', 'Rijeka', 'SKH-SDP', 3470),
            ('Radomir Hinić', 'Rijeka', 'NK', 814),
            ('Marijana Perhat', 'Rijeka', 'NK', 1347),
            ('Dušan Vukmanović', 'Rijeka', 'NK', 568),
        ]},
    ], 'winner': 'Ivica Franolić'},
    102: {'name': 'Rijeka IV', 'rounds': [
        {'registered': 9386, 'cast': 5532, 'invalid': 247, 'candidates': [
            ('Ivan Kraljić', 'Rijeka', 'NK', 1052),
            ('Velimir Tolj', 'Rijeka', 'SDSH,KNS', 1854),
            ('Boris Vujašković', 'Rijeka', 'SKH-SDP', 2355),
        ]},
        {'registered': 9095, 'cast': 5151, 'invalid': 226, 'candidates': [
            ('Boris Vujašković', 'Rijeka', 'SKH-SDP', 2418),
            ('Velimir Tolj', 'Rijeka', 'SDSH,KNS', 1756),
            ('Ivan Kraljić', 'Rijeka', 'NK', 751),
        ]},
    ], 'winner': 'Boris Vujašković'},
    103: {'name': 'Rijeka V', 'rounds': [
        {'registered': 13215, 'cast': 8626, 'invalid': 176, 'candidates': [
            ('Luidino Aničić', 'Rijeka', 'NK', 539),
            ('Slavko Bilić', 'Rijeka', 'SKH-SDP', 3998),
            ('Branko Ivanović', 'Rijeka', 'NK', 421),
            ('Nikola Jović', 'Rijeka', 'HDS,KNS', 1183),
            ('Miljenko Kordić', 'Rijeka', 'HDZ', 2281),
        ]},
        {'registered': 12358, 'cast': 7516, 'invalid': 181, 'candidates': [
            ('Slavko Bilić', 'Rijeka', 'SKH-SDP', 4363),
            ('Miljenko Kordić', 'Rijeka', 'HDZ', 2972),
        ]},
    ], 'winner': 'Slavko Bilić'},
    104: {'name': 'Rijeka VI', 'rounds': [
        {'registered': 11328, 'cast': 7508, 'invalid': 558, 'candidates': [
            ('Ivan Budić', 'Lovran', 'HSLS,KNS', 2642),
            ('Zvonko Krmpotić', 'Rijeka', 'SKH-SDP', 2771),
            ('Milan Modrić', 'Rijeka', 'NK', 981),
            ('Mile Vorkapić', 'Rijeka', 'NK', 556),
        ]},
        {'registered': 11493, 'cast': 6578, 'invalid': 385, 'candidates': [
            ('Zvonko Krmpotić', 'Rijeka', 'SKH-SDP', 3020),
            ('Ivan Budić', 'Lovran', 'HSLS,KNS', 2352),
            ('Milan Modrić', 'Rijeka', 'NK', 821),
        ]},
    ], 'winner': 'Zvonko Krmpotić'},
    105: {'name': 'Rijeka VII', 'rounds': [
        {'registered': 8955, 'cast': 7272, 'invalid': 202, 'candidates': [
            ('Mr Dragan Basta', 'Rijeka', 'NK', 613),
            ('Drago Bilić', 'Rijeka', 'HDZ', 1402),
            ('Ratko Črnjak', 'Rijeka', 'NK', 264),
            ('Zrinko Hlača', 'Rijeka', 'NK', 602),
            ('Luka Lerga', 'Rijeka', 'NK', 389),
            ('Borislav Perožić', 'Rijeka', 'SKH-SDP', 2892),
            ('Mihovil Sekula', 'Rijeka', 'HDZ', 908),
        ]},
        {'registered': 8885, 'cast': 6881, 'invalid': 125, 'candidates': [
            ('Borislav Perožić', 'Rijeka', 'SKH-SDP', 3419),
            ('Drago Bilić', 'Rijeka', 'HDZ', 2546),
            ('Mr Dragan Basta', 'Rijeka', 'NK', 791),
        ]},
    ], 'winner': 'Borislav Perožić'},
    106: {'name': 'Rijeka VIII', 'rounds': [
        {'registered': 16230, 'cast': 13061, 'invalid': 243, 'candidates': [
            ('Ivan Benčić', 'Rijeka', 'HDZ', 2722),
            ('Darko Deković', 'Rijeka', 'SDSH,HSLS,HKDS,HDS,KNS', 2139),
            ('Manon Giron', 'Rijeka', 'SKH-SDP', 5974),
            ('Dr Danilo Pavešić', 'Rijeka', 'NK', 1458),
            ('Boris Ritoša', 'Rijeka', 'NK', 525),
        ]},
        {'registered': 16522, 'cast': 12341, 'invalid': 210, 'candidates': [
            ('Manon Giron', 'Rijeka', 'SKH-SDP', 6767),
            ('Ivan Benčić', 'Rijeka', 'HDZ', 3536),
            ('Dr Danilo Pavešić', 'Rijeka', 'NK', 1828),
        ]},
    ], 'winner': 'Manon Giron'},
    107: {'name': 'Rijeka IX', 'rounds': [
        {'registered': 6137, 'cast': 2806, 'invalid': 85, 'candidates': [
            ('Franjo Dujmović', 'Rijeka', 'SSOH', 545),
            ('Željko Jovanović', 'Rijeka', 'SSOH', 774),
            ('Vesna Milković', 'Rijeka', 'HDZ', 784),
            ('Mile Perić', 'Rijeka', 'HDS,KNS', 618),
        ]},
        {'registered': 7039, 'cast': 2569, 'invalid': 73, 'candidates': [
            ('Vesna Milković', 'Rijeka', 'HDZ', 970),
            ('Željko Jovanović', 'Rijeka', 'SSOH', 1056),
            ('Franjo Dujmović', 'Rijeka', 'SSOH', 470),
        ]},
    ], 'winner': 'Željko Jovanović'},
    108: {'name': 'Opatija', 'rounds': [
        {'registered': 10400, 'cast': 8368, 'invalid': 340, 'candidates': [
            ('Želimir Cvitanić', 'Opatija', 'HKDS,KNS', 3065),
            ('Šime Jagičić', 'Rijeka', 'SKH-SDP', 3082),
            ('Ivan Matulja', 'Opatija', 'NK', 1721),
        ]},
        {'registered': 10214, 'cast': 7383, 'invalid': 282, 'candidates': [
            ('Šime Jagičić', 'Rijeka', 'SKH-SDP', 3080),
            ('Želimir Cvitanić', 'Opatija', 'HKDS,KNS', 2712),
            ('Ivan Matulja', 'Opatija', 'NK', 1309),
        ]},
    ], 'winner': 'Šime Jagičić'},
    109: {'name': 'Crikvenica', 'rounds': [
        {'registered': 9957, 'cast': 8139, 'invalid': 245, 'candidates': [
            ('Srećko Juričić', 'Novi Vinodolski', 'HDS,KNS', 1344),
            ('Dr Siniša Kalanj', 'Klenovica', 'NK', 965),
            ('Jadranko Nekić', 'Senj', 'HDZ', 2748),
            ('Vera Rivoseki', 'Senj', 'SKH-SDP', 2837),
        ]},
        {'registered': 10085, 'cast': 7362, 'invalid': 177, 'candidates': [
            ('Vera Rivoseki', 'Senj', 'SKH-SDP', 3450),
            ('Jadranko Nekić', 'Senj', 'HDZ', 2804),
            ('Srećko Juričić', 'Novi Vinodolski', 'HDS', 931),
        ]},
    ], 'winner': 'Vera Rivoseki'},
    110: {'name': 'Krk', 'rounds': [
        {'registered': 13768, 'cast': 10295, 'invalid': 547, 'candidates': [
            ('Giordano Benvin', 'Mali Lošinj', 'SKH-SDP', 2563),
            ('Silvija Dijanić', 'Krk', 'SKH-SDP', 2378),
            ('Dragutin Žic', 'Punat', 'HDS,KNS', 4807),
        ]},
        {'registered': 13925, 'cast': 8865, 'invalid': 390, 'candidates': [
            ('Dragutin Žic', 'Punat', 'HDS', 4538),
            ('Giordano Benvin', 'Mali Lošinj', 'SKH-SDP', 3937),
        ]},
    ], 'winner': 'Dragutin Žic'},
    111: {'name': 'Labin', 'rounds': [
        {'registered': 10120, 'cast': 7741, 'invalid': 631, 'candidates': [
            ('Romano Černjul', 'Grbac', 'SKH-SDP', 2317),
            ('Serdo Klapčić', 'Nedešcine', 'SSH', 2182),
            ('Enco Tireli', 'Labin', 'SKH-SDP', 2611),
        ]},
        {'registered': 10190, 'cast': 6995, 'invalid': 541, 'candidates': [
            ('Enco Tireli', 'Labin', 'SKH-SDP', 2795),
            ('Romano Černjul', 'Grbac', 'SKH-SDP', 1836),
            ('Serdo Klapčić', 'Nedešcine', 'SSH', 1822),
        ]},
    ], 'winner': 'Enco Tireli'},
    112: {'name': 'Pula I', 'rounds': [
        {'registered': 13372, 'cast': 9546, 'invalid': 555, 'candidates': [
            ('Davor Mirković', 'Pula', 'NK', 3140),
            ('Vladimir Paun', 'Pula', 'NK', 2254),
            ('Mihovil Rovis', 'Pula', 'HSS,KNS', 3597),
        ]},
        {'registered': 13390, 'cast': 8615, 'invalid': 404, 'candidates': [
            ('Mihovil Rovis', 'Pula', 'HSS,KNS', 4085),
            ('Davor Mirković', 'Pula', 'NK', 4126),
        ]},
    ], 'winner': 'Davor Mirković'},
    113: {'name': 'Pula II', 'rounds': [
        {'registered': 9695, 'cast': 7268, 'invalid': 484, 'candidates': [
            ('Ivo Markulin', 'Pula', 'HSS,KNS', 2026),
            ('Marijan Račan', 'Pula', 'NK', 4008),
            ('Zoran Risteski', 'Pula', 'NK', 750),
        ]},
    ], 'winner': 'Marijan Račan'},
    114: {'name': 'Pula III', 'rounds': [
        {'registered': 11845, 'cast': 8746, 'invalid': 354, 'candidates': [
            ('Vladan Feranda', 'Pula', 'NK', 750),
            ('Krešimir Franić', 'Pula', 'SDSH,KNS', 2036),
            ('Slobodan Jovanović', 'Pula', 'NK', 941),
            ('Livijo Matošević', 'Pula', 'NK', 2112),
            ('Albert Miletić', 'Pula', 'NK', 460),
            ('Zdenko Mitar', 'Pula', 'NK', 635),
            ('Mario Vlačić', 'Pula', 'NK', 1458),
        ]},
        {'registered': 11850, 'cast': 7766, 'invalid': 260, 'candidates': [
            ('Livijo Matošević', 'Pula', 'NK', 4024),
            ('Krešimir Franić', 'Pula', 'SDSH,KNS', 1926),
            ('Slobodan Jovanović', 'Pula', 'NK', 1005),
            ('Zdenko Mitar', 'Pula', 'NK', 551),
        ]},
    ], 'winner': 'Livijo Matošević'},
    115: {'name': 'Rovinj', 'rounds': [
        {'registered': 13927, 'cast': 10535, 'invalid': 632, 'candidates': [
            ('Ivan Bubić', 'Pazin', 'HDS,KNS', 3423),
            ('Anton Cerin', 'Rovinj', 'SKH-SDP', 3659),
            ('Ana Sinković', 'Pazin', 'SKH-SDP', 1726),
            ('Petar Šuran', 'Pazin', 'SSH', 1086),
        ]},
        {'registered': 14077, 'cast': 9614, 'invalid': 468, 'candidates': [
            ('Anton Cerin', 'Rovinj', 'SKH-SDP', 5213),
            ('Ivan Bubić', 'Pazin', 'HDS', 3931),
        ]},
    ], 'winner': 'Anton Cerin'},
    116: {'name': 'Poreč', 'rounds': [
        {'registered': 10020, 'cast': 7351, 'invalid': 367, 'candidates': [
            ('Šime Kalčić', 'Poreč', 'SKH-SDP', 3218),
            ('Mr Pavle Ružić', 'Poreč', 'HDS,KNS', 2066),
            ('Franko Žužić', 'Tar', 'SSH', 1700),
        ]},
        {'registered': 10322, 'cast': 5759, 'invalid': 289, 'candidates': [
            ('Šime Kalčić', 'Poreč', 'SKH-SDP', 2731),
            ('Mr Pavle Ružić', 'Poreč', 'HDS', 1507),
            ('Franko Žužić', 'Tar', 'SSH', 1232),
        ]},
    ], 'winner': 'Šime Kalčić'},
    117: {'name': 'Buje', 'rounds': [
        {'registered': 11659, 'cast': 8856, 'invalid': 634, 'candidates': [
            ('Edo Ivančić', 'Umag', 'SSH', 1681),
            ('Ivica Kišiček', 'Buzet', 'SKH-SDP', 1929),
            ('Marko Martinčić', 'Umag', 'SKH-SDP', 2661),
            ('Silvano Šepić', 'Buje', 'HDS,KNS', 1951),
        ]},
        {'registered': 12106, 'cast': 7846, 'invalid': 578, 'candidates': [
            ('Marko Martinčić', 'Umag', 'SKH-SDP', 3992),
            ('Silvano Šepić', 'Buje', 'HDS', 1670),
            ('Edo Ivančić', 'Umag', 'SSH', 1606),
        ]},
    ], 'winner': 'Marko Martinčić'},
    118: {'name': 'Zadar I', 'rounds': [
        {'registered': 12731, 'cast': 10412, 'invalid': 218, 'candidates': [
            ('Ante Baković', 'Zadar', 'SKH-SDP', 1989),
            ('Božo Turudić', 'Zadar', 'HDS,KNS', 1097),
            ('Zoran Vernazza', 'Zadar', 'HDZ', 6143),
            ('Josip Vlahović', 'Zadar', 'SSH', 965),
        ]},
    ], 'winner': 'Zoran Vernazza'},
    119: {'name': 'Zadar II', 'rounds': [
        {'registered': 13192, 'cast': 9299, 'invalid': 225, 'candidates': [
            ('Božo Jusup', 'Zadar', 'SKH-SDP', 2742),
            ('Dr Danijel Lovrinov', 'Zadar', 'HDS,HSS,DSAH,HKDS,HSLS,SDSH,KNS', 1280),
            ('Igor Meštrović', 'Zadar', 'HDZ', 5052),
        ]},
    ], 'winner': 'Igor Meštrović'},
    120: {'name': 'Zadar III', 'rounds': [
        {'registered': 15145, 'cast': 12596, 'invalid': 475, 'candidates': [
            ('Boris Bogdanić', 'Zadar', 'NK', 568),
            ('Dr Slobodan Čače', 'Zadar', 'HSLS,KNS', 1310),
            ('Miljenko Domijan', 'Zadar', 'SSH', 3082),
            ('Miloš Kalinić', 'Zadar', 'NK', 554),
            ('Jure Kožul', 'Zadar', 'NK', 514),
            ('Mr Vinko Marinković', 'Zadar', 'NK', 387),
            ('Vice Profaca', 'Zadar', 'HDZ', 5706),
        ]},
        {'registered': 16525, 'cast': 8984, 'invalid': 208, 'candidates': [
            ('Vice Profaca', 'Zadar', 'HDZ', 4883),
            ('Miljenko Domijan', 'Zadar', 'SSH', 3893),
        ]},
    ], 'winner': 'Vice Profaca'},
    121: {'name': 'Biograd na Moru', 'rounds': [
        {'registered': 12052, 'cast': 9306, 'invalid': 325, 'candidates': [
            ('Ilija Knežević', 'Benkovac', 'SKH-SDP', 4729),
            ('Miljenko Lepur', 'Biograd na Moru', 'SKH-SDP', 759),
            ('Petar Perković', 'Biograd na Moru', 'HDZ', 2658),
            ('Dr Ivica Vlatković', 'Biograd na Moru', 'HDS,KNS', 835),
        ]},
    ], 'winner': 'Ilija Knežević'},
    122: {'name': 'Šibenik I', 'rounds': [
        {'registered': 15355, 'cast': 11736, 'invalid': 320, 'candidates': [
            ('Josip Juras', 'Šibenik', 'HDZ', 6858),
            ('Vladimir Lipović', 'Šibenik', 'NK', 391),
            ('Josip Luketa', 'Šibenik', 'HKDS,KNS', 1064),
            ('Ivan Ninić', 'Šibenik', 'SKH-SDP', 3036),
        ]},
    ], 'winner': 'Josip Juras'},
    123: {'name': 'Šibenik II', 'rounds': [
        {'registered': 12723, 'cast': 10114, 'invalid': 215, 'candidates': [
            ('Zlatko Duić', 'Šibenik', 'HDZ', 4254),
            ('Ivan Kale', 'Šibenik', 'NK', 432),
            ('Ante Marušić', 'Vodice', 'HDS,KNS', 1437),
            ('Joško Pisa', 'Šibenik', 'SKH-SDP', 3770),
        ]},
        {'registered': 12855, 'cast': 8786, 'invalid': 222, 'candidates': [
            ('Zlatko Duić', 'Šibenik', 'HDZ', 4643),
            ('Joško Pisa', 'Šibenik', 'SKH-SDP', 3906),
        ]},
    ], 'winner': 'Zlatko Duić'},
    124: {'name': 'Knin', 'rounds': [
        {'registered': 13469, 'cast': 8639, 'invalid': 271, 'candidates': [
            ('Branko Šimpraga', 'Knin', 'NK', 1708),
            ('Radoslav Tanjga', 'Knin', 'SDS', 5286),
            ('Dragutin Vukadin', 'Knin', 'NK', 1374),
        ]},
    ], 'winner': 'Radoslav Tanjga'},
    125: {'name': 'Trogir', 'rounds': [
        {'registered': 11342, 'cast': 8913, 'invalid': 237, 'candidates': [
            ('Stipan Šoda-Čotić', 'Trogir', 'SKH-SDP', 3400),
            ('Ante Tomaš', 'Seget D. Trogir', 'HSLS,KNS', 1185),
            ('Jakov Validžić', 'Seget D. Trogir', 'HDZ', 4091),
        ]},
        {'registered': 11766, 'cast': 7962, 'invalid': 162, 'candidates': [
            ('Jakov Validžić', 'Seget D. Trogir', 'HDZ', 4009),
            ('Stipan Šoda-Čotić', 'Trogir', 'SKH-SDP', 3109),
            ('Ante Tomaš', 'Seget D. Trogir', 'HSLS,KNS', 671),
        ]},
    ], 'winner': 'Jakov Validžić'},
    126: {'name': 'Sinj', 'rounds': [
        {'registered': 15298, 'cast': 12281, 'invalid': 384, 'candidates': [
            ('Josip (Zvonko) Čabo', 'Trilj', 'SKH-SDP', 2506),
            ('Luka Carić', 'Brnaze', 'HDZ', 2908),
            ('Frano Jović', 'Imotski', 'SKH-SDP', 842),
            ('Mate Nenadić', 'Imotski', 'HDZ', 3297),
            ('Dr Neven Strukan', 'Sinj', 'KNS', 2335),
        ]},
        {'registered': 15294, 'cast': 10753, 'invalid': 309, 'candidates': [
            ('Mate Nenadić', 'Imotski', 'HDZ', 4193),
            ('Luka Carić', 'Brnaze', 'HDZ', 3029),
            ('Josip (Zvonko) Čabo', 'Trilj', 'SKH-SDP', 3222),
        ]},
    ], 'winner': 'Mate Nenadić'},
    127: {'name': 'Split I', 'rounds': [
        {'registered': 10560, 'cast': 8404, 'invalid': 131, 'candidates': [
            ('Joško Alujević', 'Split', 'SKH-SDP', 2293),
            ('Iljo Martinović', 'Split', 'HDZ', 4574),
            ('Nora Matulić-Sumić', 'Split', 'ZAS', 329),
            ('Antun Nakić', 'Split', 'HSLS,KNS', 1057),
        ]},
    ], 'winner': 'Iljo Martinović'},
    128: {'name': 'Split II', 'rounds': [
        {'registered': 9135, 'cast': 7036, 'invalid': 209, 'candidates': [
            ('Vedran Stipan Babić', 'Split', 'NK', 519),
            ('Božidar Budanko', 'Kaštel Stari', 'HDZ', 3505),
            ('Mr Vojmir Dvornik', 'Split', 'NK', 235),
            ('Marijo Jovanović', 'Split', 'NK', 86),
            ('Ante Jukić', 'Split', 'NK', 137),
            ('Marko Parać', 'Split', 'HMP,KNS', 734),
            ('Stjepko Vojković', 'Split', 'SKH-SDP', 1610),
        ]},
        {'registered': 9079, 'cast': 6367, 'invalid': 104, 'candidates': [
            ('Božidar Budanko', 'Kaštel Stari', 'HDZ', 3477),
            ('Stjepko Vojković', 'Split', 'SKH-SDP', 1950),
            ('Marko Parać', 'Split', 'HMP,KNS', 833),
        ]},
    ], 'winner': 'Božidar Budanko'},
    129: {'name': 'Split III', 'rounds': [
        {'registered': 22043, 'cast': 15179, 'invalid': 510, 'candidates': [
            ('Stjepan Bočina', 'Split', 'NK', 636),
            ('Juraj Buzolić', 'Split', 'HDZ', 8756),
            ('Šimun Debak', 'Split', 'NK', 429),
            ('Ivica Maretić', 'Split', 'NK', 510),
            ('Branislav Marić', 'Split', 'SKH-SDP', 3380),
            ('Mr Stjepan Papić', 'Split', 'NK', 849),
        ]},
    ], 'winner': 'Juraj Buzolić'},
    130: {'name': 'Split IV', 'rounds': [
        {'registered': 21355, 'cast': 15923, 'invalid': 361, 'candidates': [
            ('Branko Armanda', 'Split', 'NK', 493),
            ('Branko Bilić', 'Split', 'NK', 259),
            ('Lada Ercegović', 'Split', 'NK', 266),
            ('Josip Kunac', 'Split', 'HDZ', 7943),
            ('Ante Letica', 'Split', 'SKH-SDP', 4511),
            ('Vlatko Škiljo', 'Split', 'HMP,KNS', 1533),
            ('Josip Zudenigo', 'Split', 'NK', 212),
            ('Marin Zužul', 'Split', 'NK', 264),
        ]},
        {'registered': 21047, 'cast': 13555, 'invalid': 193, 'candidates': [
            ('Josip Kunac', 'Split', 'HDZ', 7138),
            ('Ante Letica', 'Split', 'SKH-SDP', 4742),
            ('Vlatko Škiljo', 'Split', 'HMP,KNS', 1478),
        ]},
    ], 'winner': 'Josip Kunac'},
    131: {'name': 'Split V', 'rounds': [
        {'registered': 12536, 'cast': 10925, 'invalid': 196, 'candidates': [
            ('Ivo Čorvilo', 'Split', 'NK', 343),
            ('Dr Petar Filipić', 'Split', 'SKH-SDP', 3803),
            ('Anka Mandušić', 'Split', 'NK', 763),
            ('Rade Perković', 'Split', 'HDS,KNS', 1837),
            ('Dr Ivica Ruić', 'Split', 'HDZ', 3981),
        ]},
        {'registered': 12577, 'cast': 9685, 'invalid': 182, 'candidates': [
            ('Dr Ivica Ruić', 'Split', 'HDZ', 4290),
            ('Dr Petar Filipić', 'Split', 'SKH-SDP', 4079),
            ('Rade Perković', 'Split', 'HDS', 1129),
        ]},
    ], 'winner': 'Dr Ivica Ruić'},
    132: {'name': 'Split VI', 'rounds': [
        {'registered': 11006, 'cast': 9238, 'invalid': 170, 'candidates': [
            ('Marko Borovina', 'Split', 'NK', 242),
            ('Žarko Bubalo', 'Split', 'ZAS', 713),
            ('Dr Tomislav Đorđević', 'Split', 'NK', 745),
            ('Vedrana Garafulić-Kukoč', 'Split', 'SKH-SDP', 4471),
            ('Zoran Karličić', 'Split', 'NK', 343),
            ('Branko Petrinović', 'Split', 'NK', 291),
            ('Filip Putica', 'Split', 'SDSH,KNS', 2181),
        ]},
        {'registered': 10900, 'cast': 8372, 'invalid': 120, 'candidates': [
            ('Vedrana Garafulić-Kukoč', 'Split', 'SKH-SDP', 4881),
            ('Filip Putica', 'Split', 'SDSH,KNS', 1997),
            ('Dr Tomislav Đorđević', 'Split', 'NK', 731),
            ('Žarko Bubalo', 'Split', 'ZAS', 636),
        ]},
    ], 'winner': 'Vedrana Garafulić-Kukoč'},
    133: {'name': 'Split VII', 'rounds': [
        {'registered': 8841, 'cast': 4343, 'invalid': 44, 'candidates': [
            ('Đuro Baloević', 'Split', 'NK', 76),
            ('Daria Grubišić-Čabo', 'Split', 'SKH-SDP', 1268),
            ('Žaklina Harašić', 'Split', 'ZAS', 321),
            ('Davor Lasić', 'Split', 'HDZ', 1962),
            ('Mijo Šurlin', 'Podstrana', 'HMP,KNS', 671),
        ]},
        {'registered': 9478, 'cast': 3704, 'invalid': 15, 'candidates': [
            ('Davor Lasić', 'Split', 'HDZ', 1842),
            ('Daria Grubišić-Čabo', 'Split', 'SKH-SDP', 1129),
            ('Mijo Šurlin', 'Podstrana', 'HMP,KNS', 467),
            ('Žaklina Harašić', 'Split', 'ZAS', 248),
        ]},
    ], 'winner': 'Davor Lasić'},
    134: {'name': 'Kaštela', 'rounds': [
        {'registered': 7944, 'cast': 6350, 'invalid': 193, 'candidates': [
            ('Ivan Hrgović', 'Split', 'HDZ', 3733),
            ('Milan Ravlić', 'Split', 'NK', 514),
            ('Ivan Sunara', 'Split', 'SKH-SDP', 1910),
        ]},
    ], 'winner': 'Ivan Hrgović'},
    135: {'name': 'Solin', 'rounds': [
        {'registered': 10022, 'cast': 7407, 'invalid': 299, 'candidates': [
            ('Kajo Gizdić', 'Solin', 'NK', 619),
            ('Miro Milišić', 'Split', 'SKH-SDP', 2062),
            ('Ivica Roguljić', 'Kučine-Solin', 'HDZ', 4066),
            ('Marijan Suško', 'Split', 'NK', 361),
        ]},
    ], 'winner': 'Ivica Roguljić'},
    136: {'name': 'Makarska', 'rounds': [
        {'registered': 12675, 'cast': 10468, 'invalid': 236, 'candidates': [
            ('Milivoj Franić', 'Makarska', 'HDZ', 4830),
            ('Dražen Mladin', 'Omiš', 'SKH-SDP', 4255),
            ('Miroslav Raljević', 'Omiš', 'HSLS,KNS', 1147),
        ]},
        {'registered': 13518, 'cast': 9828, 'invalid': 225, 'candidates': [
            ('Milivoj Franić', 'Makarska', 'HDZ', 5189),
            ('Dražen Mladin', 'Omiš', 'SKH-SDP', 4414),
        ]},
    ], 'winner': 'Milivoj Franić'},
    137: {'name': 'Metković', 'rounds': [
        {'registered': 16312, 'cast': 12274, 'invalid': 717, 'candidates': [
            ('Pero Musulin', 'Kardeljevo', 'NK', 3381),
            ('Dr Ivan Sokol', 'Kardeljevo', 'NK', 1732),
            ('Dr Filip Salinović', 'Kardeljevo', 'HDZ', 6444),
        ]},
    ], 'winner': 'Dr Filip Salinović'},
    138: {'name': 'Dubrovnik I', 'rounds': [
        {'registered': 14638, 'cast': 11217, 'invalid': 366, 'candidates': [
            ('Franica Krile', 'Dubrovnik', 'NK', 731),
            ('Mato-Matko Medo', 'Dubrovnik', 'HDZ', 5561),
            ('Josip Škerlj', 'Dubrovnik', 'HKDS,KNS', 1312),
            ('Đorđe Vrtikapa', 'Dubrovnik', 'SKH-SDP', 3247),
        ]},
        {'registered': 14638, 'cast': 9707, 'invalid': 274, 'candidates': [
            ('Mato-Matko Medo', 'Dubrovnik', 'HDZ', 6199),
            ('Đorđe Vrtikapa', 'Dubrovnik', 'SKH-SDP', 3234),
        ]},
    ], 'winner': 'Mato-Matko Medo'},
    139: {'name': 'Dubrovnik II', 'rounds': [
        {'registered': 12086, 'cast': 9281, 'invalid': 207, 'candidates': [
            ('Berta Dragičević', 'Dubrovnik', 'HSLS,KNS,HDZ', 722),
            ('Ivo Jelić', 'Dubrovnik', 'HDZ', 4698),
            ('Liborio Polanda', 'Dubrovnik', 'SKH-SDP', 3078),
            ('Boško Skaramuca', 'Dubrovnik', 'NK', 303),
            ('Velimir Tomašić', 'Dubrovnik', 'NK', 273),
        ]},
    ], 'winner': 'Ivo Jelić'},
    140: {'name': 'Korčula', 'rounds': [
        {'registered': 6476, 'cast': 4973, 'invalid': 238, 'candidates': [
            ('Frano Skokandić', 'Zrnovo', 'HDZ', 1822),
            ('Ivan Skokandić - Ivić', 'Korčula', 'HSLS,KNS', 655),
            ('Marko Vlašić - Čiče', 'Čara', 'SKH-SDP,SSH', 2258),
        ]},
        {'registered': 7281, 'cast': 4724, 'invalid': 185, 'candidates': [
            ('Marko Vlašić - Čiče', 'Čara', 'SKH-SDP,SSH', 2355),
            ('Frano Skokandić', 'Zrnovo', 'HDZ', 2184),
        ]},
    ], 'winner': 'Marko Vlašić - Čiče'},
    142: {'name': 'Osijek', 'rounds': [
        {'registered': 37646, 'cast': 32730, 'invalid': 3419, 'candidates': [
            ('Ljubomir Čakan', 'Vukovar', 'NK', 2171),
            ('Vladimir Dragun', 'Ilok', 'SKH-SDP', 5227),
            ('Antun Lovrić', 'Bošnjaci', 'HSS,KNS', 11310),
            ('Vlado Mandić', 'Čepin', 'SSH', 2499),
            ('Ilija Mirčetić', 'Komletinci', 'SSH', 2787),
            ('Ivan Tomičić', 'Đakovo', 'NK', 5317),
        ]},
        {'registered': 39638, 'cast': 21119, 'invalid': 652, 'candidates': [
            ('Antun Lovrić', 'Bošnjaci', 'HSS,KNS', 12364),
            ('Vladimir Dragun', 'Ilok', 'SKH-SDP', 3120),
            ('Ilija Mirčetić', 'Komletinci', 'SSH', 2697),
            ('Vlado Mandić', 'Čepin', 'SSH', 2286),
        ]},
    ], 'winner': 'Antun Lovrić'},
    143: {'name': 'Slavonska Požega', 'rounds': [
        {'registered': 48009, 'cast': 42484, 'invalid': 3505, 'candidates': [
            ('Ivan Babić', 'Nova Gradiška', 'HDZ', 21486),
            ('Ivan Rastija', 'Podravska Slatina', 'SSH', 5061),
            ('Davorin Smoljanović', 'Slavonska Požega', 'HDS,HKDS,SDSH,HSLS,KNS', 3992),
            ('Marko Vinarić', 'Slavonski Prnjavor', 'HDZ', 4119),
            ('Antun Vukasović', 'Slavonski Brod', 'SSH', 4321),
        ]},
    ], 'winner': 'Ivan Babić'},
    144: {'name': 'Bjelovar', 'rounds': [
        {'registered': 48128, 'cast': 41218, 'invalid': 2688, 'candidates': [
            ('Zlatko Blažiničić', 'Rovišće', 'HDZ', 25036),
            ('Stjepan Došen', 'Prekobrdo', 'SKH-SDP', 7863),
            ('Pero Hemonajec', 'Stanići', 'SSH', 2983),
            ('Stjepan Španić', 'Veliki Raven', 'SSH', 2647),
        ]},
    ], 'winner': 'Zlatko Blažiničić'},
    145: {'name': 'Daruvar', 'rounds': [
        {'registered': 32393, 'cast': 29351, 'invalid': 2146, 'candidates': [
            ('Radomir Dejanović', 'Suhopolje', 'SKH-SDP', 10344),
            ('Ivo Gerendjir', 'Grubišno Polje', 'SSH', 4641),
            ('Vlado Katančić', 'Lukač', 'HDZ', 12220),
        ]},
        {'registered': 32451, 'cast': 26842, 'invalid': 1803, 'candidates': [
            ('Vlado Katančić', 'Lukač', 'HDZ', 12650),
            ('Radomir Dejanović', 'Suhopolje', 'SKH-SDP', 9913),
            ('Ivo Gerendjir', 'Grubišno Polje', 'SSH', 2476),
        ]},
    ], 'winner': 'Vlado Katančić'},
    146: {'name': 'Čakovec', 'rounds': [
        {'registered': 19177, 'cast': 14545, 'invalid': 1794, 'candidates': [
            ('Bolta Jalšovec', 'Strukovec', 'HSLS,KNS', 6737),
            ('Marijan Majcen', 'Stanetinec', 'SSH', 2838),
            ('Zvonimir Pavčec', 'Prelog', 'SKH-SDP', 3176),
        ]},
        {'registered': 19319, 'cast': 13157, 'invalid': 2092, 'candidates': [
            ('Bolta Jalšovec', 'Strukovec', 'KNS', 7478),
            ('Marijan Majcen', 'Stanetinec', 'SSH', 3587),
        ]},
    ], 'winner': 'Bolta Jalšovec'},
    147: {'name': 'Varaždin', 'rounds': [
        {'registered': 14166, 'cast': 11399, 'invalid': 996, 'candidates': [
            ('Josip Koprek', 'Nova Ves', 'HDZ', 4331),
            ('Josip Rušec', 'Petrijanec', 'HDZ', 6072),
        ]},
    ], 'winner': 'Josip Rušec'},
    149: {'name': 'Zagreb', 'rounds': [
        {'registered': 50122, 'cast': 41997, 'invalid': 3732, 'candidates': [
            ('Ivan Bartolomej', 'Zelina', 'SSH', 3303),
            ('Zlatko Mužinić', 'Zelina', 'SKH-SDP', 5490),
            ('Josip Obajdin', 'Kutina', 'NK', 2704),
            ('Josip Pankretić', 'Vrbovec', 'HSS,KNS', 12916),
            ('Darko Vugec', 'Zaprešić', 'NK', 2334),
            ('Mladen Zelić', 'Samobor', 'HSS,KNS', 11518),
        ]},
        {'registered': 50535, 'cast': 36726, 'invalid': 2681, 'candidates': [
            ('Josip Pankretić', 'Vrbovec', 'HSS,KNS', 17170),
            ('Mladen Zelić', 'Samobor', 'HSS,KNS', 9582),
            ('Zlatko Mužinić', 'Zelina', 'SKH-SDP', 5296),
            ('Ivan Bartolomej', 'Zelina', 'SSH', 1997),
        ]},
    ], 'winner': 'Josip Pankretić'},
    150: {'name': 'Sisak', 'rounds': [
        {'registered': 29409, 'cast': 26938, 'invalid': 1339, 'candidates': [
            ('Nikola Culek', 'Tišina Desna', 'HSLS,KNS', 2950),
            ('Đurđa Gmaz', 'Stara Drenčina', 'HDZ', 7520),
            ('Đuro Kljajić', 'Staro Selo', 'SSH', 11497),
            ('Dragutin Mirosavljević', 'Novska', 'SSH', 3632),
        ]},
        {'registered': 29625, 'cast': 26127, 'invalid': 943, 'candidates': [
            ('Đuro Kljajić', 'Staro Selo', 'SSH', 13827),
            ('Đurđa Gmaz', 'Stara Drenčina', 'HDZ', 8323),
            ('Dragutin Mirosavljević', 'Novska', 'SSH', 1349),
            ('Nikola Culek', 'Tišina Desna', 'HSS,KNS', 1685),
        ]},
    ], 'winner': 'Đuro Kljajić'},
    152: {'name': 'Rijeka', 'rounds': [
        {'registered': 19352, 'cast': 17076, 'invalid': 1230, 'candidates': [
            ('Ivan Berljafa', 'Poreč', 'SSH', 1380),
            ('Mane Drakulić', 'Plitvička Jezera', 'SKH-SDP', 6268),
            ('Dušan Franko', 'Pazin', 'NK', 1713),
            ('Mate Kostelac', 'Otočac', 'HDZ', 6485),
        ]},
        {'registered': 20906, 'cast': 16656, 'invalid': 1046, 'candidates': [
            ('Mate Kostelac', 'Otočac', 'HDZ', 6982),
            ('Mane Drakulić', 'Plitvička Jezera', 'SKH-SDP', 6245),
            ('Dušan Franko', 'Pazin', 'NK', 1457),
            ('Ivan Berljafa', 'Poreč', 'SSH', 926),
        ]},
    ], 'winner': 'Mate Kostelac'},
    153: {'name': 'Benkovac', 'rounds': [
        {'registered': 15877, 'cast': 12769, 'invalid': 2857, 'candidates': [
            ('Jadranko Markov', 'Šibenik', 'HDZ', 6266),
            ('Šime Šestan', 'Zadar-Zemunik', 'NK', 3523),
        ]},
        {'registered': 15689, 'cast': 13555, 'invalid': 2984, 'candidates': [
            ('Jadranko Markov', 'Šibenik', 'HDZ', 6297),
            ('Šime Šestan', 'Zadar-Zemunik', 'NK', 4274),
        ]},
    ], 'winner': 'Jadranko Markov'},
    154: {'name': 'Split', 'rounds': [
        {'registered': 10222, 'cast': 8030, 'invalid': 867, 'candidates': [
            ('Stipe Čarić', 'Brnaze-Sinj', 'KNS', 5188),
            ('Pave Klapirić', 'Vinjani Donji Imotski', 'NK', 1923),
        ]},
    ], 'winner': 'Stipe Čarić'},
    155: {'name': 'Osijek', 'rounds': [
        {'registered': 11488, 'cast': 5107, 'invalid': 0, 'candidates': [
            ('Gojko Bogdanović', 'Slavonski Brod', 'NK', 593),
            ('Marijan Dosegović', 'Nova Kapela', 'NK', 279),
            ('Pero Kardum', 'Bizovac', 'NK', 691),
            ('Miljenko Ložusić', 'Osijek', 'NK', 724),
            ('Milan Markanjević', 'Slavonska Požega', 'NK', 577),
            ('Ante Prkačin', 'Slavonski Brod', 'HDS,KNS', 2175),
        ]},
        {'registered': 12022, 'cast': 3206, 'invalid': 70, 'candidates': [
            ('Ante Prkačin', 'Slavonski Brod', 'HDS', 1404),
            ('Miljenko Ložusić', 'Osijek', 'NK', 452),
            ('Pero Kardum', 'Bizovac', 'NK', 512),
            ('Gojko Bogdanović', 'Slavonski Brod', 'NK', 269),
            ('Milan Markanjević', 'Slavonska Požega', 'NK', 499),
        ]},
    ], 'winner': 'Ante Prkačin'},
    156: {'name': 'Sisak', 'rounds': [
        {'registered': 10325, 'cast': 5152, 'invalid': 106, 'candidates': [
            ('Franjo Fofonjka', 'Bjelovar', 'USPĐ', 2558),
            ('Zlatko Galić', 'Koprivnica', 'SSH', 869),
            ('Ivan Krajačević', 'Sisak', 'USPS', 1619),
        ]},
        {'registered': 10570, 'cast': 3452, 'invalid': 79, 'candidates': [
            ('Franjo Fofonjka', 'Bjelovar', 'USPĐ', 1616),
            ('Ivan Krajačević', 'Sisak', 'USPS', 1238),
            ('Zlatko Galić', 'Koprivnica', 'SSH', 519),
        ]},
    ], 'winner': 'Franjo Fofonjka'},
    157: {'name': 'Zagreb', 'rounds': [
        {'registered': 24709, 'cast': 7918, 'invalid': 17, 'candidates': [
            ('Josip Bobesić', 'Velika Gorica', 'NK', 565),
            ('Krsto Grgurić', 'Sesvete', 'NK', 230),
            ('Ćiro Grubišić', 'Zagreb', 'HDZ', 4831),
            ('Duško Horvatin', 'Zaprešić', 'NK', 240),
            ('Emanuel Justament', 'Zagreb', 'NK', 633),
            ('Željko Malenica', 'Zagreb', 'HDS,KNS', 1402),
        ]},
        {'registered': 26626, 'cast': 5089, 'invalid': 162, 'candidates': [
            ('Ćiro Grubišić', 'Zagreb', 'HDZ', 3198),
            ('Željko Malenica', 'Zagreb', 'HDS', 904),
            ('Josip Bobesić', 'Velika Gorica', 'NK', 825),
        ]},
    ], 'winner': 'Ćiro Grubišić'},
    158: {'name': 'Varaždin', 'rounds': [
        {'registered': 16581, 'cast': 7280, 'invalid': 178, 'candidates': [
            ('Stjepan Hrešč', 'Prelog', 'SSH', 890),
            ('Stjepan Kostel', 'Čakovec', 'HKDS,KNS', 1469),
            ('Ivan Kovač', 'Varaždin', 'HDS,KNS', 2525),
            ('Darko Ostoja', 'Čakovec', 'NK', 987),
            ('Stjepan Pavrlišak', 'Donja Stubica', 'NK', 442),
            ('Zvonimir Rihtarić', 'Varaždin', 'NK', 426),
            ('Josip Vidović', 'Mihovljan', 'NK', 363),
        ]},
        {'registered': 16729, 'cast': 4146, 'invalid': 48, 'candidates': [
            ('Ivan Kovač', 'Varaždin', 'HDS', 2340),
            ('Stjepan Kostel', 'Čakovec', 'HKDS,KNS', 956),
            ('Stjepan Hrešč', 'Prelog', 'SSH', 781),
        ]},
    ], 'winner': 'Ivan Kovač'},
    159: {'name': 'Rijeka', 'rounds': [
        {'registered': 12705, 'cast': 4967, 'invalid': 296, 'candidates': [
            ('Šime Coza', 'Rijeka', 'NK', 1787),
            ('Ivan Lesica', 'Krk', 'HDS,KNS', 1710),
            ('Ivan Šantić', 'Novigrad', 'NK', 629),
            ('Anton Vladišković', 'Poreč', 'NK', 545),
        ]},
        {'registered': 12924, 'cast': 3128, 'invalid': 106, 'candidates': [
            ('Šime Coza', 'Rijeka', 'NK', 1081),
            ('Ivan Lesica', 'Krk', 'HDS', 1148),
            ('Ivan Šantić', 'Novigrad', 'NK', 352),
            ('Anton Vladišković', 'Poreč', 'NK', 441),
        ]},
    ], 'winner': 'Ivan Lesica'},
    160: {'name': 'Split', 'rounds': [
        {'registered': 15977, 'cast': 5943, 'invalid': 125, 'candidates': [
            ('Ante Bego', 'Split', 'SUSPS', 1732),
            ('Mate Brajković', 'Split', 'HS', 347),
            ('Marko Kovač', 'Šibenik', 'SUSPS', 783),
            ('Jozo Topić', 'Šibenik', 'HDZ', 2930),
        ]},
        {'registered': 15600, 'cast': 4109, 'invalid': 54, 'candidates': [
            ('Jozo Topić', 'Šibenik', 'HDZ', 1968),
            ('Ante Bego', 'Split', 'SUSPS', 1721),
            ('Marko Kovač', 'Šibenik', 'SUSPS', 363),
        ]},
    ], 'winner': 'Jozo Topić'},
}
