#!/usr/bin/env python3
"""
Backfill news.json using GDELT Doc 2.0 API (free, no key).
Queries wildlife keywords + India, chunked by quarter from 2015 to today.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

sys.path.insert(0, os.path.dirname(__file__))
from extractor import extract_location
from geocoder import geocode

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

NEWS_JSON = os.path.join(os.path.dirname(__file__), '..', 'docs', 'news.json')

GDELT_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'

# Keyword groups — each group is one GDELT query to stay under URL limits
KEYWORD_GROUPS = [
    'tiger OR leopard OR elephant OR rhino OR lion wildlife India',
    'poaching wildlife India forest sanctuary reserve',
    'gharial crocodile vulture bustard dolphin India wildlife',
    'conservation habitat corridor encroachment India forest',
    'wolf bear python wildlife India national park',
    'WWF WTI WII "forest department" wildlife India',
]

START_YEAR = 2015


def load_existing():
    try:
        with open(NEWS_JSON, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def quarter_ranges(start_year):
    """Generate (start_dt, end_dt) pairs by quarter from start_year to today."""
    now = datetime.now(timezone.utc)
    dt = datetime(start_year, 1, 1, tzinfo=timezone.utc)
    while dt < now:
        end = datetime(dt.year + (dt.month + 2) // 12,
                       ((dt.month + 2) % 12) + 1, 1, tzinfo=timezone.utc)
        end = min(end, now)
        yield dt, end
        dt = end


def gdelt_fetch(query, start_dt, end_dt):
    params = urlencode({
        'query': query,
        'mode': 'artlist',
        'maxrecords': '250',
        'format': 'json',
        'startdatetime': start_dt.strftime('%Y%m%d%H%M%S'),
        'enddatetime': end_dt.strftime('%Y%m%d%H%M%S'),
        'sort': 'DateDesc',
    })
    url = f"{GDELT_URL}?{params}"
    for attempt in range(4):
        try:
            req = Request(url, headers={'User-Agent': 'wildlife-news-map-backfill/1.0'})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data.get('articles', []) or []
        except URLError as e:
            code = getattr(getattr(e, 'code', None), '__int__', lambda: None)()
            if hasattr(e, 'code') and e.code == 429:
                wait = 10 * (attempt + 1)
                logger.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.warning(f"GDELT request failed: {e}")
                return []
        except Exception as e:
            logger.warning(f"GDELT request failed: {e}")
            return []
    return []


def source_from_url(url):
    try:
        domain = url.split('/')[2].replace('www.', '')
        known = {
            'downtoearth.org': 'Down To Earth',
            'thewire.in': 'The Wire',
            'mongabay.com': 'Mongabay India',
            'thehindu.com': 'The Hindu',
            'timesofindia.indiatimes.com': 'Times of India',
            'hindustantimes.com': 'Hindustan Times',
            'ndtv.com': 'NDTV',
            'indianexpress.com': 'Indian Express',
            'scroll.in': 'Scroll',
            'firstpost.com': 'Firstpost',
            'deccanherald.com': 'Deccan Herald',
            'telegraphindia.com': 'The Telegraph',
            'business-standard.com': 'Business Standard',
            'livemint.com': 'Mint',
        }
        return known.get(domain, domain)
    except Exception:
        return 'Unknown'


def main():
    existing = load_existing()
    seen_urls = {a['url'] for a in existing}
    logger.info(f"Loaded {len(existing)} existing articles")

    new_articles = []
    quarters = list(quarter_ranges(START_YEAR))
    total = len(quarters) * len(KEYWORD_GROUPS)
    done = 0

    for start_dt, end_dt in quarters:
        period = start_dt.strftime('%Y-Q%m')
        for query in KEYWORD_GROUPS:
            done += 1
            logger.info(f"[{done}/{total}] {period} | {query[:40]}")

            articles_raw = gdelt_fetch(query, start_dt, end_dt)
            time.sleep(2)  # GDELT rate limit — 2s between requests

            for art in articles_raw:
                url = art.get('url', '')
                if not url or url in seen_urls:
                    continue

                title = art.get('title', '') or ''
                seendate = art.get('seendate', '') or ''
                # seendate format: 20230415T120000Z
                try:
                    pub_date = datetime.strptime(seendate[:8], '%Y%m%d').strftime('%Y-%m-%d')
                except Exception:
                    pub_date = start_dt.strftime('%Y-%m-%d')

                place_name, lat, lon = extract_location(title, title)

                if place_name is None:
                    continue

                if lat is None or lon is None:
                    coords = geocode(place_name)
                    if coords is None:
                        continue
                    lat, lon = coords

                article = {
                    'headline': title.strip(),
                    'url': url,
                    'source': source_from_url(url),
                    'published': pub_date,
                    'place_name': place_name,
                    'lat': lat,
                    'lon': lon,
                }
                new_articles.append(article)
                seen_urls.add(url)
                logger.info(f"  + [{pub_date}] {title[:55]} @ {place_name}")

    merged = existing + new_articles
    merged.sort(key=lambda a: a.get('published', ''), reverse=True)

    os.makedirs(os.path.dirname(NEWS_JSON), exist_ok=True)
    with open(NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info(f"\nDone. {len(new_articles)} new articles added. Total: {len(merged)}")


if __name__ == '__main__':
    main()
