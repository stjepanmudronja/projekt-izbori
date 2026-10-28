"""Corrections to the OCR reading of the 1990 Vijeće udruženog rada report,
each read off the scan (`tools/extract_scanned_pdf.py`). Applied by
`sabor_1990_vur_parse --write` before its checks.

`FIGURES`: (unit, round) -> (registered, cast, invalid) as printed.
`VOTES`: (unit, round) -> every candidate's votes, in printed order.
`CANDIDATES`: (unit, round) -> the round's candidates in full, as
(name, residence, party, votes), where OCR lost or merged some; `party` is
comma-joined abbreviations, as in the data module.
`PARTY`: (unit, round, position) -> one candidate's party, where OCR lost it
or gave it a neighbour's line (position counts from 1, in printed order).
`WINNERS`: unit -> the elected candidate as printed.
`NAMES`: unit -> the unit's name, where the heading was lost or misread.
`CONFIRMED`: (unit, round) whose candidates fall short of cast - invalid by
more than the parser's tolerance as printed — the report's own gap.
`NO_VOTES`: units whose vote counts the scan lost (cut off at the right
edge): figures, candidates and winner only; every candidate's votes are None.
`ABSENT`: units printed in neither report.
`SPELLINGS`: a name or place as `restore` spells it -> as printed, where the
vocabulary guesses wrong or OCR debris survives.
`UNITS`: unit -> (name, [((registered, cast, invalid), candidates)], winner),
whole units transcribed from the supplementary report (`vur_dopuna`), whose
OCR lost most name lines; each replaces the unit, including any reading of
it in the main report.
"""

FIGURES = {
    (43, 2): (12656, 9229, 152),
    (91, 2): (10246, 7686, 681),
    (76, 1): (14890, 10347, 336),
    (90, 2): (9293, 7203, 151),
    (109, 2): (10085, 7362, 177),
}

VOTES = {
    (43, 2): [4955, 4122],      # 4955 printed faintly; reconciles exactly
    (79, 2): [1627, 1731, 1410],  # Matija's smudged past its "1"; the rest of cast - invalid
    (157, 2): [3198, 904, 825],
}

CANDIDATES = {
    # Turkalj's line read as noise.
    (94, 2): [('Milorad Bekić', 'Topusko', 'SKH-SDP,SSH', 3835),
              ('Mile Turkalj', 'Slunj', 'SKH-SDP', 2280)],
    # Faint last candidate, read by neither pass.
    (36, 2): [('Ivan Kušen', 'Ivanec', 'HDZ', 3443),
              ('Stjepan Gašparić', 'Ladanje Donje', 'SKH-SDP', 1704),
              ('Željko Brezovec', 'Ivanec', 'HSLS,KNS', 662),
              ('Zlatko Koračević', 'Bednja', 'NK', 535)],
    # 07's name line lost, its party joined to 06.
    (56, 1): [('Stjepan Bačić', 'Zagreb', 'NK', 188),
              ('Dr Velimir Borovečki', 'Zagreb', 'NK', 160),
              ('Mr Nikica Car', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 598),
              ('Dr Frane Golem', 'Zagreb', 'HDZ', 2676),
              ('Dr Andrija Hebrang', 'Zagreb', 'NK', 366),
              ('Dr Vlado Jukić', 'Sesvete', 'NK', 77),
              ('Dr Petar Juzbašić', 'Zagreb', 'SKH-SDP', 1237),
              ('Dr Milivoj Kačić', 'Zagreb', 'NK', 134),
              ('Dr Miljenko Primorac', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 415),
              ('Dr Dušan Sabolović', 'Zagreb', 'NK', 143)],
}

PARTY = {
    (54, 1, 4): 'NK',
    (157, 1, 5): 'NK',
    (157, 1, 6): 'HDS,KNS',
}

WINNERS = {
}

NAMES = {
    15: 'SLAVONSKI BROD III',
    38: 'KRAPINA',
    55: 'ZAGREB - MAKSIMIR I',
    65: 'ZAGREB - PEŠČENICA III',
}

