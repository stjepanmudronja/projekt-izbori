from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Value
from django.db.models.functions import Replace

from elections.importers.name_utils import (
    normalize_person_name, parse_person_name,
)
from elections.management.commands.merge_person_aliases import KNOWN_ALIASES
from elections.models import (
    ElectionType, Election, ElectionRound, ElectoralDistrict, ElectoralList,
    Candidacy, Person, ParliamentMember,
)

# Seats per district-XII sub-district (one minority group each), 8 in total.
MINORITY_SEATS = {121: 3, 122: 1, 123: 1, 124: 1, 125: 1, 126: 1}

# Rosters of the Sabor convocation elected in each year, curated by hand.
#
# Why this can't be computed: preferential voting only arrived in 2015, so for
# 2007 and 2011 DIP published list totals and no candidate names at all for
# districts I-XI (only district XII names individuals). The D'Hondt allocation
# in app.py can therefore say a list won N seats but not who filled them.
# The roster also carries mid-term replacements, who are not part of any
# election-day result to begin with.
#
# Each entry is (full name, party label, elected in district XII, note).
# The name is uppercase with diacritics — normalize_person_name() maps it to
# the Person.normalized_name key. The party label is the caucus as published,
# which for a coalition year is the member's own party, not the joint list
# name they were elected on (e.g. the SDP-HNS-IDS-HSU "Kukuriku" list).
MEMBERS_BY_YEAR = {
    # 5. saziv (2003-2007), constituted 22 Dec 2003 and dissolved 12 Oct 2007.
    # 152 members for the 152 seats of that Sabor — 2003 is the year the
    # diaspora returned 4 (see DIASPORA_SEATS_BY_YEAR in app.py).
    #
    # `party` is blank throughout: the published roster of this saziv lists
    # names only. The party breakdown that accompanies it (HDZ 63, SDP 30, …)
    # describes the Sabor *at dissolution* in 2007, after four years of
    # switches and by-elections, so attaching it to the members elected in
    # 2003 would be wrong. Fill it in only from a source that gives the
    # affiliation per person at election time.
    # 5. saziv (2003-2007), constituted 22 Dec 2003 and dissolved 12 Oct 2007,
    # **as elected** — the members who took the 152 seats at the election, not
    # everyone who sat during the term.
    #
    # Entries here are 5-tuples: unlike 2007 and 2011, whose published rosters
    # are a single national roll, the 2003 result is published per electoral
    # district, so each member carries the district and the list they were
    # elected on. The party string is that list's full name, coalition members
    # included, which is what the "Stranka / Koalicija" column means and what
    # the hemicycle legend shows for the same year.
    #
    # Cross-checked against the D'Hondt allocation computed from the imported
    # votes: the seats per list per district agree exactly, all eleven
    # districts, and the national vote shares match the published ones to
    # the decimal. District III's four HDZ members were missing from the
    # first transcription — the source loses that block mid-name — and the
    # allocation is what identified the gap as HDZ and as exactly four
    # before the names were supplied. All 152 are now recorded.
    2003: [
        ('IVICA RAČAN', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, 'umro', 1),
        ('ANTUN VUJIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 1),
        ('MIRKO FILIPOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 1),
        ('IVO JOSIPOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 1),
        ('VICE VUKOV', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 1),
        ('JELENA PAVIČIĆ VUKIČEVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 1),
        ('JADRANKA KOSOR', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 1),
        ('BOŽO BIŠKUPIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 1),
        ('MARKO TURIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 1),
        ('PETAR SELEM', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 1),
        ('FRANJO ARAPOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 1),
        ('VESNA PUSIĆ', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 1),
        ('SREĆKO FERENČAK', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 1),
        ('SLAVEN LETICA', 'HRVATSKA STRANKA PRAVA - HSP, ZAGORSKA DEMOKRATSKA STRANKA - ZDS', False, '', 1),
        ('ANDRIJA HEBRANG', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 2),
        ('GORDAN JANDROKOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 2),
        ('IVANA SUČEC-TRAKOŠTANEC', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 2),
        ('STJEPAN BAČIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 2),
        ('DAMIR SESVEČAN', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 2),
        ('KARMELA CAPARIN', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 2),
        ('MILAN BANDIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 2),
        ('ZVONIMIR MRŠIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 2),
        ('JOZO RADOŠ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 2),
        ('IVICA PANČIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 2),
        ('ZLATKO TOMČIĆ', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 2),
        ('JOSIP FRIŠČIĆ', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 2),
        ('PERO KOVAČEVIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 2),
        ('ĐURĐA ADLEŠIČ', 'HRVATSKA SOCIJALNO LIBERALNA STRANKA - HSLS', False, '', 2),
        ('IVAN JARNJAK', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 3),
        ('VLADIMIR KUREČIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 3),
        ('VELIMIR PLEŠA', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 3),
        ('MARIJAN MLINARIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 3),
        ('TONINO PICULA', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 3),
        ('DRAGICA ZGREBEC', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 3),
        ('MIROSLAV KORENIKA', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 3),
        ('ŽELJKO PAVLIC', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 3),
        ('RADIMIR ČAČIĆ', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 3),
        ('DRAGUTIN LESAR', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 3),
        ('ZVONIMIR SABATI', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 3),
        ('JOSIP SUDEC', 'HRVATSKA STRANKA UMIROVLJENIKA - HSU', False, '', 3),
        ('IVAN ČEHOK', 'HRVATSKA SOCIJALNO LIBERALNA STRANKA - HSLS, DEMOKRATSKI CENTAR - DC', False, '', 3),
        ('IVO LONČAR', 'HRVATSKA DEMOKRATSKA SELJAČKA STRANKA - HDSS', False, '', 3),
        ('VLADIMIR ŠEKS', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('BRANIMIR GLAVAŠ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('MATO ŠTIMAC', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('IVICA BUCONJIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('VLADIMIR ŠIŠLJAGIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('IVAN DRMIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('JOSIP ĐAKIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 4),
        ('ŽELJKA ANTUNOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 4),
        ('ZLATKO KRAMARIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 4),
        ('VILIM HERMAN', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA', False, '', 4),
        ('ANTO ĐAPIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 4),
        ('ŽELJKO PECEK', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 4),
        ('ANTUN KAPRALJEVIĆ', 'HRVATSKA NARODNA STRANKA - HNS, SLAVONSKO-BARANJSKA HRVATSKA STRANKA - SBHS', False, '', 4),
        ('DRAGUTIN PUKLEŠ', 'HRVATSKA STRANKA UMIROVLJENIKA - HSU', False, '', 4),
        ('PETAR ČOBANKOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('ANTO BAGARIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('ZDRAVKO SOČKOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('TOMISLAV ČULJAK', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('MARIJA BAJT', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('DRAGO PRGOMET', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('PETAR MLINARIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('IVICA KLEM', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 5),
        ('MATO ARLOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 5),
        ('MATO GAVRAN', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 5),
        ('LJUBICA BRDARIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 5),
        ('VLADO JUKIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 5),
        ('LJUBICA LALIĆ', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 5),
        ('VESNA ŠKARE-OŽBOLT', 'HRVATSKA SOCIJALNO LIBERALNA STRANKA - HSLS, DEMOKRATSKI CENTAR - DC', False, '', 5),
        ('IVAN ŠUKER', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 6),
        ('ĐURO BRODARAC', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 6),
        ('STJEPAN FIOLIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 6),
        ('MARIO ZUBOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 6),
        ('ŽELJKO NENADIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 6),
        ('DRAŽEN BOŠNJAKOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 6),
        ('DAVORKO VIDOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBERALNA STRANKA - LS', False, '', 6),
        ('IVO BANAC', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBERALNA STRANKA - LS', False, '', 6),
        ('JOSIP LEKO', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBERALNA STRANKA - LS', False, '', 6),
        ('SNJEŽANA BIGA-FRIGANOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBERALNA STRANKA - LS', False, '', 6),
        ('LJUBO JURČIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBERALNA STRANKA - LS', False, '', 6),
        ('VELIMIR KVESIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 6),
        ('ALENKA KOŠIŠA ČIČIN-ŠAIN', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 6),
        ('ŽELJKO LEDINSKI', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 6),
        ('MIOMIR ŽUŽUL', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('BRANKO VUKELIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('BRANIMIR PASECKY', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('KOLINDA GRABAR-KITAROVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('IVAN VUČIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('NEVEN JURICA', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('KRUNOSLAV MLINARIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 7),
        ('MATO CRKVENAC', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 7),
        ('MILANKA OPAČIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 7),
        ('VESNA ŠKULIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 7),
        ('NENAD STAZIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 7),
        ('MIROSLAV ROŽIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 7),
        ('DARKO ŠANTIĆ', 'HRVATSKA NARODNA STRANKA - HNS, PRIMORSKO GORANSKI SAVEZ - PGS', False, '', 7),
        ('BOŽIDAR PANKRETIĆ', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 7),
        ('DAMIR KAJIN', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('GORDANA SOBOL', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('VALTER DRANDIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('BISERKA PERMAN', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('IVAN JAKOVČIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('ANTON PERUŠKO', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('DOROTEA PEŠIĆ-BUKOVAC', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('ZDENKO ANTEŠIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, ISTARSKI DEMOKRATSKI SABOR - IDS', False, '', 8),
        ('LINO ČERVAR', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 8),
        ('VLADIMIR VRANKOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 8),
        ('NEVIO ŠETIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 8),
        ('MILJENKO DORIĆ', 'HRVATSKA NARODNA STRANKA - HNS, PRIMORSKO GORANSKI SAVEZ - PGS', False, '', 8),
        ('NIKOLA IVANIŠ', 'HRVATSKA NARODNA STRANKA - HNS, PRIMORSKO GORANSKI SAVEZ - PGS', False, '', 8),
        ('SILVANO HRELJA', 'HRVATSKA STRANKA UMIROVLJENIKA - HSU', False, '', 8),
        ('BOŽIDAR KALMETA', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('DARKO MILINOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('PERICA BUKIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('JURE BITUNJAC', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('ŠIME PRTENJAČA', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('JOZO TOPIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('EMIL TOMLJANOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('ANA LOVRIN', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('NIKO REBIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 9),
        ('ŠIME LUČIN', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 9),
        ('INGRID ANTIČEVIĆ-MARINOVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP', False, '', 9),
        ('IVICA MAŠTRUKO', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 9),
        ('TONČI TADIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 9),
        ('ANTE MARKOV', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 9),
        ('IVO SANADER', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('ŽIVKO NENADIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('LUKA BEBIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('DUBRAVKA ŠUICA', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('ZVONIMIR PULJIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('DUJOMIR MARASOVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('BRANKO BAČIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 10),
        ('SLAVKO LINIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA, LIBERALNA STRANKA - LS', False, '', 10),
        ('MARIN JURJEVIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA, LIBERALNA STRANKA - LS', False, '', 10),
        ('NEVEN MIMICA', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA, LIBERALNA STRANKA - LS', False, '', 10),
        ('JAGODA MARTIĆ', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP, LIBRA-STRANKA LIBERALNIH DEMOKRATA - LIBRA, LIBERALNA STRANKA - LS', False, '', 10),
        ('JAKŠA MARASOVIĆ', 'HRVATSKA NARODNA STRANKA - HNS', False, '', 10),
        ('RUŽA TOMAŠIĆ', 'HRVATSKA STRANKA PRAVA - HSP', False, '', 10),
        ('LUKA ROIĆ', 'HRVATSKA SELJAČKA STRANKA - HSS', False, '', 10),
        ('ZDENKA BABIĆ PETRIČEVIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 11),
        ('FLORIJAN BORAS', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 11),
        ('KREŠIMIR ĆOSIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 11),
        ('IVAN BAGARIĆ', 'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', False, '', 11),
        ('VOJISLAV STANIMIROVIĆ', 'SAMOSTALNA DEMOKRATSKA SRPSKA STRANKA - SDSS', True, '', 121),
        ('MILORAD PUPOVAC', 'SAMOSTALNA DEMOKRATSKA SRPSKA STRANKA - SDSS', True, '', 121),
        ('RATKO GAJICA', 'SAMOSTALNA DEMOKRATSKA SRPSKA STRANKA - SDSS', True, '', 121),
        ('JENE ADAM', 'DEMOKRATSKA ZAJEDNICA MAĐARA HRVATSKE - DZMH', True, '', 122),
        ('FURIO RADIN', 'NEZAVISNI', True, '', 123),
        ('ZDENKA ČUHNIL', 'HRVATSKA SELJAČKA STRANKA - HSS', True, '', 124),
        ('NIKOLA MAK', 'NJEMAČKA NARODNOSNA ZAJEDNICA - ZEMALJSKA UDRUGA PODUNAVSKIH ŠVABA U HRVATSKOJ-OSIJEK', True, '', 125),
        ('ŠEMSO TANKOVIĆ', 'STRANKA DEMOKRATSKE AKCIJE HRVATSKE - SDA HRVATSKE', True, '', 126),
    ],
    # 6. saziv (2008-2011), constituted 11 Jan 2008 and dissolved 28 Oct 2011.
    # 153 members for the 153 seats of that Sabor — 2007 is the one year the
    # diaspora returned 5 rather than 3 (see DIASPORA_SEATS_BY_YEAR in app.py).
    # The listing carries no mid-term changes, so it is already an as-elected
    # roster and needs no substitution bookkeeping, unlike 2011.
    #
    # Two district-XII members are not tagged "nacionalne manjine" in the
    # source listing but plainly are, and the vote check below agrees: Ratko
    # Gajica took the third Srpska seat (9683) and Zdenka Čuhnil the Češka i
    # slovačka one (684, by three votes over Vladimir Bilek). Tagged here so
    # all 8 minority seats are accounted for.
    #
    # The source's own party tally says SDP 56 / nezavisni 5; the names it
    # lists give SDP 55 / nezavisni 6. Kept as listed per person — the extra
    # independent is Ivo Josipović, elected on the SDP list without being a
    # party member, whom that tally evidently counts as SDP.
    2007: [
        ('IVO ANDRIĆ', 'HDZ', False, ''),
        ('INGRID ANTIČEVIĆ MARINOVIĆ', 'SDP', False, ''),
        ('ŽELJKA ANTUNOVIĆ', 'SDP', False, ''),
        ('IVAN BAGARIĆ', 'HDZ', False, ''),
        ('ARSEN BAUK', 'SDP', False, ''),
        ('LUKA BEBIĆ', 'HDZ', False, ''),
        ('DAVOR BERNARDIĆ', 'SDP', False, ''),
        ('GORAN BEUS RICHEMBERGH', 'HNS', False, ''),
        ('SUZANA BILIĆ VARDIĆ', 'HDZ', False, ''),
        ('MATO BILONJIĆ', 'HDZ', False, ''),
        ('DRAGUTIN BODAKOŠ', 'SDP', False, ''),
        ('BILJANA BORZAN', 'SDP', False, ''),
        ('RADE BOŠNJAK', 'HDZ', False, ''),
        ('DRAŽEN BOŠNJAKOVIĆ', 'HDZ', False, ''),
        ('MARIN BRKARIĆ', 'IDS', False, ''),
        ('PERICA BUKIĆ', 'HDZ', False, ''),
        ('KARMELA CAPARIN', 'HDZ', False, ''),
        ('GARI CAPPELLI', 'HDZ', False, ''),
        ('BRANKICA CRLJENKO', 'SDP', False, ''),
        ('MIROSLAV ČAČIJA', 'HSS', False, ''),
        ('NADA ČAVLOVIĆ SMILJANEC', 'SDP', False, ''),
        ('IVAN ČEHOK', 'HSLS', False, ''),
        ('ZDENKA ČUHNIL', 'nezavisna', True, ''),
        ('TOMISLAV ČULJAK', 'HDZ', False, ''),
        ('KREŠIMIR ĆOSIĆ', 'HDZ', False, ''),
        ('LUKA DENONA', 'SDP', False, ''),
        ('MILJENKO DORIĆ', 'HNS', False, ''),
        ('IGOR DRAGOVAN', 'SDP', False, ''),
        ('JOSIP ĐAKIĆ', 'HDZ', False, ''),
        ('ANTO ĐAPIĆ', 'HSP', False, ''),
        ('ŠIMO ĐURĐEVIĆ', 'HDZ', False, ''),
        ('MIRJANA FERIĆ-VAC', 'SDP', False, ''),
        ('KREŠO FILIPOVIĆ', 'HDZ', False, ''),
        ('STJEPAN FIOLIĆ', 'HDZ', False, ''),
        ('GVOZDEN SREĆKO FLEGO', 'SDP', False, ''),
        ('ZDENKO FRANIĆ', 'SDP', False, ''),
        ('JOSIP FRIŠČIĆ', 'HSS', False, ''),
        ('STIPO GABRIĆ', 'HSS', False, ''),
        ('RATKO GAJICA', 'SDSS', True, ''),
        ('BRANIMIR GLAVAŠ', 'HDSSB', False, ''),
        ('IVO GRBIĆ', 'HDZ', False, ''),
        ('BRANKO GRČIĆ', 'SDP', False, ''),
        ('BORO GRUBIŠIĆ', 'HDSSB', False, ''),
        ('KREŠIMIR GULIĆ', 'HDZ', False, ''),
        ('MARIO HABEK', 'SDP', False, ''),
        ('IVAN HANŽEK', 'SDP', False, ''),
        ('ANDRIJA HEBRANG', 'HDZ', False, ''),
        ('GORAN HEFFER', 'SDP', False, ''),
        ('BOJAN HLAČA', 'HDZ', False, ''),
        ('MIRELA HOLY', 'SDP', False, ''),
        ('ZLATKO HORVAT', 'HNS', False, ''),
        ('SILVANO HRELJA', 'HSU', False, ''),
        ('DANICA HURSA', 'HNS', False, ''),
        ('DAVOR HUŠKA', 'HDZ', False, ''),
        ('TOMISLAV IVIĆ', 'HDZ', False, ''),
        ('VLADIMIR IVKOVIĆ', 'HDZ', False, ''),
        ('IVAN JARNJAK', 'HDZ', False, ''),
        ('NADICA JELAŠ', 'SDP', False, ''),
        ('ROMANA JERKOVIĆ', 'SDP', False, ''),
        ('IVO JOSIPOVIĆ', 'nezavisni', False, ''),
        ('ŽELJKO JOVANOVIĆ', 'SDP', False, ''),
        ('LJUBO JURČIĆ', 'SDP', False, ''),
        ('MARIN JURJEVIĆ', 'SDP', False, ''),
        ('DAMIR KAJIN', 'IDS', False, ''),
        ('ŽELJANA KALAŠ', 'HDZ', False, ''),
        ('ZDRAVKO KELIĆ', 'HSS', False, ''),
        ('NEDJELJKA KLARIĆ', 'HDZ', False, ''),
        ('ZLATKO KORAČEVIĆ', 'HNS', False, ''),
        ('ANTUN KORUŠEC', 'HSLS', False, ''),
        ('ANTE KOTROMANOVIĆ', 'SDP', False, ''),
        ('DRAGO KOVAČEVIĆ', 'HDZ', False, ''),
        ('DINO KOZLEVAC', 'SDP', False, ''),
        ('ANTE KULUŠIĆ', 'HDZ', False, ''),
        ('BORIS KUNST', 'HDZ', False, ''),
        ('BRUNO KURELIĆ', 'SDP', False, ''),
        ('BRANKO KUTIJA', 'HDZ', False, ''),
        ('JOSIP LEKO', 'SDP', False, ''),
        ('DRAGUTIN LESAR', 'nezavisni', False, ''),
        ('SLAVKO LINIĆ', 'SDP', False, ''),
        ('FRANJO LUCIĆ', 'HDZ', False, ''),
        ('ŠIME LUČIN', 'SDP', False, ''),
        ('MARIJA LUGARIĆ', 'SDP', False, ''),
        ('LJUBICA LUKAČIĆ', 'HDZ', False, ''),
        ('NEVENKA MAJDENIĆ', 'HDZ', False, ''),
        ('ANTON MANCE', 'HDZ', False, ''),
        ('GORDAN MARAS', 'SDP', False, ''),
        ('GORAN MARIĆ', 'HDZ', False, ''),
        ('NEVENKA MARINOVIĆ', 'HDZ', False, ''),
        ('KRUNOSLAV MARKOVINOVIĆ', 'HDZ', False, ''),
        ('BORISLAV MATKOVIĆ', 'HDZ', False, ''),
        ('FRANO MATUŠIĆ', 'HDZ', False, ''),
        ('NAZIF MEMEDI', 'nezavisni', True, ''),
        ('ANĐELKO MIHALIĆ', 'HDZ', False, ''),
        ('ZORAN MILANOVIĆ', 'SDP', False, ''),
        ('BORIS MILETIĆ', 'IDS', False, ''),
        ('STJEPAN MILINKOVIĆ', 'HDZ', False, ''),
        ('NEVEN MIMICA', 'SDP', False, ''),
        ('PETAR MLINARIĆ', 'HDZ', False, ''),
        ('DANIEL MONDEKAR', 'SDP', False, ''),
        ('MIRANDO MRSIĆ', 'SDP', False, ''),
        ('ZVONIMIR MRŠIĆ', 'SDP', False, ''),
        ('ŽIVKO NENADIĆ', 'HDZ', False, ''),
        ('MILANKA OPAČIĆ', 'SDP', False, ''),
        ('RAJKO OSTOJIĆ', 'SDP', False, ''),
        ('RANKO OSTOJIĆ', 'SDP', False, ''),
        ('IVICA PANČIĆ', 'SDP', False, ''),
        ('BOŽIDAR PANKRETIĆ', 'HSS', False, ''),
        ('MARIJA PEJČINOVIĆ BURIĆ', 'HDZ', False, ''),
        ('MARIJANA PETIR', 'HSS', False, ''),
        ('TONINO PICULA', 'SDP', False, ''),
        ('VLATKO PODNAR', 'SDP', False, ''),
        ('ZVONIMIR PULJIĆ', 'HDZ', False, ''),
        ('MILORAD PUPOVAC', 'SDSS', True, ''),
        ('VESNA PUSIĆ', 'HNS', False, ''),
        ('FURIO RADIN', 'nezavisni', True, ''),
        ('NIKO REBIĆ', 'HDZ', False, ''),
        ('IVANKA ROKSANDIĆ', 'HDZ', False, ''),
        ('ZDRAVKO RONKO', 'SDP', False, ''),
        ('JERKO ROŠIN', 'HDZ', False, ''),
        ('VEDRAN ROŽIĆ', 'HDZ', False, ''),
        ('PETAR SELEM', 'HDZ', False, ''),
        ('DAMIR SESVEČAN', 'HDZ', False, ''),
        ('GORDANA SOBOL', 'SDP', False, ''),
        ('VOJISLAV STANIMIROVIĆ', 'SDSS', True, ''),
        ('NENAD STAZIĆ', 'SDP', False, ''),
        ('NEDJELJKO STRIKIĆ', 'HDZ', False, ''),
        ('IVAN ŠANTEK', 'HDZ', False, ''),
        ('VLADIMIR ŠEKS', 'HDZ', False, ''),
        ('NEVIO ŠETIĆ', 'HDZ', False, ''),
        ('TATJANA ŠIMAC-BONAČIĆ', 'SDP', False, ''),
        ('SONJA ŠIMUNOVIĆ', 'SDP', False, ''),
        ('VLADIMIR ŠIŠLJAGIĆ', 'HDSSB', False, ''),
        ('MIROSLAV ŠKORO', 'HDZ', False, ''),
        ('VESNA ŠKULIĆ', 'SDP', False, ''),
        ('MILIVOJ ŠKVORC', 'HDZ', False, ''),
        ('DENEŠ ŠOJA', 'nezavisni', True, ''),
        ('BOŽICA ŠOLIĆ', 'HDZ', False, ''),
        ('BORIS ŠPREM', 'SDP', False, ''),
        ('DUBRAVKA ŠUICA', 'HDZ', False, ''),
        ('ŠEMSO TANKOVIĆ', 'SDAH', True, ''),
        ('EMIL TOMLJANOVIĆ', 'HDZ', False, ''),
        ('MARKO TURIĆ', 'HDZ', False, ''),
        ('ŽELJKO TURK', 'HDZ', False, ''),
        ('DAVORKO VIDOVIĆ', 'SDP', False, ''),
        ('ZORAN VINKOVIĆ', 'SDP', False, ''),
        ('BISERKA VRANIĆ', 'SDP', False, ''),
        ('TANJA VRBAT', 'SDP', False, ''),
        ('TOMISLAV VRDOLJAK', 'HDZ', False, ''),
        ('IVAN VUČIĆ', 'HDZ', False, ''),
        ('ANTUN VUJIĆ', 'SDP', False, ''),
        ('DRAGAN VUKIĆ', 'HDZ', False, ''),
        ('DRAGICA ZGREBEC', 'SDP', False, ''),
        ('MARIO ZUBOVIĆ', 'HDZ', False, ''),
    ],
    # 7. saziv (2011-2015), as elected: the 151 who won a mandate at the 2011
    # election, not everyone who sat during the term. Substitutes (zamjenici)
    # who stood in for a mandate in mirovanje are therefore out, and the member
    # they stood in for is in — a mandate in mirovanje was still won at the
    # election. Two such pairs, both from the public listing this was
    # transcribed from:
    #   Zoran Vasić stood in for Marina Lovrić Merzel (Sisak-Moslavina
    #     prefect) until she took the seat up on 11 Sep 2014. Vasić dropped.
    #   Ivan Šimunović's mandate "began 1 July 2013" — Croatia's accession day,
    #     when the 12 MEPs elected that April left the Sabor. HSP dr. Ante
    #     Starčević won exactly one seat in 2011 (district X, 14938 votes) and
    #     its holder, party leader Ruža Tomašić, is in MEPS_BY_YEAR[2013]. So
    #     Šimunović is dropped and Tomašić, who was elected, takes the row.
    # That lands the roster on exactly 151, which is the check that the
    # substitution bookkeeping came out even.
    #
    # Party labels are the caucus as of the term, so members who switched
    # (Holy → ORaH, Kajin/Grubišić/Kregar/Linić → nezavisni) show their later
    # affiliation — they will not add up to the election-day list totals.
    #
    # Three district-XII names in the public roster this was transcribed from
    # belong to a later convocation and are corrected here against the
    # imported 2011 results, which are decisive: a minority seat goes to the
    # top vote-getter in its sub-district, and a mid-term replacement can
    # only come from the same 2011 candidate list.
    #   121 (Srpska, 3 seats): Pupovac 14541, Stanimirović 14188, Vuković
    #     12249 — NOT Mile Horvat or Dragan Crnogorac, neither of whom stood
    #     in 2011 (Horvat first won in 2015, Crnogorac appears in 2024).
    #   122 (Mađarska, 1 seat): Šoja 2441 over Jankovics 2296 — NOT Šandor
    #     Juhas, who first won in 2015.
    2011: [
        ('INGRID ANTIČEVIĆ-MARINOVIĆ', 'SDP', False, ''),
        ('ANTE BABIĆ', 'HDZ', False, ''),
        ('VEDRAN BABIĆ', 'SDP', False, ''),
        ('BRANKO BAČIĆ', 'HDZ', False, ''),
        ('JAKŠA BALOEVIĆ', 'Novi val', False, ''),
        ('MARTINA BANIĆ', 'HDZ', False, ''),
        ('PETAR BARANOVIĆ', 'Narodna stranka - reformisti', False, ''),
        ('MILORAD BATINIĆ', 'HNS', False, ''),
        ('NEVENKA BEČIĆ', 'HGS', False, ''),
        ('DAVOR BERNARDIĆ', 'SDP', False, ''),
        ('GORAN BEUS RICHEMBERGH', 'HNS', False, ''),
        ('VLADIMIR BILEK', 'HNS', True, ''),
        ('DUBRAVKO BILIĆ', 'SDP', False, ''),
        ('BORIS BLAŽEKOVIĆ', 'HNS', False, ''),
        ('VALTER BOLJUNČIĆ', 'IDS', False, ''),
        ('JOSIP BORIĆ', 'HDZ', False, ''),
        ('DAVOR BOŽINOVIĆ', 'HDZ', False, ''),
        ('KREŠIMIR BUBALO', 'HDSSB', False, ''),
        ('DINKO BURIĆ', 'HDSSB', False, ''),
        ('JOVO VUKOVIĆ', 'SDSS', True, ''),
        ('LJILJANA CVJETOVIĆ', 'HSU', False, ''),
        ('NADA ČAVLOVIĆ SMILJANEC', 'SDP', False, ''),
        ('IGOR ČEŠEK', 'HDSSB', False, ''),
        ('TOMISLAV ČULJAK', 'HDZ', False, ''),
        ('MARTINA DALIĆ', 'nezavisna', False, ''),
        ('ADA DAMJANAC', 'SDP', False, ''),
        ('LUKA DENONA', 'SDP', False, ''),
        ('IGOR DRAGOVAN', 'SDP', False, ''),
        ('IVAN DRMIĆ', 'HDSSB', False, ''),
        ('JOSIP ĐAKIĆ', 'HDZ', False, ''),
        ('SAŠA ĐUJIĆ', 'SDP', False, ''),
        ('ŠIMO ĐURĐEVIĆ', 'HDZ', False, ''),
        ('DRAŽEN ĐUROVIĆ', 'HDSSB', False, ''),
        ('VESNA FABIJANČIĆ-KRIŽANIĆ', 'SDP', False, ''),
        ('ILIJA FILIPOVIĆ', 'HDZ', False, ''),
        ('GVOZDEN SREĆKO FLEGO', 'SDP', False, ''),
        ('SRĐAN GJURKOVIĆ', 'HNS', False, ''),
        ('SUNČANA GLAVAK', 'HDZ', False, ''),
        ('DRAGUTIN GLAVINA', 'HNS', False, ''),
        ('PEĐA GRBIN', 'SDP', False, ''),
        ('BORO GRUBIŠIĆ', 'HDSSB', False, ''),
        ('IVAN GRUBIŠIĆ', 'nezavisni', False, ''),
        ('MARIO HABEK', 'SDP', False, ''),
        ('DOMAGOJ HAJDUKOVIĆ', 'SDP', False, ''),
        ('NEDŽAD HODŽIĆ', 'BDSH', True, ''),
        ('MIRELA HOLY', 'ORaH', False, ''),
        ('VOJISLAV STANIMIROVIĆ', 'SDSS', True, ''),
        ('SILVANO HRELJA', 'HSU', False, ''),
        ('BRANKO HRG', 'HSS', False, ''),
        ('MARIJA ILIĆ', 'HSU', False, ''),
        ('TONKA IVČEVIĆ', 'SDP', False, ''),
        ('TOMISLAV IVIĆ', 'HDZ', False, ''),
        ('GORDAN JANDROKOVIĆ', 'HDZ', False, ''),
        ('NADICA JELAŠ', 'SDP', False, ''),
        ('PERICA JELEČEVIĆ', 'HDZ', False, ''),
        ('IVO JELUŠIĆ', 'SDP', False, ''),
        ('ROMANA JERKOVIĆ', 'SDP', False, ''),
        ('ANTE JEROLIMOV', 'HDZ', False, ''),
        ('ŽELJKO JOVANOVIĆ', 'SDP', False, ''),
        ('DENEŠ ŠOJA', 'DZMH', True, ''),
        ('BRANKA JURIČEV-MARTINČEV', 'HDZ', False, ''),
        ('MARIN JURJEVIĆ', 'SDP', False, ''),
        ('MILAN JURKOVIĆ', 'HDZ', False, ''),
        ('DAMIR KAJIN', 'nezavisni', False, ''),
        ('VELJKO KAJTAZI', 'nezavisni', True, ''),
        ('TOMISLAV KARAMARKO', 'HDZ', False, ''),
        ('ŽELJKO KERUM', 'HGS', False, ''),
        ('TOMISLAV KLARIĆ', 'HDZ', False, ''),
        ('IVAN KLARIN', 'SDP', False, ''),
        ('IGOR KOLMAN', 'HNS', False, ''),
        ('ANA KOMPARIĆ DEVČIĆ', 'SDP', False, ''),
        ('SONJA KÖNIG', 'HNS', False, ''),
        ('JADRANKA KOSOR', 'nezavisna', False, ''),
        ('JOSIP KREGAR', 'nezavisni', False, ''),
        ('JOSIP KRNIĆ', 'SDP', False, ''),
        ('ANTE KULUŠIĆ', 'HDZ', False, ''),
        ('BRANKO KUTIJA', 'HDZ', False, ''),
        ('KAROLINA LEAKOVIĆ', 'SDP', False, ''),
        ('DARKO LEDINSKI', 'SDP', False, ''),
        ('JOSIP LEKO', 'SDP', False, ''),
        ('DRAGUTIN LESAR', 'Hrvatski laburisti - Stranka rada', False, ''),
        ('SLAVKO LINIĆ', 'nezavisni', False, ''),
        ('MARINA LOVRIĆ MERZEL', 'nezavisna', False, 'mandat u mirovanju do 11. rujna 2014.'),
        ('FRANJO LUCIĆ', 'HDZ', False, ''),
        ('ŠIME LUČIN', 'SDP', False, ''),
        ('MARIJA LUGARIĆ', 'SDP', False, ''),
        ('IVICA MANDIĆ', 'HNS', False, ''),
        ('DUJOMIR MARASOVIĆ', 'HDZ', False, ''),
        ('MLADEN MARELIĆ', 'SDP', False, ''),
        ('GORAN MARIĆ', 'HDZ', False, ''),
        ('NATALIJA MARTINČEVIĆ', 'Narodna stranka - reformisti', False, ''),
        ('DAMIR MATELJAN', 'SDP', False, ''),
        ('FRANO MATUŠIĆ', 'HDZ', False, ''),
        ('JASEN MESIĆ', 'HDZ', False, ''),
        ('ZVONKO MILAS', 'HDZ', False, ''),
        ('DAVOR MILIČEVIĆ', 'HDZ', False, ''),
        ('STJEPAN MILINKOVIĆ', 'HDZ', False, ''),
        ('DARKO MILINOVIĆ', 'HDZ', False, ''),
        ('DOMAGOJ IVAN MILOŠEVIĆ', 'HDZ', False, ''),
        ('ŽELJKO MIRKOVIĆ', 'SDP', False, ''),
        ('DAVORIN MLAKAR', 'HDZ', False, ''),
        ('MARIO MOHARIĆ', 'SDP', False, ''),
        ('DANIEL MONDEKAR', 'SDP', False, ''),
        ('MELITA MULIĆ', 'SDP', False, ''),
        ('NADA MURGANIĆ', 'HDZ', False, ''),
        ('HRVOJE NEKIĆ', 'SDP', False, ''),
        ('MLADEN NOVAK', 'nezavisni', False, ''),
        ('RAJKO OSTOJIĆ', 'SDP', False, ''),
        ('DRAŽENKO PANDEK', 'SDP', False, ''),
        ('ĐURĐICA PLANČIĆ', 'SDP', False, ''),
        ('ĐURO POPIJAČ', 'HDZ', False, ''),
        ('VANJA POSAVAC', 'SDP', False, ''),
        ('IVANA POSAVEC KRIVEC', 'SDP', False, ''),
        ('ALEN PRELEC', 'SDP', False, ''),
        ('MILORAD PUPOVAC', 'SDSS', True, ''),
        ('IVAN RAČAN', 'SDP', False, ''),
        ('FURIO RADIN', 'nezavisni', True, ''),
        ('MARIJA RAPO', 'HDZ', False, ''),
        ('ŽELJKO REINER', 'HDZ', False, ''),
        ('DAMIR RILJE', 'SDP', False, ''),
        ('DAMIR RIMAC', 'SDP', False, ''),
        ('ZDRAVKO RONKO', 'SDP', False, ''),
        ('VESNA SABOLIĆ', 'Narodna stranka - reformisti', False, ''),
        ('JOSIP SALAPIĆ', 'HDSSB', False, ''),
        ('ANTE SANADER', 'HDZ', False, ''),
        ('GORDANA SOBOL', 'SDP', False, ''),
        ('GIOVANNI SPONZA', 'IDS', False, ''),
        ('NENAD STAZIĆ', 'SDP', False, ''),
        ('ĐURĐICA SUMRAK', 'HDZ', False, ''),
        ('IVAN ŠANTEK', 'HDZ', False, ''),
        ('VLADIMIR ŠEKS', 'HDZ', False, ''),
        ('ŽELJKO ŠEMPER', 'HSU', False, ''),
        ('TATJANA ŠIMAC BONAČIĆ', 'SDP', False, ''),
        ('VESNA ŠKARE OŽBOLT', 'DC', False, 'mandat u mirovanju do 18. veljače 2014.'),
        ('MARIJAN ŠKVARIĆ', 'HNS', False, ''),
        ('DUNJA ŠPOLJAR', 'SDP', False, ''),
        ('IVAN ŠUKER', 'HDZ', False, ''),
        ('NANSI TIRELI', 'Hrvatski laburisti - Stranka rada', False, ''),
        ('RUŽA TOMAŠIĆ', 'HSP dr. Ante Starčević', False, 'mandat do 1. srpnja 2013. — odlazak u Europski parlament'),
        ('DAMIR TOMIĆ', 'SDP', False, ''),
        ('MIROSLAV TUĐMAN', 'HDZ', False, ''),
        ('NADA TURINA-ĐURIĆ', 'HNS', False, ''),
        ('ZLATKO TUŠAK', 'Hrvatski laburisti - Stranka rada', False, ''),
        ('FRANKO VIDOVIĆ', 'SDP', False, ''),
        ('TANJA VRBAT GRGIĆ', 'SDP', False, ''),
        ('JOSIP VUKOVIĆ', 'SDP', False, ''),
        ('BRANKO VUKŠIĆ', 'nezavisni', False, ''),
        ('NIKOLA VULJANIĆ', 'nezavisni', False, ''),
        ('DRAGICA ZGREBEC', 'SDP', False, ''),
        ('TOMISLAV ŽAGAR', 'SDP', False, ''),
        ('VESNA ŽELJEŽNJAK', 'SDP', False, ''),
    ],
}


# Normalized variant name -> normalized canonical name, from the curated
# merges. A roster that spells a member the pre-merge way would otherwise
# recreate the row `merge_person_aliases` had just folded away, and the next
# seed would silently undo the merge — 2007 lists Tanja Vrbat, who is the
# Tanja Vrbat Grgić of 2011 and 2015.
_ALIAS_BY_VARIANT = {
    normalize_person_name(variant): normalize_person_name(canonical)
    for canonical, variant, _ in KNOWN_ALIASES
}


def _check_district_seats(roster, stderr, style):
    """Report districts whose member count differs from their seat count.

    Only meaningful for a roster that records districts. Districts I-X always
    return 14 and the six minority sub-districts always return 3/1/1/1/1/1, so
    those are checkable without consulting the election. Diaspora district XI
    is not: its size is year-dependent and that table lives in app.py, so it is
    reported rather than asserted.
    """
    counts = {}
    for entry in roster:
        d = _unpack(entry)[4]
        if d:
            counts[d] = counts.get(d, 0) + 1
    if not counts:
        return
    expected = {n: 14 for n in range(1, 11)} | MINORITY_SEATS
    for number in sorted(counts):
        want = expected.get(number)
        if want is not None and counts[number] != want:
            stderr.write(style.ERROR(
                f'  district {number}: {counts[number]} member(s) for {want} seat(s) '
                f'— roster is incomplete'))
    if 11 in counts:
        stderr.write(f'  district 11 (dijaspora): {counts[11]} member(s)')


def _unpack(entry):
    """(name, party, minority, note, district) from a roster entry.

    2003 carries a district as a fifth field; 2007 and 2011 have no district to
    carry, so their entries stay four-wide rather than ending in a column of
    None.
    """
    name, party, minority, note = entry[:4]
    return name, party, minority, note, (entry[4] if len(entry) > 4 else None)


def _find_person(normalized):
    """Look up a Person by normalized name, tolerating hyphen spelling.

    normalize_person_name() strips diacritics but keeps hyphens, so a compound
    surname written both ways across sources lands in two Person rows — DIP's
    2015 file has "ANTIČEVIĆ-MARINOVIĆ" where the roster listing writes
    "ANTIČEVIĆ MARINOVIĆ", and an exact-key lookup would create a second
    Ingrid. Croatian compound surnames differ by the hyphen alone, never two
    different people, so a loose match is safe here. Prefer a row that already
    has candidacies: that is the one carrying election data to attach to.
    """
    person = Person.objects.filter(normalized_name=normalized).first()
    if person:
        return person
    loose = normalized.replace('-', ' ')
    matches = list(
        Person.objects
        .annotate(loose_name=Replace('normalized_name', Value('-'), Value(' ')))
        .filter(loose_name=loose)
    )
    matches.sort(key=lambda q: -q.candidacies.count())
    if matches:
        return matches[0]

    canonical = _ALIAS_BY_VARIANT.get(normalized)
    return Person.objects.filter(normalized_name=canonical).first() if canonical else None


def _minority_winners(round_ids):
    """Who actually won the district-XII seats, straight from the votes.

    Minority seats need no D'Hondt — the top vote-getters in each sub-district
    take them — so this is a cheap, exact cross-check on the hand-typed part of
    the roster most likely to drift: public listings of a saziv mix in members
    who only arrived at the next election.
    """
    winners = {}
    for number, n_seats in MINORITY_SEATS.items():
        rows = (
            Candidacy.objects
            .filter(electoral_list__election_round_id__in=round_ids,
                    electoral_list__district__number=number)
            .annotate(v=Sum('results__votes'))
            .order_by('-v')[:n_seats]
        )
        for c in rows:
            winners[c.person.normalized_name] = (number, int(c.v or 0))
    return winners


# Roster party labels are abbreviations; the Zastupnici table shows the full
# "<NAME> - <ABBR>" form so a pre-2015 saziv reads the same way as 2015+, where
# the label comes straight from the electoral-list name. Spellings are taken
# from the list names actually imported for these years, so the roster matches
# its own year's hemicycle legend.
#
# Five entries cannot come from list names: BDSH, ORaH, Novi val, the
# Laburisti and the Reformisti first contested a Sabor election after the saziv
# their members sat in (or under a different banner), and DZMH and SDA Hrvatske
# are minority proposers, which DIP records in the district XII candidate
# column rather than as a list. Those are transcribed from that column.
PARTY_FULL_NAMES = {
    'HDZ':   'HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ',
    'SDP':   'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP',
    'HNS':   'HRVATSKA NARODNA STRANKA - LIBERALNI DEMOKRATI - HNS',
    'HSS':   'HRVATSKA SELJAČKA STRANKA - HSS',
    'HSP':   'HRVATSKA STRANKA PRAVA - HSP',
    'HSU':   'HRVATSKA STRANKA UMIROVLJENIKA - HSU',
    'HSLS':  'HRVATSKA SOCIJALNO LIBERALNA STRANKA - HSLS',
    'HDSSB': 'HRVATSKI DEMOKRATSKI SAVEZ SLAVONIJE I BARANJE - HDSSB',
    'IDS':   'ISTARSKI DEMOKRATSKI SABOR - IDS',
    'SDSS':  'SAMOSTALNA DEMOKRATSKA SRPSKA STRANKA - SDSS',
    'HGS':   'HRVATSKA GRAĐANSKA STRANKA - HGS',
    'DC':    'DEMOKRATSKI CENTAR - DC',
    'BDSH':  'BRANITELJSKO DOMOLJUBNA STRANKA HRVATSKE - BDSH',
    'ORaH':  'ODRŽIVI RAZVOJ HRVATSKE - ORaH',
    'SDAH':  'STRANKA DEMOKRATSKE AKCIJE HRVATSKE - SDA HRVATSKE',
    'DZMH':  'DEMOKRATSKA ZAJEDNICA MAĐARA HRVATSKE - DZMH',
    'NNZ':   ('NJEMAČKA NARODNOSNA ZAJEDNICA - ZEMALJSKA UDRUGA PODUNAVSKIH '
              'ŠVABA U HRVATSKOJ-OSIJEK'),
    'Novi val': 'NOVI VAL - STRANKA RAZVOJA - NOVI VAL',
    'HSP dr. Ante Starčević': 'HRVATSKA STRANKA PRAVA DR.ANTE STARČEVIĆ - HSP DR.ANTE STARČEVIĆ',
    'Hrvatski laburisti - Stranka rada': 'HRVATSKI LABURISTI - STRANKA RADA',
    'Narodna stranka - reformisti': 'NARODNA STRANKA - REFORMISTI',
    # Not parties; uppercased only so the column reads consistently.
    'nezavisni':  'NEZAVISNI',
    'nezavisna':  'NEZAVISNA',
}


class Command(BaseCommand):
    help = (
        'Seed the roster of Sabor members (zastupnici) for one convocation. '
        'Needed for years with no published candidate names (2007, 2011).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, required=True,
                            help='Sabor election year the convocation was elected at')
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change without writing')

    def handle(self, *args, year, dry_run, **options):
        roster = MEMBERS_BY_YEAR.get(year)
        if not roster:
            self.stderr.write(self.style.ERROR(
                f'No Sabor roster defined for {year}. Add one to MEMBERS_BY_YEAR.'
            ))
            return

        etype = ElectionType.objects.filter(name='Parlamentarni izbori').first()
        election = Election.objects.filter(election_type=etype, year=year).first() if etype else None
        if not election:
            self.stderr.write(self.style.ERROR(f'No Sabor election for {year}'))
            return

        round_ids = list(
            ElectionRound.objects.filter(election=election).values_list('id', flat=True)
        )

        created = updated = new_persons = linked = 0
        kept_ids = []
        with transaction.atomic():
            # A roster may name the party either way: 2007 and 2011 write the
            # abbreviation and it is expanded here, while 2003 carries the full
            # electoral-list name, coalitions included, which has no
            # abbreviation to write. Validating the second form against the
            # lists actually imported for the year is the useful check — it
            # catches a mistyped coalition and guarantees the column matches
            # the hemicycle legend character for character.
            known = (set(PARTY_FULL_NAMES) | set(PARTY_FULL_NAMES.values())
                     | set(ElectoralList.objects
                           .filter(election_round__election=election)
                           .values_list('name', flat=True)))
            unknown = sorted({e[1] for e in roster if e[1] and e[1] not in known})
            if unknown:
                self.stderr.write(self.style.ERROR(
                    f'No full name for party label(s): {unknown}. '
                    f'Add them to PARTY_FULL_NAMES.'))
                return

            districts = {
                d.number: d for d in ElectoralDistrict.objects.filter(election=election)
            }
            for entry in roster:
                full_name, party, minority, note, district_num = _unpack(entry)
                party = PARTY_FULL_NAMES.get(party, party)
                district = districts.get(district_num) if district_num else None
                if district_num and district is None:
                    self.stderr.write(self.style.WARNING(
                        f'  no district {district_num} in {year}; '
                        f'{full_name} stored without one'))
                normalized = normalize_person_name(full_name)
                person = _find_person(normalized)
                if person and person.normalized_name != normalized:
                    self.stdout.write(
                        f'  ~ {full_name} matched existing {person.normalized_name} '
                        f'(hyphen spelling)'
                    )
                if not person:
                    first_name, last_name = parse_person_name(full_name)
                    if dry_run:
                        self.stdout.write(self.style.WARNING(
                            f'  NEW PERSON {full_name}'
                        ))
                        new_persons += 1
                        continue
                    person = Person.objects.create(
                        first_name=first_name, last_name=last_name,
                        normalized_name=normalized,
                    )
                    new_persons += 1
                    self.stdout.write(self.style.WARNING(f'  NEW PERSON {full_name}'))

                # District XII members do have a candidacy in this election;
                # everyone else was elected off a list DIP published without
                # candidate names, so this stays null.
                candidacy = (
                    Candidacy.objects
                    .filter(person=person, electoral_list__election_round_id__in=round_ids)
                    .first()
                )
                linked += bool(candidacy)

                if dry_run:
                    continue

                obj, was_created = ParliamentMember.objects.update_or_create(
                    election=election, person=person,
                    defaults={'party': party, 'minority': minority, 'note': note,
                              'candidacy': candidacy, 'district': district},
                )
                kept_ids.append(obj.id)
                created += was_created
                updated += (not was_created)

            # This command is authoritative for the year it is run for: drop
            # rows that are no longer in the roster. Scoped to this election,
            # so other convocations are untouched.
            stale_n = 0
            if not dry_run:
                stale = ParliamentMember.objects.filter(election=election).exclude(id__in=kept_ids)
                stale_n = stale.count()
                stale.delete()

            if dry_run:
                transaction.set_rollback(True)

        _check_district_seats(roster, self.stderr, self.style)

        # Cross-check the district-XII half of the roster against the votes.
        expected = _minority_winners(round_ids)
        claimed = {
            normalize_person_name(e[0]) for e in roster if e[2]
        }
        wrong = sorted(claimed - set(expected))
        missed = sorted(set(expected) - claimed)
        if wrong or missed:
            self.stderr.write(self.style.ERROR(
                '\nDistrict XII mismatch — the roster disagrees with the imported votes:'
            ))
            for n in wrong:
                self.stderr.write(self.style.ERROR(f'  in roster but did not win: {n}'))
            for n in missed:
                number, votes = expected[n]
                self.stderr.write(self.style.ERROR(
                    f'  won sub-district {number} with {votes} votes but is missing: {n}'
                ))

        by_party = {}
        for entry in roster:
            party = _unpack(entry)[1]
            label = PARTY_FULL_NAMES.get(party, party) or '(stranka nije zabilježena)'
            by_party[label] = by_party.get(label, 0) + 1
        minority_n = sum(1 for e in roster if e[2])

        self.stdout.write('')
        for party, n in sorted(by_party.items(), key=lambda kv: (-kv[1], kv[0])):
            self.stdout.write(f'  {n:>3}  {party}')
        self.stdout.write(self.style.SUCCESS(
            f'\nSabor {year} roster ({"dry run" if dry_run else "written"}) — '
            f'{len(roster)} members, {minority_n} from district XII, '
            f'created {created}, updated {updated}, stale removed {stale_n}, '
            f'new Person rows {new_persons}, linked to a candidacy {linked}.'
        ))
        # Roster members who exist in no other election are where a spelling
        # variant hides: a name typed one way here and another way in a DIP
        # file splits one politician across two Person rows, and only the
        # roster row would be missing every other year's results. Listed on
        # every run so the split shows up rather than sitting there silently.
        if not dry_run:
            unmatched = [
                m.person for m in ParliamentMember.objects
                .filter(election=election).select_related('person')
                if not m.person.candidacies.exists()
            ]
            if unmatched:
                self.stdout.write(self.style.WARNING(
                    f'\n{len(unmatched)} roster members appear in no other election '
                    f'(no candidacy anywhere) — check for spelling variants:'
                ))
                for prs in sorted(unmatched, key=lambda q: q.normalized_name):
                    self.stdout.write(f'  {prs.normalized_name}')
                self.stdout.write(
                    'Cross-check with `merge_person_aliases --suggest` — a middle-name '
                    'variant may already exist under another spelling.'
                )
