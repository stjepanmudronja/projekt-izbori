"""Key offices held during each Sabor saziv: the Prime Minister (predsjednik
Vlade) and deputy prime ministers (potpredsjednici Vlade), the Speaker
(predsjednik Sabora), the deputy speakers (potpredsjednici Sabora) and the
Secretary (tajnik Sabora).

Pure data, no Django imports, so app.py can read it. None of this comes from
an election result: the Sabor elects its presidency and confirms the
government after it is constituted, so these are curated like the rosters in
`set_sabor_members`, with the source inline.

Each entry is (role, name, sazivi, start, end, party):
  role   'pm' | 'deputy_pm' | 'minister' | 'speaker' | 'deputy' | 'secretary'
  name   as in Person.normalized_name before diacritics are stripped (the app
         normalises it); a namesake row (Person.disambiguation set) never
         matches, only the unlabelled row
  sazivi the Sabor election year(s) whose term the office fell in. 1990 means
         the 1990-1992 Sabor, whose three chambers (DPV, Vijeće općina, Vijeće
         udruženog rada) are each their own election type here
  start, end  ISO dates, or None where the source gives none (end None with a
         start = still in office)
  title  optional 7th field, the office's own name where the role's generic
         one is not enough: a minister's ministry, as it was called then
         ("Ministrica obitelji, branitelja i međugeneracijske solidarnosti")

A role shows as a badge on the person's Sabor result(s) of that saziv and in
their offices card. A holder with no Person row (never a candidate) simply
does not show: Zlatko Mateša, Josip Sesar.

A government's term is filed under every saziv it overlapped by 30 days or
more, so a caretaker cabinet's few weeks into the next Sabor do not count.

Sources: en.wikipedia "List of prime ministers of Croatia", "Deputy Prime
Minister of Croatia", the sixteen "Cabinet of <PM>" pages (ministers), "Speaker of the
Croatian Parliament" and "List of members of the Sabor, <years>" (presidency
sections); 2024 deputies from the constituent session reports (16 May 2024)
and sabor.hr. Deputy speakers before 2000 are not yet transcribed.
"""

PM, DEPUTY_PM, MINISTER, SPEAKER, DEPUTY, SECRETARY = 'pm', 'deputy_pm', 'minister', 'speaker', 'deputy', 'secretary'

ROLE_TITLES = {
    PM: 'Predsjednik Vlade',
    DEPUTY_PM: 'Potpredsjednik Vlade',
    MINISTER: 'Ministar',
    SPEAKER: 'Predsjednik Sabora',
    DEPUTY: 'Potpredsjednik Sabora',
    SECRETARY: 'Tajnik Sabora',
}
# Display order, most senior first: a person with several roles in one saziv
# (Jandroković 2016: deputy, then speaker) is coloured by the first.
ROLE_ORDER = [PM, SPEAKER, DEPUTY_PM, MINISTER, DEPUTY, SECRETARY]

