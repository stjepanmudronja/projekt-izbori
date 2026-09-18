"""Transcription of the official 1995 Zastupnički dom result.

Source: Izborna komisija Republike Hrvatske, Klasa 013-01/95-01/01, Urbroj
56605-95-470…504, Zagreb, 14 November 1995 — the bundle of decisions declaring
the result of the election held on **29 October 1995**, scanned at
`files/rezultati_sabor_2024/1995/1995_Rezultati_Sabor_zastupnicki_dom.pdf`.
The PDF is a CCITT-G4 fax scan with no text layer; pages were rendered with
`tools/extract_scanned_pdf.py` and read off the images.

The 1995 system elected **127 members** in four separate contests, which is why
this file has four tables rather than one:

  * `NATIONAL` — one countrywide proportional list, 80 seats, 5% threshold.
  * `DIASPORA` — the "posebne liste" for citizens abroad, 12 seats. It was a
    *fixed* 12 that year, unlike the votes-per-seat conversion of 2007 or the
    fixed 3 from 2011 on.
  * `DISTRICTS` — 28 single-member districts decided by plurality, one round.
    No party list, no D'Hondt: the top candidate simply wins the seat.
  * `MINORITY_UNITS` — 5 special units for national minorities, 7 seats. Units
    1-4 return one member each; the 5th (Serbian) returns three, so its ballots
    carry up to three votes and its percentages are shares of *votes cast*, not
    of valid ballots. That is why its votes sum to more than its valid total.

Checks this transcription satisfies:

  * The 14 national lists sum to 2,417,374 — exactly the report's valid total.
    Note the HSLS figure is **279,245**; summaries printing 279,345 do not add
    up.
  * The 7 diaspora lists sum to 107,772, the report's valid total there.
  * Every one of the 28 districts sums its candidates to `cast - invalid`, and
    in each the stated winner is the candidate with the most votes.
  * Minority units 1-4 sum to their valid totals; unit 5 is the multi-vote
    exception described above.
  * 80 + 12 + 28 + 7 = 127, and the 80 national seats have 80 named members.

Grouping each winner by the **first** party of their list (`primary_party()`,
the convention used everywhere else in this project) reproduces the published
summary exactly: 127 total = HDZ 75, HSS-led 18, HSLS 12, SDP 10, HSP 4,
others 8.

Names are kept in the report's own spelling, academic titles and all;
`clean_candidate_name` strips those on import so a person matches across years.
"""