CONFIRMED = {
    (5, 1),     # Osijek IV: candidates 8,755 of 9,025 valid; every count checked on the scan
    (41, 1),    # Ivanić Grad: 10,899 of 11,433
    (97, 1),    # Ogulin: 9,419 votes + 304 invalid > 9,587 cast, every count clear
    (154, 1),   # Split (supplement): 7,111 of 7,163; all clearly printed
    (160, 1),   # Split (supplement): 5,792 of 5,818
    (160, 2),   # Split (supplement): 4,052 of 4,055
}

SPELLINGS = {
    # Names
    'Borislav Meandzija': 'Borislav Meandžija',
    'Boro Kaluder': 'Boro Kaluđer',
    'Branko Kovačic': 'Branko Kovačić',
    'Dolić Smid': 'Dolfi Šmid',
    'Dušan Saša': 'Dušan Šaša',
    'Ivan Prelcec': 'Ivan Prelčec',
    'Ivan Siepanić': 'Ivan Stepanić',
    'Ivo Corvilo': 'Ivo Čorvilo',
    'Josip (zvonko) Čabo': 'Josip (Zvonko) Čabo',
    'Josip Secen': 'Josip Sečen',
    'Mato Ecimović': 'Mato Ećimović',
    'Nikola Maćešić': 'Nikola Mačešić',
    'Petar Ećimović': 'Petar Ečimović',     # Mato in unit 21 is Ećimović
    'Radomir Šimić': 'Radomir Simić',       # printed without the caron
    'Stipan Simunović': 'Stipan Šimunović',
    'Stjepan Hrešć': 'Stjepan Hrešč',       # as printed
    'Stjepan Spanić': 'Stjepan Španić',
    'Šime Jagicić': 'Šime Jagičić',
    'Tomislav Spoljarić': 'Tomislav Špoljarić',
    'Vinko Zigo': 'Vinko Žigo',
    'Vlado Jaksić': 'Vlado Jakšić',
    'Zlatko Blaziničić': 'Zlatko Blažiničić',
    'Zoran Staré': 'Zoran Stare',
    'Zvonimir Pavcec': 'Zvonimir Pavčec',
    'Ćiro Grubišic': 'Ćiro Grubišić',
    # Places
    'Cubinec': 'Čubinec',
    'Dubrava :': 'Dubrava',
    'Dunjkove(': 'Dunjkovec',
    'Kucine-Solin': 'Kučine-Solin',
    'Lagre:': 'Zagreb',
    'Lukarisće': 'Lukarišće',
    'Pažin': 'Pazin',
    'Pliivička Jezera': 'Plitvička Jezera',
    'Slavonski Brod :': 'Slavonski Brod',
    'Stanici': 'Stanići',
    'Sumarina': 'Šumarina',
    'Veliki Ravna': 'Veliki Raven',
    'Zagreb • Tji': 'Zagreb',
}

NO_VOTES = {
    91,     # Karlovac II: every count lost its last digit to the page edge
}

ABSENT = {83, 141, 148, 151}    # page numbers run on without them


