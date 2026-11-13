"""Load the official register of political parties into RegisteredParty.

Source: "Registar političkih stranaka Republike Hrvatske" on data.gov.hr,
published daily by Ministarstvo pravosuđa, uprave i digitalne transformacije
under the Otvorena dozvola licence; the "Stranke" CSV resource. One row per
party ever registered (436 in November 2026: 157 AKTIVAN, 279 PRESTANAK),
with name, short name, OIB, seat, registration date and the date of its
current status (for PRESTANAK, when it ceased).

    python manage.py import_party_register              # download the current CSV
    python manage.py import_party_register --file x.csv # or read a saved copy

Rows are keyed on REGISTARSKI_BROJ and updated in place, so a re-run only
refreshes them; the register never drops a party, so nothing is deleted.
"""
import csv
import io
import urllib.request
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from elections.models import RegisteredParty

CSV_URL = ('https://data.gov.hr/ckan/dataset/197ea086-e03b-42d1-b3c1-0496c85faf1e/'
           'resource/cdbeedb3-6de8-4465-8057-b508decdd2d6/download/data.csv')


def _date(text):
    """'10/30/2003 12:00:00 AM' -> date(2003, 10, 30); blank -> None."""
    text = (text or '').strip()
    if not text:
        return None
    for fmt in ('%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y', '%Y-%m-%d', '%d.%m.%Y.'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise CommandError(f'unreadable date: {text!r}')


class Command(BaseCommand):
    help = 'Load the official register of political parties (data.gov.hr) into RegisteredParty'

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Read this CSV instead of downloading it')

    def handle(self, *args, file=None, **options):
        if file:
            raw = open(file, 'rb').read()
        else:
            req = urllib.request.Request(CSV_URL, headers={'User-Agent': 'projekt-izbori'})
            raw = urllib.request.urlopen(req, timeout=120).read()
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        need = {'REGISTARSKI_BROJ', 'NAZIV', 'SKRACENI_NAZIV', 'STATUS', 'DATUM_UPISA', 'DATUM_STATUSA'}
        if not rows or not need <= set(rows[0]):
            raise CommandError(f'unexpected columns: {list(rows[0]) if rows else "no rows"}')
        created = updated = 0
        with transaction.atomic():
            for r in rows:
                _, new = RegisteredParty.objects.update_or_create(
                    registry_number=int(r['REGISTARSKI_BROJ']),
                    defaults={
                        'name': r['NAZIV'].strip(),
                        'short_name': r['SKRACENI_NAZIV'].strip(),
                        'oib': r.get('OIB', '').strip(),
                        'seat': r.get('SJEDISTE', '').strip(),
                        'status': r['STATUS'].strip(),
                        'registered_on': _date(r['DATUM_UPISA']),
                        'status_on': _date(r['DATUM_STATUSA']),
                    })
                created += new
                updated += not new
        active = RegisteredParty.objects.filter(status='AKTIVAN').count()
        self.stdout.write(self.style.SUCCESS(
            f'{created} added, {updated} updated; {RegisteredParty.objects.count()} parties, {active} active'))
