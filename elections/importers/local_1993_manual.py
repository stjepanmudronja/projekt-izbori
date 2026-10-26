"""Readings of the 1993 report made by eye, from rendered crops of the scan,
where OCR could not settle a block (`local_1993_parse.py` applies them).

Keys: (county code, unit) — the unit as `_classify` names it, or the slug
for a county assembly — plus the ward's printed number for ward entries.

- MANUAL_WARDS: a ward's candidates as printed, [(name, party, votes)];
  votes None where the report prints no count; [] for a ward the report
  marks not held.
- MANUAL_WARD_FIGURES: a ward's (registered, cast, invalid).
- MANUAL_LISTS: a body's lists as printed, [(name, votes)], a coalition's
  printed lines joined by " / ".
- MANUAL_LIST_VOTES: a body's list counts in printed order, where the names
  parsed and only counts were missed.
- MANUAL_FIGURES: a body's (registered, cast, invalid); None where blank.
- CONFIRMED_LISTS / CONFIRMED_WARDS: read off the scan and right as parsed;
  the gap to cast − invalid is the report's own.
"""

MANUAL_WARDS = {
    ('01', 'SAMOBORA', 4): [('Marijan Bašić', 'HSLS, HNS, HKDS', 799), ('Franjo Kotarski', 'HDZ', 755)],
    ('01', 'SAMOBORA', 5): [('Franjo Horvat', 'HSLS, HNS, HKDS', 899), ('Josip Majcen', 'HDZ', 876)],
    # 993 + 466 against 1.350 - 51 = 1.299 valid: printed so (833 would fit).
    ('01', 'SAMOBORA', 13): [('Branko Adamek', 'HSLS, HNS, HKDS', 993), ('Blaženka Horvat', 'HDZ', 466)],
    # 432 + 103 = 535 against 562 - 36 = 526: printed so.
    ('03', 'NOVSKA', 4): [('Ivica Kozić', 'HDZ', 432), ('Krešimir Stublija', '', 103)],
    ('03', 'PETRINJA', 13): [('Ivan Roksa', 'HDZ', 193), ('Josip Vuić', 'HSS', 496)],
    ('04', 'local_county_assembly', 6): [('Zdenko Cindrić', 'HSP', 19), ('Ivan Mateša', 'HDZ', 97)],
    ('04', 'local_county_assembly', 12): [('Josip Goršćak', 'HSS', 1186), ('Miroslav Migalić', 'HDZ', 2408),
                                          ('Neven Tukac', 'HSP', 486)],
    ('04', 'local_county_assembly', 13): [('Mirko Butković, prof. dr.', 'HSLS', 1777),
                                          ('Stanko Ćosić, dipl.ing.', 'HSP', 246),
                                          ('Dubravko Heinrich', 'Nezavisni kandidat', 629),
                                          ('Ivan Navialić', 'HDZ', 766)],
    ('04', 'local_county_assembly', 17): [('Dragutin Belavić', 'HSLS', 1367), ('Josip Kučmanić', 'HSS', 417),
                                          ('Goran Latković', 'HSP', 253), ('Josip Latković', 'HDZ', 1122)],
    ('04', 'KARLOVCA', 4): [('Anto Kristić', 'HSS', 562), ('Josip Mušić', 'HDZ', 695),
                            ('Ladislav Silvaši', 'SDH, SDP, SSH', 707)],
    ('04', 'OGULINA', 1): [('Darko Magdić', 'HDZ', 372), ('Anton Stipetić', 'HSLS', 354),
                           ('Damir Štimac', 'Nezavisni kandidat', 106)],
    # "Lista za Varaždinsku županiju (HSLS,HNS,HKDU,SDP)", stored as its parties.
    ('05', 'local_county_assembly', 1): [('Franjo Bračko', 'HSLS, HNS, HKDU, SDP', 2761),
                                         ('Zvonimir Rihtarić', 'HSS', 1631),
                                         ('Jadranka Tomašić, ing.', 'HDZ', 1127)],
    ('05', 'local_county_assembly', 4): [('Ivan Hiti, prof.', 'Nezavisni kandidat', 213),
                                         ('Josip Jagić, dipl.oecc.', 'HDZ', 797),
                                         ('Branko Kostanjevec', 'Nezavisni kandidat', 121),
                                         ('Milivoj Ladić', 'HSLS, HNS, HKDU, SDP', 1397),
                                         ('Marijan Rauš', 'Nezavisni kandidat', 126),
                                         ('Stanko Stolnik', 'HSP', 276), ('Zvonko Šanjek', 'HSS', 885)],
    ('05', 'local_county_assembly', 10): [('Stjepan Galeković', 'HSS', 2157), ('Mijo Kokot', 'HDZ', 1388),
                                          ('Dražen Zebec', 'HSLS, HNS, HKDU, SDP', 1089)],
    ('05', 'VARAŽDINA', 1): [('Čiril Čoh', 'HKDU, HSLS, HNS, SDP', 728), ('Milan Leljak', 'HSS', 326),
                             ('Darko Pascuttini', 'HDZ', 457)],
    ('06', 'local_county_assembly', 1): [('Ivan Čurić, dipl.ing.', 'HDZ', 1687), ('Vlado Halusek', 'HSLS', 481),
                                         ('Vlado Rep', 'HNS, HKDS, HSS, SDP', 904)],
    # 3.136 against 3.286 - 119 = 3.167: printed so.
    ('06', 'local_county_assembly', 2): [('Vinko Antolaš, prof.', 'HDZ', 1270),
                                         ('Vladimir Kovačić', 'HNS, HKDS, HSS, SDP', 1474),
                                         ('Ivan Matkov', 'HSLS', 392)],
    ('06', 'local_county_assembly', 5): [('Vlado Gregurić', 'HSS, HKDS, HNS, SDP', 1407),
                                         ('Marijan Ivančan', 'HKDS', 319), ('Franjo Pobi', 'HDZ', 809)],
    ('06', 'local_county_assembly', 9): [('Stanko Laska', 'HKDS', 194), ('mr. Marko Mioč', 'HDZ', 737),
                                         ('dr. Dražen Sačer', 'HSLS, SDP, HNS', 2099)],
    # 3.280 against 3.437 - 170 = 3.267: printed so.
    ('06', 'local_county_assembly', 12): [('Mladen Kolarek', 'HSS', 1223), ('Ivan Picer', 'HDZ', 1202),
                                          ('Slavko Podolski', 'HSLS, SDP, HNS', 686), ('Blaženka Sataić', 'HKDS', 169)],
    ('06', 'local_county_assembly', 16): [('Franjo Kemenović', 'HSS', 1882), ('Nikola Novosel', 'SDP', 816),
                                          ('Franjo Sokač', 'HDZ', 922)],
    ('06', 'local_county_assembly', 17): [('Zvonko Beljo', 'HDZ', 1522), ('Stojan Miščević', 'HSLS', 386),
                                          ('Marijan Vuković, dipl.ing.', 'HSS', 1956)],
    ('07', 'local_county_assembly', 3): [('Stipan Cikoja', 'HDZ', 1512),
                                         ('Miroslav Dergez', 'HSLS, HNS, SDP, HKDU i Stranka Roma Hrvatske', 1446),
                                         ('Milan Devčić', 'HSS', 1009)],
    # 2.926 against 3.058 - 123 = 2.935: printed so.
    ('07', 'local_county_assembly', 6): [('Dragutin Edjut', 'HNS, HSLS, HKDU, SDP i Stranka Roma Hrvatske', 1745),
                                         ('Zdravko Ivković', 'HDZ', 1181)],
    ('07', 'local_county_assembly', 7): [('Mladen Kaminski', 'HNS, HSLS, SDP, HKDS i Stranka Roma Hrvatske', 1036),
                                         ('Josip Kiš', 'HSS', 2476), ('Josip Tolnaj', 'HDZ', 1609)],
    ('07', 'local_county_assembly', 9): [('Ivica Mlinar', 'HSS', 1369), ('Antun Perčulija', 'HDZ', 1301),
                                         ('Mira Splivalo', 'HNS, HSLS, SDP, HKDS i Stranka Roma Hrvatske', 464)],
    ('07', 'local_county_assembly', 10): [('Milan Bačani', 'SDP, HSLS, HNS, HKDS i Stranka Roma Hrvatske', 1615),
                                          ('Ivan Grabić', 'HSS', 1336), ('Zvonimir Maričić', 'HDZ', 1317)],
    ('07', 'local_county_assembly', 14): [('Zdravko Bašljan', 'HDS, HKDU, HSS, HSP', 1537),
                                          ('Vinko Gašpar', 'HDZ', 679)],
    # The report prints "Zdaravko Lojkić".
    ('07', 'local_county_assembly', 17): [('Mara Čaušić', 'HSLS, HNS, HDS, SDP', 2125),
                                          ('Zdravko Lojkić', 'HDZ', 1208)],
    # 3.106 against 3.369 - 252 = 3.117: printed so.
    ('07', 'local_county_assembly', 18): [('Zdenka Čunhil', 'HSLS, HNS, HDS, SDP', 1342),
                                          ('Mirko Horak', 'Nezavisni kandidat', 801), ('Krešimir Petrinić', 'HDZ', 963)],
    ('07', 'BJELOVARA', 10): [('Dr. Ljiljana Pleskalt', 'HNS, HSLS, SDP, HKDS i Stranka Roma Hrvatske', 862),
                              ('Ivo Pranjić', 'HSP', 240), ('Ivan Ravenšćak', 'HDZ', 772)],
    ('08', 'local_county_assembly', 15): [('Marina Dvorničić', 'RiDS', 1858), ('Ivan Karlović', 'HDZ', 2164),
                                          ('Radivoj Radivoj', 'SND', 197), ('Matko Županić', 'HSLS, SDP, HNS', 3088)],
    # 554 against 642 - 72 = 570: printed so.
    ('08', 'CRIKVENICE', 11): [('Milorad Blažić', 'SDP, HSLS, HNS', 211), ('Nenad Perhat', 'HDZ', 343)],
    # 137 against 146 - 0: printed so.
    ('08', 'ČABRA', 12): [('Zdravko Kvaternik', 'HDZ', 52), ('Ivan Turk', 'SDP, HNS, HSLS', 85)],
    # No party printed for the first two.
    ('08', 'NOVI VINODOLSKI', 2): [('Milan Butković', '', 104), ('Petar Frković', '', 59),
                                   ('Ivica Jurčić', 'Nezavisni kandidat', 124)],
    ('08', 'OPATIJE', 2): [('Daroslav Ćiković, dipl.pravnik', 'HKDS, HDS, HDZ, HNS, HSLS', 326),
                           ('Sergije Rubeša-Dedo', '', 293)],
    ('08', 'RABA', 8): [('Željko Ribarić', 'HDZ', 188), ('Žarko Španjol', 'HSLS, HNS, SDP', 214)],
    ('08', 'RABA', 9): [('Ivan Debelić, dipl.pravnik', 'HDZ', 208), ('Slavko Pahljina', 'SDP, HSLS, HNS', 277)],
    # Rijeka prints a party only for the HSLS-SDP-HNS candidates.
    ('08', 'RIJEKE', 4): [('Vlado Črnac', '', 1671), ('Nike Gogala', '', 103),
                          ('Dr. Marko Ivanović', 'HSLS, SDP, HNS', 1961), ('Ivan Krivičić', '', 1171),
                          ('Drago Kršul', '', 93), ('Daila Mastrogiovanni', '', 283), ('Ing. Ante Prpić', '', 205)],
    ('08', 'RIJEKE', 6): [('Sonja Bonifačić', '', 1802), ('Ermina Brdar', '', 554), ('Zrinko Jurišić', '', 1933),
                          ('Dinko Lupi', 'HSLS, SDP, HNS', 2019), ('Darko Peričić', '', 247)],
    ('08', 'RIJEKE', 11): [('Arsen Cimaš', '', 344), ('Zvonimir Gržeta', '', 952), ('Aleksije Pavletić', '', 1676),
                           ('Branka Renko-Silov', 'HSLS, SDP, HNS', 2451), ('Zvonimir Sablić', '', 559),
                           ('Ivanka Starčević', '', 484)],
    ('09', 'local_county_assembly', 5): [('Milan Babić', 'HNS-HKDU-SDP', 426), ('Dr. Juraj Medved', 'HDZ', 1101)],
    ('09', 'OTOČAC', 10): [('Ivan Bakarić', 'HDZ', 356), ('Marijan Kostelac - Dane', 'HSLS', 151)],
    # 2.698 against 2.877 - 129 = 2.748: printed so.
    ('10', 'local_county_assembly', 13): [('Franjo Đunđek', 'HSS', 1533), ('Ivan Nemet', 'HDZ', 1165)],
    ('10', 'PODRAVSKA SLATINA', 8): [('Željko Filković', 'HDZ', 539), ('Željko Mataija', 'HSS i SDH', 313)],
    # 3.647 against 3.764 - 177 = 3.587: printed so.
    ('11', 'local_county_assembly', 5): [('Božo Budimir', 'HSS', 2188), ('Hrvoje Sontaki', 'HDZ', 1459)],
    ('11', 'NAŠICE', 1): [('Ivan Funjak', 'HSLS', 575), ('Ivan Komak', 'HDZ', 245)],
    ('11', 'NAŠICE', 10): [('Davorin Dvoržak', 'HSLS', 343), ('Đuro Kadić', 'SDP', 90), ('Božo Papac', 'HDZ', 227)],
    # 743 against 718 - 5 = 713: printed so.
    ('11', 'NAŠICE', 12): [('Josip Matek', 'HDZ', 266), ('Branko Škoro', 'HSLS', 477)],
    ('12', 'local_county_assembly', 13): [('Petar Antunović', 'HDZ', 2030), ('Antun Radman', 'HSLS', 566),
                                          ('Drago Žambok', 'HSS', 1760)],
    # Nova Gradiška prints only each ward's winner, under its turnout.
    ('12', 'NOVA GRADIŠKA', 6): [('dipl.ing. Željko Blazina', 'HNS', None)],
    ('12', 'NOVA GRADIŠKA', 9): [('Ivo Petranović', 'HDZ', None)],
    ('12', 'NOVA GRADIŠKA', 10): [('dr. Stjepan Kovačević', 'HKDU', None)],
    ('13', 'local_county_assembly', 4): [('Željko Lukić', 'HSLS i HNS', 4), ('Frano Tamburović', 'HDZ', 9)],
    # Printed "Prof. dr. sci Josip Labar".
    ('13', 'local_county_assembly', 10): [('Josip Labar', 'HSLS, SDP i HNS', 1696), ('Ante Vulin', 'HDZ', 1494)],
    # 4.498 against 4.674 - 149 = 4.525: printed so.
    ('13', 'local_county_assembly', 11): [('Mile Ivković', 'HDZ', 3198), ('Petar Perić', 'Nezavisni kandidat', 310),
                                          ('Frane Rogoznica', 'HSLS i HNS', 990)],
    ('13', 'local_county_assembly', 12): [('Jakov Bakić', 'HDZ', 2042),
                                          ('Željko Predovan, dipl. ing.', 'HSLS i HNS', 1224)],
    ('13', 'local_county_assembly', 15): [('Ivan Bucić', 'HDZ', 1479), ('Dr. Ante Župan', 'HSLS i HNS', 601)],
    ('13', 'BIOGRADA NA MORU', 6): [('Ljubomir Brčić', 'HNS', 77), ('Tomislav Eškinja', 'HDS', 31),
                                    ('Ive Stopfer', 'HDZ', 55)],
    ('13', 'ZADRA', 1): [('Miljenko Kulišić, dipl. ing.', 'HSLS i HNS', 395),
                         ('Marij Matulina, dipl. oecc.', 'HDZ', 526), ('Tito Smirčić', 'DA', 115)],
    ('13', 'ZADRA', 9): [('prof. Dragomir Mišljenac', 'HSLS i HNS', 1110), ('Mladen Motušić', 'DA', 527),
                         ('Edvin Šimunov, dipl. iur.', 'HDZ', 666)],
    ('13', 'ZADRA', 10): [('dr. Ivo Basioli', 'HSLS i HNS', 1088), ('Marinko Burčul', 'SDP i SSH', 281),
                          ('Hrvoje Čotić', 'HDZ', 508)],
    ('13', 'ZADRA', 13): [('dr. Vinko Stipić', 'HDZ', 340), ('Josip Vlahović, dipl. ing', 'HSLS i HNS', 348)],
    # The report leaves candidates 2 and 3 unnamed; the winner line names
    # Slavko Sršić, the top (HDZ) count. The HSP candidate's 592 votes have
    # no name to hang on and are not stored.
    ('14', 'local_county_assembly', 4): [('Ivan Jugović', 'HSLS i HNS', 3401), ('Slavko Sršić', 'HDZ', 4441)],
    # 8.445 against 8.700 - 225 = 8.475: printed so.
    ('14', 'local_county_assembly', 8): [('Katarina Gantar', 'HDZ', 3221), ('Ivan Ivanišević', 'HNS', 374),
                                         ('Zvonimir Pavelić', 'HSLS', 3601), ('Branka Zamečnik', 'HSP', 565),
                                         ('Josip Žužić', 'HSS', 684)],
    ('14', 'local_county_assembly', 18): [('Zdravko Bosančić', 'SDP', 742), ('Josip Đelagić', 'HSS', 2828),
                                          ('Marijan Mikić', 'HSLS', 1224), ('Viktor Pranjković', 'HNS', 203),
                                          ('Jozo Rajić', 'HDZ', 3649)],
    # Matijaković's 606 repeats the ward's voters (606, 24 invalid): printed so.
    ('14', 'DAKOVA', 1): [('Tomica Matijaković', 'HSS, HNS, SDP, HSLS, HKDU', 606), ('Miroslav Tarnaj', 'HDZ', 421)],
    ('09', 'NOVALJA', 4): [('dipl.ing. Nenad Peranić', 'HSS, HSLS', None)],
    ('16', 'ŽUPANJA', 6): [('Petar Barišić', 'HSLS', 241), ('Vlado Matanović', 'HDZ', 130),
                           ('Ivan Živković', 'HSS', 102)],
    # Printed "nevažećih listića: 113 ili 3%": 3 % of 407 is 13, and the
    # candidates sum to 407 - 13 (figures below).
    ('16', 'ŽUPANJA', 9): [('Ivan Balentović', 'HSS', 84), ('Branislav Klaić', 'HDZ', 189), ('Ivan Tomić', 'HSLS', 121)],
    ('16', 'ŽUPANJA', 12): [('Đuro Dugalić', 'HSS', 99), ('Jakob Kopić', 'HDZ', 236), ('Stjepan Živković', 'HSLS', 124)],
    ('16', 'TORDINCI', 3): [],
    # 324 against 400 - 31 = 369: printed so.
    ('17', 'IMOTSKOG', 1): [('Ivan Bilopavlović', 'HSP', 56), ('Vjekoslav Bušić', 'HDZ', 268)],
    ('17', 'IMOTSKOG', 3): [('Ivan Medvidović "Kićo"', 'HDZ', 202), ('Vitomir Rebić', 'HSP', 131)],
    ('17', 'MAKARSKE', 3): [('Ivan Babić', 'HSLS i HNS', 78), ('prof. Zlatko Gareljić', 'SDP', 211),
                            ('Ivo Puharić', 'HDZ', 142)],
    ('17', 'MAKARSKE', 5): [('Tonči Bušelić', 'DA', 65), ('Miroslav Jurčević', 'SDP', 263),
                            ('oecc. Ivo Srzić', 'HSLS i HNS', 90), ('dipl.ing. Ljubomir Urlić', 'HDZ', 207)],
    ('17', 'MAKARSKE', 11): [('dipl.ing. Tonči Čobrnić', 'HNS i HSLS', 82), ('Tonči Čović', 'HDZ', 99),
                             ('Stipe Grubišić', 'SDP', 107)],
    ('17', 'MAKARSKE', 13): [('dipl.oecc. Ante Čović', 'HSLS i HNS', 99), ('Ivo Ševelj', 'HDZ', 87)],
    ('17', 'OMIŠA', 6): [],          # "Bez predloženih kandidata"
    ('17', 'OMIŠA', 8): [('Luka Barić', 'HDZ', 333), ('Marin Bulić', 'HSLS', 145)],
    ('17', 'OMIŠA', 9): [('Ante Ćoso', 'HSLS', 336), ('Ruzarijo-Rozarijo Huljev', 'HKDU', 138),
                         ('dipl.ing. Roko Mandić', 'HSS', 99), ('Ivan Pajdek', 'HNS', 97),
                         ('Marko Srdanović', 'HDZ', 213)],
    ('17', 'SINJA', 10): [('Drago Poljak', 'HKDU', 96), ('Dražan Šimić', 'HNS', 106), ('Dušan Šimić', 'SDP', 93),
                          ('Mate Šimić', 'HDZ', 337)],
    ('17', 'SOLINA', 1): [('Ranko Crmarić', 'HNS i HSLS', 234), ('Ivan Pletikosić', 'HDZ', 147),
                          ('Jure Žegarac', 'SDP i SSH', 49)],
    ('17', 'SOLINA', 4): [('Ante Milišić', 'HDZ', 357), ('Drago Milišić', 'SSH i SDP', 137),
                          ('Miro Mužić', 'HNS i HSLS', 210)],
    ('17', 'SOLINA', 9): [('Ivo Duvnjak', 'HNS i HSLS', 151), ('Zdravko Latinčić', 'HDZ', 212),
                          ('Duško Meštrović', 'SDP i SSH', 187)],
    ('17', 'SPLITA', 5): [('ing. Jakov Kovač', 'HDZ', 2966), ('Ante Perišić', 'SDP, SSH i SDU', 1151),
                          ('Gvido Piasevoli', 'HKDU, HRZ i KNS', 467), ('Srećko Rafanelli', 'DA', 1319),
                          ('Jasna Vulić', 'HSLS, HNS i HSS', 2809)],
    ('17', 'TROGIRA', 2): [('Ivo Slade', 'HSLS', 256), ('Vesna Strize', 'HDZ', 158), ('Ivo Vuletić', 'HSP', 41)],
    ('17', 'VISA', 8): [('Pero Bralić', 'SDP', 8), ('Ana Linčir', 'HDZ', 45), ('Joško Tomić', 'SDH', 32)],
    ('18', 'local_county_assembly', 8): [('Franco Bonassin', 'IDS', 4158), ('Anton Užila', 'HDZ', 932)],
    ('18', 'local_county_assembly', 12): [('Silvan Juran', 'IDS', 6135), ('Nelo Škabić', 'HDZ', 795)],
    ('18', 'BUJA', 3): [('Mauro Antonini', 'IDS', 131), ('Valter Bassanese', 'SDP, SSH, SDH', 43),
                        ('Josip Đurčević', 'HDZ', 51)],
    ('18', 'BUJA', 8): [('Marčelo Altin', 'SDP, SSH, SDH', 55), ('Nino Činić', 'IDS', 222),
                        ('Marčelo Perčić', 'HDZ', 23)],
    ('18', 'BUJA', 10): [('Elvino Jurjević', 'IDS', 140), ('Valter Marušić', 'SDP, SSH, SDH', 26),
                         ('Blaž Vidović', 'HDZ', 11)],
    # The report prints "Arnalodo Radin".
    ('18', 'BUJA', 12): [('Fermino Civitan', 'IDS', 112), ('Arnaldo Radin', 'SDP, SSH, SDH', 38),
                         ('Nada Vidović', 'HDZ', 10)],
    ('18', 'PAZINA', 6): [('Zdenko Paulišić', 'HDZ', 49), ('Elvis Vižentin', 'IDS', 116)],
    ('18', 'POREČA', 2): [('Azeglio Picco', 'IDS', 451), ('Stanislav Poropat', 'SDP, SSH i SDH', 67),
                          ('Lino Užila', 'HDZ', 95)],
    ('18', 'PULE', 7): [('dipl.ing Livio Bolković', 'SDP, SSH i SDH', 437), ('Miriana Ferjančić', 'IDS', 1632),
                        ('Jozo Hrstić', 'HDZ', 374)],
    ('18', 'PULE', 9): [('Zlatko Buršić', 'IDS', 1744), ('Dr. Jure Jerinić', 'HDZ', 517)],
    ('18', 'PULE', 10): [('Ljubomir Cerovac', 'Istarska pučka stranka i KNS', 194), ('Boris Kliba', 'HDZ', 421),
                         ('Aldo Skira', 'IDS', 1821)],
    ('18', 'PULE', 12): [('Mirko Milovan', 'IDS', 2264), ('Romano Štifanić', 'HDZ', 620)],
    ('18', 'ROVINJA', 2): [('Silvio Brunelli', 'IDS', 347), ('Borivoj Čukac', 'HDZ', 77),
                           ('Ivan Filipić', 'Istarska pučka stranka, Istarska nezavisna stranka, KNS, HKDS i HSP', 58)],
    ('19', 'local_county_assembly', 2): [('Tonći Padovan', 'HDZ', 2268), ('Žarko Pecotić', 'HSLS', 989)],
    ('19', 'local_county_assembly', 7): [('dipl.oecc. Nikola Brečić-Mršan', 'HKDS', 2016),
                                         ('Stjepan Kljusurić', 'HDZ', 1250)],
    ('19', 'local_county_assembly', 14): [('Božo Burić', 'Nezavisni kandidat', 903), ('Mato Kulaš', 'HSS', 459),
                                          ('Željko Kulišić', 'HDZ', 1128),
                                          ('Igor Žuvela', 'SDP, HKDS, HNS, HSLS', 1302)],
    ('19', 'local_county_assembly', 17): [('Boris Filičić', 'HDZ', 1391), ('Nina Hladilo', 'HKDU, HKDS, HDS', 631),
                                          ('prof. Igor Legaz', 'Dalmatinska akcija', 610),
                                          ('Damir Stahor', 'Nezavisni kandidat', 472)],
    # 319 against 359 - 20 = 339: printed so.
    ('19', 'KORČULE', 3): [('Marko Farac', 'HDZ', 114), ('Marko Skokandić Maki', 'HNS', 205)],
    ('19', 'METKOVIĆ', 1): [('Ante Brečić - Feđa, prof.', 'HKDS', 222), ('Ivica Gabrić', 'HDZ', 318),
                            ('Božidar Lovrić', 'HSLS', 96)],
    ('19', 'METKOVIĆ', 4): [('Mario Gabrić, dipl.ing.el.', 'HKDS', 128), ('Izvor Matičević', 'HDZ', 72),
                            ('Željko Mordžin', 'HSLS', 132)],
    ('20', 'local_county_assembly', 10): [('Zdravko Golubić', 'HSLS, SDP, HNS, SDH', 1380), ('Vinko Horvat', 'HKDU', 464),
                                          ('Stanislav Trstenjak', 'HDZ', 1346)],
    ('20', 'local_county_assembly', 18): [('Nikola Breznik', 'HSS', 550), ('Stjepan Cirković', 'KNS', 215),
                                          ('Ivan Fučko', 'HKDU', 326), ('Ivan Jurinec', 'HDZ', 459),
                                          ('Vladimir Vurušić', 'HSLS, SDP, HNS, SDH', 1392)],
    ('20', 'ČAKOVCA', 7): [('Mladen Babić', 'HSLS, SDP, HNS, SDH', 875), ('Vladimir Novaković', 'HKDU', 108),
                           ('Marijan Pintarić, dipl.oecc.', 'HDZ', 354), ('Marijan Šarić', 'HSS', 187),
                           ('Stjepan Varga', 'KNS', 74)],
    ('20', 'ČAKOVCA', 13): [('Franjo Kolar', 'HDZ', 373), ('Franjo Lehkec', 'HSS', 284),
                            ('Darinka Tompoš', 'HSLS, SDP, HNS, SDH', 715), ('Antun Varga', 'HKDU', 292)],
    ('21', 'local_city_council', 15): [('Dr. Zdenko Katalinić', 'HDZ', 5632), ('Mate Kavelj', 'HSLS', 4937),
                                       ('Josip Imprić', 'SDP', 1688), ('Ratimir Buljanović', 'HKDU', 754),
                                       ('Boris Rutar', 'Hrvatska stranka naravnog zakona', 323)],
    ('21', 'local_city_council', 17): [('Tomislav Jelić', 'HDZ', 4914), ('Siniša Peternac', 'HSLS, HNS', 3352),
                                       ('Petar Stracenski', 'HSS', 1733), ('Ivan Periša', 'SDP', 782),
                                       ('Tihomir Borovac', 'HKDU', 422),
                                       ('Biserka Draganić', 'Hrvatska stranka naravnog zakona', 174)],
    ('21', 'local_city_council', 21): [('Silvije Hum', 'HSLS', 5970), ('Krešimir Končić', 'HDZ', 5045),
                                       ('Ivan Bašić', 'HSS', 2121), ('Davor Jelavić', 'SDP', 1768),
                                       ('Ana Barišić', 'Hrvatska stranka naravnog zakona', 442),
                                       ('Stjepan Hunjet', 'Nezavisni kandidat', 370), ('Borislav Zorić', 'HKDU', 342),
                                       ('Zlatko Žilajković', 'Hrvatska stranka', 183)],
    # Only the HDZ candidate prints a party.
    ('03', 'local_county_assembly', 11): [('Ivica Doležal', '', 743), ('Antun Grgurac', '', 2244),
                                          ('dipl.ing. Edgar Horvat', '', 241), ('Ivica Mađerić', '', 1299),
                                          ('Branko Radiković', 'HDZ', 2691)],
    ('03', 'local_county_assembly', 12): [('Đurđica Čudina-Draženović', '', 689),
                                          ('mr. Vladimir Miletić', 'HSLS, HNS, SDP, SSH, SDH', 3864),
                                          ('Dinko Pintarić', '', 2306), ('Ivan Puljko', '', 596)],
    ('17', 'local_county_assembly', 3): [('Marko Bekavac', 'HDZ', 3418), ('Miroslav Granić', 'HNS, HSLS i HSS', 4729),
                                         ('Miljenko Kundid', 'HKDU, HRZ i KNS', 400),
                                         ('Nikola Šimunović', 'SDP, SSH i SDU', 2090)],
    ('17', 'local_county_assembly', 7): [('Tonko Kordić', 'HNS, HSLS i HSS', 4099), ('Josip Kunac', 'HDZ', 4066),
                                         ('Semina Lončar', 'SDP, SSH i SDU', 1318),
                                         ('Tihomir Luković', 'KNS, HRZ i HKDU', 423), ('Željana Mikelić', 'HSNZ', 277)],
    ('08', 'CRIKVENICE', 9): [('Ivan Car', 'HSS', 62), ('Dubravko Domijan', 'HDZ', 134),
                              ('Josip Jurić', 'HSLS, SDP, HNS', 244)],
    ('10', 'PODRAVSKA SLATINA', 10): [('Vlado Kočiš', 'HDZ', 290), ('Đuro Horvat', 'HSS i SDH', 325)],
    ('17', 'KAŠTELA', 3): [('Vinko Pavelin', 'HSLS, HSS, HDS, HKDS i HNS', 570), ('Antun Pavlov', 'SDP', 222),
                           ('Vinko Tangar', 'HDZ', 468)],
    ('17', 'KAŠTELA', 12): [('Vinko Ćurkov', 'HSLS, HSS, HDS, HKDS i HNS', 533),
                            ('dr. Gordana Erceg-Grgin', 'HDZ', 394)],
    ('17', 'MAKARSKE', 2): [('dipl.psiholog Silvije Bandur', 'HSLS i HNS', 89), ('Drago Družijanić', 'SDP', 141),
                            ('dipl.iur. Ivan Pavlinović', 'HDZ', 364), ('Dragan Puharić', 'DA', 53)],
    ('17', 'VISA', 12): [('Marko Bralić-Braco', 'SDP', 34), ('Miroslav Vojković', 'HSLS', 3),
                         ('Vibor Vojković', 'HDZ', 36)],
    # The invalid count is left blank (figures below).
    ('18', 'BUZETA', 12): [('Alberino Černeka', 'HSLS', 54), ('Adrijano Grbac', 'IDS', 280),
                           ('Zdravko Majcan', 'HDZ', 49)],
}