SABOR_ROLES = [
    # --- Predsjednik Vlade -------------------------------------------------
    # Before the 2000 constitutional changes a term ran from appointment by
    # the President. Tihomir Orešković (PM 22 Jan - 19 Oct 2016, 2015 saziv)
    # never stood for election; the one TIHOMIR OREŠKOVIĆ in the data is a
    # 1997 local ward candidate, so he is deliberately left out.
    (PM, 'STJEPAN MESIĆ', (1990,), '1990-05-30', '1990-08-24', 'HDZ'),
    (PM, 'JOSIP MANOLIĆ', (1990,), '1990-08-24', '1991-07-17', 'HDZ'),
    (PM, 'FRANJO GREGURIĆ', (1990,), '1991-07-17', '1992-08-12', 'HDZ'),
    (PM, 'HRVOJE ŠARINIĆ', (1992,), '1992-08-12', '1993-04-03', 'HDZ'),
    (PM, 'NIKICA VALENTIĆ', (1992,), '1993-04-03', '1995-11-07', 'HDZ'),
    (PM, 'ZLATKO MATEŠA', (1995,), '1995-11-07', '2000-01-27', 'HDZ'),
    (PM, 'IVICA RAČAN', (2000,), '2000-01-27', '2003-12-23', 'SDP'),
    (PM, 'IVO SANADER', (2003, 2007), '2003-12-23', '2009-07-06', 'HDZ'),
    (PM, 'JADRANKA KOSOR', (2007,), '2009-07-06', '2011-12-23', 'HDZ'),
    (PM, 'ZORAN MILANOVIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP'),
    (PM, 'ANDREJ PLENKOVIĆ', (2016, 2020, 2024), '2016-10-19', None, 'HDZ'),

    # --- Potpredsjednik Vlade, by government --------------------------------
    # One row per term in a cabinet, so someone who served in two (Granić,
    # Kosor's Polančec, Adlešič, Uzelac) has two. Holders marked "not in the
    # data" never stood in an election imported here.
    # Mesić
    (DEPUTY_PM, 'BERNARDO JURLINA', (1990,), '1990-05-31', '1990-08-24', 'HDZ'),
    (DEPUTY_PM, 'MATE BABIĆ', (1990,), '1990-05-31', '1990-08-24', 'HDZ'),  # not in the data
    (DEPUTY_PM, 'MILAN RAMLJAK', (1990,), '1990-05-31', '1990-08-24', 'HDZ'),  # not in the data
    # Manolić
    (DEPUTY_PM, 'BERNARDO JURLINA', (1990,), '1990-08-24', '1991-03-04', 'HDZ'),
    (DEPUTY_PM, 'MATE BABIĆ', (1990,), '1990-08-24', '1990-11-08', 'HDZ'),  # not in the data
    (DEPUTY_PM, 'MILAN RAMLJAK', (1990,), '1990-08-24', '1991-07-17', 'HDZ'),  # not in the data
    (DEPUTY_PM, 'FRANJO GREGURIĆ', (1990,), '1990-11-08', '1991-07-17', 'HDZ'),
    # Gregurić
    (DEPUTY_PM, 'MILAN RAMLJAK', (1990,), '1991-07-17', '1992-08-12', 'HDZ'),  # not in the data
    (DEPUTY_PM, 'MATE GRANIĆ', (1990,), '1991-07-31', '1992-08-12', 'HDZ'),
    (DEPUTY_PM, 'ZDRAVKO TOMAC', (1990,), '1991-07-31', '1992-06-26', 'SDP'),
    (DEPUTY_PM, 'JURICA PAVELIĆ', (1990,), '1991-11-15', '1992-08-12', 'HDZ'),
    # Šarinić
    (DEPUTY_PM, 'MATE GRANIĆ', (1992,), '1992-08-12', '1993-04-03', 'HDZ'),
    (DEPUTY_PM, 'VLADIMIR ŠEKS', (1992,), '1992-08-12', '1993-04-03', 'HDZ'),
    (DEPUTY_PM, 'DARKO ČARGONJA', (1992,), '1992-08-12', '1992-12-29', 'HDZ'),
    (DEPUTY_PM, 'IVAN MILAS', (1992,), '1992-08-27', '1993-04-03', 'HDZ'),
    (DEPUTY_PM, 'MLADEN VEDRIŠ', (1992,), '1992-12-29', '1993-04-03', 'HDZ'),
    # Valentić
    (DEPUTY_PM, 'MATE GRANIĆ', (1992,), '1993-04-03', '1995-11-07', 'HDZ'),
    (DEPUTY_PM, 'VLADIMIR ŠEKS', (1992,), '1993-04-03', '1994-09-20', 'HDZ'),
    (DEPUTY_PM, 'BORISLAV ŠKEGRO', (1992,), '1993-04-03', '1995-11-07', 'HDZ'),
    (DEPUTY_PM, 'IVICA KOSTOVIĆ', (1992,), '1993-10-12', '1995-11-07', 'HDZ'),
    (DEPUTY_PM, 'JURE RADIĆ', (1992,), '1994-10-18', '1995-11-07', 'HDZ'),
    (DEPUTY_PM, 'BOSILJKO MIŠETIĆ', (1992,), '1995-05-11', '1995-11-07', 'HDZ'),
    # Mateša
    (DEPUTY_PM, 'MATE GRANIĆ', (1995,), '1995-11-07', '2000-01-27', 'HDZ'),
    (DEPUTY_PM, 'BORISLAV ŠKEGRO', (1995,), '1995-11-07', '2000-01-27', 'HDZ'),
    (DEPUTY_PM, 'IVICA KOSTOVIĆ', (1995,), '1995-11-07', '1998-10-14', 'HDZ'),
    (DEPUTY_PM, 'JURE RADIĆ', (1995,), '1995-11-07', '2000-01-27', 'HDZ'),
    (DEPUTY_PM, 'LJERKA MINTAS-HODAK', (1995,), '1995-11-07', '2000-01-27', 'HDZ'),  # not in the data
    (DEPUTY_PM, 'MILAN RAMLJAK', (1995,), '1998-05-14', '1999-04-13', 'HDZ'),  # not in the data
    # Račan I
    (DEPUTY_PM, 'GORAN GRANIĆ', (2000,), '2000-01-27', '2002-03-21', 'HSLS'),
    (DEPUTY_PM, 'ŽELJKA ANTUNOVIĆ', (2000,), '2000-01-27', '2003-12-23', 'SDP'),
    (DEPUTY_PM, 'SLAVKO LINIĆ', (2000,), '2000-01-27', '2003-12-23', 'SDP'),
    (DEPUTY_PM, 'DRAŽEN BUDIŠA', (2000,), '2002-03-21', '2002-07-30', 'HSLS'),
    # Račan II
    (DEPUTY_PM, 'GORAN GRANIĆ', (2000,), '2002-07-30', '2003-12-23', 'HNS'),
    (DEPUTY_PM, 'ANTE SIMONIĆ', (2000,), '2002-07-30', '2003-12-23', 'HSS'),  # not in the data
    # Sanader I
    (DEPUTY_PM, 'JADRANKA KOSOR', (2003, 2007), '2003-12-23', '2009-07-06', 'HDZ'),
    (DEPUTY_PM, 'ANDRIJA HEBRANG', (2003,), '2003-12-23', '2005-02-15', 'HDZ'),
    (DEPUTY_PM, 'DAMIR POLANČEC', (2003, 2007), '2005-02-17', '2009-07-06', 'HDZ'),
    # Sanader II
    (DEPUTY_PM, 'ĐURĐA ADLEŠIĆ', (2007,), '2008-01-12', '2009-07-06', 'HSLS'),
    (DEPUTY_PM, 'SLOBODAN UZELAC', (2007,), '2008-01-12', '2009-07-06', 'SDSS'),
    # Kosor
    (DEPUTY_PM, 'DAMIR POLANČEC', (2007,), '2009-07-06', '2009-10-30', 'HDZ'),
    (DEPUTY_PM, 'ĐURĐA ADLEŠIĆ', (2007,), '2009-07-06', '2010-10-12', 'HSLS'),
    (DEPUTY_PM, 'SLOBODAN UZELAC', (2007,), '2009-07-06', '2011-12-23', 'SDSS'),
    (DEPUTY_PM, 'BOŽIDAR PANKRETIĆ', (2007,), '2009-07-06', '2011-12-23', 'HSS'),
    (DEPUTY_PM, 'IVAN ŠUKER', (2007,), '2009-11-19', '2010-12-29', 'HDZ'),
    (DEPUTY_PM, 'DARKO MILINOVIĆ', (2007,), '2009-11-19', '2011-12-23', 'HDZ'),
    (DEPUTY_PM, 'DOMAGOJ IVAN MILOŠEVIĆ', (2007,), '2010-12-29', '2011-12-23', 'HDZ'),
    (DEPUTY_PM, 'PETAR ČOBANKOVIĆ', (2007,), '2010-12-29', '2011-12-23', 'HDZ'),
    (DEPUTY_PM, 'GORDAN JANDROKOVIĆ', (2007,), '2010-12-29', '2011-12-23', 'HDZ'),
    # Milanović
    (DEPUTY_PM, 'RADIMIR ČAČIĆ', (2011,), '2011-12-23', '2012-11-14', 'HNS'),
    (DEPUTY_PM, 'NEVEN MIMICA', (2011,), '2011-12-23', '2013-07-01', 'SDP'),
    (DEPUTY_PM, 'BRANKO GRČIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP'),
    (DEPUTY_PM, 'MILANKA OPAČIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP'),
    (DEPUTY_PM, 'VESNA PUSIĆ', (2011,), '2012-11-16', '2016-01-22', 'HNS'),
    (DEPUTY_PM, 'RANKO OSTOJIĆ', (2011,), '2013-07-15', '2016-01-22', 'SDP'),
    # Orešković
    (DEPUTY_PM, 'TOMISLAV KARAMARKO', (2015,), '2016-01-22', '2016-06-15', 'HDZ'),
    (DEPUTY_PM, 'BOŽO PETROV', (2015,), '2016-01-22', '2016-10-19', 'Most'),
    # Plenković I
    (DEPUTY_PM, 'IVAN KOVAČIĆ', (2016,), '2016-10-19', '2017-04-28', 'Most'),
    (DEPUTY_PM, 'DAVOR IVO STIER', (2016,), '2016-10-19', '2017-06-19', 'HDZ'),
    (DEPUTY_PM, 'DAMIR KRSTIČEVIĆ', (2016,), '2016-10-19', '2020-05-08', 'HDZ'),
    (DEPUTY_PM, 'MARTINA DALIĆ', (2016,), '2016-10-19', '2018-05-14', 'HDZ'),
    (DEPUTY_PM, 'PREDRAG ŠTROMAR', (2016,), '2017-06-09', '2020-07-23', 'HNS'),
    (DEPUTY_PM, 'MARIJA PEJČINOVIĆ BURIĆ', (2016,), '2017-06-19', '2019-07-19', 'HDZ'),
    (DEPUTY_PM, 'TOMISLAV TOLUŠIĆ', (2016,), '2018-05-25', '2019-07-17', 'HDZ'),
    (DEPUTY_PM, 'ZDRAVKO MARIĆ', (2016, 2020), '2019-07-19', '2022-07-05', 'nezavisni'),
    (DEPUTY_PM, 'DAVOR BOŽINOVIĆ', (2016, 2020, 2024), '2019-07-19', None, 'HDZ'),
    # Plenković II
    (DEPUTY_PM, 'TOMO MEDVED', (2020, 2024), '2020-07-23', None, 'HDZ'),
    (DEPUTY_PM, 'BORIS MILOŠEVIĆ', (2020,), '2020-07-23', '2022-04-29', 'SDSS'),
    (DEPUTY_PM, 'ANJA ŠIMPRAGA', (2020,), '2022-04-29', '2024-05-17', 'SDSS'),
    (DEPUTY_PM, 'OLEG BUTKOVIĆ', (2020, 2024), '2022-07-15', None, 'HDZ'),
    (DEPUTY_PM, 'BRANKO BAČIĆ', (2020, 2024), '2023-01-17', None, 'HDZ'),
    (DEPUTY_PM, 'IVAN ANUŠIĆ', (2020, 2024), '2023-11-16', None, 'HDZ'),
    # Plenković III
    (DEPUTY_PM, 'JOSIP DABRO', (2024,), '2024-05-17', '2025-01-18', 'DP'),
    (DEPUTY_PM, 'MARKO PRIMORAC', (2024,), '2024-05-17', '2026-01-29', 'nezavisni'),
    (DEPUTY_PM, 'DAVID VLAJČIĆ', (2024,), '2025-02-11', None, 'DP'),  # not in the data
    (DEPUTY_PM, 'TOMISLAV ĆORIĆ', (2024,), '2026-01-29', None, 'HDZ'),

    # --- Ministri ----------------------------------------------------------
    # Every minister of the sixteen governments since 1990, read from the
    # cabinet tables of each "Cabinet of <PM>" page (former members
    # included) and merged where several pages repeat one term. The English
    # portfolio is given its Croatian name, Ministar/Ministrica by first name.
    # Ministers who also served as deputy PM are listed here for the ministry
    # only. A name matches only a Person with a national record (Sabor, EU,
    # presidential): holders whose only namesake in the data stood in local
    # elections (Ivica Kirin, Predrag Šustar, Berislav Rončević, Josip
    # Boljkovac…) are left unlinked rather than risk a namesake, and many
    # ministers never stood at all — both kinds are in the list regardless.
    # 1990
    (MINISTER, 'ANDRIJA HEBRANG', (1990,), '1990-05-30', '1992-08-12', 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'OSMAN MUFTIĆ', (1990,), '1990-05-30', '1991-07-31', 'HDZ', 'Ministar znanosti, tehnologije i informatike'),
    (MINISTER, 'ZVONIMIR MEDVEDOVIĆ', (1990,), '1990-05-30', '1990-07-25', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'BOŽO UDOVIČIĆ', (1990,), '1990-05-31', '1991-07-17', 'HDZ', 'Ministar energetike i industrije'),
    (MINISTER, 'DRAGUTIN KALOGJERA', (1990,), '1990-05-31', '1990-10-04', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'GOJKO ŠUŠAK', (1990,), '1990-05-31', '1991-07-17', 'HDZ', 'Ministar iseljeništva'),
    (MINISTER, 'GOJKO ŠUŠAK', (1990,), '1990-05-31', '1991-07-17', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'IVAN TARNAJ', (1990,), '1990-05-31', '1992-08-12', 'HDZ', 'Ministar poljoprivrede, šumarstva i vodoprivrede'),
    (MINISTER, 'JOSIP BOLJKOVAC', (1990,), '1990-05-31', '1991-07-02', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'MARIN ČRNJA', (1990,), '1990-05-31', '1991-03-04', 'HDZ', 'Ministar rada, branitelja i invalida'),
    (MINISTER, 'MILAN HRNJAK', (1990,), '1990-05-31', '1991-03-04', 'HDZ', 'Ministar graditeljstva, stambeno-komunalnih djelatnosti i zaštite čovjekove okoline'),
    (MINISTER, 'MILOVAN ŠIBL', (1990,), '1990-05-31', '1991-03-04', 'HDZ', 'Ministar informiranja'),
    (MINISTER, 'PETAR KRISTE', (1990,), '1990-05-31', '1990-08-24', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'STJEPAN ZDUNIĆ', (1990,), '1990-05-31', '1990-10-10', 'HDZ', 'Ministar društvenog planiranja'),
    (MINISTER, 'VLATKO PAVLETIĆ', (1990,), '1990-05-31', '1992-04-15', 'Non-partisan (later HDZ)', 'Ministar prosvjete, kulture i športa'),
    (MINISTER, 'ZDRAVKO MRŠIĆ', (1990,), '1990-05-31', '1990-11-08', 'nezavisni', 'Ministar vanjskih poslova'),
    (MINISTER, 'ZDRAVKO MRŠIĆ', (1990,), '1990-05-31', '1991-07-17', 'nezavisni', 'Ministar bez lisnice'),
    (MINISTER, 'BRANKO BABAC', (1990,), '1990-06-28', '1991-07-17', 'HDZ', 'Ministar pravosuđa i uprave'),
    (MINISTER, 'BRANKO BERGMAN', (1990,), '1990-07-25', '1991-07-17', 'HDZ', 'Ministar vodoprivrede'),
    (MINISTER, 'DAVORIN RUDOLF', (1990,), '1990-07-25', '1990-08-24', 'HDZ', 'Ministar pomorstva'),
    (MINISTER, 'JANKO VRANYCZANY-DOBRINOVIĆ', (1990,), '1990-07-25', '1991-07-17', 'HDZ', 'Ministar turizma'),
    (MINISTER, 'JOSIP BOŽIČEVIĆ', (1990,), '1990-07-25', '1992-08-12', 'Non-partisan (later HDZ)', 'Ministar prometa i veza'),
    (MINISTER, 'JOSIP BOŽIČEVIĆ', (1990,), '1990-07-25', '1992-08-12', 'HDZ', 'Ministar prometa'),
    (MINISTER, 'MARIJAN HANŽEKOVIĆ', (1990,), '1990-07-25', '1991-07-17', 'HDZ', 'Ministar financija'),
    (MINISTER, 'ZVONIMIR MEDVEDOVIĆ', (1990,), '1990-07-25', '1990-08-24', 'HDZ', 'Ministar robne razmjene'),
    (MINISTER, 'MARTIN ŠPEGELJ', (1990,), '1990-08-24', '1991-07-02', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'PETAR KRISTE', (1990,), '1990-08-24', '1992-04-15', 'HDZ', 'Ministar trgovine'),
    (MINISTER, 'PETAR KRISTE', (1990,), '1990-08-24', '1992-04-15', 'HDZ', 'Ministar robne razmjene'),
    (MINISTER, 'ZVONIMIR MEDVEDOVIĆ', (1990,), '1990-08-24', '1990-10-04', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'FRANE VINKO GOLEM', (1990,), '1990-11-08', '1991-03-05', 'HDZ', 'Ministar vanjskih poslova'),
    # 1991
    (MINISTER, 'BERNARDO JURLINA', (1990,), '1991-03-04', '1992-04-15', 'HDZ', 'Ministar rada, socijalne skrbi i obitelji'),
    (MINISTER, 'HRVOJE HITREC', (1990,), '1991-03-04', '1991-07-17', 'HDZ', 'Ministar informiranja'),
    (MINISTER, 'DAVORIN RUDOLF', (1990,), '1991-03-05', '1991-07-17', 'HDZ', 'Ministar vanjskih poslova'),
    (MINISTER, 'DAVORIN RUDOLF', (1990,), '1991-05-03', '1991-07-17', 'HDZ', 'Ministar pomorstva'),
    (MINISTER, 'ONESIN CVITAN', (1990,), '1991-07-02', '1991-07-17', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'ŠIME ĐODAN', (1990,), '1991-07-02', '1991-07-17', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'BOSILJKO MIŠETIĆ', (1990,), '1991-07-17', '1992-05-14', 'HNS (later HDZ)', 'Ministar pravosuđa i uprave'),
    (MINISTER, 'JOZO MARTINOVIĆ', (1990,), '1991-07-17', '1992-08-12', 'Non-partisan (later HDZ)', 'Ministar financija'),
    (MINISTER, 'LUKA BEBIĆ', (1990,), '1991-07-17', '1991-09-18', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'SLAVKO DEGORICIJA', (1990,), '1991-07-17', '1991-07-31', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'ANTE ČOVIĆ', (1990,), '1991-07-31', '1992-04-14', 'SDSH (later HDZ)', 'Ministar znanosti, tehnologije i informatike'),
    (MINISTER, 'IVAN VEKIĆ', (1990,), '1991-07-31', '1992-04-14', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'MUHAMED ZULIĆ', (1990,), '1991-07-31', '1992-08-12', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'VLADIMIR VESELICA', (1990,), '1991-07-31', '1991-12-02', 'HDS (later HDZ)', 'Ministar bez lisnice'),
    (MINISTER, 'ZVONIMIR ŠEPAROVIĆ', (1990,), '1991-07-31', '1992-05-27', 'HDZ', 'Ministar vanjskih poslova'),
    (MINISTER, 'ŽIVKO JUZBAŠIĆ', (1990,), '1991-07-31', '1992-08-12', 'nezavisni', 'Ministar bez lisnice'),
    (MINISTER, 'DAVORIN RUDOLF', (1990,), '1991-08-01', '1992-08-12', 'Non-partisan (later HDZ)', 'Ministar pomorstva'),
    (MINISTER, 'DRAŽEN BUDIŠA', (1990,), '1991-08-02', '1992-02-20', 'HSLS', 'Ministar bez lisnice'),
    (MINISTER, 'ENZO TIRELI', (1990,), '1991-08-02', '1992-04-15', 'SDP', 'Ministar energetike i industrije'),
    (MINISTER, 'GOJKO ŠUŠAK', (1990,), '1991-08-02', '1991-09-18', 'HDZ', 'Ministar iseljeništva'),
    (MINISTER, 'IVAN CESAR', (1990,), '1991-08-02', '1992-06-03', 'HKDS', 'Ministar bez lisnice'),
    (MINISTER, 'IVAN CIFRIĆ', (1990,), '1991-08-02', '1992-08-12', 'SSH', 'Ministar zaštite okoliša, prostornoga uređenja i graditeljstva'),
    (MINISTER, 'ZVONIMIR BALETIĆ', (1990,), '1991-08-02', '1992-08-12', 'SDSH (later HDZ)', 'Ministar bez lisnice'),
    (MINISTER, 'BRANKO SALAJ', (1990,), '1991-08-27', '1992-08-12', 'HDZ', 'Ministar informiranja'),
    (MINISTER, 'STJEPAN ZDUNIĆ', (1990,), '1991-08-31', '1991-12-14', 'Non-partisan (later HDZ)', 'Ministar bez lisnice'),
    (MINISTER, 'ANTON MARČELO POPOVIĆ', (1990,), '1991-09-16', '1992-08-12', '', 'Ministar turizma'),
    (MINISTER, 'GOJKO ŠUŠAK', (1990, 1992, 1995), '1991-09-18', '1998-05-03', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'ZDRAVKO SANČEVIĆ', (1990,), '1991-12-02', '1992-08-12', 'HDZ', 'Ministar iseljeništva'),
    (MINISTER, 'STJEPAN ZDUNIĆ', (1990,), '1991-12-15', '1992-08-12', 'Non-partisan (later HDZ)', 'Ministar gospodarskog razvitka'),
    (MINISTER, 'SLAVKO DEGORICIJA', (1990,), '1991-12-31', '1992-08-12', 'HDZ', 'Ministar obnove'),
    # 1992
    (MINISTER, 'IVAN JARNJAK', (1990, 1992, 1995), '1992-04-14', '1996-12-16', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'JURE RADIĆ', (1990,), '1992-04-14', '1992-08-07', 'HDZ', 'Ministar znanosti, tehnologije i informatike'),
    (MINISTER, 'BRANKO MIKŠA', (1990,), '1992-04-15', '1992-08-12', 'HDZ', 'Ministar trgovine'),
    (MINISTER, 'DARKO ČARGONJA', (1990,), '1992-04-15', '1992-08-12', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'FRANJO KAJFEŽ', (1990, 1992), '1992-04-15', '1993-04-03', 'HDZ', 'Ministar energetike i industrije'),
    (MINISTER, 'FRANJO KAJFEŽ', (1990, 1992), '1992-04-15', '1993-04-03', 'HDZ', 'Ministar industrije, brodogradnje i energetike'),
    (MINISTER, 'IVICA CRNIĆ', (1990,), '1992-04-15', '1992-08-12', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'JOSIP JURAS', (1990, 1992), '1992-04-15', '1993-10-12', 'HDZ', 'Ministar rada, socijalne skrbi i obitelji'),
    (MINISTER, 'JOSIP JURAS', (1990, 1992), '1992-04-15', '1993-10-12', 'HDZ', 'Ministar rada i socijalne skrbi'),
    (MINISTER, 'MLADEN VEDRIŠ', (1990,), '1992-04-15', '1992-08-12', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'VESNA GIRARDI-JURKIĆ', (1990, 1992), '1992-04-15', '1994-10-18', 'HDZ', 'Ministrica prosvjete, kulture i športa'),
    (MINISTER, 'VESNA GIRARDI-JURKIĆ', (1990, 1992), '1992-04-15', '1994-10-18', 'HDZ', 'Ministrica kulture i prosvjete'),
    (MINISTER, 'IVAN MILAS', (1990,), '1992-06-08', '1992-08-12', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'ZDENKO ŠKRABALO', (1990, 1992), '1992-06-09', '1993-05-27', 'HDZ', 'Ministar vanjskih poslova'),
    (MINISTER, 'BRANKO MIKŠA', (1992,), '1992-08-12', '1993-04-03', 'HDZ', 'Ministar turizma i trgovine'),
    (MINISTER, 'IVAN MAJDAK', (1992,), '1992-08-12', '1993-04-03', 'HDZ', 'Ministar poljoprivrede i šumarstva'),
    (MINISTER, 'IVICA CRNIĆ', (1992,), '1992-08-12', '1993-05-20', 'HDZ', 'Ministar pravosuđa i uprave'),
    (MINISTER, 'IVICA MUDRINIĆ', (1992, 1995), '1992-08-12', '1996-02-05', 'HDZ', 'Ministar pomorstva, prometa i veza'),
    (MINISTER, 'IVO SANADER', (1992,), '1992-08-12', '1993-01-07', 'HDZ', 'Ministar znanosti'),
    (MINISTER, 'JURAJ NJAVRO', (1992,), '1992-08-12', '1993-10-12', 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'SMILJKO SOKOL', (1992,), '1992-08-12', '1993-04-03', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'ZDENKO KARAKAŠ', (1992,), '1992-08-12', '1993-04-03', 'HDZ', 'Ministar graditeljstva i zaštite okoliša'),
    (MINISTER, 'ZORAN JAŠIĆ', (1992,), '1992-08-12', '1994-07-07', 'HDZ', 'Ministar financija'),
    (MINISTER, 'ČEDOMIR PAVLOVIĆ', (1992,), '1992-08-12', '1993-04-03', '', 'Ministar bez lisnice'),
    (MINISTER, 'ZVONIMIR BALETIĆ', (1992,), '1992-09-07', '1993-01-26', 'HDZ', 'Ministar bez lisnice'),
    # 1993
    (MINISTER, 'BRANKO JEREN', (1992,), '1993-02-23', '1995-11-07', 'HDZ', 'Ministar znanosti i tehnologije'),
    (MINISTER, 'IVAN MAJDAK', (1992,), '1993-04-03', '1995-11-07', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'IVAN TARNAJ', (1992,), '1993-04-03', '1994-12-31', 'HDZ', 'Ministar poljoprivrede, šumarstva i vodnoga gospodarstva'),
    (MINISTER, 'IVAN ČERMAK', (1992,), '1993-04-03', '1993-05-20', 'HDZ', 'Ministar industrije, brodogradnje i energetike'),
    (MINISTER, 'NIKO BULIĆ', (1992,), '1993-04-03', '1993-05-20', 'HDZ', 'Ministar trgovine i turizma'),
    (MINISTER, 'ZLATKO MATEŠA', (1992,), '1993-04-03', '1995-09-18', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'ZLATKO TOMČIĆ', (1992,), '1993-04-03', '1994-12-31', 'HSS', 'Ministar graditeljstva i zaštite okoliša'),
    (MINISTER, 'IVAN ČERMAK', (1992,), '1993-05-20', '1993-10-12', 'HDZ', 'Ministar gospodarstva'),
    (MINISTER, 'IVICA CRNIĆ', (1992,), '1993-05-20', '1995-05-18', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'JURICA MALČIĆ', (1992,), '1993-05-20', '1994-03-02', 'HDZ', 'Ministrica uprave'),
    (MINISTER, 'NIKO BULIĆ', (1992, 1995), '1993-05-20', '1997-09-11', 'HDZ', 'Ministar turizma'),
    (MINISTER, 'MATE GRANIĆ', (1992, 1995), '1993-05-27', '2000-01-27', 'HDZ', 'Ministar vanjskih poslova'),
    (MINISTER, 'ANDRIJA HEBRANG', (1992, 1995), '1993-10-12', '1998-05-14', 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'IVAN PARAĆ', (1992,), '1993-10-12', '1995-01-27', 'HDZ', 'Ministar rada i socijalne skrbi'),
    (MINISTER, 'JURAJ NJAVRO', (1992, 1995), '1993-10-12', '1997-12-19', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'NADAN VIDOŠEVIĆ', (1992,), '1993-10-12', '1995-09-18', 'HDZ', 'Ministar gospodarstva'),
    # 1994
    (MINISTER, 'DAVORIN MLAKAR', (1992, 1995), '1994-03-02', '1998-03-04', 'HDZ', 'Ministar uprave'),
    (MINISTER, 'BOŽO PRKA', (1992, 1995), '1994-07-07', '1997-09-11', 'HDZ', 'Ministar financija'),
    (MINISTER, 'JURE RADIĆ', (1992, 1995), '1994-10-18', '1999-05-18', 'HDZ', 'Ministar razvitka i obnove'),
    (MINISTER, 'LJILJA VOKIĆ', (1992, 1995), '1994-10-18', '1998-03-04', 'HDZ', 'Ministrica prosvjete i športa'),
    (MINISTER, 'ZLATKO VITEZ', (1992,), '1994-10-18', '1995-11-07', 'HDZ', 'Ministar kulture'),
    # 1995
    (MINISTER, 'ADALBERT REBIĆ', (1992,), '1995-01-27', '1995-11-07', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'IVAN PENIĆ', (1992, 1995), '1995-01-27', '1996-12-16', 'HDZ', 'Ministar privatizacije i upravljanja imovinom'),
    (MINISTER, 'IVICA GAŽI', (1992,), '1995-01-27', '1995-11-07', 'HDZ', 'Ministar poljoprivrede i šumarstva'),
    (MINISTER, 'JOSO ŠKARA', (1992, 1995), '1995-01-27', '2000-01-27', 'HDZ', 'Ministar rada i socijalne skrbi'),
    (MINISTER, 'MARINA MATULOVIĆ DROPULIĆ', (1992, 1995), '1995-01-27', '1996-12-16', 'HDZ', 'Ministrica prostornoga uređenja, graditeljstva i stanovanja'),
    (MINISTER, 'MARIJAN PETROVIĆ', (1992, 1995), '1995-05-11', '1996-11-13', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'MIROSLAV ŠEPAROVIĆ', (1992, 1995), '1995-05-18', '1998-04-20', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'DAVOR ŠTERN', (1992,), '1995-08-21', '1995-11-07', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'ZLATKO MATEŠA', (1992,), '1995-09-18', '1995-11-07', 'HDZ', 'Ministar gospodarstva'),
    (MINISTER, 'BOŽO BIŠKUPIĆ', (1995,), '1995-11-07', '2000-01-27', 'HDZ', 'Ministar kulture'),
    (MINISTER, 'BRANKO MOČIBOB', (1995,), '1995-11-07', '1997-05-15', 'HDZ', 'Ministar bez lisnice'),
    (MINISTER, 'DAVOR ŠTERN', (1995,), '1995-11-07', '1997-04-14', 'HDZ', 'Ministar gospodarstva'),
    (MINISTER, 'IVICA KOSTOVIĆ', (1995,), '1995-11-07', '1998-10-14', 'HDZ', 'Ministar znanosti i tehnologije'),
    (MINISTER, 'MATEJ JANKOVIĆ', (1995,), '1995-11-07', '1996-12-16', 'HDZ', 'Ministar poljoprivrede i šumarstva'),
    # 1996
    (MINISTER, 'ŽELJKO LUŽAVEC', (1995,), '1996-02-05', '1999-08-04', 'HDZ', 'Ministar pomorstva, prometa i veza'),
    (MINISTER, 'MARIJAN PETROVIĆ', (1995,), '1996-11-13', '1999-06-01', 'HDZ', 'Ministar povratka i useljeništva'),
    (MINISTER, 'IVAN PENIĆ', (1995,), '1996-12-16', '2000-01-27', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'MARKO ŠIRAC', (1995,), '1996-12-16', '2000-01-27', 'HDZ', 'Ministar prostornoga uređenja, graditeljstva i stanovanja'),
    (MINISTER, 'MILAN KOVAČ', (1995,), '1996-12-16', '1999-04-01', 'HDZ', 'Ministar privatizacije i upravljanja imovinom'),
    (MINISTER, 'ZLATKO DOMINIKOVIĆ', (1995,), '1996-12-16', '1999-02-22', 'HDZ', 'Ministar poljoprivrede i šumarstva'),
    # 1997
    (MINISTER, 'NENAD PORGES', (1995,), '1997-04-15', '2000-01-27', 'HDZ', 'Ministar gospodarstva'),
    (MINISTER, 'BORISLAV ŠKEGRO', (1995,), '1997-09-11', '2000-01-27', 'HDZ', 'Ministar financija'),
    (MINISTER, 'SERGEJ MORSAN', (1995,), '1997-11-09', '1999-04-15', 'HDZ', 'Ministar turizma'),
    (MINISTER, 'JURAJ NJAVRO', (1995,), '1997-12-19', '2000-01-27', 'HDZ', 'Ministar hrvatskih branitelja iz Domovinskog rata'),
    # 1998
    (MINISTER, 'BOŽIDAR PUGELNIK', (1995,), '1998-03-04', '1999-10-05', 'HDZ', 'Ministar prosvjete i športa'),
    (MINISTER, 'LJERKA MINTAS-HODAK', (1995,), '1998-03-04', '2000-01-27', 'HDZ', 'Ministrica europskih integracija'),
    (MINISTER, 'MARIJAN RAMUŠĆAK', (1995,), '1998-03-04', '1999-02-17', 'HDZ', 'Ministar uprave'),
    (MINISTER, 'ANDRIJA HEBRANG', (1995,), '1998-05-14', '1998-10-12', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'MILAN RAMLJAK', (1995,), '1998-05-14', '1999-04-13', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'ŽELJKO REINER', (1995,), '1998-05-14', '2000-01-27', 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'PAVAO MILJAVAC', (1995,), '1998-10-14', '2000-01-27', 'HDZ', 'Ministar obrane'),
    # 1999
    (MINISTER, 'IVAN ĐURKIĆ', (1995,), '1999-02-22', '2000-01-27', 'HDZ', 'Ministar poljoprivrede i šumarstva'),
    (MINISTER, 'MILENA ŽIC-FUCHS', (1995,), '1999-02-22', '2000-01-27', 'nezavisni', 'Ministrica znanosti i tehnologije'),
    (MINISTER, 'IVAN HERAK', (1995,), '1999-04-15', '2000-01-27', 'HDZ', 'Ministar turizma'),
    (MINISTER, 'MILAN KOVAČ', (1995,), '1999-04-15', '2000-01-27', 'HDZ', 'Ministar za posebne odnose s Bosnom i Hercegovinom'),
    (MINISTER, 'ZVONIMIR ŠEPAROVIĆ', (1995,), '1999-04-15', '2000-01-27', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'JURE RADIĆ', (1995,), '1999-05-18', '2000-01-27', 'HDZ', 'Ministar razvitka, useljeništva i obnove'),
    (MINISTER, 'IVAN PAVLOVIĆ', (1995,), '1999-08-16', '2000-01-27', 'HDZ', 'Ministar pomorstva, prometa i veza'),
    (MINISTER, 'NENSI IVANIŠEVIĆ', (1995,), '1999-10-05', '2000-01-27', 'HDZ', 'Ministar prosvjete i športa'),
    # 2000
    (MINISTER, 'ALOJZ TUŠEK', (2000,), '2000-01-27', '2002-03-21', 'HSLS', 'Ministar pomorstva, prometa i veza'),
    (MINISTER, 'ANA STAVLJENIĆ RUKAVINA', (2000,), '2000-01-27', '2001-10-23', 'nezavisni', 'Ministrica zdravstva'),
    (MINISTER, 'ANTUN VUJIĆ', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar kulture'),
    (MINISTER, 'BOŽIDAR PANKRETIĆ', (2000,), '2000-01-27', '2003-12-23', 'HSS', 'Ministar poljoprivrede i šumarstva'),
    (MINISTER, 'BOŽO KOVAČEVIĆ', (2000,), '2000-01-27', '2003-07-18', 'LS', 'Ministar zaštite okoliša i prostornoga uređenja'),
    (MINISTER, 'DAVORKO VIDOVIĆ', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar rada i socijalne skrbi'),
    (MINISTER, 'GORANKO FIŽULIĆ', (2000,), '2000-01-27', '2002-03-21', 'HSLS', 'Ministar gospodarstva'),
    (MINISTER, 'HRVOJE KRALJEVIĆ', (2000,), '2000-01-27', '2002-07-30', 'HSLS', 'Ministar znanosti i tehnologije'),
    (MINISTER, 'IVAN JAKOVČIĆ', (2000,), '2000-01-27', '2001-06-21', 'IDS', 'Ministar europskih integracija'),
    (MINISTER, 'IVICA PANČIĆ', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar hrvatskih branitelja iz Domovinskog rata'),
    (MINISTER, 'JOZO RADOŠ', (2000,), '2000-01-27', '2002-07-05', 'HSLS', 'Ministar obrane'),
    (MINISTER, 'MATO CRKVENAC', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar financija'),
    (MINISTER, 'PAVE ŽUPAN-RUSKOVIĆ', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar turizma'),
    (MINISTER, 'RADIMIR ČAČIĆ', (2000,), '2000-01-27', '2003-12-23', 'HNS', 'Ministar javnih radova, obnove i graditeljstva'),
    (MINISTER, 'STJEPAN IVANIŠEVIĆ', (2000,), '2000-01-27', '2001-09-27', 'SDP', 'Ministar pravosuđa, uprave i lokalne samouprave'),
    (MINISTER, 'TONINO PICULA', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar vanjskih poslova'),
    (MINISTER, 'VLADIMIR STRUGAR', (2000,), '2000-01-27', '2003-12-23', 'HSS', 'Ministar prosvjete i športa'),
    (MINISTER, 'ŠIME LUČIN', (2000,), '2000-01-27', '2003-12-23', 'SDP', 'Ministar unutarnjih poslova'),
    (MINISTER, 'ŽELJKO PECEK', (2000,), '2000-01-27', '2003-12-23', 'HSS', 'Ministar obrta, malog i srednjeg poduzetništva'),
    # 2001
    (MINISTER, 'INGRID ANTIČEVIĆ-MARINOVIĆ', (2000,), '2001-09-28', '2003-12-23', 'SDP', 'Ministrica pravosuđa, uprave i lokalne samouprave'),
    (MINISTER, 'NEVEN MIMICA', (2000,), '2001-09-28', '2003-12-23', 'SDP', 'Ministar europskih integracija'),
    (MINISTER, 'ANDRO VLAHUŠIĆ', (2000,), '2001-11-22', '2003-12-23', 'HNS', 'Ministar zdravstva'),
    # 2002
    (MINISTER, 'GORDANA SOBOL', (2000,), '2002-07-30', '2003-12-23', 'SDP', 'Ministrica bez lisnice'),
    (MINISTER, 'GVOZDEN FLEGO', (2000,), '2002-07-30', '2003-12-23', 'SDP', 'Ministar znanosti i tehnologije'),
    (MINISTER, 'LJUBO JURČIĆ', (2000,), '2002-07-30', '2003-12-23', 'SDP', 'Ministar gospodarstva'),
    (MINISTER, 'ROLAND ŽUVANIĆ', (2000,), '2002-07-30', '2003-12-23', 'LIBRA', 'Ministar pomorstva, prometa i veza'),
    (MINISTER, 'ŽELJKA ANTUNOVIĆ', (2000,), '2002-07-30', '2003-12-23', 'SDP', 'Ministrica obrane'),
    # 2003
    (MINISTER, 'IVO BANAC', (2000,), '2003-07-18', '2003-12-23', 'LS', 'Ministar zaštite okoliša i prostornoga uređenja'),
    (MINISTER, 'ANDRIJA HEBRANG', (2003,), '2003-12-23', '2005-02-15', 'HDZ', 'Ministar zdravstva i socijalne skrbi'),
    (MINISTER, 'BERISLAV RONČEVIĆ', (2003,), '2003-12-23', '2008-01-12', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'BOŽIDAR KALMETA', (2003, 2007), '2003-12-23', '2011-12-23', 'HDZ', 'Ministar mora, turizma, prometa i razvitka'),
    (MINISTER, 'BOŽIDAR KALMETA', (2003, 2007), '2003-12-23', '2011-12-23', 'HDZ', 'Ministar pomorstva, prometa i infrastrukture'),
    (MINISTER, 'BOŽO BIŠKUPIĆ', (2003, 2007), '2003-12-23', '2010-12-29', 'HDZ', 'Ministar kulture'),
    (MINISTER, 'BRANKO VUKELIĆ', (2003,), '2003-12-23', '2008-01-12', 'HDZ', 'Ministar gospodarstva, rada i poduzetništva'),
    (MINISTER, 'DRAGAN PRIMORAC', (2003, 2007), '2003-12-23', '2009-07-02', 'nezavisni', 'Ministar znanosti, obrazovanja i športa'),
    (MINISTER, 'IVAN ŠUKER', (2003, 2007), '2003-12-23', '2010-12-29', 'HDZ', 'Ministar financija'),
    (MINISTER, 'JADRANKA KOSOR', (2003, 2007), '2003-12-23', '2009-07-06', 'HDZ', 'Ministrica obitelji, branitelja i međugeneracijske solidarnosti'),
    (MINISTER, 'KOLINDA GRABAR-KITAROVIĆ', (2003,), '2003-12-23', '2005-02-16', 'HDZ', 'Ministrica europskih integracija'),
    (MINISTER, 'MARIJAN MLINARIĆ', (2003,), '2003-12-23', '2005-07-12', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'MARINA MATULOVIĆ DROPULIĆ', (2003, 2007), '2003-12-23', '2010-12-29', 'HDZ', 'Ministrica zaštite okoliša, prostornoga uređenja i graditeljstva'),
    (MINISTER, 'PETAR ČOBANKOVIĆ', (2003,), '2003-12-23', '2008-01-12', 'HDZ', 'Ministar poljoprivrede, šumarstva i vodnoga gospodarstva'),
    (MINISTER, 'VESNA ŠKARE OŽBOLT', (2003,), '2003-12-23', '2006-02-09', 'DC', 'Ministrica pravosuđa'),
    # 2005
    (MINISTER, 'NEVEN LJUBIČIĆ', (2003,), '2005-02-16', '2008-01-12', 'HDZ', 'Ministar zdravstva i socijalne skrbi'),
    (MINISTER, 'KOLINDA GRABAR-KITAROVIĆ', (2003,), '2005-02-17', '2008-01-12', 'HDZ', 'Ministrica vanjskih poslova i europskih integracija'),
    (MINISTER, 'MIOMIR ŽUŽUL', (2003,), '2005-02-17', '2005-02-16', 'HDZ', 'Ministar vanjskih poslova'),
    (MINISTER, 'IVICA KIRIN', (2003,), '2005-07-12', '2008-01-02', 'HDZ', 'Ministar unutarnjih poslova'),
    # 2006
    (MINISTER, 'ANA LOVRIN', (2003, 2007), '2006-02-10', '2008-10-10', 'HDZ', 'Ministrica pravosuđa'),
    # 2008
    (MINISTER, 'BERISLAV RONČEVIĆ', (2007,), '2008-01-12', '2008-10-10', 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'BOŽIDAR PANKRETIĆ', (2007,), '2008-01-12', '2009-07-06', 'HSS', 'Ministar poljoprivrede, ribarstva i ruralnog razvoja'),
    (MINISTER, 'BRANKO VUKELIĆ', (2007,), '2008-01-12', '2010-12-29', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'DAMIR BAJS', (2007,), '2008-01-12', '2011-12-23', 'HSS', 'Ministar turizma'),
    (MINISTER, 'DAMIR POLANČEC', (2007,), '2008-01-12', '2009-10-30', 'HDZ', 'Ministar gospodarstva, rada i poduzetništva'),
    (MINISTER, 'DARKO MILINOVIĆ', (2007,), '2008-01-12', '2011-12-23', 'HDZ', 'Ministar zdravstva i socijalne skrbi'),
    (MINISTER, 'DARKO MILINOVIĆ (D)', (2007,), '2008-01-12', '2011-12-23', 'HDZ', 'Ministar zdravstva i socijalne skrbi'),
    (MINISTER, 'GORDAN JANDROKOVIĆ', (2007,), '2008-01-12', '2011-12-23', 'HDZ', 'Ministar vanjskih poslova i europskih integracija'),
    (MINISTER, 'GORDAN JANDROKOVIĆ (D)', (2007,), '2008-01-12', '2011-12-23', 'HDZ', 'Ministar vanjskih poslova i europskih integracija'),
    (MINISTER, 'PETAR ČOBANKOVIĆ', (2007,), '2008-01-12', '2009-07-06', 'HDZ', 'Ministar regionalnoga razvoja, šumarstva i vodnoga gospodarstva'),
    (MINISTER, 'IVAN ŠIMONOVIĆ', (2007,), '2008-10-10', '2010-07-07', 'nezavisni', 'Ministar pravosuđa'),
    (MINISTER, 'TOMISLAV KARAMARKO', (2007,), '2008-10-10', '2011-12-23', 'HDZ', 'Ministar unutarnjih poslova'),
    # 2009
    (MINISTER, 'RADOVAN FUCHS', (2007,), '2009-07-02', '2011-12-23', 'HDZ', 'Ministar znanosti, obrazovanja i športa'),
    (MINISTER, 'BIANCA MATKOVIĆ', (2007,), '2009-07-06', '2010-03-24', 'HDZ', 'Ministrica bez lisnice'),
    (MINISTER, 'BOŽIDAR PANKRETIĆ (D)', (2007,), '2009-07-06', '2011-12-23', 'HSS', 'Ministar regionalnoga razvoja, šumarstva i vodnoga gospodarstva'),
    (MINISTER, 'DAVORIN MLAKAR', (2007,), '2009-07-06', '2011-12-23', 'HDZ', 'Ministar uprave'),
    (MINISTER, 'PETAR ČOBANKOVIĆ (D)', (2007,), '2009-07-06', '2011-12-23', 'HDZ', 'Ministar poljoprivrede, ribarstva i ruralnog razvoja'),
    (MINISTER, 'TOMISLAV IVIĆ', (2007,), '2009-07-06', '2011-12-23', 'HDZ', 'Ministar obitelji, branitelja i međugeneracijske solidarnosti'),
    (MINISTER, 'ĐURO POPIJAČ', (2007,), '2009-11-19', '2011-12-23', 'HDZ', 'Ministar gospodarstva, rada i poduzetništva'),
    # 2010
    (MINISTER, 'DRAŽEN BOŠNJAKOVIĆ', (2007,), '2010-07-07', '2011-12-23', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'BRANKO BAČIĆ', (2007,), '2010-12-29', '2011-12-23', 'HDZ', 'Ministar zaštite okoliša, prostornoga uređenja i graditeljstva'),
    (MINISTER, 'DAVOR BOŽINOVIĆ', (2007,), '2010-12-29', '2011-12-23', 'nezavisni', 'Ministar obrane'),
    (MINISTER, 'JASEN MESIĆ', (2007,), '2010-12-29', '2011-12-23', 'HDZ', 'Ministar kulture'),
    (MINISTER, 'MARTINA DALIĆ', (2007,), '2010-12-29', '2011-12-23', 'HDZ', 'Ministrica financija'),
    # 2011
    (MINISTER, 'ANDREA ZLATAR-VIOLIĆ', (2011,), '2011-12-23', '2015-03-25', 'HNS', 'Ministrica kulture'),
    (MINISTER, 'ANTE KOTROMANOVIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar obrane'),
    (MINISTER, 'ARSEN BAUK', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar uprave'),
    (MINISTER, 'BRANKO GRČIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar regionalnoga razvoja i fondova Europske unije'),
    (MINISTER, 'GORDAN MARAS', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar poduzetništva i obrta'),
    (MINISTER, 'MILANKA OPAČIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministrica socijalne politike i mladih'),
    (MINISTER, 'MIRANDO MRSIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar rada i mirovinskoga sustava'),
    (MINISTER, 'MIRELA HOLY', (2011,), '2011-12-23', '2012-06-07', 'SDP', 'Ministrica zaštite okoliša i prirode'),
    (MINISTER, 'ORSAT MILJENIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar pravosuđa'),
    (MINISTER, 'PREDRAG MATIĆ', (2011,), '2011-12-23', '2016-01-22', 'nezavisni', 'Ministar hrvatskih branitelja iz Domovinskog rata'),
    (MINISTER, 'RADIMIR ČAČIĆ', (2011,), '2011-12-23', '2012-11-14', 'HNS', 'Ministar gospodarstva'),
    (MINISTER, 'RAJKO OSTOJIĆ', (2011,), '2011-12-23', '2014-06-11', 'SDP', 'Ministar zdravstva'),
    (MINISTER, 'RANKO OSTOJIĆ', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar unutarnjih poslova'),
    (MINISTER, 'SLAVKO LINIĆ', (2011,), '2011-12-23', '2014-05-06', 'SDP', 'Ministar financija'),
    (MINISTER, 'TIHOMIR JAKOVINA', (2011,), '2011-12-23', '2016-01-22', 'SDP', 'Ministar poljoprivrede'),
    (MINISTER, 'VELJKO OSTOJIĆ', (2011,), '2011-12-23', '2013-03-09', 'IDS', 'Ministar turizma'),
    (MINISTER, 'VESNA PUSIĆ', (2011,), '2011-12-23', '2016-01-22', 'HNS-LD', 'Ministrica vanjskih i europskih poslova'),
    (MINISTER, 'ZLATKO KOMADINA', (2011,), '2011-12-23', '2012-04-04', 'SDP', 'Ministar mora, prometa i infrastrukture'),
    (MINISTER, 'ŽELJKO JOVANOVIĆ', (2011,), '2011-12-23', '2014-06-11', 'SDP', 'Ministar znanosti, obrazovanja i športa'),
    # 2012
    (MINISTER, 'SINIŠA HAJDAŠ DONČIĆ', (2011,), '2012-04-18', '2016-01-22', 'SDP', 'Ministar mora, prometa i infrastrukture'),
    (MINISTER, 'MIHAEL ZMAJLOVIĆ', (2011,), '2012-06-13', '2016-01-22', 'SDP', 'Ministar zaštite okoliša i prirode'),
    (MINISTER, 'ANKA MRAK TARITAŠ', (2011,), '2012-11-16', '2016-01-22', 'HNS-LD', 'Ministrica graditeljstva i prostornoga uređenja'),
    (MINISTER, 'IVAN VRDOLJAK', (2011,), '2012-11-16', '2016-01-22', 'HNS-LD', 'Ministar gospodarstva'),
    # 2013
    (MINISTER, 'DARKO LORENCIN', (2011,), '2013-03-19', '2016-01-22', 'IDS-DDI', 'Ministar turizma'),
    # 2014
    (MINISTER, 'BORIS LALOVAC', (2011,), '2014-05-14', '2016-01-22', 'SDP', 'Ministar financija'),
    (MINISTER, 'SINIŠA VARGA', (2011,), '2014-06-11', '2016-01-22', 'SDP', 'Ministar zdravstva'),
    (MINISTER, 'VEDRAN MORNAR', (2011,), '2014-06-11', '2016-01-22', 'nezavisni', 'Ministar znanosti, obrazovanja i športa'),
    # 2015
    (MINISTER, 'BERISLAV ŠIPUŠ', (2011,), '2015-04-24', '2016-01-22', 'nezavisni', 'Ministar kulture'),
    # 2016
    (MINISTER, 'ANTE ŠPRLJE', (2015, 2016), '2016-01-22', '2017-04-27', 'nezavisni', 'Ministar pravosuđa'),
    (MINISTER, 'ANTON KLIMAN', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar turizma'),
    (MINISTER, 'BERNARDICA JURETIĆ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministrica socijalne politike i mladih'),
    (MINISTER, 'DARIO NAKIĆ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'DARKO HORVAT', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar poduzetništva i obrta'),
    (MINISTER, 'DAVOR ROMIĆ', (2015,), '2016-01-22', '2016-10-19', 'nezavisni', 'Ministar poljoprivrede'),
    (MINISTER, 'DUBRAVKA JURLINA ALIBEGOVIĆ', (2015,), '2016-01-22', '2016-10-19', 'nezavisni', 'Ministrica uprave'),
    (MINISTER, 'JOSIP BULJEVIĆ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'LOVRO KUŠČEVIĆ', (2015, 2016), '2016-01-22', '2017-06-09', 'HDZ', 'Ministar graditeljstva i prostornoga uređenja'),
    (MINISTER, 'MIJO CRNOJA', (2015,), '2016-01-22', '2016-01-28', 'HDZ', 'Ministar hrvatskih branitelja iz Domovinskog rata'),
    (MINISTER, 'MIRO KOVAČ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar vanjskih i europskih poslova'),
    (MINISTER, 'NADA ŠIKIĆ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministrica rada i mirovinskoga sustava'),
    (MINISTER, 'OLEG BUTKOVIĆ', (2015, 2016, 2020, 2024), '2016-01-22', None, 'HDZ', 'Ministar mora, prometa i infrastrukture'),
    (MINISTER, 'PREDRAG ŠUSTAR', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar znanosti, obrazovanja i športa'),
    (MINISTER, 'SLAVEN DOBROVIĆ', (2015, 2016), '2016-01-22', '2017-04-27', 'Most', 'Ministar zaštite okoliša i energetike'),
    (MINISTER, 'SLAVEN DOBROVIĆ', (2015,), '2016-01-22', '2016-10-19', 'MOST', 'Ministar zaštite okoliša i prirode'),
    (MINISTER, 'TOMISLAV PANENIĆ', (2015,), '2016-01-22', '2016-10-19', 'MOST', 'Ministar gospodarstva'),
    (MINISTER, 'TOMISLAV TOLUŠIĆ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar regionalnoga razvoja i fondova Europske unije'),
    (MINISTER, 'VLAHO OREPIĆ', (2015, 2016), '2016-01-22', '2017-04-27', 'Most', 'Ministar unutarnjih poslova'),
    (MINISTER, 'ZDRAVKO MARIĆ', (2015, 2016, 2020), '2016-01-22', '2022-07-15', 'nezavisni', 'Ministar financija'),
    (MINISTER, 'ZLATKO HASANBEGOVIĆ', (2015,), '2016-01-22', '2016-10-19', 'HDZ', 'Ministar kulture'),
    (MINISTER, 'TOMO MEDVED', (2015,), '2016-03-21', '2016-10-19', 'HDZ', 'Ministar hrvatskih branitelja iz Domovinskog rata'),
    (MINISTER, 'DAMIR KRSTIČEVIĆ', (2016,), '2016-10-19', '2020-07-23', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'DAVOR IVO STIER', (2016,), '2016-10-19', '2017-06-12', 'HDZ', 'Ministar vanjskih i europskih poslova'),
    (MINISTER, 'GABRIJELA ŽALAC', (2016,), '2016-10-19', '2019-07-17', 'HDZ', 'Ministrica regionalnoga razvoja i fondova Europske unije'),
    (MINISTER, 'GARI CAPPELLI', (2016,), '2016-10-19', '2020-07-23', 'HDZ', 'Ministar turizma'),
    (MINISTER, 'IVAN KOVAČIĆ', (2016,), '2016-10-19', '2017-04-28', 'Most', 'Ministar uprave'),
    (MINISTER, 'MARTINA DALIĆ', (2016,), '2016-10-19', '2018-05-14', 'HDZ', 'Ministrica gospodarstva, poduzetništva i obrta'),
    (MINISTER, 'MILAN KUJUNDŽIĆ', (2016,), '2016-10-19', '2020-01-28', 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'NADA MURGANIĆ', (2016,), '2016-10-19', '2019-07-17', 'HDZ', 'Ministrica za demografiju, obitelj, mlade i socijalnu politiku'),
    (MINISTER, 'NINA OBULJEN KORŽINEK', (2016,), '2016-10-19', '2020-07-23', 'HDZ', 'Ministrica kulture'),
    (MINISTER, 'PAVO BARIŠIĆ', (2016,), '2016-10-19', '2017-06-09', 'HDZ', 'Ministar znanosti i obrazovanja'),
    (MINISTER, 'TOMISLAV TOLUŠIĆ', (2016,), '2016-10-19', '2019-07-17', 'HDZ', 'Ministar poljoprivrede'),
    (MINISTER, 'TOMISLAV ĆORIĆ', (2016,), '2016-10-19', '2017-06-09', 'HDZ', 'Ministar rada i mirovinskoga sustava'),
    (MINISTER, 'TOMO MEDVED', (2016, 2020, 2024), '2016-10-19', None, 'HDZ', 'Ministar hrvatskih branitelja'),
    (MINISTER, 'GORAN MARIĆ [HR; PL; RU; UK]', (2016,), '2016-11-15', '2019-07-15', 'HDZ', 'Ministar državne imovine'),
    # 2017
    (MINISTER, 'BLAŽENKA DIVJAK', (2016,), '2017-06-09', '2020-07-23', 'nezavisni', 'Ministrica znanosti i obrazovanja'),
    (MINISTER, 'DAVOR BOŽINOVIĆ', (2016, 2020, 2024), '2017-06-09', None, 'HDZ', 'Ministar unutarnjih poslova'),
    (MINISTER, 'DRAŽEN BOŠNJAKOVIĆ', (2016,), '2017-06-09', '2020-07-23', 'HDZ', 'Ministar pravosuđa'),
    (MINISTER, 'LOVRO KUŠČEVIĆ', (2016,), '2017-06-09', '2019-07-08', 'HDZ', 'Ministar uprave'),
    (MINISTER, 'MARKO PAVIĆ', (2016,), '2017-06-09', '2019-07-17', 'HDZ', 'Ministar rada i mirovinskoga sustava'),
    (MINISTER, 'PREDRAG ŠTROMAR', (2016,), '2017-06-09', '2020-07-23', 'HNS', 'Ministar graditeljstva i prostornoga uređenja'),
    (MINISTER, 'TOMISLAV ĆORIĆ', (2016,), '2017-06-09', '2020-07-23', 'HDZ', 'Ministar zaštite okoliša i energetike'),
    (MINISTER, 'MARIJA PEJČINOVIĆ BURIĆ', (2016,), '2017-06-19', '2019-07-17', 'HDZ', 'Ministrica vanjskih i europskih poslova'),
    # 2018
    (MINISTER, 'DARKO HORVAT', (2016,), '2018-05-25', '2020-07-23', 'HDZ', 'Ministar gospodarstva, poduzetništva i obrta'),
    # 2019
    (MINISTER, 'GORDAN GRLIĆ RADMAN', (2016, 2020, 2024), '2019-07-22', None, 'HDZ', 'Ministar vanjskih i europskih poslova'),
    (MINISTER, 'IVAN MALENICA', (2016,), '2019-07-22', '2020-07-23', 'HDZ', 'Ministar uprave'),
    (MINISTER, 'JOSIP ALADROVIĆ', (2016,), '2019-07-22', '2020-07-23', 'HDZ', 'Ministar rada i mirovinskoga sustava'),
    (MINISTER, 'MARIJA VUČKOVIĆ', (2016, 2020, 2024), '2019-07-22', None, 'HDZ', 'Ministrica poljoprivrede'),
    (MINISTER, 'MARIO BANOŽIĆ', (2016,), '2019-07-22', '2020-07-23', 'HDZ', 'Ministar državne imovine'),
    (MINISTER, 'MARKO PAVIĆ', (2016,), '2019-07-22', '2020-07-23', 'HDZ', 'Ministar regionalnoga razvoja i fondova Europske unije'),
    (MINISTER, 'VESNA BEDEKOVIĆ', (2016,), '2019-07-22', '2020-07-23', 'HDZ', 'Ministrica za demografiju, obitelj, mlade i socijalnu politiku'),
    # 2020
    (MINISTER, 'VILI BEROŠ', (2016, 2020, 2024), '2020-01-31', None, 'HDZ', 'Ministar zdravstva'),
    (MINISTER, 'BORIS MILOŠEVIĆ', (2020,), '2020-07-23', '2022-04-29', 'SDSS', 'Ministar bez lisnice'),
    (MINISTER, 'DARKO HORVAT', (2020,), '2020-07-23', '2022-02-19', 'HDZ', 'Ministar prostornoga uređenja, graditeljstva i državne imovine'),
    (MINISTER, 'JOSIP ALADROVIĆ', (2020,), '2020-07-23', '2022-04-29', 'HDZ', 'Ministar rada, mirovinskoga sustava, obitelji i socijalne politike'),
    (MINISTER, 'MARIO BANOŽIĆ', (2020,), '2020-07-23', '2023-11-11', 'HDZ', 'Ministar obrane'),
    (MINISTER, 'NATAŠA TRAMIŠAK', (2020,), '2020-07-23', '2023-01-17', 'HDZ', 'Ministrica regionalnoga razvoja i fondova Europske unije'),
    (MINISTER, 'NIKOLINA BRNJAC', (2020, 2024), '2020-07-23', None, 'HDZ', 'Ministrica turizma i sporta'),
    (MINISTER, 'NINA OBULJEN KORŽINEK', (2020, 2024), '2020-07-23', None, 'HDZ', 'Ministrica kulture i medija'),
    (MINISTER, 'RADOVAN FUCHS', (2020, 2024), '2020-07-23', None, 'HDZ', 'Ministar znanosti i obrazovanja'),
    (MINISTER, 'TOMISLAV ĆORIĆ', (2020,), '2020-07-23', '2022-04-29', 'HDZ', 'Ministar gospodarstva i održivog razvoja'),
    (MINISTER, 'IVAN MALENICA', (2020, 2024), '2020-07-24', None, 'HDZ', 'Ministar pravosuđa i uprave'),
    # 2022
    (MINISTER, 'IVAN PALADINA', (2020,), '2022-02-19', '2023-01-17', 'nezavisni', 'Ministar prostornoga uređenja, graditeljstva i državne imovine'),
    (MINISTER, 'ANJA ŠIMPRAGA', (2020, 2024), '2022-04-29', None, 'SDSS', 'Ministrica bez lisnice'),
    (MINISTER, 'DAVOR FILIPOVIĆ', (2020,), '2022-04-29', '2023-12-12', 'HDZ', 'Ministar gospodarstva i održivog razvoja'),
    (MINISTER, 'MARIN PILETIĆ', (2020, 2024), '2022-04-29', None, 'HDZ', 'Ministar rada, mirovinskoga sustava, obitelji i socijalne politike'),
    (MINISTER, 'MARKO PRIMORAC', (2020, 2024), '2022-07-15', None, 'nezavisni', 'Ministar financija'),
    # 2023
    (MINISTER, 'BRANKO BAČIĆ', (2020, 2024), '2023-01-17', None, 'HDZ', 'Ministar prostornoga uređenja, graditeljstva i državne imovine'),
    (MINISTER, 'ŠIME ERLIĆ', (2020, 2024), '2023-01-17', None, 'HDZ', 'Ministar regionalnoga razvoja i fondova Europske unije'),
    (MINISTER, 'IVAN ANUŠIĆ', (2020, 2024), '2023-11-16', None, 'HDZ', 'Ministar obrane'),
    (MINISTER, 'DAMIR HABIJAN', (2020, 2024), '2023-12-20', None, 'HDZ', 'Ministar gospodarstva i održivog razvoja'),
    # 2024
    (MINISTER, 'ANTE ŠUŠNJAR', (2024,), '2024-05-17', None, 'DP', 'Ministar gospodarstva'),
    (MINISTER, 'DAMIR HABIJAN', (2024,), '2024-05-17', None, 'HDZ', 'Ministar pravosuđa, uprave i digitalne transformacije'),
    (MINISTER, 'IVAN ŠIPIĆ', (2024,), '2024-05-17', None, 'DP', 'Ministar demografije i useljeništva'),
    (MINISTER, 'JOSIP DABRO', (2024,), '2024-05-17', '2025-01-18', 'DP', 'Ministar poljoprivrede, šumarstva i ribarstva'),
    (MINISTER, 'MARIJA VUČKOVIĆ', (2024,), '2024-05-17', None, 'HDZ', 'Ministrica zaštite okoliša i zelene tranzicije'),
    (MINISTER, 'RADOVAN FUCHS', (2024,), '2024-05-17', None, 'HDZ', 'Ministar znanosti, obrazovanja i mladih'),
    (MINISTER, 'TONČI GLAVINA', (2024,), '2024-05-17', None, 'HDZ', 'Ministar turizma i sporta'),
    (MINISTER, 'IRENA HRSTIĆ', (2024,), '2024-12-06', None, 'HDZ', 'Ministrica zdravstva'),
    # 2025
    (MINISTER, 'DAVID VLAJČIĆ', (2024,), '2025-02-11', None, 'DP', 'Ministar poljoprivrede, šumarstva i ribarstva'),
    (MINISTER, 'NATAŠA MIKUŠ ŽIGMAN', (2024,), '2025-07-15', None, 'HDZ', 'Ministrica regionalnoga razvoja i fondova Europske unije'),
    # 2026
    (MINISTER, 'TOMISLAV ĆORIĆ', (2024,), '2026-01-29', None, 'HDZ', 'Ministar financija'),
    (MINISTER, 'ALEN RUŽIĆ [HR]', (2024,), '2026-02-20', None, 'HDZ', 'Ministar rada, mirovinskoga sustava, obitelji i socijalne politike'),

    # --- Predsjednik Sabora ------------------------------------------------
    (SPEAKER, 'ŽARKO DOMLJAN', (1990,), '1990-05-30', '1992-09-07', 'HDZ'),
    (SPEAKER, 'STJEPAN MESIĆ', (1992,), '1992-09-07', '1994-05-24', 'HDZ'),
    (SPEAKER, 'NEDJELJKO MIHANOVIĆ', (1992,), '1994-05-24', '1995-11-28', 'HDZ'),
    (SPEAKER, 'VLATKO PAVLETIĆ', (1995,), '1995-11-28', '2000-02-02', 'HDZ'),
    (SPEAKER, 'ZLATKO TOMČIĆ', (2000,), '2000-02-02', '2003-12-22', 'HSS'),
    (SPEAKER, 'VLADIMIR ŠEKS', (2003,), '2003-12-22', '2008-01-11', 'HDZ'),
    (SPEAKER, 'LUKA BEBIĆ', (2007,), '2008-01-11', '2011-12-22', 'HDZ'),
    (SPEAKER, 'BORIS ŠPREM', (2011,), '2011-12-22', '2012-09-30', 'SDP'),  # died in office
    # Acting from Šprem's death (30 Sep 2012), elected 10 Oct 2012.
    (SPEAKER, 'JOSIP LEKO', (2011,), '2012-10-10', '2015-12-28', 'SDP'),
    (SPEAKER, 'ŽELJKO REINER', (2015,), '2015-12-28', '2016-10-14', 'HDZ'),
    (SPEAKER, 'BOŽO PETROV', (2016,), '2016-10-14', '2017-05-05', 'Most'),
    (SPEAKER, 'GORDAN JANDROKOVIĆ', (2016, 2020, 2024), '2017-05-05', None, 'HDZ'),

    # --- Potpredsjednici Sabora --------------------------------------------
    # 2000-2003 (4. saziv)
    (DEPUTY, 'MATO ARLOVIĆ', (2000,), None, None, 'SDP'),
    (DEPUTY, 'BALTAZAR JALŠOVEC', (2000,), None, None, 'LIBRA'),
    (DEPUTY, 'IVICA KOSTOVIĆ', (2000,), None, None, 'HDZ'),
    (DEPUTY, 'VLATKO PAVLETIĆ', (2000,), None, None, 'HDZ'),
    (DEPUTY, 'ZDRAVKO TOMAC', (2000,), None, None, 'SDP'),
    # 2003-2007 (5. saziv)
    (DEPUTY, 'LUKA BEBIĆ', (2003,), None, None, 'HDZ'),
    (DEPUTY, 'DARKO MILINOVIĆ', (2003,), None, None, 'HDZ'),
    (DEPUTY, 'ĐURĐA ADLEŠIĆ', (2003,), None, None, 'HSLS'),
    (DEPUTY, 'MATO ARLOVIĆ', (2003,), None, None, 'SDP'),
    (DEPUTY, 'VESNA PUSIĆ', (2003,), None, None, 'HNS'),
    # 2008-2011 (6. saziv)
    (DEPUTY, 'VLADIMIR ŠEKS', (2007,), None, None, 'HDZ'),
    (DEPUTY, 'IVAN JARNJAK', (2007,), None, None, 'HDZ'),
    (DEPUTY, 'JOSIP FRIŠČIĆ', (2007,), None, None, 'HSS'),
    (DEPUTY, 'ŽELJKA ANTUNOVIĆ', (2007,), None, None, 'SDP'),
    (DEPUTY, 'NEVEN MIMICA', (2007,), None, None, 'SDP'),
    # 2011-2015 (7. saziv). HDZ replaced Kosor and Šeks with Čuljak and
    # Reiner on 12 Jun 2012; Zgrebec took Leko's place when he became Speaker.
    (DEPUTY, 'JOSIP LEKO', (2011,), '2011-12-22', '2012-10-10', 'SDP'),
    (DEPUTY, 'JADRANKA KOSOR', (2011,), '2011-12-22', '2012-06-12', 'HDZ'),
    (DEPUTY, 'VLADIMIR ŠEKS', (2011,), '2011-12-22', '2012-06-12', 'HDZ'),
    (DEPUTY, 'NENAD STAZIĆ', (2011,), None, None, 'SDP'),
    (DEPUTY, 'MILORAD BATINIĆ', (2011,), None, None, 'SDP'),
    (DEPUTY, 'TOMISLAV ČULJAK', (2011,), '2012-06-12', None, 'HDZ'),
    (DEPUTY, 'ŽELJKO REINER', (2011,), '2012-06-12', None, 'HDZ'),
    (DEPUTY, 'DRAGICA ZGREBEC', (2011,), None, None, 'SDP'),
    # 2015-2016 (8. saziv)
    (DEPUTY, 'ANTE SANADER', (2015,), None, None, 'HDZ'),
    (DEPUTY, 'ROBERT PODOLNJAK', (2015,), None, None, 'Most'),
    (DEPUTY, 'IVAN TEPEŠ', (2015,), None, None, 'HSP AS'),
    (DEPUTY, 'MILANKA OPAČIĆ', (2015,), '2016-02-03', None, 'SDP'),
    (DEPUTY, 'VESNA PUSIĆ', (2015,), '2016-02-03', None, 'HNS'),
    # 2016-2020 (9. saziv)
    (DEPUTY, 'GORDAN JANDROKOVIĆ', (2016,), '2016-10-14', '2017-05-05', 'HDZ'),
    (DEPUTY, 'MILIJAN BRKIĆ', (2016,), None, None, 'HDZ'),
    (DEPUTY, 'ŽELJKO REINER', (2016,), None, None, 'HDZ'),
    (DEPUTY, 'MILANKA OPAČIĆ', (2016,), None, None, 'SDP'),
    (DEPUTY, 'IVAN VRDOLJAK', (2016,), None, '2017-06-09', 'HNS'),
    (DEPUTY, 'FURIO RADIN', (2016,), '2017-06-19', None, 'nacionalne manjine'),
    # 2020-2024 (10. saziv)
    (DEPUTY, 'ŽELJKO REINER', (2020,), None, None, 'HDZ'),
    (DEPUTY, 'ANTE SANADER', (2020,), None, None, 'HDZ'),
    (DEPUTY, 'FURIO RADIN', (2020,), None, None, 'nacionalne manjine'),
    (DEPUTY, 'SABINA GLASOVAC', (2020,), None, None, 'SDP'),
    (DEPUTY, 'DAVORKO VIDOVIĆ', (2020,), None, None, 'SD'),
    # 2024- (11. saziv), elected at the constituent session of 16 May 2024
    (DEPUTY, 'ŽELJKO REINER', (2024,), '2024-05-16', None, 'HDZ'),
    (DEPUTY, 'IVAN PENAVA', (2024,), '2024-05-16', None, 'DP'),
    (DEPUTY, 'FURIO RADIN', (2024,), '2024-05-16', None, 'nacionalne manjine'),
    (DEPUTY, 'SABINA GLASOVAC', (2024,), '2024-05-24', None, 'SDP'),

    # --- Tajnik Sabora -----------------------------------------------------
    # A civil-service post, not an elected member: shows only if the holder
    # is also in the election data, which the one known so far is not.
    (SECRETARY, 'JOSIP SESAR', (2003, 2007), None, None, ''),
]
