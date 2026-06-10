#!/usr/bin/env python3
"""
Regional-language wildlife news pipeline.

Fetches RSS feeds in Malayalam, Hindi, Assamese (and other Indian languages).
Translates headline + description snippet to English, then runs the same
keyword-filter → gazetteer → spaCy → Nominatim pipeline as the English feed.

Outputs: docs/regional/news.json
  Each article carries both the original-language headline AND the English
  translation so the UI can show the original while searching/categorising
  using the English text.

Zero paid APIs:
  - deep-translator uses Google Translate's public endpoint (no key needed)
  - Nominatim geocoding with mandatory 1s delay
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import feedparser
from dateutil import parser as dateparser

sys.path.insert(0, os.path.dirname(__file__))
from extractor import extract_location
from geocoder import geocode

# Reuse keyword matching logic from main pipeline
from fetch_and_process import (
    KEYWORDS, EXCLUDE_KEYWORDS,
    fix_encoding, matches_keywords, parse_date,
    USER_AGENT, fetch_feed,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ── Regional sources ────────────────────────────────────────────────────────
# Each entry: {'url': ..., 'source': ..., 'lang': ..., 'lang_code': ...}
# lang_code follows ISO 639-1 (used by deep-translator / Google Translate)

REGIONAL_SOURCES = [
    # ── Malayalam (Kerala) ──────────────────────────────────────────────────
    # Mathrubhumi — Kerala's largest-circulation daily; strong forest & wildlife beat
    {
        'url': 'https://www.mathrubhumi.com/rss/news',
        'source': 'Mathrubhumi',
        'lang': 'Malayalam',
        'lang_code': 'ml',
    },
    # Manorama Online — major Kerala daily; covers Periyar, Wayanad, Silent Valley
    {
        'url': 'https://www.manoramaonline.com/rss/news.xml',
        'source': 'Manorama Online',
        'lang': 'Malayalam',
        'lang_code': 'ml',
    },

    # ── Hindi (UP, MP, Uttarakhand, HP, Bihar, Rajasthan) ──────────────────
    # Dainik Jagran — largest Hindi daily; strong UP / Uttarakhand / MP coverage
    {
        'url': 'https://www.jagran.com/rss/news-national.xml',
        'source': 'Dainik Jagran',
        'lang': 'Hindi',
        'lang_code': 'hi',
    },
    # Amar Ujala — UP / Uttarakhand focus; Dudhwa, Corbett, Pilibhit coverage
    {
        'url': 'https://www.amarujala.com/rss/india-news.xml',
        'source': 'Amar Ujala',
        'lang': 'Hindi',
        'lang_code': 'hi',
    },
    # Patrika — MP / Rajasthan focused; Kanha, Bandhavgarh, Ranthambore
    {
        'url': 'https://api.patrika.com/rss/india-news',
        'source': 'Patrika',
        'lang': 'Hindi',
        'lang_code': 'hi',
    },

    # ── Assamese (Assam / Northeast) ────────────────────────────────────────
    # Pratidin Time — Assam's leading Assamese daily; Kaziranga, Manas, Dibru-Saikhowa
    {
        'url': 'https://pratidintime.com/feed/',
        'source': 'Pratidin Time',
        'lang': 'Assamese',
        'lang_code': 'as',
    },
    # Asomiya Pratidin — major Assamese-language daily
    {
        'url': 'https://asomiyapratidin.in/feed/',
        'source': 'Asomiya Pratidin',
        'lang': 'Assamese',
        'lang_code': 'as',
    },

    # ── Telugu (Andhra Pradesh / Telangana) ──────────────────────────────────
    # Sakshi — major Telugu daily (direct RSS works); AP/TG wildlife, forests
    {
        'url': 'https://www.sakshi.com/rss.xml',
        'source': 'Sakshi',
        'lang': 'Telugu',
        'lang_code': 'te',
    },
    # Eenadu via Google News — largest Telugu daily; Nagarjunasagar, Kawal, Papikonda
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:eenadu.net'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Eenadu',
        'lang': 'Telugu',
        'lang_code': 'te',
    },

    # ── Kannada (Karnataka) ──────────────────────────────────────────────────
    # Prajavani — Karnataka's leading Kannada daily (direct RSS); Bandipur, BRT, Dandeli
    {
        'url': 'https://www.prajavani.net/feed/',
        'source': 'Prajavani',
        'lang': 'Kannada',
        'lang_code': 'kn',
    },
    # Vijay Karnataka via Google News — Bangalore Mirror group; Nagarhole, Cauvery
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+sanctuary+site:vijaykarnataka.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Vijay Karnataka',
        'lang': 'Kannada',
        'lang_code': 'kn',
    },

    # ── Odia (Odisha) ─────────────────────────────────────────────────────────
    # Dharitri — major Odia daily (direct RSS); Simlipal, Bhitarkanika, Chilika
    {
        'url': 'https://www.dharitri.com/feed/',
        'source': 'Dharitri',
        'lang': 'Odia',
        'lang_code': 'or',
    },
    # Sambad via Google News — Odisha's largest-circulation paper
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+sanctuary+site:sambad.in'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Sambad',
        'lang': 'Odia',
        'lang_code': 'or',
    },

    # ── Bengali (West Bengal / Tripura) ──────────────────────────────────────
    # Anandabazar Patrika via Google News — largest Bengali daily; Sundarbans, Buxa
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:anandabazar.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Anandabazar Patrika',
        'lang': 'Bengali',
        'lang_code': 'bn',
    },
    # Sangbad Pratidin via Google News — major Bengali daily; WB wildlife news
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+sanctuary+site:sangbadpratidin.in'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Sangbad Pratidin',
        'lang': 'Bengali',
        'lang_code': 'bn',
    },

    # ── Marathi (Maharashtra) ─────────────────────────────────────────────────
    # Loksatta via Google News — Maharashtra's leading Marathi daily; Tadoba, Melghat
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:loksatta.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Loksatta',
        'lang': 'Marathi',
        'lang_code': 'mr',
    },
    # Maharashtra Times via Google News — ToI group Marathi paper; Vidarbha wildlife
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+sanctuary+site:maharashtratimes.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Maharashtra Times',
        'lang': 'Marathi',
        'lang_code': 'mr',
    },

    # ── Tamil (Tamil Nadu / Puducherry) ───────────────────────────────────────
    # Dinamalar via Google News — largest Tamil daily; Mudumalai, Anamalai, KMTR
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:dinamalar.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Dinamalar',
        'lang': 'Tamil',
        'lang_code': 'ta',
    },
    # Dinamani via Google News — established Tamil daily; forest & environment beat
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+sanctuary+site:dinamani.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Dinamani',
        'lang': 'Tamil',
        'lang_code': 'ta',
    },

    # ── Gujarati (Gujarat) ────────────────────────────────────────────────────
    # Divya Bhaskar via Google News — Gujarat's largest paper; Gir, Velavadar, Wild Ass
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+lion'
                '+elephant+poaching+sanctuary+site:divyabhaskar.co.in'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Divya Bhaskar',
        'lang': 'Gujarati',
        'lang_code': 'gu',
    },
    # Gujarat Samachar via Google News — Ahmedabad-based; Gir, Rann of Kutch
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+lion'
                '+elephant+sanctuary+site:gujaratsamachar.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Gujarat Samachar',
        'lang': 'Gujarati',
        'lang_code': 'gu',
    },
]

REGIONAL_JSON = os.path.join(
    os.path.dirname(__file__), '..', 'docs', 'regional', 'news.json'
)
INDIA_CENTER = (20.5937, 78.9629)

# ── Translation helpers ──────────────────────────────────────────────────────

_translator = None

def _get_translator():
    global _translator
    if _translator is not None:
        return _translator
    try:
        from deep_translator import GoogleTranslator
        _translator = GoogleTranslator
        logger.info('deep-translator loaded OK')
    except ImportError:
        logger.warning('deep-translator not installed — translation skipped')
        _translator = False
    return _translator


def translate_to_english(text: str, src_lang: str) -> str:
    """
    Translate text from src_lang to English using Google Translate (free).
    Returns original text unchanged if translation fails or library missing.
    Rate-limit: deep-translator does NOT enforce its own delay, so callers
    must handle pacing. We add a short sleep after each translation call.
    """
    if not text or not text.strip():
        return text
    Translator = _get_translator()
    if not Translator:
        return text
    try:
        result = Translator(source=src_lang, target='en').translate(text[:500])
        return result if result else text
    except Exception as e:
        logger.debug(f'Translation failed ({src_lang}→en): {e}')
        return text


# ── Article deduplication ────────────────────────────────────────────────────

def load_existing():
    try:
        with open(REGIONAL_JSON, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


# ── Main pipeline ────────────────────────────────────────────────────────────

def main():
    existing = load_existing()
    seen_urls = {a['url'] for a in existing}
    logger.info(f'Loaded {len(existing)} existing regional articles')

    new_articles = []

    for src in REGIONAL_SOURCES:
        feed_url   = src['url']
        source     = src['source']
        lang       = src['lang']
        lang_code  = src['lang_code']

        logger.info(f'Fetching [{lang}] {source} — {feed_url[:70]}')
        entries = fetch_feed(feed_url)

        for entry in entries:
            url = getattr(entry, 'link', None)
            if not url or url in seen_urls:
                continue

            # Raw (original language) text
            title_raw = fix_encoding(getattr(entry, 'title', '') or '')
            desc_raw  = fix_encoding(getattr(entry, 'summary', '') or '')

            if not title_raw:
                continue

            # ── Translate to English for keyword filtering + location NER ──
            title_en = translate_to_english(title_raw, lang_code)
            desc_en  = translate_to_english(desc_raw[:300], lang_code)
            # Small delay to respect Google Translate's informal rate limit
            time.sleep(0.3)

            # Skip if English title is empty after translation
            if not title_en or not title_en.strip():
                continue

            # ── Keyword filter (on translated English text) ────────────────
            if not matches_keywords(title_en, desc_en):
                continue

            pub_date = parse_date(entry)

            # ── Location extraction (translated English text) ──────────────
            place_name, lat, lon = extract_location(title_en, desc_en)

            if place_name is None:
                logger.debug(f'No location: {title_en[:60]}')
                continue

            if lat is None or lon is None:
                coords = geocode(place_name)
                if coords is None:
                    logger.debug(f'Geocoding failed: {place_name}')
                    continue
                lat, lon = coords

            # Reject generic India-centre pin
            if abs(lat - INDIA_CENTER[0]) < 0.01 and abs(lon - INDIA_CENTER[1]) < 0.01:
                continue

            article = {
                'headline':    title_raw.strip(),   # original language (shown in popup)
                'headline_en': title_en.strip(),     # English (used for search)
                'url':         url,
                'source':      source,
                'lang':        lang,
                'published':   pub_date,
                'place_name':  place_name,
                'lat':         lat,
                'lon':         lon,
            }
            new_articles.append(article)
            seen_urls.add(url)
            logger.info(f'  + [{lang}] {title_en[:55]} @ {place_name}')

    merged = existing + new_articles
    merged.sort(key=lambda a: a.get('published', ''), reverse=True)

    os.makedirs(os.path.dirname(REGIONAL_JSON), exist_ok=True)
    with open(REGIONAL_JSON, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info(
        f'Wrote {len(merged)} regional articles to docs/regional/news.json '
        f'({len(new_articles)} new)'
    )


if __name__ == '__main__':
    main()
