#!/usr/bin/env python3
import json
import logging
import os
import sys
from datetime import datetime, timezone

import feedparser
from dateutil import parser as dateparser

sys.path.insert(0, os.path.dirname(__file__))
from extractor import extract_location
from geocoder import geocode

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SOURCES = [
    # NOTE: Down to Earth — HTTP 403, blocks all RSS programmatic access.
    # NOTE: The Wire Science — RSS feed broken; serves Feb-2024 articles indefinitely.

    # Mongabay India — wildlife / forests
    'https://india.mongabay.com/feed/',
    # NDTV India — catches wildlife, forest, conservation stories
    'https://feeds.feedburner.com/ndtvnews-india-news',
    # Indian Express India — wildlife, poaching, forest coverage
    'https://indianexpress.com/section/india/feed/',
    # The Hindu — environment & sci-tech
    'https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss',
    # The Hindu — national news (catches forest fires, poaching, PA stories)
    'https://www.thehindu.com/news/national/feeder/default.rss',
    # The Hindu — other states (northeast, hill states, etc.)
    'https://www.thehindu.com/news/national/other-states/feeder/default.rss',
    # The Hindu — state-specific (major biodiversity states)
    'https://www.thehindu.com/news/national/kerala/feeder/default.rss',
    'https://www.thehindu.com/news/national/karnataka/feeder/default.rss',
    'https://www.thehindu.com/news/national/andhra-pradesh/feeder/default.rss',
    'https://www.thehindu.com/news/national/telangana/feeder/default.rss',
    'https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss',
    # Times of India — environment / wildlife section
    'https://timesofindia.indiatimes.com/rssfeeds/2647163.cms',
    # Times of India — India news (catches forest, wildlife stories)
    'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms',
]

# ── Specific wildlife / ecology keywords ────────────────────────────────────
# Use PHRASES where a single word is too ambiguous (e.g. "lion" → "asiatic lion").
KEYWORDS = [
    # Unambiguous animal names
    'tiger', 'leopard', 'elephant', 'rhinoceros', 'rhino', 'gharial',
    'crocodile', 'python', 'vulture', 'bustard', 'dolphin', 'whale',
    'dugong', 'pangolin', 'cheetah', 'snow leopard', 'clouded leopard',
    'sloth bear', 'himalayan bear', 'black bear',
    'asiatic lion', 'gir lion', 'wolf pack', 'indian wolf',
    'sea turtle', 'olive ridley', 'leatherback', 'hawksbill',
    'great indian bustard', 'red panda', 'one-horned rhino',
    'king cobra', 'monitor lizard', 'fishing cat',
    'migratory bird', 'bird species', 'raptor', 'avian', 'avifauna',
    'flamingo', 'pelican', 'hornbill', 'kingfisher', 'eagle', 'owl',
    # Wildlife / ecology terms — phrases only for ambiguous words
    'wildlife', 'poaching', 'wildlife trafficking', 'wildlife crime',
    'national park', 'wildlife sanctuary', 'tiger reserve', 'biosphere reserve',
    'wildlife corridor', 'elephant corridor', 'forest corridor',
    'wildlife conservation', 'species conservation', 'biodiversity conservation',
    'forest', 'forest department', 'forest fire', 'forest cover', 'forest loss',
    'reserve forest', 'protected forest', 'protected area',
    'deforestation', 'afforestation', 'reforestation',
    'habitat loss', 'habitat destruction', 'habitat fragmentation',
    'human-wildlife conflict', 'man-animal conflict',
    'eco-sensitive', 'biodiversity', 'mangrove', 'wetland',
    'endangered species', 'threatened species', 'extinct species',
    'invasive species', 'endemic species', 'new species',
    'camera trap', 'wildlife survey', 'wildlife census',
    'WII', 'WWF', 'WTI', 'wildlife institute',
    # Specific protected areas (unambiguous)
    'kaziranga', 'sundarbans', 'corbett', 'bandipur', 'ranthambore',
    'bandhavgarh', 'kanha', 'tadoba', 'nagarhole', 'periyar',
    'satpura', 'melghat', 'pench', 'simlipal', 'manas',
    'gir forest', 'sariska', 'rajaji', 'dudhwa',
    # Ecology / environment science
    'amphibian', 'reptile', 'frog species', 'toad species',
    'coral reef', 'seagrass', 'mangrove forest',
    'carbon sequestration', 'ecosystem', 'ecology',
    'climate change impact on wildlife', 'species extinction',
]

