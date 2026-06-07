import csv
import re
import os
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


def extract_location(title: str, description: str):
    """
    Returns (place_name, lat, lon) or (place_name, None, None).
    lat/lon are non-None only when the gazetteer provides coordinates directly.
    """
    text = f"{title} {description[:600]}"

    # Pass 1: gazetteer match — specific entries first, country-level as last resort
    gazetteer = _load_gazetteer()
    text_lower = text.lower()
    country_fallback = None
    for entry in gazetteer:
        if entry['name'].lower() in text_lower:
            if entry['type'] == 'country':
                # Record but don't return yet — prefer any specific match
                if country_fallback is None:
                    country_fallback = (entry['name'], entry['lat'], entry['lon'])
            else:
                return entry['name'], entry['lat'], entry['lon']
    if country_fallback:
        return country_fallback

    # Pass 2: spaCy NER
    nlp = _load_nlp()
    if nlp is None:
        return None, None, None

    try:
        doc = nlp(text[:1000])
        candidates = [
            ent.text.strip()
            for ent in doc.ents
            if ent.label_ in ('GPE', 'LOC') and len(ent.text.strip()) > 2
        ]
        if not candidates:
            logger.debug("spaCy found no GPE/LOC entities")
            return None, None, None
        # Prefer longer, more specific names
        best = max(candidates, key=len)
        return best, None, None
    except Exception as e:
        logger.warning(f"spaCy NER failed: {e}")
        return None, None, None
