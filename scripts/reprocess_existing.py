"""
Re-geocode existing news.json articles using the updated gazetteer.
For each article, re-runs the extractor on its headline (and empty description,
since descriptions aren't stored). Articles that now get a better gazetteer
match replace their place_name/lat/lon. Articles that lose their India-centre
pin but get no new match are either kept (if Nominatim can find them) or
removed from the map (lat/lon set to None → filtered out).

Run once: python scripts/reprocess_existing.py
"""
import json, sys, os, time, logging
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

from extractor import extract_location
from geocoder import geocode

NEWS_JSON = os.path.join(os.path.dirname(__file__), '..', 'docs', 'news.json')

INDIA_CENTER = (20.5937, 78.9629)   # generic India pin — always upgrade these
INDIA_BOUNDS = dict(lat_min=6, lat_max=37, lon_min=68, lon_max=98)

def is_india_center(lat, lon):
    return abs(lat - INDIA_CENTER[0]) < 0.01 and abs(lon - INDIA_CENTER[1]) < 0.01

def in_bounds(lat, lon):
    return (INDIA_BOUNDS['lat_min'] <= lat <= INDIA_BOUNDS['lat_max'] and
            INDIA_BOUNDS['lon_min'] <= lon <= INDIA_BOUNDS['lon_max'])

def main():
    with open(NEWS_JSON, encoding='utf-8') as f:
        articles = json.load(f)

    logger.info(f"Loaded {len(articles)} articles")
    improved = 0
    removed = 0

    for a in articles:
        headline = a.get('headline', '')
        old_place = a.get('place_name', '')
        old_lat = a.get('lat', 0)
        old_lon = a.get('lon', 0)

        # Only attempt re-extraction for:
        # 1. Articles pinned to exact India centre (lat 20.5937, lon 78.9629)
        # 2. Articles labelled "India" as place_name
        if not (old_place == 'India' or is_india_center(old_lat, old_lon)):
            continue

        logger.info(f"Re-processing: {headline[:60]}")

        # Use headline as text, empty description — description not stored
        place_name, lat, lon = extract_location(headline, '')

        if place_name is None:
            logger.info(f"  → No location found, removing from map")
            a['_remove'] = True
            removed += 1
            continue

        if lat is None:
            # Gazetteer gave a name but no coords — try Nominatim
            lat, lon = geocode(place_name)

        if lat is None or not in_bounds(lat, lon):
            logger.info(f"  → Could not geocode '{place_name}', removing")
            a['_remove'] = True
            removed += 1
            continue

        if place_name == 'India' or is_india_center(lat, lon):
            # Still too generic
            logger.info(f"  → Still generic 'India', removing from map")
            a['_remove'] = True
            removed += 1
            continue

        logger.info(f"  → Improved: '{old_place}' → '{place_name}' ({lat:.4f},{lon:.4f})")
        a['place_name'] = place_name
        a['lat'] = lat
        a['lon'] = lon
        improved += 1

    # Filter out removed articles
    kept = [a for a in articles if not a.get('_remove')]

    logger.info(f"\nResults: {improved} improved, {removed} removed, {len(kept)} kept")

    with open(NEWS_JSON, 'w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {NEWS_JSON} with {len(kept)} articles")

if __name__ == '__main__':
    main()
