import csv
import os
import re
import logging

logger = logging.getLogger(__name__)

GAZETTEER_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'india_pa_gazetteer.csv')

_gazetteer = None


def _load_gazetteer():
    global _gazetteer
    if _gazetteer is not None:
        return _gazetteer
    _gazetteer = []
    try:
        with open(GAZETTEER_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                _gazetteer.append({
                    'name': row['name'].strip(),
                    'lat': float(row['lat']),
                    'lon': float(row['lon']),
                    'type': row['type'].strip(),
                })
        # Longest names first — greedily prefer more-specific matches
        _gazetteer.sort(key=lambda x: len(x['name']), reverse=True)
    except Exception as e:
        logger.warning(f"Failed to load gazetteer: {e}")
    return _gazetteer


_nlp = None


def _load_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load('en_core_web_trf')
        except Exception as e:
            logger.warning(f"spaCy model load failed: {e}")
            _nlp = False
    return _nlp if _nlp is not False else None


# Pre-compiled regex cache: entry name → word-boundary pattern
_re_cache: dict = {}

def _word_match(name_lower: str, text_lower: str) -> bool:
    """Return True if name appears as a whole word (or phrase) in text."""
    if name_lower not in _re_cache:
        # Escape special regex chars, then wrap with word boundaries
        escaped = re.escape(name_lower)
        _re_cache[name_lower] = re.compile(r'\b' + escaped + r'\b')
    return bool(_re_cache[name_lower].search(text_lower))


def _gazetteer_scan(text_lower: str, gazetteer: list):
    """
    Scan text for gazetteer entries using word-boundary matching.
    Returns the first non-country match (most specific wins due to sort order).
    Country-type entries are stored separately as a last resort.
    Returns (name, lat, lon) or None.
    """
    country_fallback = None
    for entry in gazetteer:
        if _word_match(entry['name'].lower(), text_lower):
            if entry['type'] == 'country':
                if country_fallback is None:
                    country_fallback = (entry['name'], entry['lat'], entry['lon'])
            else:
                return (entry['name'], entry['lat'], entry['lon'])
    return country_fallback  # None or ('India', ...) as absolute last resort


def extract_location(title: str, description: str):
    """
    Returns (place_name, lat, lon) or (None, None, None).
    Never returns ('India', ...) — articles with no specific location return None.

    Strategy:
      1. Scan headline only first — title is the most reliable location signal.
         If a specific (non-country) match is found, return it immediately.
      2. Scan headline + first 600 chars of description.
         If a specific match is found, return it.
      3. spaCy NER fallback (when available).
      4. Return None — caller will skip the article.
    """
    gazetteer = _load_gazetteer()

    # Pass 1: title only
    match = _gazetteer_scan(title.lower(), gazetteer)
    if match and match[0] != 'India':
        return match

    # Pass 2: title + description
    full_lower = (title + ' ' + description[:250]).lower()
    match = _gazetteer_scan(full_lower, gazetteer)
    if match and match[0] != 'India':
        return match

    # Pass 3: spaCy NER (graceful — returns None when spaCy not installed)
    nlp = _load_nlp()
    if nlp:
        try:
            doc = nlp((title + ' ' + description[:250])[:1000])
            candidates = [
                ent.text.strip()
                for ent in doc.ents
                if ent.label_ in ('GPE', 'LOC') and len(ent.text.strip()) > 2
            ]
            if candidates:
                best = max(candidates, key=len)
                return best, None, None
        except Exception as e:
            logger.warning(f"spaCy NER failed: {e}")

    # No specific Indian location found — skip article
    return None, None, None