MANUAL_WARD_FIGURES = {
    ('05', 'local_county_assembly', 1): (8134, 5718, 199),
    ('16', 'ŽUPANJA', 9): (803, 407, 13),
    ('18', 'BUZETA', 12): (422, 394, None),
}

MANUAL_LISTS = {
    ('08', 'KRKA'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 1018), ('NEZAVISNA GRADSKA LISTA', 1532)],
    ('05', 'TRNOVEC BARTOLOVEČKI'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 896),
                                     ('HRVATSKA SELJAČKA STRANKA - HSS', 1926),
                                     ('HRVATSKA STRANKA PRAVA - HSP', 337)],
    ('08', 'PUNAT'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 227),
                      ('HRVATSKA SOCIJALNO LIBERALNA STRANKA - HSLS', 253), ('NEZAVISNA OPĆINSKA LISTA', 511)],
    ('08', 'VRBOVSKO'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 1705),
                         ('NEZAVISNA OPĆINSKA LISTA nositelj: Simeon Bunjevac', 488),
                         ('NEZAVISNA OPĆINSKA LISTA nositelj: Davorin Rački', 1230),
                         ('NEZAVISNA OPĆINSKA LISTA nositelj: Rade Rajnović', 299)],
    ('17', 'KAŠTELANSKA ZAGORA'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 1025)],
    ('17', 'VRLIKA'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 603),
                       ('HRVATSKA KRŠĆANSKA DEMOKRATSKA UNIJA - HKDU', 456)],
    ('19', 'BLATO'): [('HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 1738),
                      ('SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - STRANKA / DEMOKRATSKIH PROMJENA - SDP', 379),
                      ('HRVATSKA NARODNA STRANKA - HNS', 211)],
}