# ── Exclusion list — any match blocks the article ────────────────────────────
# Catches politics, infrastructure, crime, sports, finance etc. that
# incidentally mention an ecology keyword.
EXCLUDE_KEYWORDS = [
    # Military / security
    'militant', 'terrorist', 'encounter', 'ceasefire', 'army operation',
    'security forces', 'paramilitary', 'naxal', 'maoist', 'insurgent',
    'drone strike', 'airstrike', 'gunfight', 'firing', 'crpf', 'bsf',
    # Politics / government
    'election', 'constituency', 'mla', 'mp ', ' mp,', 'cabinet approves',
    'union cabinet', 'lok sabha', 'rajya sabha', 'parliament',
    'rebellion', 'political', 'party', 'tmc', 'bjp', 'congress', 'aap',
    'nda ', ' upa', 'chief minister', 'governor appoints',
    'anti-encroachment drive', 'demolition drive', 'encroachment drive',
    # Infrastructure / civic
    'metro', 'railway', 'highway', 'flyover', 'road widening',
    'airport link', 'commonwealth games', 'expressway',
    'mosque demolished', 'temple demolished', 'mazar',
    # Crime / law & order
    'murder', 'rape', 'kidnap', 'robbery', 'fraud', 'scam', 'arrest',
    'blast', 'bomb', 'explosion', 'riot', 'curfew', 'internet blackout',
    'prohibitory orders',
    # Sports
    'ipl', 'cricket', 'football', 'hockey match', 'tennis', 'wrestling',
    'commonwealth games',
    # Finance / economy
    'stock market', 'sensex', 'nifty', 'budget', 'gdp', 'inflation',
    'interest rate', 'rbi ', 'sebi ', 'ipo ',
]

NEWS_JSON = os.path.join(os.path.dirname(__file__), '..', 'docs', 'news.json')
INDIA_CENTER = (20.5937, 78.9629)  # generic pin — reject these


def load_existing():
    try:
        with open(NEWS_JSON, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


import re as _re

def _word_in(phrase: str, text: str) -> bool:
    """True if phrase appears as whole word(s) in text (case-insensitive)."""
    escaped = _re.escape(phrase.lower())
    return bool(_re.search(r'\b' + escaped + r'\b', text))

def matches_keywords(title: str, description: str = '') -> bool:
    """
    Two-stage check:
    1. Exclusion — whole-word match against title+description.
    2. Inclusion — at least one KEYWORD must appear as whole word(s) in the TITLE.
       Word-boundary matching prevents 'owl' matching inside 'Gachibowli', etc.
    """
    combined = (title + ' ' + description).lower()
    title_lower = title.lower()

    # Stage 1: exclude
    if any(_word_in(ex, combined) for ex in EXCLUDE_KEYWORDS):
        return False

    # Stage 2: keyword must appear in the TITLE as whole word/phrase
    return any(_word_in(kw, title_lower) for kw in KEYWORDS)


def parse_date(entry) -> str:
    for attr in ('published', 'updated'):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt:
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0 '
    'wildlife-news-map/1.0 (+https://github.com/nikunjfriends25-droid/wildlife-news-map)'
)

def fetch_feed(url: str) -> list:
    try:
        # Pass a browser-like User-Agent — some feeds (e.g. The Wire) block
        # feedparser's default "python-feedparser/..." agent.
        feed = feedparser.parse(url, agent=USER_AGENT)
        if feed.bozo and not feed.entries:
            logger.warning(f"Feed error ({url}): {feed.bozo_exception}")
            return []
        logger.info(f"  Got {len(feed.entries)} entries")
        return feed.entries
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return []


def source_name(url: str) -> str:
    mapping = {
        'downtoearth.org':    'Down To Earth',
        'thewire.in':         'The Wire',
        'mongabay.com':       'Mongabay India',
        'thehindu.com':       'The Hindu',
        'timesofindia':       'Times of India',
        'ndtv':               'NDTV',
        'indianexpress.com':  'Indian Express',
        'hindustantimes.com': 'Hindustan Times',
    }
    for key, name in mapping.items():
        if key in url:
            return name
    try:
        return url.split('/')[2]
    except IndexError:
        return url


def main():
    existing = load_existing()
    seen_urls = {a['url'] for a in existing}
    logger.info(f"Loaded {len(existing)} existing articles")

    new_articles = []

    for feed_url in SOURCES:
        logger.info(f"Fetching {feed_url}")
        entries = fetch_feed(feed_url)

        for entry in entries:
            url = getattr(entry, 'link', None)
            if not url or url in seen_urls:
                continue

            title = getattr(entry, 'title', '') or ''
            description = getattr(entry, 'summary', '') or ''
            text = f"{title} {description}"

            if not matches_keywords(title, description):
                continue

            pub_date = parse_date(entry)

            place_name, lat, lon = extract_location(title, description)

            if place_name is None:
                logger.debug(f"No location found: {title[:60]}")
                continue

            if lat is None or lon is None:
                coords = geocode(place_name)
                if coords is None:
                    logger.debug(f"Geocoding failed: {place_name}")
                    continue
                lat, lon = coords

            # Skip articles that landed on generic India centre
            if abs(lat - INDIA_CENTER[0]) < 0.01 and abs(lon - INDIA_CENTER[1]) < 0.01:
                logger.debug(f"Skipping India-centre pin: {title[:50]}")
                continue

            article = {
                'headline': title.strip(),
                'url': url,
                'source': source_name(feed_url),
                'published': pub_date,
                'place_name': place_name,
                'lat': lat,
                'lon': lon,
            }
            new_articles.append(article)
            seen_urls.add(url)
            logger.info(f"  + {title[:50]} @ {place_name}")

    merged = existing + new_articles
    merged.sort(key=lambda a: a.get('published', ''), reverse=True)

    os.makedirs(os.path.dirname(NEWS_JSON), exist_ok=True)
    with open(NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(merged)} articles to docs/news.json ({len(new_articles)} new)")


if __name__ == '__main__':
    main()