NATIONAL = {
    'registered': 3634233, 'cast': 2500040, 'invalid': 82666, 'valid': 2417374,
    'seats': 80,
    'lists': [
        ('Akcija socijaldemokrata Hrvatske - ASH', 40348, 1.67),
        ('Domovinska građanska stranka - DGS', 5343, 0.22),
        ('Hrvatska demokratska zajednica - HDZ', 1093403, 45.23),
        ('Hrvatska konzervativna stranka - HKS', 6858, 0.28),
        ('Hrvatska kršćanska demokratska stranka - HKDS', 16986, 0.70),
        ('Hrvatska seljačka stranka - HSS, Istarski demokratski sabor - IDS, '
         'Hrvatska narodna stranka - HNS, Hrvatska kršćanska demokratska unija - HKDU, '
         'Slavonsko-baranjska hrvatska stranka - SBHS', 441390, 18.26),
        ('Hrvatska socijalno liberalna stranka - HSLS', 279245, 11.55),
        ('Hrvatska stranka naravnog zakona - HSNZ', 7835, 0.32),
        ('Hrvatska stranka prava - HSP', 121095, 5.01),
        ('Hrvatska stranka prava - 1861 - HSP - 1861', 31530, 1.30),
        ('Hrvatski nezavisni demokrati - HND', 72612, 3.00),
        ('Nezavisna stranka prava - NSP', 6608, 0.27),
        ('Socijaldemokratska partija Hrvatske - SDP', 215839, 8.93),
        ('Socijalno-demokratska unija Hrvatske - SDU', 78282, 3.24),
    ],
    # Seats and members, in the report's own order.
    'seats_by_list': [
        ('Hrvatska demokratska zajednica - HDZ', 42, [
            'Dr. Nedjeljko Mihanović', 'Gojko Šušak', 'Nikica Valentić', 'Ak. Vlatko Pavletić',
            'Elio Martinčić', 'Ivan Milas', 'Dr. Ivić Pašalić', 'Antun Vrdoljak', 'Luka Bebić',
            'Martin Katičić', 'Mr. Borislav Škegro', 'Jurica Pavelić', 'Kazimir Sviben',
            'Ak. Antun Dubravko Jelčić', 'Katarina Fuček', 'Drago Krpina', 'Marija Bajt',
            'Mladen Jurković', 'Milovan Šibl', 'Milan Kovač', 'Đuro Perica', 'Zlatko Canjuga',
            'Jakob Eltz Vukovarski', 'Mario Kapulica', 'Ak. Željko Bujas', 'Hrvoje Hitrec',
            'Marino Golob', 'Bosiljko Mišetić', 'Dr. Smiljko Sokol', 'Mr. Milivoj Kujundžić',
            'Vera Stanić', 'Branimir Pasecky', 'Ivan Rabuzin', 'Matej Janković', 'Dr. Đuro Njavro',
            'Marin Mileta', 'Mr. Juraj Buzolić', 'Damir Škaro', 'Ivan Kolak', 'Dragan Kovačević',
            'Kruno Bošnjak', 'Ivan Hranjec']),
        ('Hrvatska seljačka stranka - HSS, Istarski demokratski sabor - IDS, '
         'Hrvatska narodna stranka - HNS, Hrvatska kršćanska demokratska unija - HKDU, '
         'Slavonsko-baranjska hrvatska stranka - SBHS', 16, [
            'Josip Pankretić', 'Zlatko Tomčić', 'Stjepan Radić', 'Luciano Delbianco',
            'Radimir Čačić', 'Luka Trconić', 'Joško Kovač', 'Dr. Marko Veselica',
            'Marko Miljević', 'Marijan Filipović', 'Srećko Bijelić', 'Dino Debeljuh',
            'Petar Žitnik', 'Ivan Kolar', 'Slavko Vukšić', 'Juraj Bišćan']),
        ('Hrvatska socijalno liberalna stranka - HSLS', 10, [
            'Dražen Budiša', 'Vladimir Gotovac', 'Đurđa Adlešić', 'Jozo Radoš', 'Ivica Ropuš',
            'Dr. Zlatko Kramarić', 'Vladimir Primorac', 'Božo Kovačević', 'Ivan Herak',
            'Baltazar Jalšovec']),
        ('Socijaldemokratska partija Hrvatske - SDP', 8, [
            'Ivica Račan', 'Mr. Mato Arlović', 'Željka Antunović', 'Dr. Antun Vujić',
            'Mr. Marin Jurjević', 'Dr. Nikola Ivaniš', 'Dragica Zgrebec',
            'Snježana Biga Friganović']),
        ('Hrvatska stranka prava - HSP', 4, [
            'Anto Đapić', 'Boris Kandare', 'Vlado Jukić', 'Ivan Gabelica']),
    ],
}

# "Posebne liste" — the diaspora list (pages 6-7). 12 seats, all HDZ.
DIASPORA = {
    'registered': 398839, 'cast': 109389, 'invalid': 1617, 'valid': 107772,
    'seats': 12,
    'lists': [
        ('Akcija socijaldemokrata Hrvatske - ASH', 1188, 1.10),
        ('Domovinska građanska stranka - DGS', 218, 0.20),
        ('Hrvatska demokratska zajednica - HDZ', 97012, 90.02),
        ('Hrvatska kršćanska demokratska stranka - HKDS', 648, 0.60),
        ('Hrvatska stranka prava - HSP', 3888, 3.61),
        ('Hrvatska stranka prava - 1861 - HSP - 1861', 1562, 1.45),
        ('Zajednica domovine i dijaspore - ZDD', 3256, 3.02),
    ],
    'seats_by_list': [
        ('Hrvatska demokratska zajednica - HDZ', 12, [
            'Ante Beljo', 'Marijan Petrović', 'Zdenka Babić Petričević', 'Vladimir Šuljić',
            'Mr. Zdravka Bušić', 'Ivo Lozančić', 'Jozo Marić', 'Dr. Zdravko Sančević',
            'Dr. Stanislav Janović', 'Stipe Hrkač', 'Dr. Bruno Uroić', 'Franka Barbić']),
    ],
}

