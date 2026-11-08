import re
import unicodedata


# Croatian DIP CSVs occasionally split candidate names across "tokens" with a
# stray comma (e.g. "KOLINDA GRABAR-, KITAROVIĆ") and prefix or suffix academic
# titles ("prof.dr.sc. MILAN , KUJUNDŽIĆ", "IVAN SINČIĆ, , univ.bacc.ing.el.").
# Strip both so the same person hashes to the same normalized_name across
# election years.
# NB: 'sci' precedes 'sc' so the longer spelling wins the alternation — 2003
# writes "mr.sci. STIPE ČIZMIĆ" where other years write "mr.sc.".
# 'oecc' and 'akad' likewise precede 'oec' and 'ak' ("OECC. NADAN VIDOŠEVIĆ",
# "AK. ŽELJKO BUJAS"); 'stom' and 'prim' are the dental and senior-physician
# titles ("DR.STOM.", "prim. dr. med.").
_TITLE_TOKENS = (r'(prof|doc|dr|mr|mag|dipl|univ|bacc|ing|spec|oecc|oec|iur|med|stom|prim'
                 r'|sci|sc|akad|ak|art|struc|struč)')

# A leading run of academic-title tokens, each either a title word followed by
# a dot — run together ("prof.dr.sc.") or space-separated ("prof. dr. sc.") —
# or a spelled-out title with no dot ("akademik", "akademkinja"). Real name
# tokens are never dotted and never these words, so this can't eat a name.
_LEADING_TITLES_RE = re.compile(
    r'^(?:(?:' + _TITLE_TOKENS + r'\.|(?:akademik|akademkinja)\b)\s*)+',
    re.IGNORECASE)


def _strip_titles(s):
    """Remove leading and trailing academic-title runs, leaving any comma that
    is not part of a title intact."""
    # Leading academic prefix, e.g. "prof.dr.sc. MILAN" or "dr. sc. DRAGO".
    s = _LEADING_TITLES_RE.sub('', s)
    # Trailing academic tail after a comma (e.g. ", univ.bacc.ing.el.")
    return re.sub(r',\s*' + _TITLE_TOKENS + r'\b.*$', '', s, flags=re.IGNORECASE)


# One whitespace-separated token made only of dotted titles ("DR.MED.", "dr.").
_TITLE_WORD_RE = re.compile(r'^(?:' + _TITLE_TOKENS + r'\.)+$', re.IGNORECASE)
# Titles whose dot was lost: OCR of the 1993/1997 scans ("MED BRANKO FOTIVEC",
# "ING LIVIO BOLKOVIĆ"), the 1990 report ("MR MIROSLAV KIRINČIĆ") and list
# leaders ("DR BRUNO SAVRON"). Only ever leading, and only before a full name.
_BARE_LEADING_TITLES = {'DR', 'MR', 'MED', 'ING', 'INŽ', 'OECC'}
# A father's name telling namesakes apart ("IVICA KLANAC, sin IVE"):
# `split_birth_year` makes it the person's label, so it must survive here.
_PATRONYMIC_RE = re.compile(r'\s+(?:sin|kći)\s+\S+$', re.IGNORECASE)
# "pok. Ivan" / "POK DARKA": a late father's name, not part of the person's.
_LATE_FATHER_RE = re.compile(r'\s+pok\.?\s+\S+$', re.IGNORECASE)
# A word of a name or a title: letters, with inner hyphens, apostrophes, dots,
# and maybe the comma the 2013/2017 files put before an occupation
# ("MILAN RODIĆ, magistar prava").
_PLAIN_WORD_RE = re.compile(r"^[^\W\d_][^\W\d_.'-]*(?:[.'-][^\W\d_]*)*\.?,?$")


