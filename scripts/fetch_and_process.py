#!/usr/bin/env python3
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import feedparser
from dateutil import parser as dateparser

sys.path.insert(0, os.path.dirname(__file__))
from extractor import extract_location
from geocoder import geocode

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SOURCES = [
    'https://www.downtoearth.org/rss/wildlife',
    'https://www.downtoearth.org/rss/forests',
    'https://science.thewire.in/feed/',
    'https://india.mongabay.com/feed/',
    'https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss',
    'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms',
]

KEYWORDS = [
    'tiger', 'leopard', 'elephant', 'rhino', 'lion', 'wolf', 'bear',
    'gharial', 'crocodile', 'python', 'vulture', 'bustard', 'dolphin',
    'wildlife', 'poaching', 'forest', 'sanctuary', 'reserve', 'national park',
    'conservation', 'species', 'habitat', 'corridor', 'encroachment',
    'WII', 'WWF', 'WTI', 'forest department',
]

NEWS_JSON = os.path.join(os.path.dirname(__file__), '..', 'docs', 'news.json')
CUTOFF_DAYS = 30


def load_existing():
    try:
        with open(NEWS_JSON, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def matches_keywords(text: str) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in KEYWORDS)


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


def fetch_feed(url: str) -> list:
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning(f"Feed error ({url}): {feed.bozo_exception}")
            return []
        return feed.entries
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return []


def source_name(url: str) -> str:
    mapping = {
        'downtoearth.org': 'Down To Earth',
        'thewire.in': 'The Wire',
        'mongabay.com': 'Mongabay India',
        'thehindu.com': 'The Hindu',
        'timesofindia': 'Times of India',
    }
    for key, name in mapping.items():
        if key in url:
            return name
    return url.split('/')[2]


def main():
    existing = load_existing()
    seen_urls = {a['url'] for a in existing}
    logger.info(f"Loaded {len(existing)} existing articles")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)).strftime('%Y-%m-%d')
    new_articles = []

    for feed_url in SOURCES:
        logger.info(f"Fetching {feed_url}")
        entries = fetch_feed(feed_url)
        logger.info(f"  Got {len(entries)} entries")

        for entry in entries:
            url = getattr(entry, 'link', None)
            if not url or url in seen_urls:
                continue

            title = getattr(entry, 'title', '') or ''
            description = getattr(entry, 'summary', '') or ''
            text = f"{title} {description}"

            if not matches_keywords(text):
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
    merged = [a for a in merged if a.get('published', '') >= cutoff]
    merged.sort(key=lambda a: a.get('published', ''), reverse=True)

    os.makedirs(os.path.dirname(NEWS_JSON), exist_ok=True)
    with open(NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(merged)} articles to docs/news.json ({len(new_articles)} new)")


if __name__ == '__main__':
    main()
