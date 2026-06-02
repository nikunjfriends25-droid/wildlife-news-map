# Wildlife News Map — India

## Project goal
A free, zero-ongoing-cost web platform that displays Indian wildlife 
and environment news as pins on an interactive map of India. 
Runs entirely on GitHub Actions (processing) + GitHub Pages (hosting).
No backend server. No paid APIs.

## Architecture
GitHub Actions runs fetch_and_process.py every 6 hours:
  1. Pulls articles from RSS feeds (filtered by wildlife keywords)
  2. Extracts the most specific Indian location from each article
  3. Geocodes that location to lat/lon
  4. Writes results to docs/news.json
GitHub Pages serves docs/ as a static site.
Leaflet.js map reads docs/news.json and renders pins.
User clicks pin → popup with headline + source → click → original article.

## Folder structure to create
.github/workflows/fetch_news.yml
scripts/fetch_and_process.py
scripts/extractor.py
scripts/geocoder.py
scripts/requirements.txt
data/india_pa_gazetteer.csv
docs/index.html
docs/map.js
docs/style.css

## Stack
- Python 3.11
- feedparser (RSS fetching)
- spaCy with en_core_web_trf model (NER location extraction)
- geopy Nominatim (geocoding, free)
- Leaflet.js 1.9.x via CDN (map rendering)
- GitHub Actions (scheduled pipeline)
- GitHub Pages serving from /docs folder

## File responsibilities

### scripts/fetch_and_process.py
Main pipeline script. Called by GitHub Actions.
Steps:
  1. Load existing docs/news.json (if exists) to check already-processed URLs
  2. Fetch articles from all sources in scripts/sources.yaml
  3. Filter by keywords
  4. For each NEW article only (URL not in existing news.json):
     a. Run extractor.py to get place name
     b. Run geocoder.py to get lat/lon
     c. Skip article if geocoding returns None
  5. Merge new results with existing news.json
  6. Keep only articles from last 30 days (prune older ones)
  7. Write final array to docs/news.json

### scripts/extractor.py
Two-pass location extraction. No API calls whatsoever.
Pass 1: Load data/india_pa_gazetteer.csv. Search article 
  title + first 600 chars of description for any PA name match.
  If match found, return (place_name, lat, lon) directly.
  Skip geocoding entirely for these — gazetteer has coordinates.
Pass 2: If no gazetteer match, use spaCy en_core_web_trf to 
  extract all GPE and LOC entities from article text.
  Return the most specific one (prefer longer, more specific names).
  Return None if nothing found.

### scripts/geocoder.py
Takes a place name string.
Uses geopy Nominatim with user_agent="wildlife-news-map-india".
Adds ", India" to every query to bias results.
Enforces 1 second delay between requests (Nominatim ToS).
Returns (lat, lon) tuple or None if not found.
Never geocode the same place name twice — use a simple 
in-memory dict cache within each run.

### data/india_pa_gazetteer.csv
CSV with columns: name, lat, lon, type
Covers: tiger reserves, national parks, wildlife sanctuaries,
  biosphere reserves, elephant reserves, major forest divisions.
Populate with at least 200 entries covering all Indian states.
Include common alternate names and abbreviations as separate rows.
Example rows:
  Nagarahole National Park,12.0833,76.1667,national_park
  Rajiv Gandhi National Park,12.0833,76.1667,national_park
  Kabini,12.0833,76.1667,forest_range

### docs/news.json
Auto-generated. Do not edit manually.
Format:
[
  {
    "headline": "...",
    "url": "...",
    "source": "...",
    "published": "YYYY-MM-DD",
    "place_name": "...",
    "lat": 00.0000,
    "lon": 00.0000
  }
]

### docs/index.html
Single page. Loads Leaflet.js from CDN.
Full screen map of India (default bounds lat 6-37, lon 68-98, zoom 5).
Dark or nature-themed tile layer.
Loads docs/news.json via fetch().
Renders circle markers sized by recency (newer = slightly larger).
Click marker → popup with headline, source name, date, 
  and "Read article" link opening in new tab.
Clean minimal UI. No frameworks. No build step.

### docs/map.js
Fetches news.json.
Groups pins within 40km into clusters using Leaflet.markercluster CDN plugin.
Color code markers by category if detectable 
  (poaching=red, sighting=green, conservation=blue, other=grey).
Shows total article count in top-right corner.

### docs/style.css
Minimal. Map takes full viewport. 
Popup styled cleanly. Mobile responsive.

### .github/workflows/fetch_news.yml
Trigger: schedule cron every 6 hours + manual workflow_dispatch.
Steps:
  - actions/checkout@v4
  - Set up Python 3.11
  - pip install -r scripts/requirements.txt
  - python -m spacy download en_core_web_trf
  - python scripts/fetch_and_process.py
  - Git commit and push docs/news.json if changed
    (use: git config user.email "action@github.com")
    (only commit if news.json actually changed)

## RSS sources to use (in fetch_and_process.py as a list)
- https://www.downtoearth.org/rss/wildlife
- https://www.downtoearth.org/rss/forests
- https://science.thewire.in/feed/
- https://india.mongabay.com/feed/
- https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss
- https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms

## Keywords to filter articles (any match = include)
tiger, leopard, elephant, rhino, lion, wolf, bear, 
gharial, crocodile, python, vulture, bustard, dolphin,
wildlife, poaching, forest, sanctuary, reserve, national park,
conservation, species, habitat, corridor, encroachment,
WII, WWF, WTI, forest department

## Known failure modes — handle these explicitly
- RSS feed returns 404 or timeout → log warning, continue with others
- spaCy returns no entities → log as "no location found", skip article
- Nominatim returns result outside India bounds 
  (lat < 6 or > 37, lon < 68 or > 98) → reject and skip
- news.json missing or malformed on first run → start with empty list
- GitHub Actions hits Nominatim rate limit → the 1s sleep handles this,
  do not remove it

## Constraints — do not violate these
- No paid APIs anywhere in this project
- No ANTHROPIC_API_KEY or any API key in code
- No backend server or serverless functions
- Nominatim: always 1 second sleep between calls, always add ", India"
- Never re-process an article URL already in news.json
- GitHub Actions free tier limit: 2000 min/month — 
  spaCy model download is the heavy step, cache it with 
  actions/cache@v4 keyed on requirements.txt hash
- docs/ folder is what GitHub Pages serves — all frontend files go here

## Build order for Claude Code
1. data/india_pa_gazetteer.csv (at least 200 entries)
2. scripts/requirements.txt
3. scripts/extractor.py
4. scripts/geocoder.py  
5. scripts/fetch_and_process.py
6. .github/workflows/fetch_news.yml
7. docs/index.html + docs/map.js + docs/style.css
8. Test locally: python scripts/fetch_and_process.py
   Verify news.json is generated with valid lat/lon entries.

