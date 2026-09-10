from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

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
    # 7. saziv (2011-2015). 152 names for 151 seats: Zoran Vasić held Marina
    # Lovrić Merzel's seat while hers was in mirovanje (she was Sisak-Moslavina
    # prefect) and left when she reactivated it on 11 Sep 2014. Party labels
    # are the caucus as of the term, so members who switched (Holy → ORaH,
    # Kajin/Grubišić/Kregar/Linić → nezavisni) show their later affiliation.
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
        ('INGRID ANTIČEVIĆ MARINOVIĆ', 'SDP', False, ''),
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
        ('MARINA LOVRIĆ MERZEL', 'nezavisna', False, 'reaktivirala mandat 11. rujna 2014.'),
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
        ('IVAN ŠIMUNOVIĆ', 'HSP dr. Ante Starčević', False, 'mandat počeo 1. srpnja 2013.'),
        ('VESNA ŠKARE OŽBOLT', 'DC', False, 'prestanak mirovanja mandata od 18. veljače 2014.'),
        ('MARIJAN ŠKVARIĆ', 'HNS', False, ''),
        ('DUNJA ŠPOLJAR', 'SDP', False, ''),
        ('IVAN ŠUKER', 'HDZ', False, ''),
        ('NANSI TIRELI', 'Hrvatski laburisti - Stranka rada', False, ''),
        ('DAMIR TOMIĆ', 'SDP', False, ''),
        ('MIROSLAV TUĐMAN', 'HDZ', False, ''),
        ('NADA TURINA-ĐURIĆ', 'HNS', False, ''),
        ('ZLATKO TUŠAK', 'Hrvatski laburisti - Stranka rada', False, ''),
        ('ZORAN VASIĆ', 'SDP', False, 'zastupnik do 11. rujna 2014.'),
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
                person = Person.objects.filter(normalized_name=normalized).first()
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
            by_party[party] = by_party.get(party, 0) + 1
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
        if new_persons:
            self.stdout.write(
                'Review the NEW PERSON rows with `merge_person_aliases --suggest` — '
                'a middle-name variant may already exist under another spelling.'
            )