MANUAL_LIST_VOTES = {
    ('05', 'IVANEC'): [3510, 3812],
    ('05', 'MARUŠEVEC'): [1501, 1192, 778],
    ('05', 'NOVI MAROF'): [3570, 1991, 1899],          # 7.460, 7.758 - 292 = 7.466
    # Printed 2.714 (81,67 %), the voters' line copied: a single list holds
    # every valid vote, 2.714 - 378.
    ('10', 'LUKAČ'): [2336],
    # Smudged scan; the counts that fit every printed share.
    ('17', 'DONJI PROLOŽAC'): [1288, 705, 135],
    ('17', 'JELSA'): [867, 222, 489, 369, 266],
    ('18', 'PIĆAN'): [1370],
    # Smudged scan; every count fits its printed share of the 1.586 voters.
    ('17', 'GRADAC'): [568, 126, 503, 299],
}

MANUAL_FIGURES = {
    ('11', 'DURDENOVAC'): (6433, 5309, 229),
    ('17', 'ZMIJAVCI - RUNOVIĆ'): (4049, 1336, 136),
    # Printed "Nevažećih listića: 5.840 4,46 %": 4,46 % of 63.726 is 2.842,
    # and 63.726 - 2.840 is exactly the lists' 60.886.
    ('19', 'local_county_assembly'): (95700, 63726, 2840),
}

