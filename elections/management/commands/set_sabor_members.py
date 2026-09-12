from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Value
from django.db.models.functions import Replace

from elections.importers.name_utils import (
    normalize_person_name, parse_person_name,
)
from elections.models import (
    ElectionType, Election, ElectionRound, Candidacy, Person, ParliamentMember,
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
    2003: [
        ('JENE ADAM', '', True, ''),
        ('ĐURĐA ADLEŠIČ', '', False, ''),
        ('IRENA AHEL', '', False, ''),
        ('ZDENKO ANTEŠIĆ', '', False, ''),
        ('INGRID ANTIČEVIĆ-MARINOVIĆ', '', False, ''),
        ('ŽELJKA ANTUNOVIĆ', '', False, ''),
        ('FRANJO ARAPOVIĆ', '', False, ''),
        ('MATO ARLOVIĆ', '', False, ''),
        ('ZDENKA BABIĆ PETRIČEVIĆ', '', False, ''),
        ('STJEPAN BAČIĆ', '', False, ''),
        ('ANTO BAGARIĆ', '', False, ''),
        ('IVAN BAGARIĆ', '', False, ''),
        ('MARIJA BAJT', '', False, ''),
        ('IVO BANAC', '', False, ''),
        ('LUKA BEBIĆ', '', False, ''),
        ('MARIJAN BEKAVAC', '', False, ''),
        ('JURE BITUNJAC', '', False, ''),
        ('FLORIJAN BORAS', '', False, ''),
        ('DRAŽEN BOŠNJAKOVIĆ', '', False, ''),
        ('LJUBICA BRDARIĆ', '', False, ''),
        ('MIRJANA BRNADIĆ', '', False, ''),
        ('KAJO BUĆAN', '', False, ''),
        ('PERICA BUKIĆ', '', False, ''),
        ('MIROSLAV ČAČIJA', '', False, ''),
        ('KARMELA CAPARIN', '', False, ''),
        ('IVAN ČEHOK', '', False, ''),
        ('LINO ČERVAR', '', False, ''),
        ('LUCIJA ČIKEŠ', '', False, ''),
        ('KREŠIMIR ĆOSIĆ', '', False, ''),
        ('MATO CRKVENAC', '', False, ''),
        ('ZDENKA ČUHNIL', '', True, ''),
        ('TOMISLAV ČULJAK', '', False, ''),
        ('JOSIP ĐAKIĆ', '', False, ''),
        ('ANTO ĐAPIĆ', '', False, ''),
        ('MIRJANA DIDOVIĆ', '', False, ''),
        ('MILJENKO DORIĆ', '', False, ''),
        ('VALTER DRANDIĆ', '', False, ''),
        ('IVAN DRMIĆ', '', False, ''),
        ('SREĆKO FERENČAK', '', False, ''),
        ('MIRKO FILIPOVIĆ', '', False, ''),
        ('STJEPAN FIOLIĆ', '', False, ''),
        ('RATKO GAJICA', '', True, ''),
        ('MATO GAVRAN', '', False, ''),
        ('BRANIMIR GLAVAŠ', '', False, ''),
        ('ANDRIJA HEBRANG', '', False, ''),
        ('VILIM HERMAN', '', False, ''),
        ('SILVANO HRELJA', '', False, ''),
        ('NIKOLA IVANIŠ', '', False, ''),
        ('RADE IVAS', '', False, ''),
        ('GORDAN JANDROKOVIĆ', '', False, ''),
        ('IVAN JARNJAK', '', False, ''),
        ('VLADO JELKOVAC', '', False, ''),
        ('IVO JOSIPOVIĆ', '', False, ''),
        ('VLADO JUKIĆ', '', False, ''),
        ('LJUBO JURČIĆ', '', False, ''),
        ('MARIN JURJEVIĆ', '', False, ''),
        ('IVAN JURKIN', '', False, ''),
        ('DAMIR KAJIN', '', False, ''),
        ('ANTUN KAPRALJEVIĆ', '', False, ''),
        ('IVICA KLEM', '', False, ''),
        ('IVAN KOLAR', '', False, ''),
        ('ZLATKO KORAČEVIĆ', '', False, ''),
        ('MIROSLAV KORENIKA', '', False, ''),
        ('ALENKA KOŠIŠA ČIČIN-ŠAIN', '', False, ''),
        ('PERO KOVAČEVIĆ', '', False, ''),
        ('STJEPAN KOZINA', '', False, ''),
        ('ZLATKO KRAMARIĆ', '', False, ''),
        ('VLADIMIR KUREČIĆ', '', False, ''),
        ('ŽELJKO KURTOV', '', False, ''),
        ('LJUBICA LALIĆ', '', False, ''),
        ('ŽELJKO LEDINSKI', '', False, ''),
        ('JOSIP LEKO', '', False, ''),
        ('RUŽA LELIĆ', '', False, ''),
        ('DRAGUTIN LESAR', '', False, ''),
        ('SLAVEN LETICA', '', False, ''),
        ('SLAVKO LINIĆ', '', False, ''),
        ('IVO LONČAR', '', False, ''),
        ('ŠIME LUČIN', '', False, ''),
        ('MARIJA LUGARIĆ', '', False, ''),
        ('NEVENKA MAJDENIĆ', '', False, ''),
        ('NIKOLA MAK', '', True, ''),
        ('JAKŠA MARASOVIĆ', '', False, ''),
        ('ANTE MARKOV', '', False, ''),
        ('KRUNOSLAV MARKOVINOVIĆ', '', False, ''),
        ('JAGODA MARTIĆ', '', False, ''),
        ('JAGODA MAJSKA MARTINČEVIĆ', '', False, ''),
        ('FRANO MATUŠIĆ', '', False, ''),
        ('MILAN MEDEN', '', False, ''),
        ('DARKO MILINOVIĆ', '', False, ''),
        ('NEVEN MIMICA', '', False, ''),
        ('MARIJAN MLINARIĆ', '', False, ''),
        ('PETAR MLINARIĆ', '', False, ''),
        ('ZVONIMIR MRŠIĆ', '', False, ''),
        ('ŽELJKO NENADIĆ', '', False, ''),
        ('ŽIVKO NENADIĆ', '', False, ''),
        ('MILANKA OPAČIĆ', '', False, ''),
        ('IVICA PANČIĆ', '', False, ''),
        ('BOŽIDAR PANKRETIĆ', '', False, ''),
        ('BRANIMIR PASECKY', '', False, ''),
        ('JELENA PAVIČIĆ VUKIČEVIĆ', '', False, ''),
        ('ŽELJKO PAVLIC', '', False, ''),
        ('ŽELJKO PECEK', '', False, ''),
        ('BISERKA PERMAN', '', False, ''),
        ('KRUNO PERONJA', '', False, ''),
        ('ANTON PERUŠKO', '', False, ''),
        ('DOROTEA PEŠIĆ-BUKOVAC', '', False, ''),
        ('TONINO PICULA', '', False, ''),
        ('VELIMIR PLEŠA', '', False, ''),
        ('VALTER POROPAT', '', False, ''),
        ('IVANA POSAVEC KRIVEC', '', False, ''),
        ('ŠIME PRTENJAČA', '', False, ''),
        ('DRAGUTIN PUKLEŠ', '', False, ''),
        ('MILORAD PUPOVAC', '', True, ''),
        ('VESNA PUSIĆ', '', False, ''),
        ('IVICA RAČAN', '', False, 'umro'),
        ('FURIO RADIN', '', True, ''),
        ('JOZO RADOŠ', '', False, ''),
        ('NIKO REBIĆ', '', False, ''),
        ('LUKA ROIĆ', '', False, ''),
        ('IVANKA ROKSANDIĆ', '', False, ''),
        ('MIROSLAV ROŽIĆ', '', False, ''),
        ('ZVONIMIR SABATI', '', False, ''),
        ('VLADIMIR ŠEKS', '', False, ''),
        ('PETAR SELEM', '', False, ''),
        ('DAMIR SESVEČAN', '', False, ''),
        ('MARKO ŠIRAC', '', False, ''),
        ('VLADIMIR ŠIŠLJAGIĆ', '', False, ''),
        ('VESNA ŠKARE OŽBOLT', '', False, ''),
        ('VESNA ŠKULIĆ', '', False, ''),
        ('GORDANA SOBOL', '', False, ''),
        ('ZDRAVKO SOČKOVIĆ', '', False, ''),
        ('BOŽICA ŠOLIĆ', '', False, ''),
        ('NIKOLA SOPČIĆ', '', False, ''),
        ('VOJISLAV STANIMIROVIĆ', '', True, ''),
        ('NENAD STAZIĆ', '', False, ''),
        ('VLADIMIR ŠTENGL', '', False, ''),
        ('IVANA SUČEC-TRAKOŠTANEC', '', False, ''),
        ('TONČI TADIĆ', '', False, ''),
        ('ŠEMSO TANKOVIĆ', '', True, ''),
        ('RUŽA TOMAŠIĆ', '', False, ''),
        ('TOMISLAV TOMIĆ', '', False, ''),
        ('EMIL TOMLJANOVIĆ', '', False, ''),
        ('JOZO TOPIĆ', '', False, ''),
        ('PEJO TRGOVČEVIĆ', '', False, ''),
        ('MARKO TURIĆ', '', False, ''),
        ('DAVORKO VIDOVIĆ', '', False, ''),
        ('IVAN VUČIĆ', '', False, ''),
        ('ANTUN VUJIĆ', '', False, ''),
        ('NIKOLA VULJANIĆ', '', False, ''),
        ('DRAGICA ZGREBEC', '', False, ''),
        ('MARIO ZUBOVIĆ', '', False, ''),
        ('MIOMIR ŽUŽUL', '', False, ''),
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
    return matches[0] if matches else None


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
            for full_name, party, minority, note in roster:
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
                    defaults={'party': party, 'minority': minority,
                              'note': note, 'candidacy': candidacy},
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

        # Cross-check the district-XII half of the roster against the votes.
        expected = _minority_winners(round_ids)
        claimed = {
            normalize_person_name(full_name)
            for full_name, _, minority, _ in roster if minority
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
        for _, party, _, _ in roster:
            by_party[party or '(stranka nije zabilježena)'] = (
                by_party.get(party or '(stranka nije zabilježena)', 0) + 1)
        minority_n = sum(1 for _, _, m, _ in roster if m)

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
