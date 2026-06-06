import re
import unicodedata


# Croatian DIP CSVs occasionally split candidate names across "tokens" with a
# stray comma (e.g. "KOLINDA GRABAR-, KITAROVIĆ") and prefix or suffix academic
# titles ("prof.dr.sc. MILAN , KUJUNDŽIĆ", "IVAN SINČIĆ, , univ.bacc.ing.el.").
# Strip both so the same person hashes to the same normalized_name across
# election years.
_TITLE_TOKENS = r'(prof|doc|dr|mr|mag|dipl|univ|bacc|ing|spec|oec|iur|med|sc|akad|struc|struč)'


def clean_candidate_name(raw):
    """Strip academic titles and stray commas from a CSV candidate column."""
    s = (raw or '').strip()
    # Leading academic prefix (e.g. "prof.dr.sc. MILAN")
    s = re.sub(r'^(prof\.dr\.sc\.|doc\.dr\.sc\.|dr\.sc\.|mr\.sc\.|prof\.|doc\.|dr\.|mr\.|mag\.\w*\.?|dipl\.\w*\.?)\s+',
               '', s, flags=re.IGNORECASE)
    # Trailing academic tail after a comma (e.g. ", univ.bacc.ing.el.")
    s = re.sub(r',\s*' + _TITLE_TOKENS + r'\b.*$', '', s, flags=re.IGNORECASE)
    # Collapse stray ", " into a single space; drop any remaining bare commas.
    s = s.replace(', ', ' ').replace(',', '')
    # Fix hyphenated surnames split with a space (e.g. "GRABAR- KITAROVIĆ").
    s = re.sub(r'-\s+', '-', s)
    return ' '.join(s.split())


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