CONFIRMED_LISTS = {
    ('05', 'NOVI MAROF'),
    ('03', 'SISKA'),          # 30.492 in lists, 31.615 - 1.153 = 30.462
    ('03', 'SUNJA'),          # 3.809, 3.947 - 21 = 3.926
    ('03', 'KOTAR GLINA'),    # 5.042, 5.649 - 591 = 5.058
    ('04', 'GENERALSKI STOL'),  # 1.360 + 742 = 2.102, 2.258 - 232 = 2.026; shares of voters fit
    ('07', 'KONČANICA'),      # 984 + 951 = 1.935, 2.097 - 149 = 1.948
    ('10', 'ŠPIŠIĆ BUKOVICA'),  # 1.475 + 1.433 = 2.908, 3.030 - 113 = 2.917
    ('12', 'NOVA GRADIŠKA'),  # 7.576 in lists (shares of that), 7.837 - 392 = 7.445
    ('01', 'VRBOVEC'),        # 8.481 in lists, 8.744 - 252 = 8.492
    ('14', 'ANTUNOVAC'),      # 951 + 531 = 1.482, 1.588 - 84 = 1.504
    ('14', 'MARIJANCI'),      # no invalid count; shares of 1.831, one under the 1.832 voters
    ('17', 'OTOK'),           # 1.839 + 464 = 2.303, 2.443 - 132 = 2.311
    ('18', 'ROVINJA'),        # 7.116 in lists, 7.680 - 263 = 7.417
    ('18', 'MARČANA'),        # no invalid count; 2.321 in lists of 2.508 voters, shares of mixed bases
    ('19', 'VELA LUKA'),      # 2.451 in lists, 2.577 - 315 = 2.262
    ('20', 'PODTUREN'),       # no invalid count; 2.364 in lists of 2.594 voters
    # 95.731 in lists, 104.296 - 3.565 = 100.731: exactly 5.000 apart, a
    # misprinted digit somewhere, but no share is printed to say where.
    ('03', 'local_county_assembly'),
}

CONFIRMED_WARDS = {
    ('15', 'local_county_assembly', 15),   # unopposed 832, 1.198 - 305 = 893
    ('15', 'local_county_assembly', 16),   # unopposed 981, 1.212 - 199 = 1.013
    ('15', 'DRNIŠA', 6),                   # unopposed 83, 158 - 35 = 123
    ('16', 'local_county_assembly', 11),   # 2.364 + 1.930 = 4.294, 4.482 - 198 = 4.284
}
