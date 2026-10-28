"""Transcription of the 1990 Vijeće općina election.

Source: `files/rezultati_sabor/1990/1990_1_3_Sabor_Rezultati_Vijece_opcina.pdf`
(109 pages) and its supplement `1990_1_4_…_dopunski_izvjestaj.pdf` (7 pages),
CCITT-G4 scans with no text layer, rendered with `tools/extract_scanned_pdf.py`
and read off the images.

Chamber B) of the 1990 Sabor, the "council of municipalities": every općina
returned one member, Grad Zagreb's fourteen općine one each plus one for the
Gradska zajednica općina Zagreb as a whole. 115 single-member units under the
same two-round majority rule as the Društveno-političko vijeće (Article 58 of
the electoral law): a majority in round 1 elects, otherwise the vote is
repeated and the round-2 leader elected.

Units 1-109 are the main report in its own (alphabetical, Zagreb last) order;
110-115 come from the supplement, which carries Hvar, Osijek, Rovinj, Sisak,
Split and Vukovar. Vukovar was printed as unfinished in the main report while
an appeal was pending at the Supreme Court; the supplement's note says it was
in fact decided on 6 May 1990.

Same shapes as `sabor_1990_dpv_data`: unit -> name, rounds, winner; each round
holds registered, cast, invalid and the candidates as (name, residence, party,
votes), in the report's order, `party` being comma-joined abbreviations from
`PARTIES`. Where the report labels a joint candidate differently in round 2
(Pezo "HDS - KNS" then plain "HDS"), both are kept as printed.

Checks: in every round, candidate votes + invalid never exceed `cast`, and the
named winner leads the deciding round. As in the DPV report the candidates
often fall short of `cast - invalid`, by 0 to a few hundred. The outliers are
the Gradska zajednica općina Zagreb (5,694 of 563,943, 1%) and Split round 1
(1,992, almost exactly its 1,994 invalid ballots, as if those were subtracted
twice in the report's own sum); both were re-read from the scan and stand.
"Pekota - Kopal" is a double surname, written here with a plain hyphen so
`person_name` does not strip the second half as a nickname.
"""
from .sabor_1990_dpv_data import (  # noqa: F401  (shared helpers)
    PARTIES as _DPV_PARTIES, party_label, person_name,
)

ELECTION_TYPE_SLUG = 'sabor_vo'
ELECTION_TYPE_NAME = 'Vijeće općina Sabora'

# Units whose voters are also counted in other units. The Gradska zajednica
# općina Zagreb (109) was elected by the whole city, every one of whose voters
# also voted in their own Zagreb općina (8, 14, 21, 53, 54, 59, 70, 78, 80, 86,
# 89, 90, 94, 105), so its electorate must not be added to the rest: the other
# 114 units sum to 3,533,210 registered in round 1, within 0.3% of the
# Društveno-političko vijeće's 3,544,112, and with it they would read 4.2 million.
OVERLAPPING_UNITS = {109}

PARTIES = {
    **_DPV_PARTIES,
    'DKS': 'Demokratska kršćanska stranka',
    'SUBNOR': 'Savez udruženja boraca NOR-a',
    'EFZP': 'Eko forum - Zeleni Pula',
    'LZR': 'Lista za Rab',
    'EPZAŠ': 'Ekološki pokret "Zelena akcija" Šibenik',
    'ADSH': 'Autonomni demokratski savez Hrvatske',
    'RUSED': 'Radikalno udruženje za Sjedinjene Evropske Države',
    'SZH': 'Savez zelenih Hrvatske',
    'USP': 'Udruženje samostalnih privrednika',
    'HRSS': 'Hrvatska republikanska seljačka stranka',
    'SGS': 'Sisački građanski savez',
    'GS': 'Građanska stranka',
}