# Single-member districts I-XXVIII (first-past-the-post), pages 8-35.
# Each: number -> registered, cast, invalid, candidates [(name, party, votes, pct)],
# winner name.
DISTRICTS = {
    1: {'registered': 137640, 'cast': 107528, 'invalid': 3783, 'candidates': [
        ('MARIJAN CRNKOVIĆ', 'HKDS', 3451, 3.33),
        ('IVICA GAŽI', 'HDZ', 46733, 45.05),
        ('ZDENKO HARAMIJA', 'HSS,HSLS,HNS,HKDU,HND,SDP,HSP-1861', 46623, 44.94),
        ('TOMISLAV IVANDA', 'HSP', 6453, 6.22),
        ('BORAN IVASOVIĆ', 'HDMS', 485, 0.47),
    ], 'winner': 'IVICA GAŽI'},
    2: {'registered': 152714, 'cast': 109835, 'invalid': 4184, 'candidates': [
        ('STANISLAV GORUPEC', 'HSP', 10001, 9.47),
        ('IVAN JARNJAK', 'HDZ', 64232, 60.80),
        ('Dr. IVAN OBREŽ', 'HSLS', 31418, 29.74),
    ], 'winner': 'IVAN JARNJAK'},
    3: {'registered': 85396, 'cast': 48249, 'invalid': 1690, 'candidates': [
        ('ĐURO BRODARAC', 'HDZ', 23740, 50.99),
        ('EDGAR HORVAT', 'HSNZ', 1009, 2.17),
        ('MARIO MAROT', 'HSP', 6055, 13.01),
        ('DAVORKO VIDOVIĆ', 'SDP,HND,HSLS,HSS,HNS', 15381, 33.04),
        ('ZLATKO ŽILAJKOVIĆ', 'HS', 374, 0.80),
    ], 'winner': 'ĐURO BRODARAC'},
    4: {'registered': 122487, 'cast': 71804, 'invalid': 2088, 'candidates': [
        ('JOSIP BALJA', 'HKDU', 3453, 4.95),
        ('JANKO BOBETKO', 'HDZ', 39155, 56.16),
        ('MIROSLAV KURTZ', 'HKDS', 978, 1.40),
        ('MARIJAN PLANINČIĆ', 'HSP', 4116, 5.90),
        ('REHAN-ANTE SKENDŽIĆ', 'HDMS', 341, 0.49),
        ('HRVOJE ZORIĆ', 'HSLS,HSS', 21673, 31.09),
    ], 'winner': 'JANKO BOBETKO'},
    5: {'registered': 148266, 'cast': 108873, 'invalid': 3599, 'candidates': [
        ('JELKA GLUMIČIĆ', 'SDU', 3901, 3.71),
        ('JOSIP JAKOVČIĆ', 'HDZ', 53741, 51.05),
        ('DARKO ŠANTIĆ', 'HNS,HSLS,HSS,SDP,HSP-1861,HND', 36779, 34.94),
        ('Mr. PAVAO TONKOVIĆ', 'HSP', 6971, 6.62),
        ('TIHOMIR ŽALAC', 'HSNZ', 863, 0.82),
        ('MARINA ŽGANJER', 'Nezavisni kandidat', 3019, 2.87),
    ], 'winner': 'JOSIP JAKOVČIĆ'},
    6: {'registered': 129699, 'cast': 97022, 'invalid': 2935, 'candidates': [
        ('Dr. FRANJO GREGURIĆ', 'HDZ', 43721, 46.47),
        ('IVAN HITI', 'Nezavisni kandidat', 2136, 2.27),
        ('NINOSLAV MEIĆ', 'HSP', 4120, 4.38),
        ('IVAN RUKLJIĆ', 'HKDS', 3391, 3.60),
        ('Dr. ZVONIMIR SABATI', 'HSS', 39158, 41.62),
        ('Mr. ZORAN VINCEKOVIĆ', 'Nezavisni kandidat', 1561, 1.66),
    ], 'winner': 'Dr. FRANJO GREGURIĆ'},
    7: {'registered': 178756, 'cast': 115568, 'invalid': 3891, 'candidates': [
        ('BOŽIDAR ČOHAR dr.med.', 'HSP', 5840, 5.23),
        ('STEVO ĐURĐEVIĆ', 'Stranka Roma Hrvatske', 3011, 2.70),
        ('STJEPAN HITTNER', 'NSP', 1990, 1.78),
        ('MARIJAN IVANČAN', 'HKDS', 3565, 3.19),
        ('MLADEN MARKAČ', 'HDZ', 51169, 45.82),
        ('JURAJ MATIĆ', 'Nezavisni kandidat', 1611, 1.44),
        ('IVAN STANČER', 'HSS,HSLS,HNS,SDP,HND,HSP-1861', 44491, 39.84),
    ], 'winner': 'MLADEN MARKAČ'},
    8: {'registered': 150310, 'cast': 112630, 'invalid': 3498, 'candidates': [
        ('NADA BARTOLIĆ-MATKOVIĆ dr.med.', 'HSP', 5821, 5.33),
        ('VLADIMIR BEBIĆ', 'SDU', 11217, 10.28),
        ('ANTON CELIĆ', 'Nezavisni kandidat', 965, 0.88),
        ('NATALIJA HARHAJ', 'HSNZ', 838, 0.77),
        ('DAMIR KAJIN', 'IDS,HSS,HNS,HSLS,HND,SDP', 57203, 52.42),
        ('ŽELJKO LUŽAVEC', 'HDZ', 23883, 21.88),
        ('Dr. IVAN MILOŠ', 'Nezavisni kandidat', 1225, 1.12),
        ('BERNARDO DI LENARDO ZAMLIĆ', 'RiDS', 7980, 7.31),
    ], 'winner': 'DAMIR KAJIN'},
    9: {'registered': 138655, 'cast': 103061, 'invalid': 2681, 'candidates': [
        ('ZDRAVKO BENZIA', 'HSNZ', 1089, 1.08),
        ('BERISLAV BUJAN', 'HSP', 5671, 5.65),
        ('ERNEST CUKROV', 'ASH', 1069, 1.06),
        ('SLAVKO LINIĆ', 'SDP', 39016, 38.87),
        ('IVICA MALATESTINIĆ', 'HSLS', 12885, 12.84),
        ('SLAVKO MEŠTROVIĆ', 'HKDS', 4978, 4.96),
        ('ANTONIJA PINTAR', 'SDU', 3113, 3.10),
        ('HRVOJE ŠARINIĆ', 'HDZ', 32559, 32.44),
    ], 'winner': 'SLAVKO LINIĆ'},
    10: {'registered': 100655, 'cast': 49560, 'invalid': 1941, 'candidates': [
        ('DRAŽEN BOBINAC', 'HDZ', 30831, 64.75),
        ('SLAVKO DEGORICIJA', 'HND,HNS,HSS,HSLS,HSP-1861,IDS,SDP', 10457, 21.96),
        ('NEBOJŠA MAGDIĆ', 'HSP', 4968, 10.43),
        ('IVAN MILKOVIĆ', 'Nezavisni kandidat', 1363, 2.86),
    ], 'winner': 'DRAŽEN BOBINAC'},
    11: {'registered': 148655, 'cast': 109524, 'invalid': 3494, 'candidates': [
        ('ĐURO DEČAK', 'HDZ', 57054, 53.81),
        ('ZDENKO MATEK', 'HSP', 8655, 8.16),
        ('FRANJO ODOBAŠIĆ', 'HSS,HSLS,HNS,HND,SDP', 40321, 38.03),
    ], 'winner': 'ĐURO DEČAK'},
    12: {'registered': 121317, 'cast': 85273, 'invalid': 2737, 'candidates': [
        ('MIRO ANTUNOVIĆ', 'HSP', 4716, 5.71),
        ('MATO GRGIĆ dr.med.', 'SBHS', 5644, 6.84),
        ('ĐURO JAPARIĆ', 'Nezavisni kandidat', 1052, 1.27),
        ('MATO KOLUNDŽIĆ', 'HKDU', 2438, 2.95),
        ('Mr. ANTUN PITLOVIĆ dr.med.', 'HDZ', 45263, 54.84),
        ('JERKO ZOVAK', 'SDP,HSLS,HSS,HNS,HND', 22328, 27.05),
        ('TOMISLAV ŽUPAN', 'Nezavisni kandidat', 1095, 1.33),
    ], 'winner': 'Mr. ANTUN PITLOVIĆ dr.med.'},
    13: {'registered': 132929, 'cast': 70483, 'invalid': 2310, 'candidates': [
        ('DINKO BRKIĆ', 'HND,HNS,HSS,HSLS,HSP-1861,IDS,SDP', 18522, 27.17),
        ('MLADEN KOSTIĆ', 'DA', 2490, 3.65),
        ('VLADISLAV KRPINA', 'HSP', 8472, 12.43),
        ('VALENTINA MEIĆ', 'HSNZ', 1161, 1.70),
        ('JOSO ŠKARA', 'HDZ', 36014, 52.83),
        ('JULIJA ZDRAVKOVIĆ', 'SDU', 1514, 2.22),
    ], 'winner': 'JOSO ŠKARA'},
    14: {'registered': 108578, 'cast': 85751, 'invalid': 2395, 'candidates': [
        ('ZLATKO BENAŠIĆ', 'HSLS', 23607, 28.32),
        ('Dr. NEDELJKO BOSANAC', 'Nezavisni kandidat', 1443, 1.73),
        ('BRANIMIR GLAVAŠ', 'HDZ', 44853, 53.81),
        ('DAVOR KRTIĆ', 'Nezavisni kandidat', 6088, 7.30),
        ('JOSIP VUKOVIĆ', 'HSP', 7365, 8.84),
    ], 'winner': 'BRANIMIR GLAVAŠ'},
    15: {'registered': 88117, 'cast': 63671, 'invalid': 1760, 'candidates': [
        ('MILE DADIĆ', 'Nezavisni kandidat', 2679, 4.33),
        ('DANIEL SRB', 'HSP', 5752, 9.29),
        ('VLADIMIR ŠEKS', 'HDZ', 36001, 58.15),
        ('IVICA ŠUTALO', 'HSLS', 17479, 28.23),
    ], 'winner': 'VLADIMIR ŠEKS'},
    16: {'registered': 123654, 'cast': 58578, 'invalid': 1777, 'candidates': [
        ('BOŠKO BARANOVIĆ', 'DA', 1585, 2.79),
        ('ANA DEKOVIĆ', 'SDU', 796, 1.40),
        ('JOSIP JURAS', 'HDZ', 28546, 50.26),
        ('BORE KAREGA', 'Nezavisni kandidat', 2004, 3.53),
        ('KRSTE NAKIĆ-ALFIREVIĆ', 'HSP', 3160, 5.56),
        ('VICE VUKOV', 'HNS,HSLS,HSS,SDP,HND,HSP-1861', 20710, 36.46),
    ], 'winner': 'JOSIP JURAS'},
    17: {'registered': 121265, 'cast': 81125, 'invalid': 2717, 'candidates': [
        ('ANTUN KLADARIĆ', 'HSP', 6246, 7.97),
        ('ANTO LOVRIĆ', 'HSS,SBHS', 17674, 22.54),
        ('JURAJ NJAVRO', 'HDZ', 44983, 57.37),
        ('MARIJAN ŽIVKOVIĆ', 'Nezavisni kandidat', 9505, 12.12),
    ], 'winner': 'JURAJ NJAVRO'},
    18: {'registered': 101151, 'cast': 71742, 'invalid': 2641, 'candidates': [
        ('MARINKO GRUBIŠIĆ-ČABO', 'DA', 3023, 4.37),
        ('ANTON KOVAČEV', 'HDZ', 33975, 49.17),
        ('MARIO PITEŠA', 'HSP', 3864, 5.59),
        ('ANTE PRKAČIN', 'HNS,HSLS,HSS,SDP,HND', 27061, 39.16),
        ('TATJANA VIDOVIĆ', 'SDU', 1178, 1.70),
    ], 'winner': 'ANTON KOVAČEV'},
    19: {'registered': 120350, 'cast': 87760, 'invalid': 2676, 'candidates': [
        ('BORISLAV ALERIĆ', 'HSP', 9541, 11.21),
        ('Mr. PETAR KROLO', 'HSLS', 21743, 25.55),
        ('ROZINA LOVRIĆ', 'SDU', 2526, 2.97),
        ('GABRIJEL POPIĆ', 'DA', 5307, 6.24),
        ('JURE RADIĆ', 'HDZ', 45967, 54.03),
    ], 'winner': 'JURE RADIĆ'},
    20: {'registered': 126726, 'cast': 94993, 'invalid': 2372, 'candidates': [
        ('BORIS BOBAN', 'Nezavisni kandidat', 1499, 1.62),
        ('Dr. ZDRAVKA BOŽIKOV', 'HKDS', 2815, 3.04),
        ('TEO KLARIĆ', 'HSP', 6335, 6.84),
        ('MATE MALJKOVIĆ', 'Nezavisni kandidat', 779, 0.84),
        ('JADRANKA MAVRO', 'SDU', 3000, 3.24),
        ('IVAN PLEIĆ', 'Nezavisni kandidat', 1094, 1.18),
        ('NIKOLA ŠIMUNOVIĆ', 'ASH,DA', 7685, 8.30),
        ('Mr. ANTE TUKIĆ dr.med.', 'HSLS', 38228, 41.27),
        ('NADAN VIDOŠEVIĆ', 'HDZ', 31186, 33.67),
    ], 'winner': 'Mr. ANTE TUKIĆ dr.med.'},
    21: {'registered': 121637, 'cast': 89383, 'invalid': 2208, 'candidates': [
        ('BRANKA AJREDINI', 'HSNZ', 1461, 1.68),
        ('PETAR FABRIS', 'HSP', 3097, 3.55),
        ('IVAN JAKOVČIĆ', 'IDS', 65283, 74.89),
        ('DENIS JELENKOVIĆ', 'HDZ', 13491, 15.48),
        ('ANTE MIHOVILOVIĆ dr.med.', 'INS', 3843, 4.41),
    ], 'winner': 'IVAN JAKOVČIĆ'},
    22: {'registered': 98599, 'cast': 71838, 'invalid': 1850, 'candidates': [
        ('ZDRAVKO BASELLI', 'HSNZ', 324, 0.46),
        ('VIDO BOGDANOVIĆ', 'HSS,HSLS,HSP-1861,HNS,SDP', 23044, 32.93),
        ('MATE GRANIĆ', 'HDZ', 33523, 47.90),
        ('IGOR LEGAZ', 'DA', 1000, 1.43),
        ('VJEKOSLAV-LUJO LASIĆ', 'HSP', 1676, 2.39),
        ('IVICA MOLNAR SOLJANAC', 'HOP,HS', 340, 0.49),
        ('Dr. ZVONIMIR ŠEPAROVIĆ', 'Nezavisni kandidat', 9037, 12.91),
        ('DARKA ŠUTIĆ', 'SDU', 1044, 1.49),
    ], 'winner': 'MATE GRANIĆ'},
    23: {'registered': 109669, 'cast': 83490, 'invalid': 3163, 'candidates': [
        ('JOSIP KOLARIĆ', 'HSP', 2722, 3.39),
        ('BRANKO LEVAČIĆ', 'HSLS,HSS,SDP,HNS,HND,HSP-1861', 40496, 50.41),
        ('ĐURO MAJERČAK dr.med.', 'HKDU', 3215, 4.00),
        ('Mr. DRAGUTIN PALAŠEK', 'ASH', 1007, 1.25),
        ('ZDRAVKO PREPOLEC dr.med.', 'KDM,HKDS,KNS', 4657, 5.80),
        ('MARIJAN RAMUŠĆAK', 'HDZ', 22119, 27.54),
        ('VLADIMIR TURK dr.stom.', 'HDSS', 6111, 7.61),
    ], 'winner': 'BRANKO LEVAČIĆ'},
    24: {'registered': 138378, 'cast': 98922, 'invalid': 2527, 'candidates': [
        ('Dr. ŽARKO DOMLJAN', 'HDZ', 37673, 39.08),
        ('IVAN KRANJČINA', 'HSP', 12551, 13.02),
        ('MARIO LIVAJA', 'HSLS', 32113, 33.31),
        ('MARIO MANDARIĆ', 'Nezavisni kandidat', 2685, 2.79),
        ('Dr. VLATKO MIĆKOVIĆ', 'HS', 995, 1.03),
        ('ZORICA MILOŠEVIĆ', 'SDU', 5152, 5.34),
        ('MLADEN SCHWARTZ', 'HDMS', 1686, 1.75),
        ('ANTUN SOLIĆ', 'HKDU', 3540, 3.67),
    ], 'winner': 'Dr. ŽARKO DOMLJAN'},
    25: {'registered': 156993, 'cast': 110253, 'invalid': 3479, 'candidates': [
        ('Mr. BOŽO BIŠKUPIĆ', 'HDZ', 41153, 38.54),
        ('Dr. ALOJZ BRKIĆ', 'HND,HNS,HSS,HSLS,HSP-1861,IDS,SDP', 42109, 39.44),
        ('JOSIP ČORKO', 'HKDU', 3358, 3.14),
        ('MATO GJURANOVIĆ', 'HS', 525, 0.49),
        ('MLADEN PAVKOVIĆ', 'HNP-SH', 1485, 1.39),
        ('NEVENKA RAHIĆ', 'SDU', 2329, 2.18),
        ('ZDENKO REBA', 'HSNZ', 975, 0.91),
        ('JOZO RENIĆ', 'HSP', 7614, 7.13),
        ('TUGA TARLE-CRNOGORAC', 'Nezavisni kandidat', 1717, 1.61),
        ('IVAN VEKIĆ', 'Nezavisni kandidat', 5509, 5.16),
    ], 'winner': 'Dr. ALOJZ BRKIĆ'},
    26: {'registered': 132556, 'cast': 92354, 'invalid': 1929, 'candidates': [
        ('SILVIJE DEGEN', 'ASH', 14598, 16.14),
        ('ZVONKO KOPRIVČIĆ', 'HS', 670, 0.74),
        ('ANKICA LUČIĆ', 'HDMS', 803, 0.89),
        ('BRANKO MIKŠA', 'HDZ', 32536, 35.98),
        ('DAVORIN POKRAJAC', 'DGS', 436, 0.48),
        ('BRANKO POLAK', 'HSP', 6957, 7.69),
        ('NINA SABOL', 'SDU', 2357, 2.61),
        ('Mr. IVO ŠKRABALO', 'HSLS', 32068, 35.46),
    ], 'winner': 'BRANKO MIKŠA'},
    27: {'registered': 106821, 'cast': 72125, 'invalid': 2246, 'candidates': [
        ('MILAN BUJAN', 'Nezavisni kandidat', 626, 0.90),
        ('BOŽIDAR GALLI', 'HKDS', 917, 1.31),
        ('Dr. IVICA KOSTOVIĆ', 'HDZ', 27363, 39.16),
        ('JASMINKO MIKLEC', 'HSNZ', 724, 1.04),
        ('TATJANA ROKVIĆ', 'SDU', 1407, 2.01),
        ('Mr. MIROSLAV ROŽIĆ', 'HSP', 3368, 4.82),
        ('MIROSLAV RUDOLF', 'HS', 201, 0.29),
        ('MLADEN ŠARIĆ', 'Nezavisni kandidat', 487, 0.70),
        ('Dr. ZDRAVKO TOMAC', 'SDP,HSLS,HSS,HNS,HND', 33927, 48.55),
        ('ZVONIMIR TRUSIĆ', 'Nezavisni kandidat', 550, 0.79),
        ('Dr. PETAR VUČIĆ', 'HDMS', 309, 0.44),
    ], 'winner': 'Dr. ZDRAVKO TOMAC'},
    28: {'registered': 113188, 'cast': 75940, 'invalid': 2289, 'candidates': [
        ('RUŽICA ĆAVAR dr.stom. dr.med.', 'HNP-SH', 2714, 3.68),
        ('Dr. ANDRIJA HEBRANG', 'HDZ', 33984, 46.14),
        ('SLAVKO KRNJAK', 'HSS,HSLS,SDP,HND,HNS,HSP-1861', 29451, 39.99),
        ('ALOJZIJE ŠLAT', 'HKDS', 1262, 1.71),
        ('TONČI TADIĆ', 'HSP', 4760, 6.46),
        ('MARIJA VEGRIN', 'SDU', 1480, 2.01),
    ], 'winner': 'Dr. ANDRIJA HEBRANG'},
}