def _strip_loose_titles(s):
    """Remove titles and occupations written without the comma the trailing
    rule needs, from a name printed in capitals.

    The 2013/2017 lokalni files type occupations into the name column in
    lowercase ("IVAN TRGOVEC magistar prava", "PERO VRŽOGIĆ prim. dr. med."),
    the 1995 Sabor report appends titles in capitals ("BOŽIDAR ČOHAR DR.MED."),
    and one ethnicity slipped in ("ROBERT RADOJKOVIĆ Talijan"). In a name
    whose own words are all capitals, any leading or trailing word with a
    lowercase letter is therefore not part of it; a dotted title word is
    dropped at either end whatever the case. Names written in title case
    ("Zlatko Prpić") only lose dotted title words.
    """
    patronymic = ''
    m = _PATRONYMIC_RE.search(s)
    if m:
        s, patronymic = s[:m.start()], m.group(0)
    s = _LATE_FATHER_RE.sub('', s)
    words = s.split()
    # Only a bare name: the cleaner also sees list labels ("Hrvatska stranka
    # prava - HSP", "DAVOR FERENC (Nezavisni kandidat)"), which carry a dash,
    # brackets, commas or digits and must come through untouched.
    if not all(_PLAIN_WORD_RE.match(w) for w in words):
        return s + patronymic
    caps = [i for i, w in enumerate(words) if not any(c.islower() for c in w)
            and not _TITLE_WORD_RE.match(w)]
    in_caps = len(caps) >= 2 and caps == list(range(caps[0], caps[-1] + 1))

    def junk(w):
        return bool(_TITLE_WORD_RE.match(w)) or (in_caps and any(c.islower() for c in w))

    while len(words) > 2 and junk(words[-1]):
        words.pop()
    while len(words) > 2 and (junk(words[0]) or (
            words[0] in _BARE_LEADING_TITLES and len(words) >= 3)):
        words.pop(0)
    return ' '.join(words) + patronymic


def clean_candidate_name(raw):
    """Strip academic titles and stray commas from a CSV candidate column."""
    s = _strip_loose_titles(_strip_titles((raw or '').strip()))
    # Collapse stray ", " into a single space; drop any remaining bare commas.
    # NB: a ", rođ. 1962." disambiguator survives this (minus its comma) on
    # purpose — DIP uses it to tell two same-named candidates apart, so
    # dropping it would merge them into one Person.
    s = s.replace(', ', ' ').replace(',', '')
    # Fix hyphenated surnames split with a space (e.g. "GRABAR- KITAROVIĆ").
    s = re.sub(r'-\s+', '-', s)
    return ' '.join(s.split())


# A birth-year disambiguator DIP appends when two candidates share a name
# ("JOZO RADOŠ, rođ. 1962."). Not a title, but equally not part of the name.
_BIRTH_YEAR_RE = re.compile(r',\s*ro[đd]\.?\s*\d{4}\.?\s*$', re.IGNORECASE)

# The same disambiguator as a whole suffix, in every shape the files use:
# "JOZO RADOŠ, rođ. 1962.", "MILJENKO MARIĆ; rođ. 1970.", "IVAN PAVUSA rođ.1962."
# (clean_candidate_name has already dropped the comma by the time most names
# reach the importer).
_BIRTH_SUFFIX_RE = re.compile(r'[,;]?\s*ro[đd]\.?\s*(\d{4})\.?\s*$', re.IGNORECASE)


def split_birth_year(name):
    """("JOZO RADOŠ", "rođ. 1962.") from "JOZO RADOŠ, rođ. 1962.", else (name, '').

    The suffix tells namesakes apart, so it belongs in Person.disambiguation:
    kept in the name it hides the person from a plain-name search and from
    every other election they stood in.
    """
    m = _BIRTH_SUFFIX_RE.search(name or '')
    if m:
        return name[:m.start()].strip(), f'rođ. {m.group(1)}.'
    # A father's name does the same job: 2017 ran two "IVICA KLANAC" for one
    # načelnik, printed "IVICA KLANAC, sin IVE" and "…, sin DRAGUTINA".
    m = re.search(r'[,;]?\s+(sin|kći)\s+(\S+)$', name or '', re.IGNORECASE)
    if m:
        return name[:m.start()].strip(), f'{m.group(1).lower()} {m.group(2).capitalize()}'
    return name, ''


