"""Split a Person row that holds two or more different people of the same name.

The inverse of `merge_person_aliases`. Every import matches a candidate to a
Person by normalized name alone, so namesakes merge: the HDZ Ante Jelavić of
Osijek and the Zelena akcija Ante Jelavić of Split both stood for the 1990
Društveno-političko vijeće, and both landed on the row a 2024 Domovinski pokret
candidate of that name also uses. Nothing in a name can tell them apart, so
every split here is a curated, evidenced decision, like `KNOWN_ALIASES`.

A split moves the candidacies a selector picks out (and the seats won with
them) onto a separate Person carrying the same name plus a `disambiguation`
label, which the UI shows beside the name. Everything not selected stays on
the unlabelled row, which is the one imports keep matching by name; the base
importer never matches a labelled row, and finds an existing candidacy on
whichever namesake holds it, so a re-import neither undoes a split nor
duplicates a candidacy. Selectors name an election and district rather than
row ids, so a wiped and re-imported election is split again by re-running this
command, as `merge_person_aliases` is re-run after an import.

`--suggest` lists the Persons that look like more than one person, strongest
evidence first:

  1. two candidacies in the same election round. Under different parties this
     is two people; under the same party in two districts it may be one person
     listed twice, so it is shown apart;
  2. 1990 candidacies giving different places of residence;
  3. a gap of 15 years or more between consecutive elections — in practice a
     1990/1992 candidate matching a 2015+ one by name alone.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from elections.importers.name_utils import (
    normalize_person_name, parse_person_name, split_birth_year,
)
from elections.models import Candidacy, County, Municipality, ParliamentMember, Person


# (name, label, selectors, evidence). A selector is (election type slug, year,
# district number or None, list-name prefix or None) and picks the candidacies
# of that name that belong to the labelled person; the rest stay put. The
# label is what tells the namesakes apart on screen: place and year where the
# report gives one, else party and year.
KNOWN_DISTINCT = [
    # --- Two candidacies in one election round under different parties. A
    # person may stand on one list only, so each pair is two people; the
    # candidacy that breaks the row's party/district continuity is the one
    # carved off. Links across years that nothing settles stay on the
    # unlabelled row and are listed by `--suggest` for review.
    ('ANTE JELAVIĆ', 'Osijek, 1990.', [('sabor_dpv', 1990, 2)],
     'DPV 1990: HDZ in Osijek I (both rounds, residence Osijek) while a Zelena '
     'akcija Split candidate of the name stood in Split II'),
    ('ANTE JELAVIĆ', 'Split, 1990.', [('sabor_dpv', 1990, 74)],
     'DPV 1990: Zelena akcija Split in Split II, residence Split, the same round '
     'as the Osijek HDZ one; the 2024 Domovinski pokret candidate is left on the '
     'main row, being neither provably'),
    ('ANTONIO GRGIĆ', 'Pametno, 2020.', [('sabor', 2020, 2)],
     'sabor 2020: Pametno in II. IJ while the A-HSP candidate stood #5 in IV. IJ, '
     'as in 2015 and 2016'),
    ('DALIBOR FUĆAK', 'Akcija mladih, 2015.', [('sabor', 2015, 5)],
     'sabor 2015: Akcija mladih in V. IJ while the A-HSP candidate stood in VIII. '
     'IJ, where he runs every year 2015-2024'),
    ('DARKO HORVAT', 'HBPS, 2016.', [('sabor', 2016, 1)],
     'sabor 2016: HBPS in I. IJ while the HDZ Darko Horvat stood in III. IJ, as '
     'in 2015 and 2020'),
    ('HRVOJE PERNAR', 'A-HSP, 2015.-2016.', [('sabor', 2015, 3), ('sabor', 2016, 3)],
     'sabor 2015: A-HSP in III. IJ while a Živi zid candidate stood in I. IJ; '
     'A-HSP III. IJ again in 2016. Which of them is the 2024 Stranka Ivana '
     'Pernara candidate (IV. IJ) is not settled'),
    ('IVAN KNEŽEVIĆ', 'BUZ, 2020.', [('sabor', 2020, 6)],
     'sabor 2020: Blok umirovljenici zajedno in VI. IJ while a Most candidate '
     'stood in IV. IJ; the 1992 HSLS and 2016 SMS candidates are not settled'),
    ('IVAN KOVAČIĆ', 'Živi zid, 2016.', [('sabor', 2016, 10, 'ŽIVI ZID')],
     'sabor 2016 X. IJ: on both the Živi zid (#11) and the Most (#2) list; the '
     'Most one heads its X. IJ list in 2015 too'),
    ('IVAN MATIĆ', 'Domovinski pokret, 2020.', [('sabor', 2020, 4)],
     'sabor 2020: Domovinski pokret in IV. IJ while the Most candidate stood in '
     'IX. IJ, as in 2024 (and on Most\'s 2019 EU list)'),
    ('IVAN MOLNAR', 'HDS, 1992.', [('sabor', 1992, 30)],
     'sabor 1992: HDS in district XXX while an SDP candidate stood in district XII'),
    ('IVAN TOMLJENOVIĆ', 'Most, 2016.', [('sabor', 2016, 7)],
     'sabor 2016: Most in VII. IJ while an HSP candidate stood in II. IJ'),
    ('IVAN VUČIĆ', 'BDSH, 2015.', [('sabor', 2015, 3)],
     'sabor 2015: BDSH in III. IJ while an HDZ candidate stood in VII. IJ'),
    ('JOSIP BUDIMIR', 'Pametno, 2020.', [('sabor', 2020, 1)],
     'sabor 2020: Pametno in I. IJ while an NHR candidate stood in IX. IJ; the '
     '2015 HDZ and 2025 mayoral candidates are not settled'),
    ('JOSIP LEKO', 'dijaspora, 2015.', [('sabor', 2015, 11)],
     'sabor 2015: Neovisna lista Vesne Pinjuh in the diaspora district while the '
     'SDP Josip Leko headed the SDP-led list in II. IJ'),
    ('JOSIP MIKUŠ', 'Agrarna stranka, 2024.', [('sabor', 2024, 2)],
     'sabor 2024: Agrarna stranka in II. IJ while a Most candidate stood in X. IJ'),
    ('KATARINA NEMET', 'Radnička fronta, 2024.', [('sabor', 2024, 9)],
     'sabor 2024: Radnička fronta in IX. IJ while the IDS-led list carried a '
     'Katarina Nemet in VIII. IJ, where an SDP one stood in 2020'),
    ('MARKO KOVAČEVIĆ', 'Most, 2020.', [('sabor', 2020, 5)],
     'sabor 2020: Most in V. IJ while a BUZ candidate stood in X. IJ, who stood '
     'there for Umirovljenici zajedno in 2024'),
    ('MIRJANA SPAJIĆ', 'SHZ, 2020.', [('sabor', 2020, 7)],
     'sabor 2020: Stranka hrvatskog zajedništva in VII. IJ while a Slobodna '
     'Hrvatska candidate stood in III. IJ (SH and NLSP ran together in 2016)'),
    ('MIROSLAV MARKOVIĆ', 'HSP, 2024.', [('sabor', 2024, 8)],
     'sabor 2024: HSP in VIII. IJ while the SDP candidate stood in III. IJ, as '
     'in 2020'),
    ('SUZANA MIŠIĆ', 'Istarski demokrati, 2016.', [('sabor', 2016, 8)],
     'sabor 2016: Istarski demokrati in VIII. IJ while an NLSP candidate stood in '
     'VII. IJ'),
    ('TOMISLAV BEDEKOVIĆ', 'Demokrati, 2020.', [('sabor', 2020, 2)],
     'sabor 2020: Demokrati in II. IJ while a Pametno candidate stood in III. '
     'IJ; the 2024 Javno dobro candidate is not settled'),
    ('TOMISLAV JURIĆ', 'Obiteljska stranka, 2013.',
     [('eu_parliament', 2013, None, 'OBITELJSKA STRANKA')],
     'EU 2013: on both the Obiteljska stranka (#7) and the HRS (#10) list; the '
     'HRS one stood for HRS again in 2016'),
    ('TOMISLAV JURIĆ', 'HSP, 2016.', [('sabor', 2016, 9)],
     'sabor 2016: HSP in IX. IJ while the HRS candidate stood in I. IJ; the 2015 '
     'HKS candidate (X. IJ) is not settled'),
    ('ŽELJKO NOVAKOVIĆ', 'dijaspora, 2016.', [('sabor', 2016, 11)],
     'sabor 2016: BDSH in the diaspora district while an ABU candidate stood in '
     'IV. IJ'),
    ('ŽELJKO PAVLIC', 'A-HSP, 2016.', [('sabor', 2016, 8)],
     'sabor 2016: A-HSP in VIII. IJ while the MDS leader headed the MDS list in '
     'III. IJ, as in 2014, 2015 and 2024'),
    ('ZLATKO PINTARIĆ', 'HSR, 2020.', [('sabor', 2020, 4)],
     'sabor 2020: Hrvatska stranka reda in IV. IJ while an HDS candidate stood in '
     'I. IJ'),
    ('ZORAN BRKIĆ', 'HDS, 2020.', [('sabor', 2020, 6)],
     'sabor 2020: HDS in VI. IJ while a BDSH candidate stood in IV. IJ'),
    ('ZORAN RADMAN', 'Stranka Ivana Pernara, 2024.', [('sabor', 2024, 7)],
     'sabor 2024: Stranka Ivana Pernara in VII. IJ while the Radnička fronta '
     'candidate headed its X. IJ list'),

    # --- Same party in two districts of one round. The election law lets a
    # candidate stand in one electoral district at a time, so these are two
    # people as surely as the cross-party pairs above. Both halves are
    # labelled where the person stood only in that election, since the
    # unlabelled row's year span could not tell them apart.
    ('IVANA JURIĆ', 'V. IJ, 2015.', [('sabor', 2015, 5)],
     'sabor 2015, U ime obitelji: #4 in V. IJ as plain "IVANA JURIĆ" while #14 in '
     'VII. IJ is "IVANA JURIĆ, dipl. ing." on the same party\'s list, which writes '
     'titles throughout (Excel, CSV and DB agree)'),
    ('IVANA JURIĆ', 'dipl. ing., VII. IJ, 2015.', [('sabor', 2015, 7)],
     'the titled half of the pair above'),
    ('JOSIP BABOK', 'HSGO, II. IJ 2020., III. IJ 2024.',
     [('sabor', 2020, 2), ('sabor', 2024, 3)],
     'HSGO lists carry a Josip Babok in two districts in 2020 (II. #10, VII. #1) '
     'and 2024 (III. #1, VI. #1). Each list also carries a female Babok, and '
     'they pair the listings: Janja Babok stands with the party leader every '
     'time (HBPS II. 2016, VII. 2020, EU 2024, VI. 2024), Nada Babok with this '
     'one (II. 2020 #12, III. 2024 #11)'),
    ('MIRA TUPEK', 'II. IJ, 2024.', [('sabor', 2024, 2)],
     'Umirovljenici zajedno 2024: #8 in II. IJ and #14 in V. IJ; one district '
     'per candidate, and neither stood in any other election'),
    ('MIRA TUPEK', 'V. IJ, 2024.', [('sabor', 2024, 5)],
     'the V. IJ half of the pair above'),

    # --- Lokalni: a candidate's list is scoped to its race by an
    # ElectoralDistrict numbered by the Municipality's primary key, so the
    # district number here is a municipality id (named in each comment).
    ('ANTE MARTINOVIĆ', 'Kukljica, 2021.', [('local_mayor', 2021, 298)],  # 298 Kukljica
     'načelnik 2021 round 1 in both Kukljica and Sukošan (Zadarska); one race '
     'per candidate, and neither stood in another election'),
    ('ANTE MARTINOVIĆ', 'Sukošan, 2021.', [('local_mayor', 2021, 313)],  # 313 Sukošan
     'the Sukošan half of the pair above'),
    ('MILAN KNEŽEVIĆ', 'Donji Lapac', [('local_mayor', 2025, 225)],  # 225 Donji Lapac
     'načelnik 2025 in both Donji Lapac (Ličko-senjska, both rounds) and Petlovac '
     '(Osječko-baranjska); the Petlovac one also ran there in 2021'),
    ('MILAN KNEŽEVIĆ', 'Petlovac', [('local_mayor', 2017, 347), ('local_mayor', 2021, 347),
                                    ('local_mayor', 2025, 347)],  # 347 Petlovac
     'the Petlovac half of the pair above, 2017, 2021 and 2025'),

    # Two executive races on one lokalni polling day: a candidate runs in one
    # race only, whatever its type (načelnik, gradonačelnik, zamjenik). The
    # one carved off is the side with no other elections behind it.
    ('TOMISLAV KLARIĆ', 'Brtonigla, 2021.', [('local_mayor', 2021, None, 'TOMISLAV')],
     '2021: načelnik of Brtonigla (Istarska) while the HDZ Tomislav Klarić ran '
     'for gradonačelnik of Bakar, as again in 2025 (Sabor HDZ VII./VIII. IJ)'),
    ('IVAN MILETIĆ', 'Otočac, 2025.', [('local_city_mayor', 2025, None, 'IVAN')],
     '2025: gradonačelnik of Otočac while the Lovinac načelnik candidate of 2021 '
     'ran in Lovinac again'),
    ('IVANA MARKOVIĆ', 'Čeminac, 2025.', [('local_mayor', 2025, None, 'IVANA')],
     '2025: načelnica of Čeminac (Osječko-baranjska) while the SDP Ivana Marković '
     'of Supetar (2021, 2025; Sabor X. IJ) ran in Supetar'),
    ('BARBARA KNEŽEVIĆ', 'Draž', [('local_mayor', 2021, None, 'BARBARA'),
                                  ('local_mayor', 2025, None, 'BARBARA')],
     '2021: načelnica of Draž while the Domovinski pokret Barbara Knežević ran '
     'for gradonačelnica of Zaprešić (and župan of Zagrebačka in 2025); Draž again 2025'),
    ('IVAN VIDOVIĆ', 'Biskupija, 2025.', [('local_deputy_mayor', 2025, None, 'IVAN')],
     '2025: zamjenik načelnika of Biskupija (Šibensko-kninska) while the Most '
     'Ivan Vidović (EU 2024, Sabor VIII. IJ) ran for gradonačelnik of Umag'),
    ('EDI PASTROVICCHIO', 'Bale', [('local_mayor', 2017, None, 'EDI'),
                                   ('local_mayor', 2021, None, 'EDI')],
     '2021: načelnik of Bale and gradonačelnik of Vodnjan on the same day; '
     'the Bale one also ran there in 2017, the Vodnjan one nowhere else'),
    ('EDI PASTROVICCHIO', 'Vodnjan, 2021.', [('local_city_mayor', 2021, None, 'EDI')],
     'the Vodnjan half of the pair above'),
    ('DARKO HORVAT', 'Gornji Mihaljevec, 2017.', [('local_mayor', 2017, 541)],  # 541 Gornji Mihaljevec
     '2017: načelnik of Gornji Mihaljevec while "Darko Horvat, dipl. ing. el." '
     'ran for župan of Međimurska — the HDZ electrical engineer of III. IJ'),
    ('IVAN VRKIĆ', 'Obrovac', [('local_city_mayor', 2013, 289),
                               ('local_city_mayor', 2017, 289)],  # 289 Obrovac
     '2013 and 2017: gradonačelnik of Obrovac (Zadarska) while the Osijek '
     'candidate (both rounds both years; HNS IV. IJ in 2020) ran in Osijek'),
    ('IVO MILIĆ', 'Nuštar, 2017.', [('local_mayor', 2017, 402)],  # 402 Nuštar
     '2017: načelnik of Nuštar ("Ivo Milić, bacc. ing. techn. inf.") and '
     'gradonačelnik of Trogir on the same day; neither stood in another election'),
    ('IVO MILIĆ', 'Trogir, 2017.', [('local_city_mayor', 2017, 425)],  # 425 Trogir
     'the Trogir half of the pair above'),
    ('IVAN KOVAČIĆ', 'Veliko Trojstvo', [('local_mayor', 2013, 182), ('local_mayor', 2017, 182),
                                         ('local_mayor', 2021, 182)],  # 182 Veliko Trojstvo
     '2013: načelnik of Veliko Trojstvo (Bjelovarsko-bilogorska) and of Krapinske '
     'Toplice while "dr. sc. Ivan Kovačić" ran for gradonačelnik of Omiš — the '
     'Most X. IJ candidate; Veliko Trojstvo again in 2017 and 2021'),
    ('IVAN KOVAČIĆ', 'Krapinske Toplice, 2013.', [('local_mayor', 2013, 52)],  # 52 Krapinske Toplice
     'the Krapinske Toplice third of the 2013 triple above'),
    ('IVAN VUKOVIĆ', 'Rakovica', [('local_mayor', 2009, 102),
                                  ('local_mayor', 2013, 102)],  # 102 Rakovica
     '2009 and 2013: načelnik of Rakovica while "mr. sc. Ivan Vuković, dipl. '
     'ing." ran for gradonačelnik of Ogulin — both SDP in 2009 — as he did for '
     'župan of Karlovačka in 2017 (Pametno, SDP VII. IJ)'),
    ('DARKO HORVAT', 'Breznica, 2013.', [('local_mayor', 2013, 116)],  # 116 Breznica
     '2013: načelnik of Breznica (Zagrebačka) while the HDZ Darko Horvat ran for '
     'župan of Međimurska, as in 2017'),
    ('IGOR RUBEŠA', 'Viškovo, 2013.', [('local_mayor', 2013, 218)],  # 218 Viškovo
     '2013: načelnik of Viškovo (Primorsko-goranska) while the Pisarovina '
     'candidate of 2013, 2017 and 2021 ran in Pisarovina'),
    ('IVAN MARUNICA', 'Feričanci, 2013.', [('local_mayor', 2013, 339)],  # 339 Feričanci
     '2013: načelnik of Feričanci and of Hrvace on the same day; neither stood '
     'in another election'),
    ('IVAN MARUNICA', 'Hrvace, 2013.', [('local_mayor', 2013, 437)],  # 437 Hrvace
     'the Hrvace half of the pair above'),
    ('MILAN GRAHOVAC', 'Kneževi Vinogradi, 2013.', [('local_deputy_mayor', 2013, 342)],  # 342
     '2013: zamjenik načelnika of Kneževi Vinogradi (Osječko-baranjska) while the '
     'Đulovac načelnik candidate of 2013 and 2017 ran in Đulovac'),

    # 2009 prints each executive candidate's nominating parties, which the
    # Excel years do not, so the evidence below names them.
    ('LUKA ZUBČIĆ', 'Belišće, 2009.', [('local_city_mayor', 2009, 321)],  # 321 Belišće
     '2009: "mr. sc. Luka Zubčić" for gradonačelnik of Belišće (HDZ, HSLS, HSP, '
     'HSS) and an independent Luka Zubčić for načelnik of Posedarje (Zadarska)'),
    ('LUKA ZUBČIĆ', 'Posedarje, 2009.', [('local_mayor', 2009, 305)],  # 305 Posedarje
     'the Posedarje half of the pair above'),
    ('JOSIP HORVAT', 'Krapina, 2009.', [('local_city_mayor', 2009, 37)],  # 37 Krapina
     '2009: three Josip Horvats on one polling day — gradonačelnik of Krapina '
     '(HDZ), of Delnice (SDP, HNS) and načelnik of Beretinec (independent). '
     'Which, if any, is the HSR Sabor candidate of 2016/2020 is not settled'),
    ('JOSIP HORVAT', 'Delnice, 2009.', [('local_city_mayor', 2009, 188)],  # 188 Delnice
     'the Delnice third of the triple above'),
    ('JOSIP HORVAT', 'Beretinec, 2009.', [('local_mayor', 2009, 115)],  # 115 Beretinec
     'the Beretinec third of the triple above, both rounds'),
    ('JOSIP TOMIĆ', 'Fužine, 2009.', [('local_mayor', 2009, 202)],  # 202 Fužine
     '2009: "Josip Tomić, dipl. theol." for načelnik of Fužine (HSS, HNS; both '
     'rounds) and an independent for načelnik of Dugi Rat'),
    ('JOSIP TOMIĆ', 'Dugi Rat, 2009.', [('local_mayor', 2009, 434)],  # 434 Dugi Rat
     'the Dugi Rat half of the pair above'),
    ('STJEPAN ŽIVKOVIĆ', 'Drenje, 2009.', [('local_mayor', 2009, 335)],  # 335 Drenje
     '2009: načelnik of Drenje (HDZ) while the HSS Stjepan Živković ran in '
     'Magadenovac, as again 2013-2021'),
    ('ŽELJKO VILJEVAC', 'Gradina, 2009.', [('local_mayor', 2009, 238)],  # 238 Gradina
     '2009: "Željko Viljevac, dipl. ing." for načelnik of Gradina (HSP, HSU) '
     'while the HDSSB-HSS Željko Viljevac ran in Viljevo, as again 2013-2017'),
    ('FRANJO TUĐMAN', 'Luka, 1997.', [('local_council_ward', 1997, 2402)],  # Luka, ward II
     '1997: an HDZ candidate in a single-member ward of the Luka općinsko '
     'vijeće — a namesake, not the President, who stood for no local office'),
]

# Names `--suggest` flags on a weak signal (a long gap, two residences) but
# that were checked and are one person, so the report stops raising them.
KNOWN_SAME = {
}

GAP_YEARS = 15

# Lokalni types whose candidates are people (council lists are party tickets),
# split by the level of the race; their lists' district number is the primary
# key of that municipality or county (see LocalImporter._race_district).
LOCAL_MUNI_RACES = {'local_mayor', 'local_city_mayor', 'local_deputy_mayor',
                    'local_deputy_city_mayor'}
LOCAL_COUNTY_RACES = {'local_county_prefect', 'local_deputy_county_prefect'}


class Command(BaseCommand):
    help = 'Split curated same-name Person rows into the different people they hold'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be split without changing anything')
        parser.add_argument('--suggest', action='store_true',
                            help='List Persons that look like more than one person, then exit')

    def handle(self, *args, **options):
        if options['suggest']:
            self._suggest()
            return

        dry_run = options['dry_run']
        self._label_birth_years(dry_run)
        moved = 0
        for name, label, selectors, evidence in KNOWN_DISTINCT:
            normalized = normalize_person_name(name)
            picked = [c for c in self._candidacies(normalized)
                      if any(self._matches(c, sel) for sel in selectors)
                      and c.person.disambiguation != label]
            if not picked:
                if not dry_run:
                    self._drop_empty(normalized)
                continue
            self.stdout.write(f'  {name} -> "{label}": {len(picked)} candidacy(ies)\n     {evidence}')
            for c in picked:
                self.stdout.write(f'       {self._describe(c)}')
            if not dry_run:
                self._move(normalized, label, picked)
            moved += len(picked)

        action = 'Would move' if dry_run else 'Moved'
        self.stdout.write(self.style.SUCCESS(f'{action} {moved} candidacy(ies) to namesakes'))

    def _label_birth_years(self, dry_run):
        """Move a birth-year suffix out of a stored name into its label.

        DIP appends "rođ. 1962." where two candidates share a name, and older
        imports kept it in the surname ("RADOŠ rođ. 1962."), which hid the
        person from a plain-name search. The importer now splits it off on the
        way in; this converts rows stored before that.
        """
        for person in Person.objects.filter(disambiguation='', normalized_name__iregex=r'ROD\.?\s*[0-9]{4}'):
            full = f'{person.first_name} {person.last_name}'
            bare, label = split_birth_year(full)
            if not label:
                continue
            normalized = normalize_person_name(bare)
            twin = Person.objects.filter(normalized_name=normalized, disambiguation=label).first()
            self.stdout.write(f'  {full} -> {bare} ({label})' + (f' merged into id={twin.pk}' if twin else ''))
            if dry_run:
                continue
            if twin:
                from .merge_person_aliases import Command as Merge
                Merge._absorb(twin, person)
            else:
                person.first_name, person.last_name = parse_person_name(bare)
                person.normalized_name = normalized
                person.disambiguation = label
                person.save(update_fields=['first_name', 'last_name', 'normalized_name',
                                           'disambiguation'])

    @staticmethod
    def _candidacies(normalized):
        return list(
            Candidacy.objects
            .filter(person__normalized_name=normalized)
            .select_related('person', 'electoral_list__district',
                            'electoral_list__election_round__election__election_type')
        )

    @staticmethod
    def _matches(candidacy, selector):
        slug, year, district, prefix = (tuple(selector) + (None, None))[:4]
        el = candidacy.electoral_list
        election = el.election_round.election
        if election.election_type.slug != slug or election.year != year:
            return False
        if district is not None and (el.district is None or el.district.number != district):
            return False
        return prefix is None or el.name.upper().startswith(prefix.upper())

    @staticmethod
    def _move(normalized, label, candidacies):
        """Repoint the candidacies, and the seats won with them, to the
        labelled namesake, creating it on first use.

        ParliamentMember is unique per (election, person); a seat the namesake
        already holds for that election is the same membership twice, and the
        moving copy is dropped.
        """
        source = candidacies[0].person
        with transaction.atomic():
            target, _ = Person.objects.get_or_create(
                normalized_name=normalized, disambiguation=label,
                defaults={'first_name': source.first_name, 'last_name': source.last_name})
            ids = [c.pk for c in candidacies]
            Candidacy.objects.filter(pk__in=ids).update(person=target)
            seats = ParliamentMember.objects.filter(candidacy_id__in=ids).exclude(person=target)
            taken = set(ParliamentMember.objects.filter(person=target)
                        .values_list('election_id', flat=True))
            seats.filter(election_id__in=taken).delete()
            seats.update(person=target)
            Command._drop_empty(normalized)

    @staticmethod
    def _drop_empty(normalized):
        """Delete same-named rows left holding nothing: a namesake emptied by a
        relabel, or the unlabelled row once every candidacy is carved off
        (a re-import recreates it empty, as it finds each candidacy on its
        namesake, so this also runs when there is nothing left to move)."""
        for person in Person.objects.filter(normalized_name=normalized):
            if (not person.candidacies.exists()
                    and not person.parliament_memberships.exists()):
                person.delete()

    # ---- --suggest -----------------------------------------------------

    def _suggest(self):
        by_person = defaultdict(list)
        for c in (Candidacy.objects
                  .select_related('person', 'electoral_list__district',
                                  'electoral_list__election_round__election__election_type')):
            by_person[c.person].append(c)

        same_round_diff, same_round_same, residence, gap, places = [], [], [], [], []
        for person, cands in by_person.items():
            rounds = defaultdict(list)
            for c in cands:
                rounds[self._polling_key(c)].append(c)
            clashes = [cs for cs in rounds.values() if len(cs) > 1]
            if clashes:
                parties = [{self._party(c) for c in cs} for cs in clashes]
                (same_round_diff if any(len(p) > 1 for p in parties)
                 else same_round_same).append(person)
                continue
            if self._name(person) in KNOWN_SAME:
                continue
            homes = {c.residence.upper() for c in cands if c.residence}
            if len(homes) > 1:
                residence.append(person)
                continue
            munis = {c.electoral_list.district.number for c in cands
                     if c.electoral_list.district
                     and c.electoral_list.election_round.election.election_type.slug
                     in LOCAL_MUNI_RACES}
            if len(munis) > 1:
                places.append(person)
                continue
            years = sorted({c.electoral_list.election_round.election.year for c in cands})
            if any(b - a >= GAP_YEARS for a, b in zip(years, years[1:])):
                gap.append(person)

        sections = [
            ('Same round, different parties — two people', same_round_diff),
            ('Same round, same party in two districts — two people (one district per candidate)',
             same_round_same),
            ('1990: different places of residence', residence),
            ('Lokalni: executive races in different municipalities', places),
            (f'A gap of {GAP_YEARS}+ years between elections', gap),
        ]
        for title, persons in sections:
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n{title} ({len(persons)})'))
            for person in sorted(persons, key=lambda p: (p.normalized_name, p.disambiguation)):
                label = f' ({person.disambiguation})' if person.disambiguation else ''
                self.stdout.write(f'\n  {self._name(person)}{label}  id={person.pk}')
                for c in sorted(by_person[person], key=self._sort_key):
                    self.stdout.write(f'     {self._describe(c)}')

    @staticmethod
    def _polling_key(c):
        """What "the same round" means for a clash. Lokalni races of every
        type share one polling day, and a candidate runs in one race only, so
        a načelnik in one place and a gradonačelnik or zamjenik in another on
        that day are two people too; other types clash within their round."""
        er = c.electoral_list.election_round
        slug = er.election.election_type.slug
        if slug.startswith('local') and slug not in ('local_municipal_council',
                                                     'local_city_council',
                                                     'local_county_assembly'):
            return ('local', er.election.year, er.round_number)
        return er.id

    @staticmethod
    def _sort_key(c):
        er = c.electoral_list.election_round
        return (er.election.year, er.election.election_type.slug, er.round_number)

    @staticmethod
    def _party(candidacy):
        name = candidacy.electoral_list.name.split('\n', 1)[0]
        return name.split(',', 1)[0].strip().upper()

    _places = None

    @classmethod
    def _place(cls, slug, number):
        if cls._places is None:
            cls._places = {
                'muni': dict(Municipality.objects.values_list('pk', 'name')),
                'county': dict(County.objects.values_list('pk', 'name')),
            }
        if slug in LOCAL_MUNI_RACES:
            return cls._places['muni'].get(number, number)
        if slug in LOCAL_COUNTY_RACES:
            return cls._places['county'].get(number, number)
        return f'd{number}'

    @classmethod
    def _describe(cls, c):
        el = c.electoral_list
        er = el.election_round
        slug = er.election.election_type.slug
        where = cls._place(slug, el.district.number) if el.district else '-'
        residence = f'  [{c.residence}]' if c.residence else ''
        return (f'{er.election.election_type.slug} {er.election.year} r{er.round_number} '
                f'{where} #{c.position_on_list}  {cls._party(c)[:60]}{residence}')

    @staticmethod
    def _name(person):
        return f'{person.first_name} {person.last_name}'.strip()
