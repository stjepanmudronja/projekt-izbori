"""Transcription of the 1990 Društveno-političko vijeće election.

Source: `files/rezultati_sabor/1990/1990_1_1_Sabor_Rezultati_Drustveno_politicko_vijece.pdf`
(76 pages) and its supplement `…_dopunski_izvjestaj.pdf` (4 pages), both
CCITT-G4 scans with no text layer, rendered with `tools/extract_scanned_pdf.py`
and read off the images.

The 1990 Sabor had three chambers, each elected separately; this is chamber
A), the "socio-political council" every adult voted for — the one usually
quoted as *the* 1990 result. 80 single-member units, two-round majority: a
candidate who won outright in round 1 was elected, otherwise the vote was
repeated two weeks later (Article 58(2) of the electoral law) and the round-2
leader elected (Article 58(6)).

`DISTRICTS`: unit -> name, rounds, winner. Each round holds registered, cast,
invalid and the candidates as (name, residence, party, votes), in the report's
order. `party` is a comma-separated string of abbreviations from `PARTIES`, the
report printing each nominating party in full on its own line; a coalition
joined under "Koalicija narodnog sporazuma" ends in `KNS`.

Checks: in every round, candidate votes + invalid ballots never exceed `cast`,
and the named winner leads the deciding round. Unlike 1992 they often fall
*short* of it — by 0 to a few hundred, never the other way — because "glasalo
je N birača" counts voters signed off at the polling place, and the report
never accounts for every one of those as a ballot. The gap is the report's,
not the transcription's: units 4, 10, 11 and 80 were re-read off zoomed crops
of the scan and the digits stand. Korčula (80) round 1 is the outlier at 1,246
(4% of the vote); every other gap is under 2%. Valid votes are therefore taken as the sum of
the candidates, and the gap is kept visible rather than spread onto anyone.
"""

PARTIES = {
    'HDZ': 'Hrvatska demokratska zajednica',
    'SKH-SDP': 'Savez komunista Hrvatske - Stranka demokratskih promjena',
    'SSH': 'Socijalistički savez - Savez socijalista Hrvatske',
    'SSOH': 'Savez socijalističke omladine Hrvatske',
    'HKDS': 'Hrvatska kršćanska demokratska stranka',
    'HDS': 'Hrvatska demokratska stranka',
    'SDSH': 'Socijaldemokratska stranka Hrvatske',
    'HSS': 'Hrvatska seljačka stranka',
    'HSLS': 'Hrvatski socijalno-liberalni savez',
    'KNS': 'Koalicija narodnog sporazuma',
    'JSDS': 'Jugoslavenska samostalna demokratska stranka',
    'SDSHJ': 'Socijaldemokratski savez Hrvatske / Jugoslavije',
    'HS': 'Hrvatska stranka',
    'DSAH': 'Demokratski savez Albanaca Hrvatske',
    'ZAZ-EZL': 'Zelena akcija Zagreb - Evropska zelena lista',
    'RUSED-EZL': 'Radikalno udruženje za Sjedinjene Evropske Države - Evropska zelena lista',
    'ADSH-EZL': 'Autonomni demokratski savez Hrvatske - Evropska zelena lista',
    'PZK': 'Pokret za konfederaciju',
    'SDS': 'Srpska demokratska stranka',
    'SJ': 'Stranka Jugoslavena',
    'RDS': 'Riječki demokratski savez',
    'ODF': 'Otočki demokratski forum',
    'USPŠ': 'Udruženje samostalnih privrednika Šibenika',
    'HMP': 'Hrvatski mirotvorni pokret',
    'ZAS': 'Zelena akcija Split',
    'ZSR': 'Zelena stranka Rijeka',
    'NK': 'Nezavisni kandidat',
}