# A personal-name token: letters only, optionally hyphenated or apostrophed.
_NAME_TOKEN_RE = re.compile(r"^[^\W\d_]+(?:[-'][^\W\d_]+)*$", re.UNICODE)


def looks_like_person_name(text):
    """True if `text` reads as an individual's name rather than a party or
    coalition name.

    Used to find list-group boundaries in variable-width Sabor headers, where
    a list-name column is followed by a run of candidate-name columns. Titles
    and birth-year suffixes are stripped first, so "IVANA BUNTIĆ, mag. iur."
    is recognised as a person even though the raw string contains a comma.
    A party name that survives stripping still gives itself away with a comma,
    a digit, or a token count outside the 2-4 range typical of personal names.
    """
    s = _strip_titles(_BIRTH_YEAR_RE.sub('', (text or '').strip()))
    if ',' in s:
        return False
    tokens = s.split()
    if not 2 <= len(tokens) <= 4:
        return False
    return all(_NAME_TOKEN_RE.match(tok) for tok in tokens)


# "GRAD X" / "OPĆINA X" prefixes are administrative qualifiers some DIP files
# include and others omit, which otherwise splits a place into two rows.
_MUNI_PREFIX_RE = re.compile(r'^(GRAD|OP[ĆC]INA)\s+')


def normalize_municipality_name(name):
    """Canonical key for matching a municipality name across imports: drop the
    GRAD/OPĆINA prefix and collapse hyphen/space variants
    (e.g. 'ZLATAR-BISTRICA' == 'ZLATAR BISTRICA')."""
    n = (name or '').upper().strip()
    n = _MUNI_PREFIX_RE.sub('', n)
    n = re.sub(r'\s*-\s*', ' ', n)
    return re.sub(r'\s+', ' ', n).strip()


def strip_diacritics(text):
    """Remove diacritical marks from text (e.g. Č→C, Š→S, Ž→Z, Đ→D)."""
    # Handle Đ/đ specially since NFKD doesn't decompose it
    text = text.replace('Đ', 'D').replace('đ', 'd')
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')


def place_key(name, location='', address=''):
    """Which place a polling station is, for matching it across years.

    Station numbers are not: DIP renumbers them between elections (Grad
    Zagreb's Odranski Strmec is 605 in 2021 and 604 in 2025). The place is the
    building and address; the station's name (usually its mjesni odbor) is
    only used when neither is given. Case, diacritics, spacing and
    punctuation are ignored. An empty key means the source named no place.
    """
    def norm(s):
        return re.sub(r'[^0-9A-Z]', '', strip_diacritics((s or '').upper()))
    loc = norm(location) + '|' + norm(address)
    if loc != '|':
        return loc
    return 'N|' + norm(name) if norm(name) else ''


def normalize_person_name(full_name):
    """Normalize a full name for cross-election matching.

    Returns uppercase, diacritics-stripped version.
    """
    name = full_name.strip()
    name = strip_diacritics(name)
    name = name.upper()
    # Collapse multiple spaces
    name = ' '.join(name.split())
    return name


def parse_person_name(full_name):
    """Parse 'FIRST LAST' or 'FIRST MIDDLE LAST' into (first_name, last_name).

    Croatian convention in CSV: names are uppercase, typically FIRST LAST.
    For compound last names like SELAK RASPUDIĆ, we take the first token as
    first_name and everything else as last_name.
    """
    parts = full_name.strip().split()
    if len(parts) == 0:
        return ('', '')
    if len(parts) == 1:
        return (parts[0], '')
    first_name = parts[0]
    last_name = ' '.join(parts[1:])
    return (first_name, last_name)