# National-minority special units (pages 37-41). Units 1-4 elect one member each;
# the 5th (Serbs) elects three, so its ballots carry up to three votes and the
# percentages are shares of total votes cast, not of valid ballots.
MINORITY_UNITS = {
    1: {'name': 'BUJE', 'minority': 'talijanska', 'seats': 1,
        'registered': 17439, 'cast': 10436, 'invalid': 275, 'candidates': [
            ('Dr. TULLIO PERSI', 'Nezavisni kandidat', 1538, 15.14),
            ('Dr. FURIO RADIN', 'Nezavisni kandidat', 8623, 84.86),
        ], 'winners': ['Dr. FURIO RADIN']},
    2: {'name': 'OSIJEK', 'minority': 'mađarska', 'seats': 1,
        'registered': 6938, 'cast': 3292, 'invalid': 110, 'candidates': [
            ('DANIEL DEME DEŽE', 'Nezavisni kandidat', 290, 9.11),
            ('SANDOR JAKAB', 'Nezavisni kandidat', 1084, 34.07),
            ('STEVAN KIŠPAL', 'Nezavisni kandidat', 374, 11.75),
            ('TIBOR SANTO', 'HSLS', 741, 23.29),
            ('IMRE TAUS', 'Mađarska narodna stranka Hrvatske', 693, 21.78),
        ], 'winners': ['SANDOR JAKAB']},
    3: {'name': 'DARUVAR', 'minority': 'češka i slovačka', 'seats': 1,
        'registered': 10216, 'cast': 6786, 'invalid': 274, 'candidates': [
            ('ANDRIJA PEKAR', 'Nezavisni kandidat', 884, 13.57),
            ('NJEGOVAN STAREK', 'Nezavisni kandidat', 3352, 51.47),
            ('ZDENKA ZVONAREK', 'HDZ', 2276, 34.95),
        ], 'winners': ['NJEGOVAN STAREK']},
    4: {'name': 'OSIJEK', 'minority': 'rusinska, ukrajinska, njemačka i austrijska',
        'seats': 1,
        'registered': 2578, 'cast': 1389, 'invalid': 20, 'candidates': [
            ('ĐURO HARHAJ', 'Nezavisni kandidat', 259, 18.92),
            ('Mr. MIROSLAV KIŠ', 'Nezavisni kandidat', 466, 34.04),
            ('IVAN KOROPATNICKI', 'Nezavisni kandidat', 217, 15.85),
            ('ŠIMO MARKSER', 'HND', 43, 3.14),
            ('JASMINKA PETTER', 'Nezavisni kandidat', 50, 3.65),
            ('VESNA PICHLER', 'Nezavisni kandidat', 334, 24.40),
        ], 'winners': ['Mr. MIROSLAV KIŠ']},
    5: {'name': '5. posebna izborna jedinica', 'minority': 'srpska', 'seats': 3,
        'registered': 174611, 'cast': 55013, 'invalid': 5280, 'candidates': [
            ('MILAN ĐUKIĆ', 'SNS', 30382, 27.05),
            ('ŽIVKO JUZBAŠIĆ', 'ASH', 12036, 10.72),
            ('VELJKO MILJEVIĆ', 'SNS', 12821, 11.42),
            ('VESELIN PEJNOVIĆ', 'SNS', 24857, 22.13),
            ('Dr. MILORAD PUPOVAC', 'ASH', 17639, 15.70),
            ('MILE STOJSAVLJEVIĆ', 'Nezavisni kandidat', 3567, 3.18),
            ('NEDELJKO VIŠNIĆ', 'ASH', 5927, 5.28),
            ('BOŠKO VUJNOVIĆ', 'Nezavisni kandidat', 5088, 4.53),
        ], 'winners': ['MILAN ĐUKIĆ', 'VESELIN PEJNOVIĆ', 'Dr. MILORAD PUPOVAC']},
}