DISTRICTS = {
    1: {'name': 'Beli Manastir', 'rounds': [
        {'registered': 40529, 'cast': 33800, 'invalid': 3303, 'candidates': [
            ('Goran Blagus', 'Beli Manastir', 'NK', 6322),
            ('Ivan Gregurek', 'Kneževi Vinogradi', 'SKH-SDP', 6589),
            ('Stjepan Kalčić', 'Luč', 'SSH', 4128),
            ('Janoš Sloboda', 'Beli Manastir', 'SSH', 4122),
            ('Ivan Tormaš', 'Beli Manastir', 'SKH-SDP', 9336),
        ]},
        {'registered': 39767, 'cast': 27645, 'invalid': 2067, 'candidates': [
            ('Ivan Tormaš', 'Beli Manastir', 'SKH-SDP', 11610),
            ('Ivan Gregurek', 'Kneževi Vinogradi', 'SKH-SDP', 3994),
            ('Goran Blagus', 'Beli Manastir', 'NK', 5565),
            ('Stjepan Kalčić', 'Luč', 'SSH', 1880),
            ('Janoš Sloboda', 'Beli Manastir', 'SSH', 2529),
        ]},
    ], 'winner': 'Ivan Tormaš'},
    2: {'name': 'Osijek I', 'rounds': [
        {'registered': 43615, 'cast': 34510, 'invalid': 1347, 'candidates': [
            ('Dr Dubravko Božić', 'Osijek', 'SSH', 12841),
            ('Ante Jelavić', 'Osijek', 'HDZ', 13920),
            ('Dr Josip Planinić', 'Osijek', 'HKDS,HDS,SDSH,KNS', 6402),
        ]},
        {'registered': 44382, 'cast': 32072, 'invalid': 6664, 'candidates': [
            ('Ante Jelavić', 'Osijek', 'HDZ', 15611),
            ('Dr Josip Planinić', 'Osijek', 'HKDS,HDS,SDSH,KNS', 9797),
        ]},
    ], 'winner': 'Ante Jelavić'},
    3: {'name': 'Osijek II', 'rounds': [
        {'registered': 43181, 'cast': 34899, 'invalid': 1314, 'candidates': [
            ('Mr Mato Arlović', 'Osijek', 'SKH-SDP', 7179),
            ('Dr Đuro Berber', 'Osijek', 'SKH-SDP', 6030),
            ('Mr Anto Lovrić', 'Osijek', 'HDZ', 11782),
            ('Miroslav Pisarević', 'Osijek', 'SSH', 1644),
            ('Ivan Škoro', 'Osijek', 'HDS,HKDS,SDSH,KNS', 5517),
            ('Dr Željko Živković', 'Osijek', 'NK', 1433),
        ]},
        {'registered': 43921, 'cast': 32802, 'invalid': 960, 'candidates': [
            ('Mr Anto Lovrić', 'Osijek', 'HDZ', 13823),
            ('Mr Mato Arlović', 'Osijek', 'SKH-SDP,SSH,SSOH', 14284),
            ('Ivan Škoro', 'Osijek', 'HDS,HKDS,SDSH,KNS', 3735),
        ]},
    ], 'winner': 'Mr Mato Arlović'},
    4: {'name': 'Osijek III', 'rounds': [
        {'registered': 42156, 'cast': 35842, 'invalid': 2352, 'candidates': [
            ('Vlado Čerina', 'Sarvaš', 'SSH', 1861),
            ('Ilija Dumančić', 'Čepin', 'HDS,SDSH,HKDS,KNS', 3205),
            ('Mijo Grbeša', 'Čepin', 'SKH-SDP', 7248),
            ('Milan Ilić', 'Bijelo Brdo', 'JSDS', 4183),
            ('Simo Trbojević', 'Tenja', 'NK', 3969),
            ('Ivan Vekić', 'Višnjevac', 'HDZ', 13023),
        ]},
        {'registered': 43053, 'cast': 34307, 'invalid': 1079, 'candidates': [
            ('Ivan Vekić', 'Višnjevac', 'HDZ', 14919),
            ('Mijo Grbeša', 'Čepin', 'SKH-SDP', 11983),
            ('Milan Ilić', 'Bijelo Brdo', 'JSDS', 4319),
            ('Ilija Dumančić', 'Čepin', 'HDS,SDSH,HKDS,KNS', 2007),
        ]},
    ], 'winner': 'Ivan Vekić'},
    5: {'name': 'Našice', 'rounds': [
        {'registered': 51465, 'cast': 46025, 'invalid': 1847, 'candidates': [
            ('Nikola Abramović', 'Našice', 'SSH', 2660),
            ('Mr Drago Balač', 'Našice', 'SKH-SDP', 5500),
            ('Vinko Buljan', 'Feričanci', 'HDZ', 12647),
            ('Krunoslav Nikšić', 'Našice', 'HKDS,KNS', 6992),
            ('Ivan Petrović', 'Valpovo', 'SKH-SDP', 4901),
            ('Željko Šafranko', 'Valpovo', 'HDZ', 11478),
        ]},
        {'registered': 50909, 'cast': 40945, 'invalid': 954, 'candidates': [
            ('Vinko Buljan', 'Feričanci', 'HDZ', 13578),
            ('Željko Šafranko', 'Valpovo', 'HDZ', 11576),
            ('Krunoslav Nikšić', 'Našice', 'HKDS,KNS', 5204),
            ('Mr Drago Balač', 'Našice', 'SKH-SDP', 9633),
        ]},
    ], 'winner': 'Vinko Buljan'},
    6: {'name': 'Podravska Slatina', 'rounds': [
        {'registered': 49509, 'cast': 45356, 'invalid': 1746, 'candidates': [
            ('Ivan Bušljeta', 'Zdenci', 'SKH-SDP', 5033),
            ('Đuro Jorgić', 'Podravska Slatina', 'NK', 5165),
            ('Stjepan Mesić', 'Zagreb', 'HDZ', 22713),
            ('Ivica Mikičić', 'Donji Miholjac', 'KNS', 2495),
            ('Ksenija Plantak', 'Podravska Slatina', 'SKH-SDP', 6849),
            ('Mirko Šomođi', 'Podravska Slatina', 'SSH', 1355),
        ]},
    ], 'winner': 'Stjepan Mesić'},
    7: {'name': 'Vukovar', 'rounds': [
        {'registered': 61387, 'cast': 54183, 'invalid': 2053, 'candidates': [
            ('Teodora Aleksić', 'Ilok', 'SSH', 1908),
            ('Gordana Gvojić', 'Vukovar', 'NK', 1638),
            ('Franjo Ivančić', 'Borovo', 'NK', 1252),
            ('Božidar Jukić', 'Vukovar', 'SKH-SDP', 23048),
            ('Martin Kešnjer', 'Vukovar', 'SSH', 2209),
            ('Jure Kolak', 'Vukovar', 'HDZ', 15891),
            ('Andrija Kuric', 'Ilok', 'HKDS,KNS', 2255),
            ('Gojko Medaković', 'Borovo', 'NK', 3929),
        ]},
        {'registered': 62014, 'cast': 52301, 'invalid': 1315, 'candidates': [
            ('Božidar Jukić', 'Vukovar', 'SKH-SDP', 31762),
            ('Jure Kolak', 'Vukovar', 'HDZ', 19224),
        ]},
    ], 'winner': 'Božidar Jukić'},
    8: {'name': 'Vinkovci I', 'rounds': [
        {'registered': 38318, 'cast': 33679, 'invalid': 1161, 'candidates': [
            ('Drago Ereš', 'Cerić', 'HDZ', 19634),
            ('Mr Zvonimir Levaković', 'Vinkovci', 'NK', 2419),
            ('Emil Međugorac', 'Vinkovci', 'NK', 1600),
            ('Petar Šuker', 'Nuštar', 'SKH-SDP,SSH', 8865),
        ]},
    ], 'winner': 'Drago Ereš'},
    9: {'name': 'Vinkovci II', 'rounds': [
        {'registered': 29396, 'cast': 25820, 'invalid': 928, 'candidates': [
            ('Mladen Kevo', 'Privlaka', 'SSH,SKH-SDP', 6900),
            ('Ivan Prgomet', 'Vinkovci', 'NK', 2269),
            ('Vladimir Šeks', 'Osijek', 'HDZ', 15723),
        ]},
    ], 'winner': 'Vladimir Šeks'},
    10: {'name': 'Županja', 'rounds': [
        {'registered': 32117, 'cast': 27142, 'invalid': 1033, 'candidates': [
            ('Krunoslav Baotić', 'Županja', 'NK', 1923),
            ('Josip Barišić', 'Županja', 'SKH-SDP', 4818),
            ('Stjepan Blažinkov', 'Županja', 'HDZ', 13750),
            ('Dr Josip Stojanović', 'Zagreb', 'HSS,KNS', 5515),
        ]},
    ], 'winner': 'Stjepan Blažinkov'},
    11: {'name': 'Đakovo', 'rounds': [
        {'registered': 35301, 'cast': 31442, 'invalid': 916, 'candidates': [
            ('Mirko Križić', 'Đakovo', 'SKH-SDP', 4460),
            ('Dr Mirko Petrošević', 'Đakovo', 'SSH', 2707),
            ('Ivica Šutalo', 'Đakovo', 'KNS', 3970),
            ('Darko Vrtarić', 'Đakovo', 'HDZ', 19362),
        ]},
    ], 'winner': 'Darko Vrtarić'},
    12: {'name': 'Slavonski Brod I', 'rounds': [
        {'registered': 39377, 'cast': 32666, 'invalid': 1069, 'candidates': [
            ('Ivan Grgić', 'Slavonski Brod', 'SSH', 2192),
            ('Petar Katalinić', 'Slavonski Brod', 'HDS,KNS', 5795),
            ('Antun Milović', 'Slavonski Brod', 'SKH-SDP', 10738),
            ('Milan Tapalović', 'Slavonski Brod', 'HDZ', 12609),
        ]},
        {'registered': 40434, 'cast': 26957, 'invalid': 491, 'candidates': [
            ('Milan Tapalović', 'Slavonski Brod', 'HDZ', 13211),
            ('Antun Milović', 'Slavonski Brod', 'SKH-SDP', 10245),
            ('Petar Katalinić', 'Slavonski Brod', 'HDS', 2972),
        ]},
    ], 'winner': 'Milan Tapalović'},
    13: {'name': 'Slavonski Brod II', 'rounds': [
        {'registered': 40316, 'cast': 35364, 'invalid': 1493, 'candidates': [
            ('Mihael Blaževac', 'Slavonski Brod', 'HDS,KNS', 5646),
            ('Ivan Borevković', 'Slavonski Brod', 'SSH', 2376),
            ('Ante Klarić', 'Slavonski Brod', 'HDZ', 19470),
            ('Ivo Marković', 'Slavonski Brod', 'SKH-SDP', 4600),
            ('Mirko Šamija', 'Zagreb', 'NK', 1301),
        ]},
    ], 'winner': 'Ante Klarić'},
    14: {'name': 'Slavonska Požega', 'rounds': [
        {'registered': 50380, 'cast': 45261, 'invalid': 343, 'candidates': [
            ('Marija Bajt', 'Slavonska Požega', 'HDZ', 24934),
            ('Slavko Bartošak', 'Slavonska Požega', 'SKH-SDP', 9688),
            ('Tomislav Crnjac', 'Kutjevo', 'SSH', 1233),
            ('Tomislav Čulina', 'Zagreb', 'HSS,KNS', 1537),
            ('Ivan Enjingi', 'Slavonska Požega', 'NK', 776),
            ('Dane Pavlica', 'Slavonska Požega', 'NK', 2368),
            ('Filip Potrebica', 'Slavonska Požega', 'HSLS,HDS,SDSH,HKDS,KNS', 4318),
        ]},
    ], 'winner': 'Marija Bajt'},
    15: {'name': 'Nova Gradiška', 'rounds': [
        {'registered': 43522, 'cast': 39592, 'invalid': 1444, 'candidates': [
            ('Milan Drageljević', 'Nova Gradiška', 'SKH-SDP,SSH', 10592),
            ('Alojz Dubiel', 'Staro Petrovo Selo', 'HDZ', 19236),
            ('Igor Ferenčina', 'Nova Gradiška', 'HSLS,HDS,HKDS,KNS', 5717),
            ('Branko Mlinac', 'Nova Gradiška', 'SSH', 939),
            ('Ivan Povh', 'Nova Gradiška', 'SSH', 1174),
            ('Vojislav Vujisić', 'Nova Gradiška', 'NK', 490),
        ]},
        {'registered': 42960, 'cast': 36552, 'invalid': 692, 'candidates': [
            ('Alojz Dubiel', 'Staro Petrovo Selo', 'HDZ', 24491),
            ('Milan Drageljević', 'Nova Gradiška', 'SKH-SDP,SSH', 11369),
        ]},
    ], 'winner': 'Alojz Dubiel'},
    16: {'name': 'Daruvar', 'rounds': [
        {'registered': 42013, 'cast': 36583, 'invalid': 7744, 'candidates': [
            ('Petar Džodan', 'Pakrac', 'SKH-SDP', 20917),
            ('Savo Šeatović', 'Lipik', 'SSH', 7922),
        ]},
    ], 'winner': 'Petar Džodan'},
    17: {'name': 'Garešnica', 'rounds': [
        {'registered': 36515, 'cast': 32938, 'invalid': 2144, 'candidates': [
            ('Antun Baković', 'Zagreb', 'HDZ', 7705),
            ('Ivan Lacković', 'Garešnica', 'SSH', 7357),
            ('Marija Pintarić', 'Garešnica', 'HDS,KNS', 9040),
            ('Boro Preradović', 'Zagreb', 'SSH', 6692),
        ]},
        {'registered': 36170, 'cast': 30244, 'invalid': 1838, 'candidates': [
            ('Marija Pintarić', 'Garešnica', 'HDS', 9065),
            ('Antun Baković', 'Zagreb', 'HDZ', 8046),
            ('Ivan Lacković', 'Garešnica', 'SSH', 11295),
        ]},
    ], 'winner': 'Ivan Lacković'},
    18: {'name': 'Virovitica', 'rounds': [
        {'registered': 33317, 'cast': 30343, 'invalid': 796, 'candidates': [
            ('Dr Ivica Babić', 'Virovitica', 'NK', 1951),
            ('Mr Vladimir Bogati', 'Virovitica', 'HDZ', 17098),
            ('Radovan Jelić', 'Virovitica', 'SSH', 2832),
            ('Darko Marendić', 'Virovitica', 'SKH-SDP', 7666),
        ]},
    ], 'winner': 'Mr Vladimir Bogati'},
    19: {'name': 'Bjelovar', 'rounds': [
        {'registered': 49011, 'cast': 40790, 'invalid': 1546, 'candidates': [
            ('Stjepan Grula', 'Bjelovar', 'SSH', 2941),
            ('Dr Špiro Klobučić', 'Bjelovar', 'NK', 2128),
            ('Đuro Panjan', 'Bjelovar', 'HDZ', 15239),
            ('Stanislav Veseli', 'Bjelovar', 'HDS,KNS', 7577),
            ('Marija Vidaković', 'Bjelovar', 'SKH-SDP', 11359),
        ]},
        {'registered': 51116, 'cast': 37713, 'invalid': 938, 'candidates': [
            ('Đuro Panjan', 'Bjelovar', 'HDZ', 17714),
            ('Marija Vidaković', 'Bjelovar', 'SKH-SDP', 13985),
            ('Stanislav Veseli', 'Bjelovar', 'HDS', 5076),
        ]},
    ], 'winner': 'Đuro Panjan'},
    20: {'name': 'Đurđevac', 'rounds': [
        {'registered': 59590, 'cast': 52322, 'invalid': 2292, 'candidates': [
            ('Fabijan Fuček', 'Đurđevac', 'HKDS,KNS', 8860),
            ('Željko Husinec', 'Križevci', 'SSH', 4634),
            ('Ivanka Konfic', 'Križevci', 'SKH-SDP', 5700),
            ('Stjepan Sulimanac', 'Turnašica', 'HDZ', 24942),
            ('Martin Špegelj', 'Zagreb', 'SKH-SDP', 5894),
        ]},
        {'registered': 59274, 'cast': 41716, 'invalid': 1085, 'candidates': [
            ('Stjepan Sulimanac', 'Turnašica', 'HDZ', 25796),
            ('Fabijan Fuček', 'Đurđevac', 'HKDS,KNS', 5662),
            ('Ivanka Konfic', 'Križevci', 'SKH-SDP', 9173),
        ]},
    ], 'winner': 'Stjepan Sulimanac'},
    21: {'name': 'Koprivnica', 'rounds': [
        {'registered': 46213, 'cast': 38553, 'invalid': 1539, 'candidates': [
            ('Dr Dragutin Feletar', 'Koprivnica', 'NK', 3213),
            ('Stjepan Kapusta', 'Koprivnica', 'SKH-SDP', 11952),
            ('Ivan Keglević', 'Zagreb', 'HKDS,KNS', 2795),
            ('Dr Ivan Mesić', 'Koprivnica', 'HDZ', 15184),
            ('Ivan Večenaj', 'Gola', 'HSS,KNS', 3870),
        ]},
        {'registered': 44426, 'cast': 30470, 'invalid': 614, 'candidates': [
            ('Dr Ivan Mesić', 'Koprivnica', 'HDZ', 16531),
            ('Stjepan Kapusta', 'Koprivnica', 'SKH-SDP', 11028),
            ('Dr Dragutin Feletar', 'Koprivnica', 'NK', 2297),
        ]},
    ], 'winner': 'Dr Ivan Mesić'},
    22: {'name': 'Čakovec I', 'rounds': [
        {'registered': 43120, 'cast': 36541, 'invalid': 1741, 'candidates': [
            ('Franjo Čavlek', 'Juraj u Trnju', 'SSH', 2467),
            ('Ivan Hranjec', 'Goričan', 'HDZ', 11757),
            ('Anton Jurinec', 'Zagreb', 'NK', 2046),
            ('Stjepan Okun', 'Savska Ves', 'SSOH', 1303),
            ('Davorin Radošević', 'Čakovec', 'HKDS,KNS', 7848),
            ('Danijel Režek', 'Zagreb', 'SKH-SDP', 9379),
        ]},
        {'registered': 42727, 'cast': 31967, 'invalid': 1258, 'candidates': [
            ('Ivan Hranjec', 'Goričan', 'HDZ', 13092),
            ('Danijel Režek', 'Zagreb', 'SKH-SDP', 11693),
            ('Davorin Radošević', 'Čakovec', 'HKDS,KNS', 5924),
        ]},
    ], 'winner': 'Ivan Hranjec'},
    23: {'name': 'Čakovec II', 'rounds': [
        {'registered': 40905, 'cast': 33935, 'invalid': 1920, 'candidates': [
            ('Josip Cesar', 'Mursko Središće', 'SKH-SDP', 7931),
            ('Vladimir Kalšan', 'Šenkovec', 'SSH', 3349),
            ('Vjekoslav Marđetko', 'Čakovec', 'NK', 4318),
            ('Ivan Mezga', 'Selnica', 'HDZ', 13853),
            ('Dragutin Palašek', 'Zagreb', 'SDSHJ', 2564),
        ]},
        {'registered': 40465, 'cast': 28860, 'invalid': 1336, 'candidates': [
            ('Ivan Mezga', 'Selnica', 'HDZ', 16982),
            ('Josip Cesar', 'Mursko Središće', 'SKH-SDP', 10542),
        ]},
    ], 'winner': 'Ivan Mezga'},
    24: {'name': 'Varaždin I', 'rounds': [
        {'registered': 40047, 'cast': 34568, 'invalid': 1290, 'candidates': [
            ('Velimir Đuras', 'Varaždin', 'SKH-SDP', 7239),
            ('Josip Gomaz', 'Varaždin', 'NK', 2687),
            ('Mirko Ramušćak', 'Varaždin', 'HDS,KNS', 10164),
            ('Franjo Vručina', 'Zagreb', 'HDZ', 13188),
        ]},
        {'registered': 39157, 'cast': 29620, 'invalid': 1094, 'candidates': [
            ('Franjo Vručina', 'Zagreb', 'HDZ', 14690),
            ('Mirko Ramušćak', 'Varaždin', 'HDS', 6306),
            ('Velimir Đuras', 'Varaždin', 'SKH-SDP', 7530),
        ]},
    ], 'winner': 'Franjo Vručina'},
    25: {'name': 'Varaždin II', 'rounds': [
        {'registered': 45004, 'cast': 37706, 'invalid': 650, 'candidates': [
            ('Marijan Cingula', 'Varaždin', 'SKH-SDP', 9793),
            ('Radimir Čačić', 'Varaždin', 'KNS', 13009),
            ('Stjepan Drožđek', 'Sračinec', 'SSH', 2244),
            ('Alojz Markač', 'Hrašćica', 'HDZ', 12010),
        ]},
        {'registered': 45322, 'cast': 32067, 'invalid': 717, 'candidates': [
            ('Radimir Čačić', 'Varaždin', 'KNS', 8965),
            ('Alojz Markač', 'Hrašćica', 'HDZ', 12807),
            ('Marijan Cingula', 'Varaždin', 'SKH-SDP', 9578),
        ]},
    ], 'winner': 'Alojz Markač'},
    26: {'name': 'Ivanec', 'rounds': [
        {'registered': 51649, 'cast': 44873, 'invalid': 1557, 'candidates': [
            ('Ivan Beloša', 'Novi Marof', 'SSH', 2844),
            ('Martin Bunić', 'Ivanec', 'NK', 3453),
            ('Anđelko Havaš', 'Ljubešćica', 'HSLS,HDS,SDSH,HKDS,KNS', 6599),
            ('Mirjana Janušić', 'Novi Marof', 'SKH-SDP', 5365),
            ('Ivić Pašalić', 'Ivanec', 'HDZ', 21181),
            ('Davorin Zver', 'Ivanec', 'HSLS,KNS', 3874),
        ]},
        {'registered': 51789, 'cast': 34402, 'invalid': 1059, 'candidates': [
            ('Ivić Pašalić', 'Ivanec', 'HDZ', 24242),
            ('Anđelko Havaš', 'Ljubešćica', 'HSLS,HDS,SDSH,HKDS,KNS', 6234),
            ('Davorin Zver', 'Ivanec', 'HSLS,KNS', 2867),
        ]},
    ], 'winner': 'Ivić Pašalić'},
    27: {'name': 'Kutina', 'rounds': [
        {'registered': 47247, 'cast': 42298, 'invalid': 1729, 'candidates': [
            ('Branko Božičević', 'Kutina', 'HS', 2791),
            ('Stjepan Magdić', 'Kutina', 'SKH-SDP', 12929),
            ('Borislav Šelaj', 'Ivanić Grad', 'SSH', 2308),
            ('Ante Todorić', 'Zagreb', 'HSLS,KNS', 8475),
            ('Đuro Vidmarović', 'Zagreb', 'HDZ', 13987),
        ]},
        {'registered': 47354, 'cast': 36130, 'invalid': 1058, 'candidates': [
            ('Đuro Vidmarović', 'Zagreb', 'HDZ', 20350),
            ('Stjepan Magdić', 'Kutina', 'SKH-SDP', 14707),
        ]},
    ], 'winner': 'Đuro Vidmarović'},
    28: {'name': 'Vrbovec', 'rounds': [
        {'registered': 48619, 'cast': 42349, 'invalid': 2358, 'candidates': [
            ('Marija Belaić', 'Dugo Selo', 'SSH', 3575),
            ('Ivica Gaži', 'Zagreb', 'HDZ', 19512),
            ('Ljerka Habuzin', 'Zelina', 'SSH', 1903),
            ('Dr Ivan Kalinski', 'Zelina', 'HDS,KNS', 6352),
            ('Franjo Štefanović', 'Vrbovec', 'SSH', 8579),
        ]},
        {'registered': 49059, 'cast': 36546, 'invalid': 1514, 'candidates': [
            ('Ivica Gaži', 'Zagreb', 'HDZ', 20464),
            ('Franjo Štefanović', 'Vrbovec', 'SSH', 10064),
            ('Dr Ivan Kalinski', 'Zelina', 'HDS', 4504),
        ]},
    ], 'winner': 'Ivica Gaži'},
    29: {'name': 'Zlatar Bistrica', 'rounds': [
        {'registered': 46932, 'cast': 40862, 'invalid': 1633, 'candidates': [
            ('Marijan Gereci', 'Marija Bistrica', 'HDZ', 29173),
            ('Valentin Martinek', 'Donja Stubica', 'SKH-SDP', 4406),
            ('Dr Ivan Šantek', 'Zlatar Bistrica', 'SKH-SDP', 5650),
        ]},
    ], 'winner': 'Marijan Gereci'},
    30: {'name': 'Zabok', 'rounds': [
        {'registered': 36013, 'cast': 29873, 'invalid': 1336, 'candidates': [
            ('Mr Željko Bajza', 'Bedekovčina', 'SSH', 2085),
            ('Dr Stanko Belina', 'Zabok', 'HSLS,KNS', 3221),
            ('Petar Jakopec', 'Zlatar Bistrica', 'SKH-SDP', 4884),
            ('Dr Ivo Valent', 'Zabok', 'HDZ', 18347),
        ]},
    ], 'winner': 'Dr Ivo Valent'},
    31: {'name': 'Krapina', 'rounds': [
        {'registered': 33169, 'cast': 26334, 'invalid': 1733, 'candidates': [
            ('Sebastijan Dragčević', 'Pačetina Gornja', 'HDZ', 14836),
            ('Nikola Šiljeg', 'Hum na Sutli', 'HSLS,KNS', 4189),
            ('Davorin Šutina', 'Pregrada', 'SKH-SDP', 5127),
        ]},
    ], 'winner': 'Sebastijan Dragčević'},
    32: {'name': 'Zagreb - Dubrava I', 'rounds': [
        {'registered': 50762, 'cast': 41433, 'invalid': 748, 'candidates': [
            ('Dr Tomo Jantol', 'Sesvete', 'SSH', 1744),
            ('Slobodan Praljak', 'Zagreb', 'HDS,KNS', 4907),
            ('Marija Šola', 'Sesvete', 'SKH-SDP', 6375),
            ('Dr Franjo Tuđman', 'Zagreb', 'HDZ', 27643),
        ]},
    ], 'winner': 'Dr Franjo Tuđman'},
    33: {'name': 'Zagreb - Dubrava II', 'rounds': [
        {'registered': 49668, 'cast': 40256, 'invalid': 893, 'candidates': [
            ('Tom Berisha', 'Zagreb', 'DSAH,KNS', 3944),
            ('Josip Manolić', 'Zagreb', 'HDZ', 26488),
            ('Ivan Šiber', 'Zagreb', 'SKH-SDP', 8912),
        ]},
    ], 'winner': 'Josip Manolić'},
    34: {'name': 'Zagreb - Maksimir', 'rounds': [
        {'registered': 52666, 'cast': 41537, 'invalid': 615, 'candidates': [
            ('Dr Branko Caratan', 'Zagreb', 'SKH-SDP', 8147),
            ('Darko Mihajlović', 'Zagreb', 'ZAZ-EZL', 1319),
            ('Dane Roško', 'Zagreb', 'SSH', 2215),
            ('Dr Franjo Zenko', 'Zagreb', 'HSLS,KNS', 7321),
            ('Mr Miljenko Žagar', 'Zagreb', 'HDZ', 21403),
        ]},
    ], 'winner': 'Mr Miljenko Žagar'},
    35: {'name': 'Zagreb - Medveščak', 'rounds': [
        {'registered': 39560, 'cast': 32357, 'invalid': 349, 'candidates': [
            ('Vlado Gotovac', 'Zagreb', 'HSLS,KNS', 9281),
            ('Branko Grahovac', 'Zagreb', 'SSH', 605),
            ('Jasenka Kodrnja', 'Zagreb', 'ZAZ-EZL', 1249),
            ('Ivan Lučev', 'Zagreb', 'HDZ', 11902),
            ('Joško Marušić', 'Zagreb', 'SKH-SDP', 8442),
            ('Agata Račan', 'Zagreb', 'NK', 529),
        ]},
        {'registered': 40076, 'cast': 29260, 'invalid': 324, 'candidates': [
            ('Ivan Lučev', 'Zagreb', 'HDZ', 11597),
            ('Vlado Gotovac', 'Zagreb', 'HSLS,KNS', 8738),
            ('Joško Marušić', 'Zagreb', 'SKH-SDP', 8601),
        ]},
    ], 'winner': 'Ivan Lučev'},
    36: {'name': 'Zagreb - Peščenica', 'rounds': [
        {'registered': 38539, 'cast': 33206, 'invalid': 828, 'candidates': [
            ('Dušan Bilandžić', 'Zagreb', 'SKH-SDP', 10551),
            ('Tihomir Buklijaš', 'Zagreb', 'SSH', 1135),
            ('Lucijano Lukšić', 'Zagreb', 'ZAZ-EZL', 1476),
            ('Ivan Milas', 'Zagreb', 'HDZ', 13282),
            ('Đorđe Pribičević', 'Zagreb', 'HDS,KNS', 4929),
            ('Ivan Puhek', 'Zagreb', 'NK', 993),
        ]},
        {'registered': 38158, 'cast': 29292, 'invalid': 452, 'candidates': [
            ('Ivan Milas', 'Zagreb', 'HDZ', 14714),
            ('Dušan Bilandžić', 'Zagreb', 'SKH-SDP', 11351),
            ('Đorđe Pribičević', 'Zagreb', 'HDS', 2723),
        ]},
    ], 'winner': 'Ivan Milas'},
    37: {'name': 'Zagreb - Centar', 'rounds': [
        {'registered': 46592, 'cast': 33457, 'invalid': 625, 'candidates': [
            ('Dražen Budiša', 'Zagreb', 'HSLS,KNS', 9381),
            ('Milan Gavrović', 'Zagreb', 'SKH-SDP', 6603),
            ('Tatjana Holjevac-Koren', 'Zagreb', 'NK', 843),
            ('Ante Matutinović', 'Zagreb', 'SSH', 742),
            ('Božidar Petrač', 'Zagreb', 'HDZ', 13621),
            ('Diana Rexhepi', 'Zagreb', 'RUSED-EZL', 1012),
            ('Josip Živković', 'Zagreb', 'HS', 630),
        ]},
        {'registered': 45286, 'cast': 30368, 'invalid': 2087, 'candidates': [
            ('Božidar Petrač', 'Zagreb', 'HDZ', 15770),
            ('Dražen Budiša', 'Zagreb', 'HSLS,KNS', 12354),
        ]},
    ], 'winner': 'Božidar Petrač'},
    38: {'name': 'Zagreb - Črnomerec', 'rounds': [
        {'registered': 41952, 'cast': 34328, 'invalid': 520, 'candidates': [
            ('Marijan Hrđok', 'Zagreb', 'SSH', 1303),
            ('Ivan Šifter', 'Zagreb', 'SKH-SDP', 7333),
            ('Mr Gordana Turić', 'Zagreb', 'HDZ', 15856),
            ('Dr Marko Veselica', 'Zagreb', 'HSLS,HDS,SDSH,HKDS,HSS,KNS', 9298),
        ]},
        {'registered': 43469, 'cast': 30837, 'invalid': 481, 'candidates': [
            ('Mr Gordana Turić', 'Zagreb', 'HDZ', 14191),
            ('Dr Marko Veselica', 'Zagreb', 'HKDS,HDS,HSS,SDSH,HSLS,KNS', 9059),
            ('Ivan Šifter', 'Zagreb', 'SKH-SDP', 7064),
        ]},
    ], 'winner': 'Mr Gordana Turić'},
    39: {'name': 'Zagreb - Trnje', 'rounds': [
        {'registered': 39823, 'cast': 33773, 'invalid': 650, 'candidates': [
            ('Silvije Degen', 'Zagreb', 'SSH', 1610),
            ('Krešimir Džeba', 'Zagreb', 'KNS', 5759),
            ('Zoran Milović', 'Zagreb', 'ADSH-EZL', 931),
            ('Zvonimir Pavelić', 'Zagreb', 'HDZ', 11206),
            ('Ivica Račan', 'Zagreb', 'SKH-SDP', 13617),
        ]},
        {'registered': 39796, 'cast': 30706, 'invalid': 630, 'candidates': [
            ('Ivica Račan', 'Zagreb', 'SKH-SDP', 16060),
            ('Zvonimir Pavelić', 'Zagreb', 'HDZ', 14016),
        ]},
    ], 'winner': 'Ivica Račan'},
    40: {'name': 'Zagreb - Trešnjevka I', 'rounds': [
        {'registered': 42472, 'cast': 38594, 'invalid': 2141, 'candidates': [
            ('Ranko Čađo', 'Zagreb', 'NK', 727),
            ('Milan Kovač', 'Zagreb', 'HDZ', 16965),
            ('Jelena Lovrić', 'Zagreb', 'SKH-SDP', 9609),
            ('Dobrila Mikac', 'Zagreb', 'SSH', 1184),
            ('Dr Vlado Pandžić', 'Zagreb', 'HKDS,KNS', 7968),
        ]},
        {'registered': 46731, 'cast': 33586, 'invalid': 842, 'candidates': [
            ('Milan Kovač', 'Zagreb', 'HDZ', 16492),
            ('Jelena Lovrić', 'Zagreb', 'SKH-SDP', 9713),
            ('Dr Vlado Pandžić', 'Zagreb', 'HKDS,KNS', 6539),
        ]},
    ], 'winner': 'Milan Kovač'},
    41: {'name': 'Zagreb - Trešnjevka II', 'rounds': [
        {'registered': 52646, 'cast': 45203, 'invalid': 1878, 'candidates': [
            ('Vito Česmadžiski', 'Zagreb', 'RUSED-EZL', 1522),
            ('Neven Jurica', 'Zagreb', 'HDZ', 19206),
            ('Srđan Kliska', 'Zagreb', 'SSH', 1105),
            ('Dr Milorad Pupovac', 'Zagreb', 'SDSHJ', 762),
            ('Dr Zlatko Šimenc', 'Zagreb', 'SKH-SDP', 11837),
            ('Dr Antun Vujić', 'Zagreb', 'SDSH,KNS', 8893),
        ]},
        {'registered': 52383, 'cast': 38072, 'invalid': 2679, 'candidates': [
            ('Neven Jurica', 'Zagreb', 'HDZ', 18648),
            ('Dr Antun Vujić', 'Zagreb', 'SDSH,KNS', 16745),
        ]},
    ], 'winner': 'Neven Jurica'},
    42: {'name': 'Novi Zagreb I', 'rounds': [
        {'registered': 52019, 'cast': 42027, 'invalid': 726, 'candidates': [
            ('Aleksandar Broz', 'Zagreb', 'SKH-SDP', 13063),
            ('Ivan Družijanić', 'Zagreb', 'NK', 797),
            ('Dr Ivan Jakopović', 'Zagreb', 'NK', 585),
            ('Dubravka Korljan', 'Zagreb', 'HS', 610),
            ('Ivo Pancirov', 'Zagreb', 'HKDS,KNS', 5257),
            ('Željko Roško', 'Zagreb', 'RUSED-EZL', 1571),
            ('Zvonimir Turk', 'Zagreb', 'HDZ', 15485),
            ('Petar Vučić', 'Zagreb', 'PZK,KNS', 2529),
            ('Ljubomir Weiss', 'Zagreb', 'SSH', 978),
        ]},
        {'registered': 51476, 'cast': 36611, 'invalid': 698, 'candidates': [
            ('Zvonimir Turk', 'Zagreb', 'HDZ', 20187),
            ('Aleksandar Broz', 'Zagreb', 'SKH-SDP', 15726),
        ]},
    ], 'winner': 'Zvonimir Turk'},
    43: {'name': 'Novi Zagreb II', 'rounds': [
        {'registered': 50824, 'cast': 41753, 'invalid': 722, 'candidates': [
            ('Dr Drago Droždjek', 'Zagreb', 'SKH-SDP', 9931),
            ('Ivan Hetrich', 'Zagreb', 'ZAZ-EZL', 3202),
            ('Slavko Sontag', 'Zagreb', 'NK', 566),
            ('Dafinka Večerina', 'Zagreb', 'HSLS,KNS', 4923),
            ('Vice Vukojević', 'Zagreb', 'HDZ', 22053),
        ]},
    ], 'winner': 'Vice Vukojević'},
    44: {'name': 'Samobor', 'rounds': [
        {'registered': 58974, 'cast': 51594, 'invalid': 1449, 'candidates': [
            ('Relja Bašić', 'Zagreb', 'HSLS,KNS', 8245),
            ('Zvonimir Gajšak', 'Samobor', 'HDZ', 32729),
            ('Mr Jasna Juračić', 'Samobor', 'SSH', 2011),
            ('Dr Josip Šoić', 'Samobor', 'SKH-SDP', 7076),
        ]},
    ], 'winner': 'Zvonimir Gajšak'},
    45: {'name': 'Zagreb - Susedgrad', 'rounds': [
        {'registered': 80220, 'cast': 67978, 'invalid': 1391, 'candidates': [
            ('Ivan-Zvonimir Čičak', 'Zagreb', 'HSS,KNS', 5086),
            ('Dragutin Lučić', 'Zagreb', 'NK', 1160),
            ('Katarina Maksimović', 'Zagreb', 'NK', 1615),
            ('Bosiljko Mišetić', 'Zagreb', 'HDS,KNS', 7477),
            ('Martin Sagner', 'Zagreb', 'HDZ', 37903),
            ('Stjepan Tomažin', 'Zagreb', 'SKH-SDP', 12927),
        ]},
    ], 'winner': 'Martin Sagner'},
    46: {'name': 'Velika Gorica', 'rounds': [
        {'registered': 44114, 'cast': 37960, 'invalid': 1327, 'candidates': [
            ('Slavko Popijač', 'Velika Gorica', 'SKH-SDP', 8957),
            ('Antun Šagovac', 'Zagreb', 'SDSH,KNS', 7422),
            ('Zvonimir Špišić', 'Velika Gorica', 'HDZ', 20254),
        ]},
    ], 'winner': 'Zvonimir Špišić'},
    48: {'name': 'Sisak II', 'rounds': [
        {'registered': 34297, 'cast': 28227, 'invalid': 915, 'candidates': [
            ('Đuro Brodarac', 'Sisak', 'KNS', 3455),
            ('Petar Olujić', 'Sisak', 'SSH', 2307),
            ('Ivan Radičević', 'Sisak', 'HDZ', 6334),
            ('Milan Stojanović', 'Sisak', 'SKH-SDP', 15216),
        ]},
    ], 'winner': 'Milan Stojanović'},
    49: {'name': 'Glina', 'rounds': [
        {'registered': 40421, 'cast': 35405, 'invalid': 957, 'candidates': [
            ('Stjepan Car', 'Velika Gorica', 'HDZ', 5063),
            ('Aleksa Čučilović', 'Glina', 'SKH-SDP,SSH', 8575),
            ('Matija Herman', 'Glina', 'HDS,KNS', 2524),
            ('Dr Dušan Jović', 'Glina', 'SDS', 6053),
            ('Janko Vasiljević', 'Dvor', 'SKH-SDP,SSH', 10895),
            ('Vukašin Zorić', 'Zagreb', 'JSDS', 1338),
        ]},
        {'registered': 41200, 'cast': 35004, 'invalid': 765, 'candidates': [
            ('Janko Vasiljević', 'Dvor', 'SKH-SDP,SSH', 20850),
            ('Dr Dušan Jović', 'Glina', 'SDS', 6116),
            ('Stjepan Car', 'Velika Gorica', 'HDZ', 7219),
        ]},
    ], 'winner': 'Janko Vasiljević'},
    50: {'name': 'Petrinja', 'rounds': [
        {'registered': 43429, 'cast': 38887, 'invalid': 1515, 'candidates': [
            ('Miko Bokulić', 'Petrinja', 'NK', 1150),
            ('Branko Čačić', 'Petrinja', 'HSLS,KNS', 5335),
            ('Velimir Jakupec', 'Novska', 'SKH-SDP', 7012),
            ('Berislav Ličina', 'Petrinja', 'SSH,SKH-SDP', 13516),
            ('Antun Vidaković', 'Novska', 'HSLS,HDZ', 10236),
        ]},
        {'registered': 44041, 'cast': 35636, 'invalid': 1021, 'candidates': [
            ('Berislav Ličina', 'Petrinja', 'SKH-SDP,SSH', 19833),
            ('Antun Vidaković', 'Novska', 'HDZ,HSLS', 14782),
        ]},
    ], 'winner': 'Berislav Ličina'},
    51: {'name': 'Karlovac', 'rounds': [
        {'registered': 59716, 'cast': 53379, 'invalid': 1069, 'candidates': [
            ('Mato Crkvenac', 'Zagreb', 'SKH-SDP', 22078),
            ('Vladimir Funduk', 'Karlovac', 'SDSHJ', 2549),
            ('Petar Grgec', 'Karlovac', 'SSOH', 1145),
            ('Nada Hartman', 'Karlovac', 'SDSH,KNS', 3605),
            ('Andrija Križanić', 'Karlovac', 'HSS,KNS', 2211),
            ('Mijo Laić', 'Karlovac', 'HDZ', 19768),
            ('Stanislav Rožman', 'Karlovac', 'NK', 954),
        ]},
        {'registered': 59913, 'cast': 48499, 'invalid': 642, 'candidates': [
            ('Mato Crkvenac', 'Zagreb', 'SKH-SDP', 22750),
            ('Mijo Laić', 'Karlovac', 'HDZ', 25107),
        ]},
    ], 'winner': 'Mijo Laić'},
    52: {'name': 'Duga Resa', 'rounds': [
        {'registered': 32334, 'cast': 28112, 'invalid': 1102, 'candidates': [
            ('Antun Bosiljevac', 'Ozalj', 'SKH-SDP', 2608),
            ('Sonja Čavlina', 'Duga Resa', 'SKH-SDP', 2600),
            ('Ivan Presečan', 'Karlovac', 'HDS,KNS', 4010),
            ('Ante-Jozo Ramić', 'Generalski Stol', 'HDZ', 9848),
            ('Nikola Sopčić', 'Ribnik', 'HDZ', 6558),
            ('Juraj Šomen', 'Duga Resa', 'SSH', 1386),
        ]},
        {'registered': 32303, 'cast': 25248, 'invalid': 607, 'candidates': [
            ('Ante-Jozo Ramić', 'Generalski Stol', 'HDZ', 17553),
            ('Ivan Presečan', 'Karlovac', 'HDS', 2957),
            ('Antun Bosiljevac', 'Ozalj', 'SKH-SDP', 4131),
        ]},
    ], 'winner': 'Ante-Jozo Ramić'},
    # Round 1 prints "Cupač", round 2 and the decision "Cupać"; one person.
    53: {'name': 'Slunj', 'rounds': [
        {'registered': 33473, 'cast': 29071, 'invalid': 997, 'candidates': [
            ('Stevan Cupać', 'Topusko', 'SKH-SDP,SSH', 14005),
            ('Ante Ercegović', 'Zagreb', 'SJ', 1355),
            ('Nikola Kobac', 'Topusko', 'JSDS', 4504),
            ('Mile Skukan', 'Slunj', 'HDZ', 8210),
        ]},
        {'registered': 33529, 'cast': 28385, 'invalid': 645, 'candidates': [
            ('Stevan Cupać', 'Topusko', 'SKH-SDP,SSH', 14965),
            ('Mile Skukan', 'Slunj', 'HDZ', 8474),
            ('Nikola Kobac', 'Topusko', 'JSDS', 4301),
        ]},
    ], 'winner': 'Stevan Cupać'},
    54: {'name': 'Ogulin', 'rounds': [
        {'registered': 45025, 'cast': 40392, 'invalid': 1439, 'candidates': [
            ('Željko Mažar', 'Rijeka', 'SSH', 12037),
            ('Biserka Pleše', 'Delnice', 'SKH-SDP', 10556),
            ('Ivanka Polić-Kružić', 'Rijeka', 'HSS,KNS', 3204),
            ('Krunoslav Prebeg', 'Ogulin', 'HDZ', 13008),
        ]},
        {'registered': 44406, 'cast': 39862, 'invalid': 1020, 'candidates': [
            ('Krunoslav Prebeg', 'Ogulin', 'HDZ', 17029),
            ('Željko Mažar', 'Rijeka', 'SSH', 21800),
        ]},
    ], 'winner': 'Željko Mažar'},
    55: {'name': 'Poreč', 'rounds': [
        {'registered': 50812, 'cast': 40940, 'invalid': 4613, 'candidates': [
            ('Ante Ikica', 'Poreč', 'HDS,KNS', 9148),
            ('Veljko Ivančić', 'Umag', 'SSH', 7025),
            ('Dr Branimir Šimunić', 'Umag', 'HDZ', 5456),
            ('Ivan Šorić', 'Rovinj', 'SKH-SDP', 14698),
        ]},
        {'registered': 50862, 'cast': 34408, 'invalid': 3230, 'candidates': [
            ('Ivan Šorić', 'Rovinj', 'SKH-SDP', 16276),
            ('Ante Ikica', 'Poreč', 'HDS', 5572),
            ('Veljko Ivančić', 'Umag', 'SSH', 4795),
            ('Dr Branimir Šimunić', 'Umag', 'HDZ', 4534),
        ]},
    ], 'winner': 'Ivan Šorić'},
    56: {'name': 'Pula', 'rounds': [
        {'registered': 67086, 'cast': 53007, 'invalid': 2474, 'candidates': [
            ('Edi Bastijanić', 'Pula', 'NK', 4528),
            ('Dr Tulio Persi', 'Pula', 'NK', 6068),
            ('Branko Peruško', 'Pula', 'HDZ', 5839),
            ('Boris Rotar', 'Medulin', 'HSS,KNS', 6253),
            ('Igor Štoković', 'Pula', 'SKH-SDP,SSH', 16738),
            ('Lenko Uravić', 'Pula', 'SKH-SDP,SSH', 11107),
        ]},
        {'registered': 67003, 'cast': 43877, 'invalid': 1407, 'candidates': [
            ('Igor Štoković', 'Pula', 'SKH-SDP,SSH', 20794),
            ('Lenko Uravić', 'Pula', 'SKH-SDP,SSH', 6829),
            ('Boris Rotar', 'Medulin', 'HSS,KNS', 5413),
            ('Dr Tulio Persi', 'Pula', 'NK', 5335),
            ('Branko Peruško', 'Pula', 'HDZ', 4099),
        ]},
    ], 'winner': 'Igor Štoković'},
    57: {'name': 'Labin', 'rounds': [
        {'registered': 40315, 'cast': 33918, 'invalid': 2631, 'candidates': [
            ('Delfina Arapović', 'Labin', 'SKH-SDP', 8207),
            ('Nada Bartolić-Matković', 'Pazin', 'HDS,KNS', 10572),
            ('Bruno Hrvatin', 'Labin', 'SSH', 5637),
            ('Mladen Močibob', 'Pazin', 'SKH-SDP', 4934),
            ('Vlado Vlahović', 'Pazin', 'SSH', 1764),
        ]},
        {'registered': 39509, 'cast': 31177, 'invalid': 1576, 'candidates': [
            ('Nada Bartolić-Matković', 'Pazin', 'HDS', 13300),
            ('Delfina Arapović', 'Labin', 'SKH-SDP', 16242),
        ]},
    ], 'winner': 'Delfina Arapović'},
    58: {'name': 'Rijeka I', 'rounds': [
        {'registered': 49877, 'cast': 41404, 'invalid': 1225, 'candidates': [
            ('Leonardo Bressan', 'Rijeka', 'RDS', 3722),
            ('Alceo Frank', 'Rijeka', 'SKH-SDP', 19760),
            ('Mr Miljenko Kurobasa', 'Rijeka', 'HKDS,KNS', 6856),
            ('Oskar Valenčić', 'Klana', 'HDZ', 9841),
        ]},
        {'registered': 49730, 'cast': 35853, 'invalid': 915, 'candidates': [
            ('Alceo Frank', 'Rijeka', 'SKH-SDP', 20891),
            ('Oskar Valenčić', 'Klana', 'HDZ', 13957),
        ]},
    ], 'winner': 'Alceo Frank'},
    59: {'name': 'Rijeka II', 'rounds': [
        {'registered': 50519, 'cast': 41154, 'invalid': 1154, 'candidates': [
            ('Miroslav Akmadža', 'Rijeka', 'HDZ', 9295),
            ('Ognjen Crnković', 'Rijeka', 'HSS,KNS', 2793),
            ('Dr Darko Gašparović', 'Rijeka', 'SDSH,KNS', 5519),
            ('Radovan Perić', 'Rijeka', 'RDS', 2860),
            ('Luciano Sušanj', 'Rijeka', 'SKH-SDP', 19533),
        ]},
        {'registered': 50643, 'cast': 35696, 'invalid': 826, 'candidates': [
            ('Luciano Sušanj', 'Rijeka', 'SKH-SDP', 21408),
            ('Miroslav Akmadža', 'Rijeka', 'HDZ', 13462),
        ]},
    ], 'winner': 'Luciano Sušanj'},
    61: {'name': 'Opatija', 'rounds': [
        {'registered': 33213, 'cast': 26214, 'invalid': 1402, 'candidates': [
            ('Edvard Ercegović', 'Mali Lošinj', 'HDZ', 4512),
            ('Marijan Šimunić', 'Matulji', 'HKDS,KNS', 7919),
            ('Ranko Štefan', 'Lovran', 'SKH-SDP', 9110),
            ('Nivio Toić', 'Cres', 'ODF', 3189),
        ]},
        {'registered': 32927, 'cast': 23995, 'invalid': 1094, 'candidates': [
            ('Ranko Štefan', 'Lovran', 'SKH-SDP', 9811),
            ('Marijan Šimunić', 'Matulji', 'HKDS,KNS', 10402),
            ('Nivio Toić', 'Cres', 'ODF', 2688),
        ]},
    ], 'winner': 'Marijan Šimunić'},
    62: {'name': 'Crikvenica', 'rounds': [
        {'registered': 45799, 'cast': 39067, 'invalid': 2430, 'candidates': [
            ('Blaž Domijan', 'Dramalj', 'SKH-SDP', 6262),
            ('Stipe Lauš', 'Njivice', 'HDZ', 8732),
            ('Čedomir Lončarić', 'Selce', 'SSH', 1971),
            ('Ratko Stipeč', 'Bribir', 'HDZ', 6080),
            ('Nikola Šnjarić', 'Crikvenica', 'HSS,KNS', 6833),
            ('Boris Tepšić', 'Rijeka', 'SKH-SDP', 6759),
        ]},
        {'registered': 46928, 'cast': 35362, 'invalid': 1171, 'candidates': [
            ('Stipe Lauš', 'Njivice', 'HDZ', 14800),
            ('Nikola Šnjarić', 'Crikvenica', 'HSS,KNS', 6570),
            ('Boris Tepšić', 'Rijeka', 'SKH-SDP', 12821),
        ]},
    ], 'winner': 'Stipe Lauš'},
    63: {'name': 'Gospić', 'rounds': [
        {'registered': 21802, 'cast': 19037, 'invalid': 1979, 'candidates': [
            ('Mirko Marković - Mišo', 'Gospić', 'SSH', 2257),
            ('Milan Rukavina-Šain', 'Zagreb', 'SKH-SDP', 7542),
            ('Jure Šonje', 'Zagreb', 'KNS', 7259),
        ]},
        {'registered': 22451, 'cast': 17994, 'invalid': 836, 'candidates': [
            ('Milan Rukavina-Šain', 'Zagreb', 'SKH-SDP', 7575),
            ('Jure Šonje', 'Zagreb', 'KNS', 8552),
            ('Mirko Marković - Mišo', 'Gospić', 'SSH', 1029),
        ]},
    ], 'winner': 'Jure Šonje'},
    64: {'name': 'Otočac', 'rounds': [
        {'registered': 41576, 'cast': 36766, 'invalid': 1019, 'candidates': [
            ('Toma Burić', 'Zagreb', 'HKDS,KNS', 2028),
            ('Simo Rajić', 'Zagreb', 'SKH-SDP', 13892),
            ('Petar Štikovac', 'Lička Kaldrma', 'SDS', 9492),
            ('Ivan Vičić', 'Brinje', 'HDZ', 9272),
            ('Petar Vidaković', 'Samobor', 'NK', 1063),
        ]},
        {'registered': 41784, 'cast': 36239, 'invalid': 675, 'candidates': [
            ('Simo Rajić', 'Zagreb', 'SKH-SDP', 13334),
            ('Petar Štikovac', 'Lička Kaldrma', 'SDS', 11342),
            ('Ivan Vičić', 'Brinje', 'HDZ', 10860),
        ]},
    ], 'winner': 'Simo Rajić'},
    65: {'name': 'Zadar I', 'rounds': [
        {'registered': 56669, 'cast': 42852, 'invalid': 1612, 'candidates': [
            ('Ivan Aralica', 'Zadar', 'NK', 5850),
            ('Mr Marko Marinović', 'Zadar', 'NK', 1278),
            ('Petar Šale', 'Zadar', 'HDZ', 19623),
            ('Mr Ante Vodopija', 'Zadar', 'SKH-SDP', 13978),
            ('Duje Dujam Vukasović', 'Zadar', 'NK', 511),
        ]},
        {'registered': 57687, 'cast': 35397, 'invalid': 591, 'candidates': [
            ('Petar Šale', 'Zadar', 'HDZ', 20479),
            ('Mr Ante Vodopija', 'Zadar', 'SKH-SDP', 14327),
        ]},
    ], 'winner': 'Petar Šale'},
    66: {'name': 'Zadar II', 'rounds': [
        {'registered': 39286, 'cast': 31093, 'invalid': 1233, 'candidates': [
            ('Jakov Bačić', 'Zadar', 'KNS', 2584),
            ('Radmil Božulić', 'Zadar', 'SSH', 3618),
            ('Dr Nikola Jakšić', 'Zadar', 'HDZ', 22366),
            ('Veseljko Kurta', 'Zadar', 'NK', 1292),
        ]},
    ], 'winner': 'Dr Nikola Jakšić'},
    67: {'name': 'Benkovac', 'rounds': [
        {'registered': 41888, 'cast': 36667, 'invalid': 885, 'candidates': [
            ('Borislav Brzić', 'Biograd n/m', 'HDS,KNS', 1709),
            ('Drago Krpina', 'Biograd n/m', 'HDZ', 15642),
            ('Davor Santini', 'Biograd n/m', 'SSH', 963),
            ('Dušan (pok. Nikole) Starević', 'Benkovac', 'SDS', 10184),
            ('Marinko Vranković', 'Obrovac', 'SKH-SDP,SSH', 2978),
            ('Nikola Vukas', 'Benkovac', 'SKH-SDP,SSH', 3807),
        ]},
        {'registered': 42772, 'cast': 36928, 'invalid': 807, 'candidates': [
            ('Drago Krpina', 'Biograd n/m', 'HDZ', 18897),
            ('Dušan (pok. Nikole) Starević', 'Benkovac', 'SDS', 17224),
        ]},
    ], 'winner': 'Drago Krpina'},
    68: {'name': 'Knin', 'rounds': [
        {'registered': 31524, 'cast': 26107, 'invalid': 868, 'candidates': [
            ('Đorđe Bjegović', 'Knin', 'SSH', 2839),
            ('Zvonko Laća', 'Knin', 'SKH-SDP', 4836),
            ('Jovo Opačić', 'Knin', 'SDS', 17563),
        ]},
    ], 'winner': 'Jovo Opačić'},
    69: {'name': 'Šibenik', 'rounds': [
        {'registered': 65623, 'cast': 52114, 'invalid': 1436, 'candidates': [
            ('Ivan Brešan', 'Šibenik', 'SKH-SDP', 14521),
            ('Antun Carić', 'Šibenik', 'HKDS,KNS', 7061),
            ('Božo Erlić', 'Šibenik', 'HDZ', 24904),
            ('Branko Popović', 'Šibenik', 'SDS', 3126),
            ('Ante Žeravica', 'Šibenik', 'USPŠ', 886),
        ]},
        {'registered': 65493, 'cast': 47792, 'invalid': 865, 'candidates': [
            ('Božo Erlić', 'Šibenik', 'HDZ', 26269),
            ('Ivan Brešan', 'Šibenik', 'SKH-SDP', 16358),
            ('Antun Carić', 'Šibenik', 'HKDS,KNS', 4118),
        ]},
    ], 'winner': 'Božo Erlić'},
    70: {'name': 'Drniš', 'rounds': [
        {'registered': 34805, 'cast': 28989, 'invalid': 1463, 'candidates': [
            ('Ajka Hamer-Plećaš', 'Drniš', 'SSH', 7439),
            ('Joso Pavičić', 'Parčića', 'HDZ', 16706),
            ('Niko Tarle', 'Drniš', 'HSLS,KNS', 3258),
        ]},
    ], 'winner': 'Joso Pavičić'},
    71: {'name': 'Kaštela', 'rounds': [
        {'registered': 43967, 'cast': 36250, 'invalid': 1309, 'candidates': [
            ('Šime Đodan', 'Zagreb', 'HDZ', 20700),
            ('Ante Kovač', 'Kaštel Gomilica', 'SKH-SDP', 7409),
            ('Ilija Krišto', 'Kaštel Štafilić', 'HDZ', 3123),
            ('Ivica Škiljo', 'Solin', 'HMP,KNS', 3617),
        ]},
    ], 'winner': 'Šime Đodan'},
    72: {'name': 'Sinj', 'rounds': [
        {'registered': 41155, 'cast': 34856, 'invalid': 903, 'candidates': [
            ('Josip Bradarić', 'Sinj', 'SSH', 5294),
            ('Dr Stipan Janković', 'Split', 'NK', 1235),
            ('Ante Turudić', 'Vrlika', 'HDZ', 17206),
            ('Dr Vladimir Veselica', 'Zagreb', 'KNS', 10027),
        ]},
        {'registered': 37469, 'cast': 30523, 'invalid': 454, 'candidates': [
            ('Ante Turudić', 'Vrlika', 'HDZ', 9969),
            ('Dr Vladimir Veselica', 'Zagreb', 'KNS', 16074),
            ('Josip Bradarić', 'Sinj', 'SSH', 4026),
        ]},
    ], 'winner': 'Dr Vladimir Veselica'},
    73: {'name': 'Split I', 'rounds': [
        {'registered': 47974, 'cast': 40623, 'invalid': 695, 'candidates': [
            ('Dr Zvonimir Marković', 'Split', 'HDZ', 22943),
            ('Dr Jakov-Jakša Miličić', 'Split', 'SKH-SDP,SSH', 9512),
            ('Joško Niskota', 'Split', 'ZAS', 1139),
            ('Luka Podrug', 'Split', 'HDS,KNS', 5993),
        ]},
    ], 'winner': 'Dr Zvonimir Marković'},
    75: {'name': 'Split III', 'rounds': [
        {'registered': 56013, 'cast': 43648, 'invalid': 644, 'candidates': [
            ('Mate Bosnić', 'Split', 'HDZ', 13937),
            ('Boris Kuljiš', 'Split', 'NK', 442),
            ('Mr Šime Pilić', 'Split', 'SSH', 1213),
            ('Dr Juraj Romac', 'Split', 'SDSH,KNS', 9882),
            ('Dr Nikola Visković', 'Split', 'ZAS,SKH-SDP', 17527),
        ]},
        {'registered': 55990, 'cast': 37719, 'invalid': 433, 'candidates': [
            ('Dr Nikola Visković', 'Split', 'ZAS,SKH-SDP', 17938),
            ('Mate Bosnić', 'Split', 'HDZ', 12543),
            ('Dr Juraj Romac', 'Split', 'SDSH,KNS', 6750),
        ]},
    ], 'winner': 'Dr Nikola Visković'},
    76: {'name': 'Imotski', 'rounds': [
        {'registered': 31493, 'cast': 27832, 'invalid': 520, 'candidates': [
            ('Branimir Buljan', 'Imotski', 'SSH', 4116),
            ('Ivan Gabelica', 'Zagreb', 'HDS,KNS', 6386),
            ('Viktor Grabovac', 'Proložac Donji', 'HDZ', 16146),
            ('Dinko Zdilar', 'Glavina Donja', 'NK', 664),
        ]},
    ], 'winner': 'Viktor Grabovac'},
    77: {'name': 'Omiš', 'rounds': [
        {'registered': 33597, 'cast': 28621, 'invalid': 881, 'candidates': [
            ('Dr Žarko Domljan', 'Zagreb', 'HDZ', 14431),
            ('Zvonimir Hrabar', 'Zagreb', 'SKH-SDP', 9563),
            ('Dr Božidar Šošić', 'Brela', 'HDS,KNS', 3746),
        ]},
    ], 'winner': 'Dr Žarko Domljan'},
    78: {'name': 'Metković', 'rounds': [
        {'registered': 24095, 'cast': 21360, 'invalid': 1179, 'candidates': [
            ('Dr Đuro Njavro', 'Zagreb', 'HDS,KNS', 1925),
            ('Stipe Parun', 'Metković', 'SKH-SDP', 5528),
            ('Boško Šiljeg', 'Kardeljevo', 'HDZ', 11416),
            ('Nikola Vučković', 'Metković', 'HKDS,KNS', 1312),
        ]},
    ], 'winner': 'Boško Šiljeg'},
    79: {'name': 'Dubrovnik', 'rounds': [
        {'registered': 54144, 'cast': 44892, 'invalid': 1687, 'candidates': [
            ('Adam Benović', 'Dubrovnik', 'SSH', 2762),
            ('Hrvoje Kačić', 'Dubrovnik', 'NK', 25690),
            ('Dragan Parežanin', 'Dubrovnik', 'JSDS', 3535),
            ('Pero Vičan', 'Dubrovnik', 'SKH-SDP', 11218),
        ]},
    ], 'winner': 'Hrvoje Kačić'},
    # 47, 60, 74 and 80 are missing from the main report; they are printed in the
    # supplement (`…_dopunski_izvjestaj.pdf`, pages 2-5).
    47: {'name': 'Sisak I', 'rounds': [
        {'registered': 31137, 'cast': 25556, 'invalid': 700, 'candidates': [
            ('Ivan Bobetko', 'Zagreb', 'HDZ', 10964),
            ('Slavko Kireta', 'Sisak', 'SSH', 1969),
            ('Stjepan Marić', 'Sisak', 'HSS,KNS', 3358),
            ('Nikola Tadić', 'Sisak', 'SKH-SDP', 8565),
        ]},
        {'registered': 31879, 'cast': 22243, 'invalid': 372, 'candidates': [
            ('Ivan Bobetko', 'Zagreb', 'HDZ,HSS', 13022),
            ('Nikola Tadić', 'Sisak', 'SKH-SDP', 8849),
        ]},
    ], 'winner': 'Ivan Bobetko'},
    60: {'name': 'Rijeka III', 'rounds': [
        {'registered': 53102, 'cast': 45567, 'invalid': 1208, 'candidates': [
            ('Darko Čargonja', 'Rijeka', 'SKH-SDP', 17853),
            ('Darko First', 'Rijeka', 'RDS', 1506),
            ('Dr Vinko Hlača', 'Rijeka', 'HDS,KNS', 9805),
            ('Dr Kazimir Kauzlarić', 'Rijeka', 'ZSR', 2742),
            ('Josip Pahljina', 'Rijeka', 'SSH', 1478),
            ('Ervin Radetić', 'Rijeka', 'HDZ', 9811),
            ('Mr Tomislav Sabljar', 'Rijeka', 'NK', 1163),
        ]},
        {'registered': 51361, 'cast': 40520, 'invalid': 1356, 'candidates': [
            ('Darko Čargonja', 'Rijeka', 'SKH-SDP', 20816),
            ('Dr Vinko Hlača', 'Rijeka', 'HDS', 18348),
        ]},
    ], 'winner': 'Darko Čargonja'},
    74: {'name': 'Split II', 'rounds': [
        {'registered': 49711, 'cast': 41456, 'invalid': 686, 'candidates': [
            ('Dr Ante Jelavić', 'Split', 'ZAS', 2034),
            ('Goran Pavlov', 'Split', 'HDZ', 13640),
            ('Dr Dubravka Regner', 'Split', 'SSH', 938),
            ('Ante Roje', 'Split', 'SKH-SDP', 17505),
            ('Velimir Terzić', 'Split', 'HSLS,KNS', 5684),
            ('Dr Blažo Zlopaša', 'Cavtat', 'SJ', 766),
        ]},
        {'registered': 51345, 'cast': 36290, 'invalid': 400, 'candidates': [
            ('Ante Roje', 'Split', 'SKH-SDP', 18512),
            ('Goran Pavlov', 'Split', 'HDZ', 12990),
            ('Velimir Terzić', 'Split', 'HSLS,KNS', 4337),
        ]},
    ], 'winner': 'Ante Roje'},
    # Round 1 prints "Kalođera", round 2 "Kalogjera"; the same person.
    80: {'name': 'Korčula', 'rounds': [
        {'registered': 37471, 'cast': 30882, 'invalid': 1108, 'candidates': [
            ('Vicko Dabelić', 'Orebić', 'NK', 1794),
            ('Dušan Kalogjera', 'Korčula', 'SKH-SDP,SSH', 11758),
            ('Vicko Krajančić', 'Čara', 'HDZ', 9332),
            ('Ante Vukasović', 'Zagreb', 'HDS,KNS', 5644),
        ]},
        {'registered': 37183, 'cast': 29093, 'invalid': 1803, 'candidates': [
            ('Dušan Kalogjera', 'Korčula', 'SKH-SDP,SSH', 13308),
            ('Vicko Krajančić', 'Čara', 'HDZ', 13982),
        ]},
    ], 'winner': 'Vicko Krajančić'},
}


# ---- shared with app.py, which cannot import the Django-bound importer ----

import re  # noqa: E402

from .sabor_1992_data import person_name as _person_name_1992  # noqa: E402

ELECTION_TYPE_SLUG = 'sabor_dpv'
ELECTION_TYPE_NAME = 'Društveno-političko vijeće Sabora'

# 1990 writes titles without the dot ("Dr Franjo Tuđman", "Mr Mato Arlović"),
# which `clean_candidate_name` does not recognise as a title.
_UNDOTTED_TITLE = re.compile(r'^(dr|mr)\s+', re.I)


def person_name(raw):
    return _person_name_1992(_UNDOTTED_TITLE.sub('', raw))


def party_label(abbrs):
    """'HKDS,HDS,SDSH,KNS' -> 'HKDS, HDS, SDSH - KNS', the report's own reading:
    nominating parties, then the coalition they ran under."""
    parts = abbrs.split(',')
    if len(parts) > 1 and parts[-1] == 'KNS':
        return f"{', '.join(parts[:-1])} - KNS"
    return ', '.join(parts)
