import unicodedata


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
