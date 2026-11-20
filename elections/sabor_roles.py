"""Key offices held during each Sabor saziv: the Prime Minister (predsjednik
Vlade), the Speaker (predsjednik Sabora), the deputy speakers
(potpredsjednici) and the Secretary (tajnik Sabora).

Pure data, no Django imports, so app.py can read it. None of this comes from
an election result: the Sabor elects its presidency and confirms the
government after it is constituted, so these are curated like the rosters in
`set_sabor_members`, with the source inline.

Each entry is (role, name, sazivi, start, end, party):
  role   'pm' | 'speaker' | 'deputy' | 'secretary'
  name   as in Person.normalized_name before diacritics are stripped (the app
         normalises it); a namesake row (Person.disambiguation set) never
         matches, only the unlabelled row
  sazivi the Sabor election year(s) whose term the office fell in. 1990 means
         the 1990-1992 Sabor, whose three chambers (DPV, Vijeće općina, Vijeće
         udruženog rada) are each their own election type here
  start, end  ISO dates, or None where the source gives none (end None with a
         start = still in office)

A role shows as a badge on the person's Sabor result(s) of that saziv and in
their offices card. A holder with no Person row (never a candidate) simply
does not show: Zlatko Mateša, Josip Sesar.

Sources: en.wikipedia "List of prime ministers of Croatia", "Speaker of the
Croatian Parliament" and "List of members of the Sabor, <years>" (presidency
sections); 2024 deputies from the constituent session reports (16 May 2024)
and sabor.hr. Deputy speakers before 2000 are not yet transcribed.
"""

PM, SPEAKER, DEPUTY, SECRETARY = 'pm', 'speaker', 'deputy', 'secretary'

ROLE_TITLES = {
    PM: 'Predsjednik Vlade',
    SPEAKER: 'Predsjednik Sabora',
    DEPUTY: 'Potpredsjednik Sabora',
    SECRETARY: 'Tajnik Sabora',
}
# Display order, most senior first: a person with several roles in one saziv
# (Jandroković 2016: deputy, then speaker) is coloured by the first.
ROLE_ORDER = [PM, SPEAKER, DEPUTY, SECRETARY]

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