DISTRICTS = {
    1: {'name': 'Beli Manastir', 'rounds': [
        {'registered': 40529, 'cast': 33816, 'invalid': 3205, 'candidates': [
            ('Marko Barišin', 'Draž', 'SSH', 5446),
            ('Boško Jančić', 'Beli Manastir', 'SKH-SDP', 9389),
            ('Imre Keteš', 'Beli Manastir', 'NK', 6006),
            ('Valentin Videmšek', 'Beli Manastir', 'SKH-SDP', 5672),
            ('Agica Vujaklija', 'Beli Manastir', 'SKH-SDP', 4098),
        ]},
        {'registered': 39764, 'cast': 27656, 'invalid': 2196, 'candidates': [
            ('Boško Jančić', 'Beli Manastir', 'SKH-SDP', 14761),
            ('Imre Keteš', 'Beli Manastir', 'NK', 6273),
            ('Marko Barišin', 'Draž', 'SSH', 4426),
        ]},
    ], 'winner': 'Boško Jančić'},
    2: {'name': 'Benkovac', 'rounds': [
        {'registered': 21714, 'cast': 19504, 'invalid': 483, 'candidates': [
            ('Marko Atlagić', 'Benkovac', 'SSH', 9183),
            ('Ante Mišura', 'Podlug', 'HDS,KNS', 7267),
            ('Marijan Vrkić', 'Benkovac', 'SKH-SDP', 2571),
        ]},
        {'registered': 21702, 'cast': 20019, 'invalid': 440, 'candidates': [
            ('Marko Atlagić', 'Benkovac', 'SSH', 10633),
            ('Ante Mišura', 'Podlug', 'HDS', 7528),
            ('Marijan Vrkić', 'Benkovac', 'SKH-SDP', 1418),
        ]},
    ], 'winner': 'Marko Atlagić'},
    3: {'name': 'Biograd na Moru', 'rounds': [
        {'registered': 11923, 'cast': 9774, 'invalid': 217, 'candidates': [
            ('Tihomir Crnogorac', 'Biograd na Moru', 'HDS,KNS', 965),
            ('Dr Josip Labar', 'Biograd na Moru', 'SKH-SDP', 1988),
            ('Ante Vulin', 'Pakoštane', 'HDZ', 6460),
        ]},
    ], 'winner': 'Ante Vulin'},
    4: {'name': 'Bjelovar', 'rounds': [
        {'registered': 48772, 'cast': 40618, 'invalid': 1585, 'candidates': [
            ('Dr Božidar Bišćan', 'Bjelovar', 'SKH-SDP', 8016),
            ('Zdravko Drobac', 'Bjelovar', 'NK', 1438),
            ('Vladimir Družinec', 'Bjelovar', 'SSH', 2971),
            ('Stipan Gojević', 'Bjelovar', 'HDS,KNS', 6010),
            ('Branko Knežević', 'Bjelovar', 'SKH-SDP', 5717),
            ('Slavko Raić', 'Bjelovar', 'NK', 567),
            ('Dane Sučić', 'Novoseljani', 'HDZ', 14294),
        ]},
        {'registered': 51116, 'cast': 37737, 'invalid': 931, 'candidates': [
            ('Dane Sučić', 'Novoseljani', 'HDZ', 17751),
            ('Dr Božidar Bišćan', 'Bjelovar', 'SKH-SDP', 15123),
            ('Stipan Gojević', 'Bjelovar', 'HDS', 3932),
        ]},
    ], 'winner': 'Dane Sučić'},
    5: {'name': 'Brač', 'rounds': [
        {'registered': 9595, 'cast': 8837, 'invalid': 592, 'candidates': [
            ('Griška Arnerić', 'Postira', 'SSH,SKH-SDP', 2496),
            ('Andrija Buljević', 'Supetar', 'SDSH,KNS', 2436),
            ('Božo Sinčić', 'Supetar', 'HDZ', 1905),
            ('Josip Štambuk', 'Supetar', 'SKH-SDP', 1408),
        ]},
        {'registered': 9736, 'cast': 8296, 'invalid': 348, 'candidates': [
            ('Griška Arnerić', 'Postira', 'SSH,SKH-SDP', 2977),
            ('Andrija Buljević', 'Supetar', 'SDSH,KNS', 4139),
            ('Josip Štambuk', 'Supetar', 'SKH-SDP', 832),
        ]},
    ], 'winner': 'Andrija Buljević'},
    6: {'name': 'Buje', 'rounds': [
        {'registered': 18555, 'cast': 14803, 'invalid': 2405, 'candidates': [
            ('Dario Forza', 'Umag', 'SSH', 6542),
            ('Dragoljub Kraljević', 'Buje', 'SKH-SDP', 5856),
        ]},
        {'registered': 18584, 'cast': 13157, 'invalid': 2136, 'candidates': [
            ('Dario Forza', 'Umag', 'SSH', 5444),
            ('Dragoljub Kraljević', 'Buje', 'SKH-SDP', 5577),
        ]},
    ], 'winner': 'Dragoljub Kraljević'},
    7: {'name': 'Buzet', 'rounds': [
        {'registered': 5674, 'cast': 5097, 'invalid': 289, 'candidates': [
            ('Mladenko Budan', 'Buzet', 'SDSH,KNS', 1194),
            ('Savo Černeha', 'Buzet', 'SKH-SDP', 2188),
            ('Gvido Jermaniš', 'Buzet', 'SSH', 1421),
        ]},
        {'registered': 5698, 'cast': 4974, 'invalid': 247, 'candidates': [
            ('Savo Černeha', 'Buzet', 'SKH-SDP', 2342),
            ('Gvido Jermaniš', 'Buzet', 'SSH', 1297),
            ('Mladenko Budan', 'Buzet', 'SDSH,KNS', 1077),
        ]},
    ], 'winner': 'Savo Černeha'},
    8: {'name': 'Centar - Zagreb', 'rounds': [
        {'registered': 46592, 'cast': 33414, 'invalid': 661, 'candidates': [
            ('Josip Bratulić', 'Zagreb', 'HKDS,KNS', 8359),
            ('Slavko Degoricija', 'Zagreb', 'HDZ', 13794),
            ('Stjepan Herceg', 'Zagreb', 'DKS', 2135),
            ('Josip Knjaz', 'Zagreb', 'SSH', 1168),
            ('Edo Murtić', 'Zagreb', 'SKH-SDP', 7297),
        ]},
        {'registered': 45286, 'cast': 30368, 'invalid': 362, 'candidates': [
            ('Slavko Degoricija', 'Zagreb', 'HDZ', 15021),
            ('Josip Bratulić', 'Zagreb', 'HKDS,KNS', 7077),
            ('Edo Murtić', 'Zagreb', 'SKH-SDP', 7780),
        ]},
    ], 'winner': 'Slavko Degoricija'},
    9: {'name': 'Cres - Lošinj', 'rounds': [
        {'registered': 8512, 'cast': 6741, 'invalid': 325, 'candidates': [
            ('Tomislav Gospodnetić', 'Mali Lošinj', 'ODF', 1740),
            ('Milan Kovačić', 'Mali Lošinj', 'SKH-SDP', 1661),
            ('Sergio Negovetić', 'Cres', 'HKDS,KNS', 1814),
            ('Nikola Prkačin', 'Mali Lošinj', 'HDZ', 814),
            ('Cvetko Zorović', 'Mali Lošinj', 'SSH', 387),
        ]},
        {'registered': 8568, 'cast': 6140, 'invalid': 227, 'candidates': [
            ('Sergio Negovetić', 'Cres', 'HKDS,KNS', 2550),
            ('Tomislav Gospodnetić', 'Mali Lošinj', 'ODF', 926),
            ('Milan Kovačić', 'Mali Lošinj', 'SKH-SDP', 1892),
            ('Nikola Prkačin', 'Mali Lošinj', 'HDZ', 533),
        ]},
    ], 'winner': 'Sergio Negovetić'},
    10: {'name': 'Crikvenica', 'rounds': [
        {'registered': 14760, 'cast': 12893, 'invalid': 550, 'candidates': [
            ('Zvonko Balić', 'Novi Vinodolski', 'HDS,KNS', 1652),
            ('Žarko Gašparović', 'Tribalj', 'NK', 728),
            ('Zdenko Ivančić', 'Crikvenica', 'HDZ', 2751),
            ('Petar Lončarić', 'Selce', 'SSH', 893),
            ('Dr Branko Prošić', 'Klenovica', 'SKH-SDP', 5192),
            ('Eduard Ripl', 'Crikvenica', 'NK', 1127),
        ]},
        {'registered': 14709, 'cast': 12018, 'invalid': 469, 'candidates': [
            ('Dr Branko Prošić', 'Klenovica', 'SKH-SDP', 7149),
            ('Zdenko Ivančić', 'Crikvenica', 'HDZ', 4400),
        ]},
    ], 'winner': 'Dr Branko Prošić'},
    11: {'name': 'Čabar', 'rounds': [
        {'registered': 3999, 'cast': 3297, 'invalid': 379, 'candidates': [
            ('Ivan Janeš', 'Čabar', 'SKH-SDP', 1868),
            ('Krešimir Ožbolt', 'Čabar', 'NK', 1035),
        ]},
    ], 'winner': 'Ivan Janeš'},
    12: {'name': 'Čakovec', 'rounds': [
        {'registered': 83907, 'cast': 70514, 'invalid': 3562, 'candidates': [
            ('Ljubo Begović', 'Mačkovec', 'NK', 3341),
            ('Dr Vjekoslav Jazbec', 'Čakovec', 'HDZ', 22250),
            ('Ivan Kovač', 'Čakovec', 'SSOH', 3451),
            ('Dr Rudolf Maršanić', 'Pušćine', 'HDS,KNS', 7982),
            ('Mr Vladimir Matjačić', 'Čakovec', 'SSH', 3611),
            ('Velimir Pleša', 'Čakovec', 'HKDS,KNS', 10781),
            ('Franjo Turza', 'Čakovec', 'SKH-SDP', 15536),
        ]},
        {'registered': 83181, 'cast': 60797, 'invalid': 2575, 'candidates': [
            ('Dr Vjekoslav Jazbec', 'Čakovec', 'HDZ', 35213),
            ('Franjo Turza', 'Čakovec', 'SKH-SDP', 23009),
        ]},
    ], 'winner': 'Dr Vjekoslav Jazbec'},
    13: {'name': 'Čazma', 'rounds': [
        {'registered': 12075, 'cast': 10655, 'invalid': 608, 'candidates': [
            ('Branko Bradić', 'Čazma', 'SSH', 2509),
            ('Drago Bukovac', 'Čazma', 'SSH', 1050),
            ('Nikola Deveđija', 'Čazma', 'NK', 1300),
            ('Viktor Pezo', 'Čazma', 'HDS,KNS', 5188),
        ]},
        {'registered': 12132, 'cast': 9450, 'invalid': 429, 'candidates': [
            ('Viktor Pezo', 'Čazma', 'HDS', 5066),
            ('Branko Bradić', 'Čazma', 'SSH', 3082),
            ('Nikola Deveđija', 'Čazma', 'NK', 873),
        ]},
    ], 'winner': 'Viktor Pezo'},
    14: {'name': 'Črnomerec - Zagreb', 'rounds': [
        {'registered': 41952, 'cast': 34328, 'invalid': 668, 'candidates': [
            ('Josip Đugum', 'Zagreb', 'HDZ', 16718),
            ('Mile Japunčić', 'Zagreb', 'SSH', 559),
            ('Dr Asim Kurjak', 'Zagreb', 'SKH-SDP', 7965),
            ('Dr Anto Matković', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 7303),
            ('Mr Tomislav Matošin', 'Zagreb', 'SSH', 871),
        ]},
        {'registered': 43469, 'cast': 30844, 'invalid': 447, 'candidates': [
            ('Josip Đugum', 'Zagreb', 'HDZ', 16724),
            ('Dr Asim Kurjak', 'Zagreb', 'SKH-SDP', 7781),
            ('Dr Anto Matković', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 5845),
        ]},
    ], 'winner': 'Josip Đugum'},
    15: {'name': 'Daruvar', 'rounds': [
        {'registered': 22299, 'cast': 19302, 'invalid': 4168, 'candidates': [
            ('Nikola Petrović', 'Daruvar', 'SKH-SDP,SSH', 6701),
            ('Miroslav Zailac', 'Daruvar', 'SKH-SDP,SSH', 8433),
        ]},
        {'registered': 22254, 'cast': 17161, 'invalid': 3957, 'candidates': [
            ('Miroslav Zailac', 'Daruvar', 'SKH-SDP,SSH', 9625),
            ('Nikola Petrović', 'Daruvar', 'SKH-SDP,SSH', 3579),
        ]},
    ], 'winner': 'Miroslav Zailac'},
    16: {'name': 'Delnice', 'rounds': [
        {'registered': 14013, 'cast': 12592, 'invalid': 498, 'candidates': [
            ('Nada Glad', 'Delnice', 'SSH', 3644),
            ('Ivan Liker', 'Ravna Gora', 'SKH-SDP', 3806),
            ('Marko Starčević', 'Mrkopalj', 'HDZ', 4571),
        ]},
        {'registered': 13790, 'cast': 11970, 'invalid': 329, 'candidates': [
            ('Marko Starčević', 'Mrkopalj', 'HDZ', 5410),
            ('Ivan Liker', 'Ravna Gora', 'SKH-SDP', 6219),
        ]},
    ], 'winner': 'Ivan Liker'},
    17: {'name': 'Donja Stubica', 'rounds': [
        {'registered': 23170, 'cast': 20051, 'invalid': 660, 'candidates': [
            ('Berislav Korbar', 'Donja Stubica', 'SSH', 934),
            ('Darko Kucelj', 'Donja Stubica', 'SKH-SDP', 2751),
            ('Boris Potočnjak', 'Donja Stubica', 'NK', 1130),
            ('Branimir Salijević', 'Jakovlje', 'HDZ', 13460),
            ('Željko Škudar', 'Gornja Stubica', 'NK', 1116),
        ]},
    ], 'winner': 'Branimir Salijević'},
    18: {'name': 'Donji Lapac', 'rounds': [
        {'registered': 6205, 'cast': 5193, 'invalid': 165, 'candidates': [
            ('Dušan Ergarac', 'Donji Lapac', 'SDS', 2400),
            ('Ilija Milošević', 'Donji Lapac', 'NK', 183),
            ('Ilija Rađenović-Čalda', 'Srb', 'NK', 213),
            ('Dragan Rodić', 'Srb', 'SKH-SDP,SSH,SUBNOR,SSOH', 2232),
        ]},
        {'registered': 6058, 'cast': 5041, 'invalid': 120, 'candidates': [
            ('Dušan Ergarac', 'Donji Lapac', 'SDS', 2728),
            ('Dragan Rodić', 'Srb', 'SKH-SDP,SSH,SUBNOR,SSOH', 2193),
        ]},
    ], 'winner': 'Dušan Ergarac'},
    19: {'name': 'Donji Miholjac', 'rounds': [
        {'registered': 15064, 'cast': 13758, 'invalid': 542, 'candidates': [
            ('Zdravko Bunjevac', 'Donji Miholjac', 'KNS', 1679),
            ('Josip Dolančić', 'Donji Miholjac', 'SKH-SDP', 3183),
            ('Miroslav Pavin', 'Donji Miholjac', 'HDZ', 7808),
            ('Valent Poslon', 'Donji Miholjac', 'SSH', 546),
        ]},
    ], 'winner': 'Miroslav Pavin'},
    20: {'name': 'Drniš', 'rounds': [
        {'registered': 18719, 'cast': 15381, 'invalid': 295, 'candidates': [
            ('Petar Knez', 'Drniš', 'SKH-SDP', 2146),
            ('Ante Marčić', 'Drniš', 'NK', 656),
            ('Nikola Ožegović', 'Knin', 'SDS', 2181),
            ('Smiljan Reljić', 'Drniš', 'HDZ', 10103),
        ]},
    ], 'winner': 'Smiljan Reljić'},
    21: {'name': 'Dubrava - Zagreb', 'rounds': [
        {'registered': 64630, 'cast': 50911, 'invalid': 970, 'candidates': [
            ('Slavica Bajan', 'Zagreb', 'SDSH,KNS', 7924),
            ('Stjepan Brčić', 'Zagreb', 'HDZ', 30818),
            ('Ivan Cifrić', 'Zagreb', 'SSH', 1797),
            ('Marijan Galeković', 'Zagreb', 'NK', 1080),
            ('Enver Šehović', 'Zagreb', 'SKH-SDP', 8322),
        ]},
    ], 'winner': 'Stjepan Brčić'},
    22: {'name': 'Dubrovnik', 'rounds': [
        {'registered': 54144, 'cast': 44863, 'invalid': 1162, 'candidates': [
            ('Petar Baničević', 'Dubrovnik', 'NK', 1399),
            ('Jure Burić', 'Dubrovnik', 'HKDS,KNS', 10670),
            ('Mato Kapović', 'Dubrovnik', 'SKH-SDP', 12043),
            ('Ivan Mustać', 'Dubrovnik', 'HDZ', 17589),
            ('Miljenko Reljić', 'Dubrovnik', 'JSDS', 2000),
        ]},
        {'registered': 54055, 'cast': 40573, 'invalid': 694, 'candidates': [
            ('Ivan Mustać', 'Dubrovnik', 'HDZ', 25379),
            ('Mato Kapović', 'Dubrovnik', 'SKH-SDP', 14500),
        ]},
    ], 'winner': 'Ivan Mustać'},
    23: {'name': 'Duga Resa', 'rounds': [
        {'registered': 22142, 'cast': 19325, 'invalid': 622, 'candidates': [
            ('Zvonko Car', 'Duga Resa', 'NK', 892),
            ('Mr Marija Polović', 'Duga Resa', 'NK', 655),
            ('Robert Polović', 'Duga Resa', 'HDS,KNS', 2500),
            ('Branko Primužak', 'Duga Resa', 'HDZ', 11097),
            ('Janko Tomičić', 'Duga Resa', 'SKH-SDP', 3044),
            ('Vladimir Vranić', 'Duga Resa', 'SSH', 515),
        ]},
    ], 'winner': 'Branko Primužak'},
    24: {'name': 'Dugo Selo', 'rounds': [
        {'registered': 14953, 'cast': 11154, 'invalid': 550, 'candidates': [
            ('Magdalena Gregurić-Lacković', 'Obedišće', 'NK', 946),
            ('Božidar Grgošić', 'Dugo Selo', 'SKH-SDP', 2666),
            ('Ivan Šarić', 'Dugo Selo', 'HSLS,KNS', 1344),
            ('Borislav Zorić', 'Dugo Selo', 'HDZ', 5648),
        ]},
    ], 'winner': 'Borislav Zorić'},
    25: {'name': 'Dvor', 'rounds': [
        {'registered': 11215, 'cast': 9827, 'invalid': 714, 'candidates': [
            ('Milan Đurić', 'Dvor', 'NK', 1345),
            ('Savan Grabundžija', 'D. Oraovica', 'SKH-SDP,SSH,SSOH,SUBNOR', 3380),
            ('Miloš Mrkobrada', 'Dvor', 'SDS', 2419),
            ('Mr Svetozar Vinčić', 'Dvor', 'SKH-SDP,SSH,SSOH,SUBNOR', 1969),
        ]},
        {'registered': 11248, 'cast': 9731, 'invalid': 445, 'candidates': [
            ('Savan Grabundžija', 'D. Oraovica', 'SKH-SDP,SSH,SSOH,SUBNOR', 4212),
            ('Miloš Mrkobrada', 'Dvor', 'SDS', 2081),
            ('Mr Svetozar Vinčić', 'Dvor', 'SKH-SDP,SSH,SSOH,SUBNOR', 2166),
            ('Milan Đurić', 'Dvor', 'NK', 827),
        ]},
    ], 'winner': 'Savan Grabundžija'},
    26: {'name': 'Đakovo', 'rounds': [
        {'registered': 35301, 'cast': 31442, 'invalid': 1014, 'candidates': [
            ('Zvonimir Jurić', 'Đakovo', 'HDZ', 19251),
            ('Vladimir Pološki', 'Đakovo', 'SKH-SDP', 5856),
            ('Mirko Predrijevac', 'Đakovo', 'KNS', 5225),
        ]},
    ], 'winner': 'Zvonimir Jurić'},
    27: {'name': 'Đurđevac', 'rounds': [
        {'registered': 30395, 'cast': 25486, 'invalid': 1107, 'candidates': [
            ('Vjekoslav Flamaceta', 'Đurđevac', 'SKH-SDP', 5273),
            ('Ivan Franjić', 'Đurđevac', 'SSH', 2620),
            ('Marijan Ivančan', 'Molve', 'HDZ', 12795),
            ('Vladimir Mirović', 'Đurđevac', 'HKDS,KNS', 3691),
        ]},
    ], 'winner': 'Marijan Ivančan'},
    28: {'name': 'Garešnica', 'rounds': [
        {'registered': 13363, 'cast': 12213, 'invalid': 478, 'candidates': [
            ('Josip Balja', 'Garešnica', 'HDS,KNS', 6776),
            ('Slavko Bosanac', 'Zagreb', 'SSH', 4959),
        ]},
    ], 'winner': 'Josip Balja'},
    29: {'name': 'Glina', 'rounds': [
        {'registered': 18023, 'cast': 16073, 'invalid': 414, 'candidates': [
            ('Milivoj Vojnović', 'Glina', 'SKH-SDP,SSH', 10887),
            ('Milan Zgurić', 'Glina', 'HDZ', 4772),
        ]},
    ], 'winner': 'Milivoj Vojnović'},
    30: {'name': 'Gospić', 'rounds': [
        {'registered': 21802, 'cast': 18781, 'invalid': 875, 'candidates': [
            ('Grga Pavletić', 'Zagreb', 'SKH-SDP', 7170),
            ('Miroslav Petry', 'Gospić', 'HDZ', 8514),
            ('Branko Saša', 'Lički Osik', 'SSH', 2222),
        ]},
        {'registered': 22451, 'cast': 17997, 'invalid': 523, 'candidates': [
            ('Miroslav Petry', 'Gospić', 'HDZ', 9020),
            ('Grga Pavletić', 'Zagreb', 'SKH-SDP', 7387),
            ('Branko Saša', 'Lički Osik', 'SSH', 1066),
        ]},
    ], 'winner': 'Miroslav Petry'},
    31: {'name': 'Gračac', 'rounds': [
        {'registered': 8249, 'cast': 7034, 'invalid': 558, 'candidates': [
            ('Milan Bjelobaba', 'Gračac', 'SKH-SDP,SSH', 1332),
            ('Željko Đekić', 'Gračac', 'SKH-SDP,SSH', 1306),
            ('Dragica Kesić', 'Gračac', 'NK', 296),
            ('Ratko Ličina', 'Gračac', 'SDS', 1962),
            ('Dane Stanisavljević', 'Gračac', 'NK', 1104),
            ('Svetozar Tojaga', 'Zrmanja', 'NK', 476),
        ]},
        {'registered': 8384, 'cast': 6913, 'invalid': 329, 'candidates': [
            ('Ratko Ličina', 'Gračac', 'SDS', 3835),
            ('Željko Đekić', 'Gračac', 'SKH-SDP,SSH', 1770),
            ('Dane Stanisavljević', 'Gračac', 'NK', 979),
        ]},
    ], 'winner': 'Ratko Ličina'},
    32: {'name': 'Grubišno Polje', 'rounds': [
        {'registered': 11077, 'cast': 10067, 'invalid': 682, 'candidates': [
            ('Rade Jovičić', 'Grubišno Polje', 'SKH-SDP', 4847),
            ('Franjo Levatić', 'Grubišno Polje', 'HDS,KNS', 2842),
            ('Antun Sedlaček', 'Grubišno Polje', 'SSH', 1694),
        ]},
        {'registered': 11075, 'cast': 9482, 'invalid': 630, 'candidates': [
            ('Rade Jovičić', 'Grubišno Polje', 'SKH-SDP', 4918),
            ('Franjo Levatić', 'Grubišno Polje', 'HDS', 2944),
            ('Antun Sedlaček', 'Grubišno Polje', 'SSH', 990),
        ]},
    ], 'winner': 'Rade Jovičić'},
    33: {'name': 'Imotski', 'rounds': [
        {'registered': 25638, 'cast': 22325, 'invalid': 257, 'candidates': [
            ('Željko Đerek', 'Vinjani Donji', 'NK', 1518),
            ('Zdenko Lozo', 'Brela', 'HS', 1047),
            ('Marijan Milinović', 'Lovreč', 'HDZ', 16927),
            ('Branimir Šuto', 'Zmijavci', 'HDS,KNS', 2576),
        ]},
    ], 'winner': 'Marijan Milinović'},
    34: {'name': 'Ivanec', 'rounds': [
        {'registered': 30444, 'cast': 25921, 'invalid': 1717, 'candidates': [
            ('Slavko Canjuga', 'Ivanec', 'HDZ', 13038),
            ('Vinko Cerjan', 'Maruševac', 'NK', 2177),
            ('Nevenka Kurelić', 'Donja Voća', 'HSLS,KNS', 2559),
            ('Adam Pintarić', 'Ivanec', 'NK', 2635),
            ('Goran Šarić', 'Ivanec', 'HDS,KNS', 3795),
        ]},
    ], 'winner': 'Slavko Canjuga'},
    35: {'name': 'Ivanić Grad', 'rounds': [
        {'registered': 19620, 'cast': 16963, 'invalid': 1197, 'candidates': [
            ('Stjepan Bunjevac', 'Kloštar Ivanić', 'NK', 1739),
            ('Ivan Frater', 'Novoselec', 'NK', 1475),
            ('Josip Kitanić', 'Kloštar Ivanić', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 7255),
            ('Palma Klun-Posavec', 'Ivanić Grad', 'SKH-SDP', 5242),
        ]},
        {'registered': 19509, 'cast': 13832, 'invalid': 580, 'candidates': [
            ('Josip Kitanić', 'Kloštar Ivanić', 'HSLS,HDZ', 6784),
            ('Palma Klun-Posavec', 'Ivanić Grad', 'SKH-SDP', 4943),
            ('Stjepan Bunjevac', 'Kloštar Ivanić', 'NK', 798),
            ('Ivan Frater', 'Novoselec', 'NK', 715),
        ]},
    ], 'winner': 'Josip Kitanić'},
    36: {'name': 'Jastrebarsko', 'rounds': [
        {'registered': 23545, 'cast': 21452, 'invalid': 700, 'candidates': [
            ('Alojz Gojšić', 'Jastrebarsko', 'SKH-SDP', 3243),
            ('Željko Olujić', 'Zagreb', 'SDSH,KNS', 3431),
            ('Ivan Marijan Severinac', 'Jastrebarsko', 'HDZ', 14074),
        ]},
    ], 'winner': 'Ivan Marijan Severinac'},
    37: {'name': 'Kardeljevo', 'rounds': [
        {'registered': 8588, 'cast': 7650, 'invalid': 373, 'candidates': [
            ('Zlatko Raič', 'Gradac', 'SKH-SDP', 3635),
            ('Vedran Sršen', 'Kardeljevo', 'HDZ', 3642),
        ]},
        {'registered': 8864, 'cast': 7353, 'invalid': 170, 'candidates': [
            ('Vedran Sršen', 'Kardeljevo', 'HDZ', 3472),
            ('Zlatko Raič', 'Gradac', 'SKH-SDP', 3711),
        ]},
    ], 'winner': 'Zlatko Raič'},
    38: {'name': 'Karlovac', 'rounds': [
        {'registered': 59716, 'cast': 53343, 'invalid': 1042, 'candidates': [
            ('Vladimir Cvitanović', 'Karlovac', 'HDZ', 21418),
            ('Željko Gojšić', 'Karlovac', 'HDS,KNS', 5999),
            ('Darko Jerinić', 'Karlovac', 'SKH-SDP', 21070),
            ('Marinko Panić', 'Karlovac', 'SSH', 2574),
            ('Zlatko Vuković', 'Karlovac', 'SDSH,KNS', 1240),
        ]},
        {'registered': 59913, 'cast': 48508, 'invalid': 664, 'candidates': [
            ('Vladimir Cvitanović', 'Karlovac', 'HDZ', 25771),
            ('Darko Jerinić', 'Karlovac', 'SKH-SDP', 22073),
        ]},
    ], 'winner': 'Vladimir Cvitanović'},
    39: {'name': 'Kaštela', 'rounds': [
        {'registered': 24158, 'cast': 18661, 'invalid': 528, 'candidates': [
            ('Joško Kovač', 'K. Sućurac', 'HDZ,HSS', 11232),
            ('Cvitko Maleš', 'K. Gomilica', 'HMP,KNS', 1779),
            ('Mate Maljković Motika', 'Ladin Dalmatinski', 'NK', 517),
            ('Luka Meštrov', 'K. Sućurac', 'SKH-SDP', 3403),
            ('Bogdan Pensa', 'K. Lukšić', 'NK', 616),
            ('Marin Peran', 'K. Stari', 'NK', 316),
            ('Boris Perišić', 'K. Štafilić', 'NK', 166),
        ]},
    ], 'winner': 'Joško Kovač'},
    40: {'name': 'Klanjec', 'rounds': [
        {'registered': 8565, 'cast': 6780, 'invalid': 392, 'candidates': [
            ('Tomislav Gadža', 'Kumrovec', 'SSH', 1757),
            ('Krunoslav Kroflin', 'Klanjec', 'HDZ', 4455),
        ]},
    ], 'winner': 'Krunoslav Kroflin'},
    41: {'name': 'Knin', 'rounds': [
        {'registered': 31471, 'cast': 26126, 'invalid': 545, 'candidates': [
            ('Marinko Čavka', 'Kijevo', 'HDZ', 1873),
            ('Mirko Sinobrad', 'Knin', 'SSH', 5470),
            ('Dušan Zelembaba', 'Knin', 'SDS', 18237),
        ]},
    ], 'winner': 'Dušan Zelembaba'},
    42: {'name': 'Koprivnica', 'rounds': [
        {'registered': 46213, 'cast': 38631, 'invalid': 1584, 'candidates': [
            ('Mr Ivan Biršić', 'Koprivnica', 'HKDS,KNS', 4498),
            ('Ivan Mikulić', 'Koprivnica', 'HDZ', 13641),
            ('Zlatko Panić', 'Koprivnica', 'SSH', 2973),
            ('Ivan Stančer', 'Gola', 'HSS,KNS', 3270),
            ('Dr Krešimir Švarc', 'Koprivnica', 'SKH-SDP', 12665),
        ]},
        {'registered': 44428, 'cast': 30474, 'invalid': 743, 'candidates': [
            ('Ivan Mikulić', 'Koprivnica', 'HDZ', 16052),
            ('Dr Krešimir Švarc', 'Koprivnica', 'SKH-SDP', 11751),
            ('Zlatko Panić', 'Koprivnica', 'SSH', 1926),
        ]},
    ], 'winner': 'Ivan Mikulić'},
    43: {'name': 'Korčula', 'rounds': [
        {'registered': 14106, 'cast': 11557, 'invalid': 627, 'candidates': [
            ('Alena Fazinić', 'Korčula', 'HKDS,KNS', 1699),
            ('Boris Grbin-Grozde', 'Blato', 'HDZ', 3961),
            ('Josip Podbevšek', 'Korčula', 'SKH-SDP,SSH', 5219),
        ]},
        {'registered': 14085, 'cast': 10743, 'invalid': 422, 'candidates': [
            ('Josip Podbevšek', 'Korčula', 'SKH-SDP,SSH', 5376),
            ('Boris Grbin-Grozde', 'Blato', 'HDZ', 4945),
        ]},
    ], 'winner': 'Josip Podbevšek'},
    44: {'name': 'Kostajnica', 'rounds': [
        {'registered': 11098, 'cast': 9927, 'invalid': 415, 'candidates': [
            ('Dušan Glušac', 'Kostajnica', 'NK', 1406),
            ('Ivo Kovačević', 'Kostajnica', 'NK', 1639),
            ('Perica Kutlić', 'Kostajnica', 'SKH-SDP,SSH', 4922),
            ('Vladislav Milić', 'Kostajnica', 'SDSHJ', 294),
            ('Dr Davorin Runje', 'Mečenčani', 'SKH-SDP,SSH', 1251),
        ]},
        {'registered': 11057, 'cast': 9392, 'invalid': 288, 'candidates': [
            ('Perica Kutlić', 'Kostajnica', 'SKH-SDP,SSH', 6812),
            ('Ivo Kovačević', 'Kostajnica', 'NK', 1496),
            ('Dr Davorin Runje', 'Mečenčani', 'NK', 794),
        ]},
    ], 'winner': 'Perica Kutlić'},
    45: {'name': 'Krapina', 'rounds': [
        {'registered': 19745, 'cast': 16655, 'invalid': 1008, 'candidates': [
            ('Ivan Malogorski', 'Krapina', 'HDZ', 10840),
            ('Dr Ivan Ovčariček', 'Krapina', 'SKH-SDP', 3158),
            ('Mr Ivan Švaljek', 'Krapina', 'NK', 1279),
        ]},
    ], 'winner': 'Ivan Malogorski'},
    46: {'name': 'Križevci', 'rounds': [
        {'registered': 29528, 'cast': 26756, 'invalid': 911, 'candidates': [
            ('Karlo Florenino', 'Križevci', 'SKH-SDP', 5473),
            ('Mirko Pomper', 'Križevci', 'SSH', 2530),
            ('Josip Širjan', 'Kusijevec', 'HDZ', 14634),
            ('Mr Franjo Zadro', 'Zagreb', 'HSLS,KNS', 3208),
        ]},
    ], 'winner': 'Josip Širjan'},
    47: {'name': 'Krk', 'rounds': [
        {'registered': 12316, 'cast': 10063, 'invalid': 483, 'candidates': [
            ('Anton Bogović', 'Krk', 'SKH-SDP', 1589),
            ('Mladen Dujmović', 'Krk', 'SSH', 1021),
            ('Anton Katunar', 'Krk', 'HDS,KNS', 5392),
            ('Franjo Mrakovčić', 'Kornić', 'SKH-SDP', 1518),
        ]},
    ], 'winner': 'Anton Katunar'},
    48: {'name': 'Kutina', 'rounds': [
        {'registered': 27627, 'cast': 25287, 'invalid': 726, 'candidates': [
            ('Mijo Hlad', 'Zagreb', 'HDZ', 11284),
            ('Ivan Kerepčić', 'Popovača', 'SKH-SDP', 7683),
            ('Snježana Kramarić', 'Kutina', 'HS', 1212),
            ('Hrvoje Zorić', 'Kutina', 'HSLS,KNS', 4382),
        ]},
        {'registered': 27843, 'cast': 22297, 'invalid': 368, 'candidates': [
            ('Mijo Hlad', 'Zagreb', 'HDZ', 11990),
            ('Ivan Kerepčić', 'Popovača', 'SKH-SDP', 7471),
            ('Hrvoje Zorić', 'Kutina', 'HSLS,KNS', 2468),
        ]},
    ], 'winner': 'Mijo Hlad'},
    49: {'name': 'Labin', 'rounds': [
        {'registered': 19681, 'cast': 16924, 'invalid': 2037, 'candidates': [
            ('Ercole Golja', 'Labin', 'SKH-SDP', 5481),
            ('Gracijano Kiršić', 'Labin', 'SKH-SDP', 9325),
        ]},
    ], 'winner': 'Gracijano Kiršić'},
    50: {'name': 'Lastovo', 'rounds': [
        {'registered': 705, 'cast': 520, 'invalid': 68, 'candidates': [
            ('Katja Antičević', 'Lastovo', 'SKH-SDP', 93),
            ('Veljko Dražinić', 'Lastovo', 'NK', 131),
            ('Ivan Ivelja', 'Lastovo', 'SKH-SDP', 169),
            ('Leo Katić', 'Lastovo', 'NK', 59),
        ]},
        {'registered': 716, 'cast': 456, 'invalid': 28, 'candidates': [
            ('Ivan Ivelja', 'Lastovo', 'SKH-SDP', 205),
            ('Veljko Dražinić', 'Lastovo', 'NK', 155),
            ('Katja Antičević', 'Lastovo', 'SKH-SDP', 38),
            ('Leo Katić', 'Lastovo', 'NK', 30),
        ]},
    ], 'winner': 'Ivan Ivelja'},
    51: {'name': 'Ludbreg', 'rounds': [
        {'registered': 16138, 'cast': 14875, 'invalid': 970, 'candidates': [
            ('Mladen Dolovski', 'Ludbreg', 'HDS,KNS', 4853),
            ('Marijan Krobot', 'Ludbreg', 'SKH-SDP', 4622),
            ('Renato Molnar', 'Varaždin', 'HDZ', 4430),
        ]},
        {'registered': 15851, 'cast': 13264, 'invalid': 521, 'candidates': [
            ('Marijan Krobot', 'Ludbreg', 'SKH-SDP', 5909),
            ('Renato Molnar', 'Varaždin', 'HDZ', 6834),
        ]},
    ], 'winner': 'Renato Molnar'},
    52: {'name': 'Makarska', 'rounds': [
        {'registered': 15455, 'cast': 12748, 'invalid': 444, 'candidates': [
            ('Ivan Ivanda', 'Makarska', 'HDZ', 3409),
            ('Antun Miličević', 'Makarska', 'HDS,KNS', 2321),
            ('Branko Puharić', 'Zagreb', 'SKH-SDP', 6574),
        ]},
    ], 'winner': 'Branko Puharić'},
    53: {'name': 'Maksimir - Zagreb', 'rounds': [
        {'registered': 52666, 'cast': 41492, 'invalid': 571, 'candidates': [
            ('Tomislav Bilogrivić', 'Zagreb', 'ZAZ-EZL', 1883),
            ('Ante Karić', 'Zagreb', 'HDZ', 19499),
            ('Mr Ivo Kujundžić', 'Zagreb', 'HDS,KNS', 8303),
            ('Stjepan Leskovec', 'Zagreb', 'SSH', 963),
            ('Ivan Tarle', 'Zagreb', 'SKH-SDP', 7596),
            ('Velimir Zajec', 'Zagreb', 'NK', 2268),
        ]},
        {'registered': 52377, 'cast': 36551, 'invalid': 512, 'candidates': [
            ('Ante Karić', 'Zagreb', 'HDZ', 20284),
            ('Mr Ivo Kujundžić', 'Zagreb', 'HDS', 6390),
            ('Ivan Tarle', 'Zagreb', 'SKH-SDP', 9235),
        ]},
    ], 'winner': 'Ante Karić'},
    54: {'name': 'Medveščak - Zagreb', 'rounds': [
        {'registered': 39560, 'cast': 32357, 'invalid': 442, 'candidates': [
            ('Tugomir Filipan', 'Zagreb', 'SSH', 600),
            ('Željko Gyorgy', 'Zagreb', 'NK', 449),
            ('Bernardo Jurlina', 'Zagreb', 'SSH', 830),
            ('Biljana Kašić', 'Zagreb', 'ZAZ-EZL', 1647),
            ('Nedjeljko Mihanović', 'Zagreb', 'HDZ', 13170),
            ('Ivo Škrabalo', 'Zagreb', 'HSLS,KNS', 6960),
            ('Zdravko Tomac', 'Zagreb', 'SKH-SDP', 8259),
        ]},
        {'registered': 40076, 'cast': 29284, 'invalid': 349, 'candidates': [
            ('Nedjeljko Mihanović', 'Zagreb', 'HDZ', 13603),
            ('Zdravko Tomac', 'Zagreb', 'SKH-SDP', 9275),
            ('Ivo Škrabalo', 'Zagreb', 'HSLS,KNS', 6057),
        ]},
    ], 'winner': 'Nedjeljko Mihanović'},
    55: {'name': 'Metković', 'rounds': [
        {'registered': 15488, 'cast': 13700, 'invalid': 1008, 'candidates': [
            ('Luka Bebić', 'Metković', 'HDZ', 10251),
            ('Slobodan Volarević', 'Metković', 'SKH-SDP', 2441),
        ]},
    ], 'winner': 'Luka Bebić'},
    56: {'name': 'Našice', 'rounds': [
        {'registered': 27824, 'cast': 25139, 'invalid': 825, 'candidates': [
            ('Vilko Belak', 'Markovac Našički', 'SSH', 2774),
            # Printed "ĆIĆEK" here, "ČIČEK" in round 2 and the decision.
            ('Miroslav Čiček', 'Našice', 'HDZ', 11361),
            ('Ivica Jerković', 'Našice', 'SKH-SDP', 4947),
            ('Ivan Drago Trošelj', 'Našice', 'HSLS,HDS,SDSH,HKDS,KNS', 5222),
        ]},
        {'registered': 27674, 'cast': 24144, 'invalid': 551, 'candidates': [
            ('Miroslav Čiček', 'Našice', 'HDZ', 13453),
            ('Ivan Drago Trošelj', 'Našice', 'HSLS,HDS,SDSH,HKDS,KNS', 4156),
            ('Ivica Jerković', 'Našice', 'SKH-SDP,SSH', 5982),
        ]},
    ], 'winner': 'Miroslav Čiček'},
    57: {'name': 'Nova Gradiška', 'rounds': [
        {'registered': 43522, 'cast': 39589, 'invalid': 1653, 'candidates': [
            ('Mirko Babić', 'Nova Kapela', 'SSH', 7773),
            ('Stjepan Erpačić', 'Nova Gradiška', 'HSLS,HDS,HKDS,KNS', 8817),
            ('Leonard Stazić', 'Nova Gradiška', 'SSH', 5558),
            ('Miroslav Župančić', 'Kosovac', 'HDZ', 15787),
        ]},
        {'registered': 42960, 'cast': 36539, 'invalid': 811, 'candidates': [
            ('Miroslav Župančić', 'Kosovac', 'HDZ', 23189),
            ('Mirko Babić', 'Nova Kapela', 'SSH', 12539),
        ]},
    ], 'winner': 'Miroslav Župančić'},
    58: {'name': 'Novi Marof', 'rounds': [
        {'registered': 21205, 'cast': 18952, 'invalid': 600, 'candidates': [
            ('Jozo Knežević', 'Novi Marof', 'HKDS,KNS', 4083),
            ('Željko Lacković', 'Varaždinske Toplice', 'SDSH,KNS', 1356),
            ('Ante Luetić', 'Varaždinske Toplice', 'NK', 1130),
            ('Borislav Planinc', 'Varaždinske Toplice', 'NK', 707),
            ('Vinko Pošta', 'Novi Marof', 'SSH', 1151),
            ('Ratimir Slavić', 'Orešje', 'HDZ', 9925),
        ]},
    ], 'winner': 'Ratimir Slavić'},
    59: {'name': 'Novi Zagreb', 'rounds': [
        {'registered': 102689, 'cast': 83084, 'invalid': 1459, 'candidates': [
            ('Zdenko Duić', 'Zagreb', 'ZAZ-EZL', 3769),
            ('Dr Ivo Goldstein', 'Zagreb', 'HSLS,KNS', 14318),
            ('Davor Golić', 'Zagreb', 'HDZ', 37180),
            ('Vladimir Konić', 'Zagreb', 'SSH', 1589),
            ('Veljko Platiša', 'Zagreb', 'NK', 774),
            ('Božidar Sušec', 'Zagreb', 'SKH-SDP', 22163),
            ('Neven Vranković', 'Zagreb', 'SSOH', 1347),
        ]},
        {'registered': 101933, 'cast': 74113, 'invalid': 805, 'candidates': [
            ('Davor Golić', 'Zagreb', 'HDZ', 38141),
            ('Božidar Sušec', 'Zagreb', 'SKH-SDP', 23325),
            ('Dr Ivo Goldstein', 'Zagreb', 'HSLS,KNS', 11842),
        ]},
    ], 'winner': 'Davor Golić'},
    60: {'name': 'Novska', 'rounds': [
        {'registered': 17438, 'cast': 15584, 'invalid': 641, 'candidates': [
            ('Dr Antun Čevizović', 'Novska', 'HDZ,HSLS', 8572),
            ('Ante Đerek', 'Novska', 'SKH-SDP', 4045),
            ('Teodor Fricki', 'Zagreb', 'SSH', 2326),
        ]},
    ], 'winner': 'Dr Antun Čevizović'},
    61: {'name': 'Obrovac', 'rounds': [
        {'registered': 8738, 'cast': 7358, 'invalid': 137, 'candidates': [
            ('Dušan Badža', 'Obrovac', 'SKH-SDP,SSH', 3160),
            ('Ilija Baljak - Ićo', 'Obrovac', 'NK', 410),
            ('Svetozar Jovančević', 'Obrovac', 'NK', 1137),
            ('Marko Jurjević-Lako', 'Kruševo', 'HDZ', 2514),
        ]},
        {'registered': 8764, 'cast': 7673, 'invalid': 115, 'candidates': [
            ('Dušan Badža', 'Obrovac', 'SKH-SDP,SSH', 3783),
            ('Marko Jurjević-Lako', 'Kruševo', 'HDZ', 2688),
            ('Svetozar Jovančević - Zoran', 'Obrovac', 'NK', 1087),
        ]},
    ], 'winner': 'Dušan Badža'},
    62: {'name': 'Ogulin', 'rounds': [
        {'registered': 22291, 'cast': 20563, 'invalid': 392, 'candidates': [
            ('Boris Mihelčić', 'Ogulin', 'SKH-SDP', 4551),
            ('Nikola Pavličić', 'Ogulin', 'HDZ', 8389),
            ('Milan Rendulić', 'Josipdol', 'NK', 967),
            ('Nedeljko Višnić', 'Ogulin', 'SSH', 6112),
        ]},
        {'registered': 21990, 'cast': 20143, 'invalid': 284, 'candidates': [
            ('Nikola Pavličić', 'Ogulin', 'HDZ', 9354),
            ('Nedeljko Višnić', 'Ogulin', 'SSH,SKH-SDP', 10505),
        ]},
    ], 'winner': 'Nedeljko Višnić'},
    63: {'name': 'Omiš', 'rounds': [
        {'registered': 18140, 'cast': 15861, 'invalid': 358, 'candidates': [
            ('Dr Jure Bilić', 'Split', 'HDZ', 11244),
            ('Mr Božo Čapeta', 'Omiš', 'SKH-SDP', 2865),
            ('Radoslav Vuković', 'Krilo-Jesenice', 'HMP,KNS', 1367),
        ]},
    ], 'winner': 'Dr Jure Bilić'},
    64: {'name': 'Opatija', 'rounds': [
        {'registered': 24701, 'cast': 19789, 'invalid': 1390, 'candidates': [
            ('Josip Dukić', 'Lovran', 'HDZ', 4082),
            ('Ratimir Jazvić', 'Ika', 'NK', 1161),
            ('Mirna Karina', 'Brseč', 'SSH', 1533),
            ('Slavko Kinkela', 'Matulji', 'SKH-SDP', 6586),
            ('Ivan Rebac', 'Opatija', 'HSLS,KNS', 459),
            ('Maksim Valenčić', 'Matulji, Pobri', 'HDS,KNS', 4305),
        ]},
        {'registered': 24261, 'cast': 17869, 'invalid': 877, 'candidates': [
            ('Slavko Kinkela', 'Matulji', 'SKH-SDP', 8527),
            ('Josip Dukić', 'Lovran', 'HDZ', 6672),
            ('Mirna Karina', 'Brseč', 'SSH', 1793),
        ]},
    ], 'winner': 'Slavko Kinkela'},
    65: {'name': 'Orahovica', 'rounds': [
        {'registered': 11088, 'cast': 10405, 'invalid': 374, 'candidates': [
            ('Josip Kolarić', 'Orahovica', 'SKH-SDP', 4617),
            ('Milan Pezić', 'Orahovica', 'HDZ', 5414),
        ]},
    ], 'winner': 'Milan Pezić'},
    66: {'name': 'Otočac', 'rounds': [
        {'registered': 18393, 'cast': 16451, 'invalid': 686, 'candidates': [
            ('Dražen Bobinac', 'Otočac', 'HDZ', 8594),
            ('Milan Dujmović', 'Čoviće', 'HDS,KNS', 689),
            ('Vlade Kostelac', 'Prozor', 'SSOH', 416),
            ('Vladimir Moćan', 'Brinje', 'SKH-SDP', 6066),
        ]},
    ], 'winner': 'Dražen Bobinac'},
    67: {'name': 'Ozalj', 'rounds': [
        {'registered': 9677, 'cast': 8798, 'invalid': 319, 'candidates': [
            ('Ivan Jančić', 'Ozalj', 'SKH-SDP', 1879),
            ('Mladen Kobasić', 'Ozalj', 'HDZ', 4813),
            ('Ante Kokić', 'Ozalj', 'HDS,KNS', 1289),
            ('Zvonimir Rusjan', 'Ozalj', 'NK', 498),
        ]},
    ], 'winner': 'Mladen Kobasić'},
    68: {'name': 'Pag', 'rounds': [
        {'registered': 5471, 'cast': 4650, 'invalid': 181, 'candidates': [
            ('Nikola Crnković', 'Novalja', 'HSS,KNS', 1243),
            ('Josip Kurilić', 'Pag', 'NK', 295),
            ('Ante Tičić', 'Pag', 'SKH-SDP', 908),
            ('Petar Tičić', 'Povljana', 'HDZ', 2023),
        ]},
        {'registered': 5713, 'cast': 4320, 'invalid': 367, 'candidates': [
            ('Petar Tičić', 'Povljana', 'HDZ', 2470),
            ('Nikola Crnković', 'Novalja', 'HSS,KNS', 1483),
        ]},
    ], 'winner': 'Petar Tičić'},
    69: {'name': 'Pakrac', 'rounds': [
        {'registered': 19689, 'cast': 16545, 'invalid': 1971, 'candidates': [
            ('Veljko Bosanac', 'Pakrac', 'JSDS', 5420),
            ('Tomo Jendrašić', 'Pakrac', 'SKH-SDP', 4945),
            ('Marko Širac', 'Zagreb', 'SSH', 4209),
        ]},
        {'registered': 19650, 'cast': 15931, 'invalid': 2533, 'candidates': [
            ('Veljko Bosanac', 'Pakrac', 'JSDS', 4733),
            ('Tomo Jendrašić', 'Pakrac', 'SKH-SDP', 8665),
        ]},
    ], 'winner': 'Tomo Jendrašić'},
    70: {'name': 'Peščenica - Zagreb', 'rounds': [
        {'registered': 38539, 'cast': 33203, 'invalid': 748, 'candidates': [
            ('Antun Abramović', 'Zagreb', 'HDZ', 13661),
            ('Zvonimir Baletić', 'Zagreb', 'SDSH,KNS', 3650),
            ('Zoran Lukić', 'Zagreb', 'HSS,KNS', 1762),
            ('Zoran Oštrić', 'Zagreb', 'ZAZ-EZL', 1567),
            ('Marko Soldo', 'Zagreb', 'SSH', 1311),
            ('Ivan Šikić', 'Zagreb', 'SKH-SDP', 10409),
        ]},
        {'registered': 38158, 'cast': 29292, 'invalid': 377, 'candidates': [
            ('Antun Abramović', 'Zagreb', 'HDZ', 13959),
            ('Ivan Šikić', 'Zagreb', 'SKH-SDP', 11007),
            ('Zvonimir Baletić', 'Zagreb', 'SDSH,KNS', 3913),
        ]},
    ], 'winner': 'Antun Abramović'},
    71: {'name': 'Petrinja', 'rounds': [
        {'registered': 25962, 'cast': 23433, 'invalid': 882, 'candidates': [
            ('Darko Bakarić', 'Petrinja', 'SKH-SDP,SSH', 13658),
            ('Petar Ladjević', 'Petrinja', 'SDSHJ', 1405),
            ('Vjekoslav Marović', 'Petrinja', 'HSLS,KNS', 5853),
            ('Stevo Tomić', 'Petrinja', 'NK', 1635),
        ]},
    ], 'winner': 'Darko Bakarić'},
    72: {'name': 'Podravska Slatina', 'rounds': [
        {'registered': 23133, 'cast': 21038, 'invalid': 579, 'candidates': [
            ('Miško Granjaš', 'Sopje', 'HDZ', 9776),
            ('Mirko Lukač', 'Podravska Slatina', 'SSH', 1935),
            ('Milorad Ojkić', 'Podravska Slatina', 'SKH-SDP', 8748),
        ]},
        {'registered': 23125, 'cast': 19906, 'invalid': 439, 'candidates': [
            ('Miško Granjaš', 'Sopje', 'HDZ', 10169),
            ('Milorad Ojkić', 'Podravska Slatina', 'SKH-SDP', 9275),
        ]},
    ], 'winner': 'Miško Granjaš'},
    73: {'name': 'Poreč', 'rounds': [
        {'registered': 17982, 'cast': 14080, 'invalid': 1285, 'candidates': [
            ('Franko Beaković', 'Poreč', 'SSH', 2982),
            ('Miro Dodić', 'Poreč', 'SKH-SDP', 2981),
            ('Božidar Kadić', 'Poreč', 'NK', 2436),
            ('Đenio Radić', 'Poreč', 'SKH-SDP', 4396),
        ]},
        {'registered': 17987, 'cast': 10460, 'invalid': 710, 'candidates': [
            ('Đenio Radić', 'Poreč', 'SKH-SDP', 5730),
            ('Franko Beaković', 'Poreč', 'SSH', 1877),
            ('Božidar Kadić', 'Poreč', 'NK', 2143),
        ]},
    ], 'winner': 'Đenio Radić'},
    74: {'name': 'Pregrada', 'rounds': [
        {'registered': 13298, 'cast': 9639, 'invalid': 553, 'candidates': [
            ('Zvonko Salamon', 'Pregrada', 'HDZ', 6153),
            ('Dragutin Špiljak', 'Hum na Sutli', 'SKH-SDP', 2931),
        ]},
    ], 'winner': 'Zvonko Salamon'},
    75: {'name': 'Pula', 'rounds': [
        {'registered': 67086, 'cast': 52930, 'invalid': 2308, 'candidates': [
            ('Josip Brakus', 'Pula', 'HDZ', 4488),
            ('Nevio Bugarin', 'Pula', 'SKH-SDP,SSH', 9867),
            ('Walter Kapov', 'Pula', 'EFZP', 2066),
            ('Bruno Langer', 'Pula', 'NK', 4266),
            ('Dr Marija Pekota-Kopal', 'Pula', 'HKDS,KNS', 6452),
            ('Ivica Percan', 'Pula', 'SKH-SDP,SSH', 16995),
            ('Dušan Rađenović', 'Medulin', 'SJ', 1831),
            ('Tomislav Ravnić', 'Pula', 'SKH-SDP,SSH', 4657),
        ]},
        {'registered': 67003, 'cast': 43890, 'invalid': 1233, 'candidates': [
            ('Ivica Percan', 'Pula', 'SKH-SDP,SSH', 29657),
            ('Dr Marija Pekota-Kopal', 'Pula', 'HKDS,KNS', 6310),
            ('Josip Brakus', 'Pula', 'HDZ', 3666),
            ('Bruno Langer', 'Pula', 'NK', 3024),
        ]},
    ], 'winner': 'Ivica Percan'},
    76: {'name': 'Rab', 'rounds': [
        {'registered': 6351, 'cast': 5602, 'invalid': 258, 'candidates': [
            ('Dragan Andrić', 'Barbat', 'SKH-SDP', 1625),
            ('Josip Andrić', 'Barbat', 'HDZ', 2533),
            ('Zdenko Matijević', 'Palit', 'LZR', 1132),
        ]},
        {'registered': 6624, 'cast': 5447, 'invalid': 178, 'candidates': [
            ('Josip Andrić', 'Barbat', 'HDZ', 2699),
            ('Dragan Andrić', 'Barbat', 'SKH-SDP', 1673),
            ('Zdenko Matijević', 'Palit', 'LZR', 803),
        ]},
    ], 'winner': 'Josip Andrić'},
    77: {'name': 'Rijeka', 'rounds': [
        {'registered': 153825, 'cast': 128144, 'invalid': 3969, 'candidates': [
            ('Lovorko Barbarić', 'Rijeka', 'SDSH,KNS', 22298),
            ('Josip Buršić', 'Rijeka', 'SKH-SDP', 53829),
            ('Marin Črnja', 'Rijeka', 'HDZ', 32219),
            ('Slavko Jurišić', 'Rijeka', 'SSH', 5723),
            ('Rade Marelić', 'Rijeka', 'RDS', 10106),
        ]},
        {'registered': 153575, 'cast': 112622, 'invalid': 2937, 'candidates': [
            ('Josip Buršić', 'Rijeka', 'SKH-SDP', 63598),
            ('Marin Črnja', 'Rijeka', 'HDZ', 46087),
        ]},
    ], 'winner': 'Josip Buršić'},
    78: {'name': 'Samobor - Zagreb', 'rounds': [
        {'registered': 35354, 'cast': 30016, 'invalid': 644, 'candidates': [
            ('Vladimir Burić', 'Samobor', 'SSH', 2459),
            ('Ivan Dujmović', 'Rude', 'HDZ', 17360),
            ('Zoran Legac', 'Lug', 'SKH-SDP', 3593),
            ('Dr Dinko Stanić', 'Zagreb', 'HDS,KNS', 5753),
        ]},
    ], 'winner': 'Ivan Dujmović'},
    79: {'name': 'Senj', 'rounds': [
        {'registered': 6825, 'cast': 6276, 'invalid': 197, 'candidates': [
            ('Zlatko Lenac', 'Rijeka', 'HDZ', 4123),
            ('Ivan Prpić', 'Senj', 'SKH-SDP', 1956),
        ]},
    ], 'winner': 'Zlatko Lenac'},
    80: {'name': 'Sesvete - Zagreb', 'rounds': [
        {'registered': 36901, 'cast': 30541, 'invalid': 465, 'candidates': [
            ('Ivan Kolak', 'Zagreb', 'HDZ', 19683),
            ('Branko Mihelić', 'Kobiljak', 'NK', 1379),
            ('Jozo Radoš', 'Sesvete', 'HSLS,KNS', 3761),
            ('Ivan Srbanić', 'Sesvetski Kraljevac', 'SKH-SDP', 5209),
        ]},
    ], 'winner': 'Ivan Kolak'},
    81: {'name': 'Sinj', 'rounds': [
        {'registered': 40437, 'cast': 34854, 'invalid': 883, 'candidates': [
            ('Ivan Ćurković', 'Sinj', 'KNS', 8101),
            ('Ante Gverić', 'Vrlika-Sinj', 'HDZ', 19373),
            ('Ante Sikirica', 'Split', 'SKH-SDP', 6308),
        ]},
    ], 'winner': 'Ante Gverić'},
    82: {'name': 'Slavonski Brod', 'rounds': [
        {'registered': 79762, 'cast': 67955, 'invalid': 2418, 'candidates': [
            ('Antun Babić', 'Oriovac', 'HDZ', 33787),
            ('Stjepan Lovrić', 'Slavonski Brod', 'SSH', 3704),
            ('Mladen Poštenjak', 'Slavonski Brod', 'HDS,KNS', 11703),
            ('Mirko Stuparević', 'Dubočac', 'NK', 1526),
            ('Mirko Šetina', 'Slavonski Brod', 'SKH-SDP', 13879),
        ]},
        {'registered': 81915, 'cast': 56343, 'invalid': 1112, 'candidates': [
            ('Antun Babić', 'Oriovac', 'HDZ', 33053),
            ('Mirko Šetina', 'Slavonski Brod', 'SKH-SDP', 15133),
            ('Mladen Poštenjak', 'Slavonski Brod', 'HDS', 6997),
        ]},
    ], 'winner': 'Antun Babić'},
    83: {'name': 'Slavonska Požega', 'rounds': [
        {'registered': 50380, 'cast': 45672, 'invalid': 775, 'candidates': [
            ('Vladimir Englman', 'Slavonska Požega', 'HDZ', 25337),
            ('Željko Krpan', 'Zagreb', 'NK', 1258),
            ('Ljiljana Kus', 'Slavonska Požega', 'SKH-SDP', 10651),
            ('Antun Lovrić', 'Slavonska Požega', 'HSLS,HDS,SDSH,HKDS,KNS', 5080),
            ('Đuro Šimić', 'Slavonska Požega', 'SSH', 2562),
        ]},
    ], 'winner': 'Vladimir Englman'},
    84: {'name': 'Slunj', 'rounds': [
        {'registered': 14496, 'cast': 12232, 'invalid': 245, 'candidates': [
            ('Rajko Katić', 'Slunj', 'SKH-SDP', 5429),
            ('Miroslav Modrušan', 'Slunj', 'HDZ', 6558),
        ]},
    ], 'winner': 'Miroslav Modrušan'},
    85: {'name': 'Solin', 'rounds': [
        {'registered': 19809, 'cast': 17589, 'invalid': 629, 'candidates': [
            ('Zvonimir Hrgović', 'Solin', 'HDZ', 13003),
            ('Mirko Kljaković Gašpić', 'Solin', 'SKH-SDP', 3957),
        ]},
    ], 'winner': 'Zvonimir Hrgović'},
    86: {'name': 'Susedgrad - Zagreb', 'rounds': [
        {'registered': 50697, 'cast': 42534, 'invalid': 790, 'candidates': [
            ('Milan Bajto', 'Zagreb', 'HDZ', 24183),
            ('Ante Iličić', 'Zagreb', 'NK', 2076),
            ('Miroslav Kolovrat', 'Zagreb', 'HKDS,KNS', 6748),
            ('Antun-Miroslav Tunuković', 'Zagreb', 'SKH-SDP', 8704),
        ]},
    ], 'winner': 'Milan Bajto'},
    87: {'name': 'Šibenik', 'rounds': [
        {'registered': 65623, 'cast': 52114, 'invalid': 1302, 'candidates': [
            ('Marko Dobrijević', 'Šibenik', 'SDS', 3548),
            ('Tome Mileta', 'Šibenik', 'HSLS,KNS', 6751),
            ('Vlatko Mrša', 'Šibenik', 'SKH-SDP', 13591),
            ('Zdravko Stančić', 'Šibenik', 'HDZ', 25037),
            ('Eugen Stojnić', 'Šibenik', 'EPZAŠ', 1493),
        ]},
        {'registered': 65493, 'cast': 47792, 'invalid': 856, 'candidates': [
            ('Zdravko Stančić', 'Šibenik', 'HDZ', 26173),
            ('Vlatko Mrša', 'Šibenik', 'SKH-SDP', 15963),
            ('Tome Mileta', 'Šibenik', 'HSLS,KNS', 4625),
        ]},
    ], 'winner': 'Zdravko Stančić'},
    88: {'name': 'Titova Korenica', 'rounds': [
        {'registered': 8729, 'cast': 8260, 'invalid': 1616, 'candidates': [
            ('Stevo Kalember', 'Titova Korenica', 'SKH-SDP', 4271),
            ('Dušan Zubović', 'Plitvička Jezera', 'SKH-SDP', 2356),
        ]},
    ], 'winner': 'Stevo Kalember'},
    89: {'name': 'Trešnjevka - Zagreb', 'rounds': [
        {'registered': 99419, 'cast': 83363, 'invalid': 3802, 'candidates': [
            ('Marijana Crnjak-Habek', 'Zagreb', 'NK', 1457),
            ('Dr Zvonko Lerotić', 'Zagreb', 'HSLS,KNS', 15262),
            ('Dr Branimir Molak', 'Zagreb', 'ADSH,RUSED,ZAZ-EZL', 4076),
            ('Jozef Papo', 'Zagreb', 'SKH-SDP', 19872),
            ('Ivan Sabolić', 'Zagreb', 'SSH', 2434),
            ('Vera Stanić', 'Zagreb', 'HDZ', 36460),
        ]},
        {'registered': 99883, 'cast': 72516, 'invalid': 518, 'candidates': [
            ('Vera Stanić', 'Zagreb', 'HDZ', 34723),
            ('Jozef Papo', 'Zagreb', 'SKH-SDP', 21957),
            ('Dr Zvonko Lerotić', 'Zagreb', 'HSLS,KNS', 15318),
        ]},
    ], 'winner': 'Vera Stanić'},
    90: {'name': 'Trnje - Zagreb', 'rounds': [
        {'registered': 39823, 'cast': 33701, 'invalid': 622, 'candidates': [
            ('Želimir Broz', 'Zagreb', 'HKDS,KNS', 5548),
            ('Gordana Grbić', 'Zagreb', 'SKH-SDP', 12367),
            ('Branka Slijepčević', 'Zagreb', 'SSH', 1348),
            ('Maja Uzelac', 'Zagreb', 'SSOH,ADSH-EZL', 1488),
            ('Ivanka Zorić', 'Zagreb', 'HDZ', 12328),
        ]},
        {'registered': 39796, 'cast': 30711, 'invalid': 395, 'candidates': [
            ('Gordana Grbić', 'Zagreb', 'SKH-SDP', 13522),
            ('Ivanka Zorić', 'Zagreb', 'HDZ', 12225),
            ('Želimir Broz', 'Zagreb', 'HKDS,KNS', 4569),
        ]},
    ], 'winner': 'Gordana Grbić'},
    91: {'name': 'Trogir', 'rounds': [
        {'registered': 16086, 'cast': 13562, 'invalid': 618, 'candidates': [
            ('Tonči Buble', 'Trogir', 'HSLS,KNS', 2222),
            ('Tonči Frana', 'Trogir', 'SKH-SDP', 4347),
            ('Branko Stamać', 'Trogir', 'HDZ', 6280),
        ]},
        {'registered': 16353, 'cast': 12533, 'invalid': 365, 'candidates': [
            ('Branko Stamać', 'Trogir', 'HDZ', 6396),
            ('Tonči Frana', 'Trogir', 'SKH-SDP', 4454),
            ('Tonči Buble', 'Trogir', 'HSLS,KNS', 1318),
        ]},
    ], 'winner': 'Branko Stamać'},
    92: {'name': 'Valpovo', 'rounds': [
        {'registered': 24438, 'cast': 20933, 'invalid': 727, 'candidates': [
            ('Martin Arnaut', 'Valpovo', 'HKDS,KNS', 2848),
            ('Zdravko Birovljević', 'Belišće', 'SKH-SDP', 5212),
            ('Tomislav Šutalo', 'Valpovo', 'HDZ', 11921),
        ]},
    ], 'winner': 'Tomislav Šutalo'},
    93: {'name': 'Varaždin', 'rounds': [
        {'registered': 68913, 'cast': 58571, 'invalid': 1860, 'candidates': [
            ('Branimir Cvetko', 'Varaždin', 'NK', 3410),
            ('Branko Čep', 'Varaždin', 'HDZ', 21087),
            ('Vilim Habuš', 'Varaždin', 'SKH-SDP', 13154),
            ('Stanko Ilčić', 'Varaždin', 'HDS,KNS', 19060),
        ]},
        {'registered': 68639, 'cast': 48462, 'invalid': 1152, 'candidates': [
            ('Branko Čep', 'Varaždin', 'HDZ', 22335),
            ('Stanko Ilčić', 'Varaždin', 'HDS', 11703),
            ('Vilim Habuš', 'Varaždin', 'SKH-SDP', 13272),
        ]},
    ], 'winner': 'Branko Čep'},
    94: {'name': 'Velika Gorica - Zagreb', 'rounds': [
        {'registered': 44114, 'cast': 37781, 'invalid': 938, 'candidates': [
            ('Nikola Bulat', 'D. Lomnica', 'HDZ', 20455),
            ('Ivan Cigetić', 'Velika Gorica', 'SSH', 6642),
            ('Stanko Cvjetko', 'Velika Gorica', 'SDSH,KNS', 6789),
            ('Zdravko Gudek', 'Staro Čiče', 'NK', 1159),
            ('Krunoslav Sabolić', 'Velika Gorica', 'NK', 1798),
        ]},
    ], 'winner': 'Nikola Bulat'},
    95: {'name': 'Vinkovci', 'rounds': [
        {'registered': 67714, 'cast': 59499, 'invalid': 1944, 'candidates': [
            ('Šime Brkljača', 'Vinkovci', 'SSH', 14484),
            ('Josip Dolanski', 'Vinkovci', 'HSS,KNS', 8677),
            ('Josip Peći', 'Vinkovci', 'HDZ', 32739),
            ('Dragutin Žanić', 'Vinkovci', 'HRSS', 1655),
        ]},
    ], 'winner': 'Josip Peći'},
    96: {'name': 'Virovitica', 'rounds': [
        {'registered': 33990, 'cast': 31013, 'invalid': 1248, 'candidates': [
            ('Dr Ratomir Hasan', 'Virovitica', 'SKH-SDP', 8919),
            ('Dr Josip Katanušić', 'Virovitica', 'HDZ', 16949),
            ('Tomo Kurečić', 'Virovitica', 'SSH', 1636),
            ('Drago Pocrnić', 'Virovitica', 'SDSH,KNS', 2261),
        ]},
    ], 'winner': 'Dr Josip Katanušić'},
    97: {'name': 'Vis', 'rounds': [
        {'registered': 3124, 'cast': 2622, 'invalid': 212, 'candidates': [
            ('Dr Joško Božanić', 'Komiža', 'NK', 663),
            ('Branko Pašalić', 'Vis', 'HDZ', 595),
            ('Miće Radišić - Pavla', 'Vis', 'SKH-SDP', 1152),
        ]},
        {'registered': 3176, 'cast': 2469, 'invalid': 153, 'candidates': [
            ('Miće Radišić - Pavla', 'Vis', 'SKH-SDP', 1171),
            ('Dr Joško Božanić', 'Komiža', 'NK', 536),
            ('Branko Pašalić', 'Vis', 'HDZ', 609),
        ]},
    ], 'winner': 'Miće Radišić - Pavla'},
    98: {'name': 'Vojnić', 'rounds': [
        {'registered': 6167, 'cast': 5737, 'invalid': 110, 'candidates': [
            ('Mile Dakić', 'Vojnić', 'JSDS', 2807),
            ('Milić Napijalo', 'Vojnić', 'SKH-SDP', 2820),
        ]},
        {'registered': 6132, 'cast': 5571, 'invalid': 69, 'candidates': [
            ('Milić Napijalo', 'Vojnić', 'SKH-SDP,SSH,SSOH,SUBNOR', 3462),
            ('Mile Dakić', 'Vojnić', 'JSDS', 2040),
        ]},
    ], 'winner': 'Milić Napijalo'},
    99: {'name': 'Vrbovec', 'rounds': [
        {'registered': 20616, 'cast': 19699, 'invalid': 1085, 'candidates': [
            ('Mr Mladen Beck', 'Celine', 'SKH-SDP', 4982),
            ('Darko Hrastovec', 'Ladina', 'HDZ', 9806),
            ('Mr Dragutin Vulić', 'Vrbovec', 'SDSH,KNS', 3826),
        ]},
        {'registered': 21070, 'cast': 17720, 'invalid': 712, 'candidates': [
            ('Darko Hrastovec', 'Ladina', 'HDZ', 10177),
            ('Mr Mladen Beck', 'Celine', 'SKH-SDP', 4663),
            ('Mr Dragutin Vulić', 'Vrbovec', 'SDSH,KNS', 2168),
        ]},
    ], 'winner': 'Darko Hrastovec'},
    100: {'name': 'Vrbovsko', 'rounds': [
        {'registered': 5496, 'cast': 4987, 'invalid': 549, 'candidates': [
            ('Krunoslav Antić', 'Vrbovsko', 'SKH-SDP', 2974),
            ('Boris Kučić', 'Srp. Moravice', 'SSH', 574),
            ('Nedjeljko Mamula', 'Vrbovsko', 'SJ', 883),
        ]},
    ], 'winner': 'Krunoslav Antić'},
    101: {'name': 'Vrginmost', 'rounds': [
        {'registered': 12384, 'cast': 11112, 'invalid': 1478, 'candidates': [
            ('Željko Milojević', 'Vrginmost', 'NK', 2069),
            ('Veljko Pjevac', 'Vrginmost', 'SKH-SDP,SSH', 7565),
        ]},
    ], 'winner': 'Veljko Pjevac'},
    102: {'name': 'Vrgorac', 'rounds': [
        {'registered': 5853, 'cast': 4834, 'invalid': 212, 'candidates': [
            ('Ante Galić', 'Vrgorac', 'HDZ', 1572),
            ('Vatro Kapović', 'Vrgorac', 'SSOH', 218),
            ('Vlado Ravlić', 'Zagreb', 'SKH-SDP', 2832),
        ]},
    ], 'winner': 'Vlado Ravlić'},
    103: {'name': 'Zabok', 'rounds': [
        {'registered': 27927, 'cast': 23143, 'invalid': 1046, 'candidates': [
            ('Dragutin Bratković', 'Zabok', 'SKH-SDP', 4565),
            ('Franjo Car', 'Bedekovčina', 'KNS', 3293),
            ('Dr Juraj Frajman', 'Krapinske Toplice', 'HDZ', 12397),
            ('Dr Željko Lončar', 'Zabok', 'SSH', 1842),
        ]},
    ], 'winner': 'Dr Juraj Frajman'},
    104: {'name': 'Zadar', 'rounds': [
        {'registered': 95561, 'cast': 73484, 'invalid': 1391, 'candidates': [
            ('Stanislav Antić', 'Zadar', 'SKH-SDP', 19986),
            ('Davor Aras', 'Zadar', 'HDZ', 40600),
            ('Miroslav Buljan', 'Zadar', 'SZH', 1047),
            ('Ante Jurjević', 'Zadar', 'NK', 1129),
            ('Mladen Katić', 'Zadar', 'NK', 554),
            ('Vjekoslav Krpina', 'Zadar', 'SSH', 1078),
            ('Gojko Marinković', 'Zagreb', 'RUSED-EZL', 887),
            ('Zlatko Matulić', 'Zadar', 'HSLS,KNS', 4460),
            ('Jovan Prostran', 'Zadar', 'NK', 1452),
            ('Vjekoslav Surač', 'Zadar', 'USP', 900),
        ]},
    ], 'winner': 'Davor Aras'},
    105: {'name': 'Zaprešić - Zagreb', 'rounds': [
        {'registered': 29342, 'cast': 25170, 'invalid': 790, 'candidates': [
            ('Nikola Čubela', 'Prudnice', 'NK', 1476),
            ('Mile Ivančić', 'Zaprešić', 'HDZ', 16312),
            ('Ivan Košir', 'Zaprešić', 'SKH-SDP', 4558),
            ('Nikola Rešetar', 'Laduč', 'SSH', 2034),
        ]},
    ], 'winner': 'Mile Ivančić'},
    106: {'name': 'Zelina', 'rounds': [
        {'registered': 12879, 'cast': 11477, 'invalid': 308, 'candidates': [
            ('Goran Biljan', 'Zelina', 'HDZ', 6503),
            ('Ivan Grošinić', 'Zelina', 'KNS', 2320),
            ('Branko Žigrović', 'Zelina', 'SKH-SDP', 1589),
            ('Drago Žigrović', 'Zelina', 'SSH', 649),
        ]},
    ], 'winner': 'Goran Biljan'},
    107: {'name': 'Zlatar Bistrica', 'rounds': [
        {'registered': 23813, 'cast': 21157, 'invalid': 780, 'candidates': [
            ('Franjo Bolfek', 'Zlatar', 'SKH-SDP', 1679),
            ('Dragutin Jakopović', 'Konjščina', 'SKH-SDP', 1828),
            ('Željko Jakopović', 'Konjščina', 'SSH', 1176),
            ('Kazimir Sviben', 'Zlatar', 'HDZ', 15407),
        ]},
    ], 'winner': 'Kazimir Sviben'},
    108: {'name': 'Županja', 'rounds': [
        {'registered': 32401, 'cast': 27369, 'invalid': 1166, 'candidates': [
            ('Mirko Gloković', 'Županja', 'HSS,KNS', 5487),
            ('Matej Janković', 'Vrbanja', 'HDZ', 14506),
            ('Josip Šinka', 'Županja', 'SSH', 1638),
            ('Stjepan Tucaković', 'Županja', 'SKH-SDP', 4464),
        ]},
    ], 'winner': 'Matej Janković'},
    109: {'name': 'Gradska zajednica općina Zagreb', 'rounds': [
        {'registered': 703370, 'cast': 576948, 'invalid': 13005, 'candidates': [
            ('Ljudevit Bauer', 'Martin pod Okićem', 'NK', 24236),
            ('Lovro Lisičić', 'Zagreb', 'SSH', 22482),
            ('Siniša Maričić', 'Zagreb', 'SDSHJ', 30533),
            ('Dr Mato Mikić', 'Zagreb', 'SKH-SDP', 153433),
            ('Đuro Perica', 'Zagreb', 'HDZ', 327565),
        ]},
    ], 'winner': 'Đuro Perica'},
    110: {'name': 'Hvar', 'rounds': [
        {'registered': 9416, 'cast': 7649, 'invalid': 340, 'candidates': [
            ('Božidar Gamulin', 'Jelsa', 'HKDS,KNS', 1340),
            ('Marin Mileta', 'Pitve', 'HDZ', 2593),
            ('Branko Nardelli', 'Zagreb', 'SKH-SDP', 2384),
            ('Luka Roić', 'Split', 'HSS,KNS', 673),
        ]},
        {'registered': 9461, 'cast': 7132, 'invalid': 314, 'candidates': [
            ('Marin Mileta', 'Pitve', 'HDZ', 3982),
            ('Branko Nardelli', 'Zagreb', 'SKH-SDP', 2836),
        ]},
    ], 'winner': 'Marin Mileta'},
    111: {'name': 'Osijek', 'rounds': [
        {'registered': 130142, 'cast': 106825, 'invalid': 5850, 'candidates': [
            ('Dr Gordana Ajduković', 'Osijek', 'SSOH', 37901),
            ('Marija Arhanić', 'Osijek', 'NK', 5793),
            ('Petar Kljaić', 'Osijek', 'HDZ', 34980),
            ('Ivica Vrkić', 'Osijek', 'HDS,SDSH,HKDS,KNS', 22301),
        ]},
        {'registered': 131403, 'cast': 98882, 'invalid': 3234, 'candidates': [
            ('Dr Gordana Ajduković', 'Osijek', 'SSOH,SKH-SDP,SSH', 42655),
            ('Petar Kljaić', 'Osijek', 'HDZ', 40094),
            ('Ivica Vrkić', 'Osijek', 'HDS,SDSH,HKDS,KNS', 12899),
        ]},
    ], 'winner': 'Dr Gordana Ajduković'},
    112: {'name': 'Rovinj', 'rounds': [
        {'registered': 14715, 'cast': 11999, 'invalid': 1295, 'candidates': [
            ('Petar Bralić', 'Rovinj', 'SKH-SDP', 5894),
            ('Mario Matohanca', 'Rovinj', 'HDS,KNS', 4799),
        ]},
        {'registered': 14864, 'cast': 6421, 'invalid': 523, 'candidates': [
            ('Petar Bralić', 'Rovinj', 'SKH-SDP', 3117),
            ('Mario Matohanca', 'Rovinj', 'HDS', 2780),
        ]},
    ], 'winner': 'Petar Bralić'},
    113: {'name': 'Sisak', 'rounds': [
        {'registered': 65431, 'cast': 53280, 'invalid': 1515, 'candidates': [
            ('Ivan Gavron', 'Sisak', 'HDZ', 16551),
            ('Marijan Malina', 'Sisak', 'SKH-SDP', 23659),
            ('Franjo Matoc', 'Sisak', 'HSLS,KNS', 6120),
            ('Mile Mikić', 'Sisak', 'SGS', 1370),
            ('Josip Podnar', 'Sisak', 'SSH', 4065),
        ]},
        {'registered': 66294, 'cast': 47613, 'invalid': 1986, 'candidates': [
            ('Marijan Malina', 'Sisak', 'SKH-SDP', 26233),
            ('Franjo Matoc', 'Sisak', 'HSLS,KNS', 19388),
        ]},
    ], 'winner': 'Marijan Malina'},
    114: {'name': 'Split', 'rounds': [
        {'registered': 150610, 'cast': 125727, 'invalid': 1994, 'candidates': [
            ('Dr Branko Božinović', 'Split', 'HDZ', 50859),
            ('Mr Miljenko Lović', 'Split', 'NK', 961),
            ('Ankica Luetić', 'Split', 'ZAS', 3384),
            ('Jadran Marinković', 'Split', 'SKH-SDP', 47433),
            ('Đorđe Paro', 'Split', 'GS', 625),
            ('Dr Ante Tukić', 'Split', 'HSLS,KNS', 18479),
        ]},
        {'registered': 155921, 'cast': 106037, 'invalid': 1121, 'candidates': [
            ('Dr Branko Božinović', 'Split', 'HDZ', 46176),
            ('Jadran Marinković', 'Split', 'SKH-SDP', 45635),
            ('Dr Ante Tukić', 'Split', 'HSLS,KNS', 12988),
        ]},
    ], 'winner': 'Dr Branko Božinović'},
    # The main report listed Vukovar as unfinished (an appeal was pending at
    # the Supreme Court); the supplement corrects it: decided 6 May 1990.
    115: {'name': 'Vukovar', 'rounds': [
        {'registered': 61387, 'cast': 54202, 'invalid': 2161, 'candidates': [
            ('Dušan Gajari', 'Borovo', 'NK', 1866),
            ('Borislav Magovac', 'Ilok', 'NK', 1231),
            ('Dr Lazar Maričić', 'Vukovar', 'SSH', 3571),
            ('Milan Milić', 'Vukovar', 'SSH', 1700),
            ('Milenko Milinković', 'Vukovar', 'SKH-SDP', 24726),
            ('Božo Srebrović', 'Vukovar', 'HDZ', 14498),
            ('Dragutin Šurlan', 'Borovo', 'SSH', 1394),
            ('Mladen Tadić', 'Ilok', 'HKDS,KNS', 3055),
        ]},
        {'registered': 62014, 'cast': 52257, 'invalid': 1227, 'candidates': [
            ('Milenko Milinković', 'Vukovar', 'SKH-SDP', 32182),
            ('Božo Srebrović', 'Vukovar', 'HDZ', 18848),
        ]},
    ], 'winner': 'Milenko Milinković'},
}