# The supplementary report (1990_1_6_..._dopunski_izvjestaj.pdf), pages 13-26,
# read off the scan; every round reconciles exactly unless CONFIRMED.
UNITS = {
    49: ('ZAGREB - CENTAR V', [
        ((15099, 10346, 137), [
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
            ('Ivica Vuković', 'Zagreb', 'NK', 110)]),
        ((15125, 7799, 94), [
            ('Damir Mejovšek', 'Zagreb', 'HDZ', 4004),
            ('Dr Adolf Dragičević', 'Zagreb', 'SKH-SDP', 1822),
            ('Dr Tihomil Maštrović', 'Zagreb', 'HSLS,KNS', 1879)]),
    ], 'Damir Mejovšek'),
    50: ('ZAGREB - CENTAR VI', [
        ((13748, 8953, 1305), [
            ('Tomislav Bilić', 'Zagreb', 'NK', 2010),
            ('Ljerka Ercegović', 'Zagreb', 'SKH-SDP', 4003),
            ('Jadranka Japunčić', 'Zagreb', 'NK', 762),
            ('Katica Pezo', 'Zagreb', 'NK', 873)]),
        ((12690, 6430, 937), [
            ('Ljerka Ercegović', 'Zagreb', 'SKH-SDP', 2825),
            ('Tomislav Bilić', 'Zagreb', 'NK', 1403),
            ('Katica Pezo', 'Zagreb', 'NK', 614),
            ('Jadranka Japunčić', 'Zagreb', 'NK', 651)]),
    ], 'Ljerka Ercegović'),
    67: ('ZAGREB - PEŠČENICA V', [
        ((7906, 6172, 109), [
            ('Joso Bičanić', 'Zagreb', 'NK', 227),
            ('Franjo Dubrović', 'Zagreb', 'HSS,KNS', 378),
            ('Stjepan Klenkar', 'Zagreb', 'NK', 150),
            ('Petar Radić', 'Zagreb', 'PZK', 136),
            ('Branko Sabljak', 'Zagreb', 'HDZ', 2834),
            ('Nenad Starc', 'Zagreb', 'SKH-SDP', 1478),
            ('Zvonimir Šain', 'Zagreb', 'HSLS,KNS', 860)]),
        ((7733, 5402, 74), [
            ('Branko Sabljak', 'Zagreb', 'HDZ', 2756),
            ('Nenad Starc', 'Zagreb', 'SKH-SDP', 1483),
            ('Zvonimir Šain', 'Zagreb', 'HSLS,KNS', 1089)]),
    ], 'Branko Sabljak'),
    73: ('ZAGREB - TREŠNJEVKA III', [
        ((7369, 4513, 225), [
            ('Željko Gudan', 'Zagreb', 'HDZ', 2346),
            ('Juraj Jergović', 'Zagreb', 'SKH-SDP', 1148),
            ('Tomislav Madžar', 'Zagreb', 'NK', 464),
            ('Stanko Tratnik', 'Zagreb', 'SSH', 330)]),
        ((8414, 4003, 153), [
            ('Željko Gudan', 'Zagreb', 'HDZ', 2085),
            ('Juraj Jergović', 'Zagreb', 'SKH-SDP', 1188),
            ('Tomislav Madžar', 'Zagreb', 'NK', 368),
            ('Stanko Tratnik', 'Zagreb', 'SSH', 209)]),
    ], 'Željko Gudan'),
    74: ('ZAGREB - TREŠNJEVKA IV', [
        ((10403, 7173, 1339), [
            ('Miodrag Petrović', 'Zagreb', 'NK', 2815),
            ('Janko Radić', 'Zagreb', 'SKH-SDP', 3019)]),
        ((10368, 5912, 1380), [
            ('Janko Radić', 'Zagreb', 'SKH-SDP', 2502),
            ('Miodrag Petrović', 'Zagreb', 'NK', 2030)]),
    ], 'Janko Radić'),
    75: ('ZAGREB - TREŠNJEVKA V', [
        ((13739, 10658, 262), [
            ('Mirko Crnojević', 'Zagreb', 'SSH', 361),
            ('Ivan Hren', 'Zagreb', 'HDZ', 4679),
            ('Branko Jakopec', 'Zagreb', 'NK', 159),
            ('Vesna Kanižaj', 'Zagreb', 'NK', 243),
            ('Marija Lončar-Matijašević', 'Zagreb', 'NK', 156),
            ('Branko Molan', 'Zagreb', 'SKH-SDP', 2174),
            ('Julijus Pevalek', 'Zagreb', 'NK', 720),
            ('Dr Valentin Puževski', 'Križevci', 'NK', 248),
            ('Vlado Sužnjević', 'Zagreb', 'SDSH,KNS', 1229),
            ('Dr Petar Tocilj', 'Zagreb', 'NK', 427)]),
        ((13966, 9315, 277), [
            ('Ivan Hren', 'Zagreb', 'HDZ', 5589),
            ('Branko Molan', 'Zagreb', 'SKH-SDP', 3449)]),
    ], 'Ivan Hren'),
    106: ('RIJEKA VIII', [
        ((16230, 13061, 243), [
            ('Ivan Benčić', 'Rijeka', 'HDZ', 2722),
            ('Darko Deković', 'Rijeka', 'SDSH,HSLS,HKDS,HDS,KNS', 2139),
            ('Manon Giron', 'Rijeka', 'SKH-SDP', 5974),
            ('Dr Danilo Pavešić', 'Rijeka', 'NK', 1458),
            ('Boris Ritoša', 'Rijeka', 'NK', 525)]),
        ((16522, 12341, 210), [
            ('Manon Giron', 'Rijeka', 'SKH-SDP', 6767),
            ('Ivan Benčić', 'Rijeka', 'HDZ', 3536),
            ('Dr Danilo Pavešić', 'Rijeka', 'NK', 1828)]),
    ], 'Manon Giron'),
    120: ('ZADAR III', [
        ((15145, 12596, 475), [
            ('Boris Bogdanić', 'Zadar', 'NK', 568),
            ('Dr Slobodan Čače', 'Zadar', 'HSLS,KNS', 1310),
            ('Miljenko Domijan', 'Zadar', 'SSH', 3082),
            ('Miloš Kalinić', 'Zadar', 'NK', 554),
            ('Jure Kožul', 'Zadar', 'NK', 514),
            ('Mr Vinko Marinković', 'Zadar', 'NK', 387),
            ('Vice Profaca', 'Zadar', 'HDZ', 5706)]),
        ((16525, 8984, 208), [
            ('Vice Profaca', 'Zadar', 'HDZ', 4883),
            ('Miljenko Domijan', 'Zadar', 'SSH', 3893)]),
    ], 'Vice Profaca'),
    142: ('OSIJEK', [
        ((37646, 32730, 3419), [
            ('Ljubomir Čakan', 'Vukovar', 'NK', 2171),
            ('Vladimir Dragun', 'Ilok', 'SKH-SDP', 5227),
            ('Antun Lovrić', 'Bošnjaci', 'HSS,KNS', 11310),
            ('Vlado Mandić', 'Čepin', 'SSH', 2499),
            ('Ilija Mirčetić', 'Komletinci', 'SSH', 2787),
            ('Ivan Tomičić', 'Đakovo', 'NK', 5317)]),
        ((39638, 21119, 652), [
            ('Antun Lovrić', 'Bošnjaci', 'HSS,KNS', 12364),
            ('Vladimir Dragun', 'Ilok', 'SKH-SDP', 3120),
            ('Ilija Mirčetić', 'Komletinci', 'SSH', 2697),
            ('Vlado Mandić', 'Čepin', 'SSH', 2286)]),
    ], 'Antun Lovrić'),
    145: ('DARUVAR', [
        ((32393, 29351, 2146), [
            ('Radomir Dejanović', 'Suhopolje', 'SKH-SDP', 10344),
            ('Ivo Gerendjir', 'Grubišno Polje', 'SSH', 4641),
            ('Vlado Katančić', 'Lukač', 'HDZ', 12220)]),
        ((32451, 26842, 1803), [
            ('Vlado Katančić', 'Lukač', 'HDZ', 12650),
            ('Radomir Dejanović', 'Suhopolje', 'SKH-SDP', 9913),
            ('Ivo Gerendjir', 'Grubišno Polje', 'SSH', 2476)]),
    ], 'Vlado Katančić'),
    150: ('SISAK', [
        ((29409, 26938, 1339), [
            ('Nikola Culek', 'Tišina Desna', 'HSLS,KNS', 2950),
            ('Đurđa Gmaz', 'Stara Drenčina', 'HDZ', 7520),
            ('Đuro Kljajić', 'Staro Selo', 'SSH', 11497),
            ('Dragutin Mirosavljević', 'Novska', 'SSH', 3632)]),
        # Culek's party as printed: HSLS in round 1, HSS in round 2.
        ((29625, 26127, 943), [
            ('Đuro Kljajić', 'Staro Selo', 'SSH', 13827),
            ('Đurđa Gmaz', 'Stara Drenčina', 'HDZ', 8323),
            ('Dragutin Mirosavljević', 'Novska', 'SSH', 1349),
            ('Nikola Culek', 'Tišina Desna', 'HSS,KNS', 1685)]),
    ], 'Đuro Kljajić'),
    154: ('SPLIT', [
        ((10222, 8030, 867), [
            ('Stipe Čarić', 'Brnaze-Sinj', 'KNS', 5188),
            ('Pave Klapirić', 'Vinjani Donji Imotski', 'NK', 1923)]),
    ], 'Stipe Čarić'),
    160: ('SPLIT', [
        ((15977, 5943, 125), [
            ('Ante Bego', 'Split', 'SUSPS', 1732),
            ('Mate Brajković', 'Split', 'HS', 347),
            ('Marko Kovač', 'Šibenik', 'SUSPS', 783),
            ('Jozo Topić', 'Šibenik', 'HDZ', 2930)]),
        ((15600, 4109, 54), [
            ('Jozo Topić', 'Šibenik', 'HDZ', 1968),
            ('Ante Bego', 'Split', 'SUSPS', 1721),
            ('Marko Kovač', 'Šibenik', 'SUSPS', 363)]),
    ], 'Jozo Topić'),
}


def _lines(codes):
    from .sabor_1990_vur_parse import PARTY_NAMES
    names = {}
    for name, code in PARTY_NAMES.items():
        names.setdefault(code, name)
    return [('- ' if c == 'KNS' else '') + names[c] for c in codes.split(',')]


def apply(all_units):
    for unit, (name, rounds, winner) in UNITS.items():
        all_units[unit] = {
            'number': unit, 'name': name, 'winner': winner, 'file': 'vur_dopuna',
            'rounds': [{'figures': figures, 'orphans': [], 'candidates': [
                {'no': i, 'name': n, 'residence': r, 'party': _lines(p), 'votes': v,
                 'exact': True}
                for i, (n, r, p, v) in enumerate(cands, 1)]}
                for figures, cands in rounds]}
    for (unit, rnd), figures in FIGURES.items():
        all_units[unit]['rounds'][rnd - 1]['figures'] = figures
    for (unit, rnd), cands in CANDIDATES.items():
        u = all_units.setdefault(unit, {'number': unit, 'name': NAMES.get(unit, ''),
                                        'rounds': [], 'winner': None, 'file': 'manual'})
        while len(u['rounds']) < rnd:
            u['rounds'].append({'candidates': [], 'figures': None})
        u['rounds'][rnd - 1]['orphans'] = []
        u['rounds'][rnd - 1]['candidates'] = [
            {'no': i, 'name': n, 'residence': r, 'party': _lines(p), 'votes': v,
             'exact': True}
            for i, (n, r, p, v) in enumerate(cands, 1)]
    for (unit, rnd), votes in VOTES.items():
        cands = all_units[unit]['rounds'][rnd - 1]['candidates']
        if len(votes) != len(cands):
            raise ValueError(f'{unit} r{rnd}: {len(votes)} votes for {len(cands)} candidates')
        for c, v in zip(cands, votes):
            c['votes'] = v
    for (unit, rnd, pos), codes in PARTY.items():
        all_units[unit]['rounds'][rnd - 1]['candidates'][pos - 1]['party'] = _lines(codes)
    for unit, winner in WINNERS.items():
        all_units[unit]['winner'] = winner
    for unit, name in NAMES.items():
        all_units[unit]['name'] = name
    for unit, rnd in CONFIRMED:
        all_units[unit]['rounds'][rnd - 1]['confirmed'] = True
    for unit in NO_VOTES:
        all_units[unit]['no_votes'] = True
        for r in all_units[unit]['rounds']:
            r['orphans'] = []
            for c in r['candidates']:
                c['votes'] = None
