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
    # NOTE: The Wire Science feed — broken, serves Feb-2024 articles indefinitely.
    # NOTE: The Wire Environment (cms.thewire.in) — server times out consistently.

    # Mongabay India — wildlife / forests (best Indian wildlife source)
    'https://india.mongabay.com/feed/',
    # Research Matters — Indian science & ecology research
    'https://researchmatters.in/rss.xml',
    # Nature India — Nature journal's India science coverage
    'https://www.nature.com/natindia.rss',
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

    # ── Northeast India ────────────────────────────────────────────────────────
    # Assam Tribune — Assam's leading English daily; strong forest/wildlife beat
    'https://www.assamtribune.com/feed/',
    # Northeast Now — dedicated Northeast desk; covers all 8 NE states
    'https://nenow.in/feed',
    # EastMojo — covers all 8 NE states; environment & wildlife desk
    'https://eastmojo.com/feed/',

    # ── J&K & Ladakh ──────────────────────────────────────────────────────────
    # Greater Kashmir — J&K's largest English daily; Dachigam, Hangul, snow leopard
    'https://www.greaterkashmir.com/feed/',
    # Rising Kashmir — broad J&K coverage; forest, wildlife, environment
    'https://risingkashmir.com/feed/',
    # Daily Excelsior — Jammu-based; covers Trikuta hills, Ramnagar, Chenab valley forests
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+snow+leopard'
                '+elephant+poaching+sanctuary+site:dailyexcelsior.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Daily Excelsior',
    },

    # ── UP & MP (Central India tiger belt) ────────────────────────────────────
    # The Pioneer — Lucknow-based; covers Dudhwa, Pilibhit (UP) + Kanha, Bandhavgarh (MP)
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:dailypioneer.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'The Pioneer',
    },
    # Central Chronicle — Bhopal-based; dedicated MP coverage (Satpura, Pench, Panna)
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:centralchronicle.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Central Chronicle',
    },

    # ── Himachal Pradesh & Uttarakhand ────────────────────────────────────────
    # Hill Post — HP & Uttarakhand focus; Great Himalayan NP, Govind Pashu Vihar
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+snow+leopard'
                '+tiger+sanctuary+site:hillpost.in'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Hill Post',
    },

    # ── National ───────────────────────────────────────────────────────────────
    # Hindustan Times — strong UP, Uttarakhand, Gujarat, national coverage
    'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',

    # ── Via Google News proxy (direct RSS blocked by Cloudflare / 403) ────────
    # Google pre-filters by wildlife keywords AND serves through Google's CDN,
    # bypassing the source site's bot protection entirely.
    # entry.source.title in each result gives the real publication name.
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:thewire.in'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'The Wire',
    },
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:tribuneindia.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Tribune India',
    },
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:telegraphindia.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Telegraph India',
    },
    {
        'url': ('https://news.google.com/rss/search?q=wildlife+forest+tiger'
                '+elephant+poaching+sanctuary+site:deccanherald.com'
                '&hl=en-IN&gl=IN&ceid=IN:en'),
        'source': 'Deccan Herald',
    },
]

# ── Comprehensive species + ecology keywords ────────────────────────────────
KEYWORDS = [

    # ── MAMMALS ──────────────────────────────────────────────────────────────
    # Big cats & felids
    'tiger', 'leopard', 'cheetah', 'snow leopard', 'clouded leopard',
    'fishing cat', 'rusty-spotted cat', 'jungle cat', 'leopard cat', 'caracal',
    # Elephants & rhinos
    'elephant', 'rhinoceros', 'rhino', 'one-horned rhino',
    # Bears
    'sloth bear', 'himalayan bear', 'black bear', 'brown bear', 'sun bear',
    # Canids & hyena
    'wolf', 'dhole', 'indian wild dog', 'wild dog', 'jackal', 'fox', 'hyena',
    # Primates
    'langur', 'macaque', 'gibbon', 'hoolock gibbon', 'lion-tailed macaque',
    'bonnet macaque', 'slow loris', 'monkey',
    # Deer & antelope
    'sambar', 'chital', 'spotted deer', 'barasingha', 'swamp deer',
    'hog deer', 'barking deer', 'mouse deer', 'musk deer',
    'nilgai', 'blackbuck', 'chinkara', 'four-horned antelope', 'gazelle',
    # Mountain ungulates
    'nilgiri tahr', 'markhor', 'ibex', 'blue sheep', 'bharal', 'hangul',
    'kashmir stag', 'mithun', 'gaur', 'bison', 'wild buffalo',
    # Lions
    'asiatic lion', 'gir lion',
    # Pangolin, panda & others
    'pangolin', 'red panda', 'giant squirrel', 'malabar squirrel',
    'flying squirrel', 'porcupine', 'Indian crested porcupine',
    # Otters, civets & mustelids
    'otter', 'smooth-coated otter', 'small-clawed otter',
    'civet', 'palm civet', 'binturong', 'mongoose',
    # Wild pig
    'wild boar',
    # Marine mammals
    'dolphin', 'river dolphin', 'gangetic dolphin', 'irrawaddy dolphin',
    'whale', 'blue whale', 'humpback whale', 'sperm whale', 'porpoise', 'dugong',

    # ── BIRDS ────────────────────────────────────────────────────────────────
    # Raptors
    'eagle', 'vulture', 'osprey', 'falcon', 'kite', 'hawk', 'harrier',
    'buzzard', 'kestrel', 'raptor', 'shikra', 'goshawk',
    # Bustards & cranes
    'bustard', 'great indian bustard', 'sarus crane', 'demoiselle crane', 'crane',
    # Large waterbirds
    'flamingo', 'pelican', 'stork', 'spoonbill', 'ibis', 'adjutant',
    'painted stork', 'cormorant', 'darter', 'egret', 'heron',
    # Hornbills, kingfishers & related
    'hornbill', 'kingfisher', 'bee-eater', 'roller', 'hoopoe', 'barbet',
    # Owls & nightjars
    'owl', 'owlet', 'nightjar', 'frogmouth',
    # Parakeets & pigeons
    'parakeet', 'parrot', 'pigeon', 'dove',
    # Peacock
    'peacock', 'peafowl',
    # Pheasants & junglefowl
    'pheasant', 'junglefowl', 'jungle fowl', 'partridge', 'quail',
    # Passerines & others
    'sunbird', 'woodpecker', 'drongo', 'pitta', 'bulbul', 'babbler',
    'warbler', 'flycatcher', 'robin', 'thrush', 'myna', 'starling',
    'weaver', 'munia', 'sparrow',
    # Shorebirds & wetland birds
    'plover', 'sandpiper', 'lapwing', 'tern', 'skimmer', 'snipe',
    'avocet', 'stilt', 'pratincole',
    # General bird terms
    'avian', 'avifauna', 'migratory bird', 'bird species', 'bird migration',
    'nesting bird', 'breeding bird', 'waterbird', 'wader', 'seabird',

    # ── REPTILES ─────────────────────────────────────────────────────────────
    'crocodile', 'gharial', 'mugger',
    'python', 'king cobra', 'cobra', 'krait', 'viper', 'russell viper',
    'rat snake', 'sand boa', 'boa', 'sea snake',
    'monitor lizard', 'lizard', 'gecko', 'skink', 'chameleon', 'agama',
    'turtle', 'tortoise', 'sea turtle', 'olive ridley', 'leatherback', 'hawksbill',
    'green turtle', 'loggerhead', 'softshell turtle',

    # ── AMPHIBIANS ───────────────────────────────────────────────────────────
    'frog', 'toad', 'salamander', 'newt', 'caecilian', 'amphibian',
    'tree frog', 'night frog', 'shrub frog', 'torrent frog',

    # ── FISH ─────────────────────────────────────────────────────────────────
    'mahseer', 'hilsa', 'rohu', 'catfish', 'snakehead',
    'shark', 'whale shark', 'ray', 'manta ray', 'sawfish',
    'seahorse', 'pufferfish', 'clownfish', 'coral fish',
    'eel', 'river fish', 'freshwater fish', 'marine fish',

    # ── INVERTEBRATES ────────────────────────────────────────────────────────
    'butterfly', 'moth', 'dragonfly', 'damselfly', 'odonate',
    'beetle', 'wasp', 'bee', 'honeybee', 'bumblebee',
    'ant', 'termite', 'firefly', 'glowworm', 'cicada',
    'spider', 'scorpion', 'crab', 'horseshoe crab',
    'coral', 'coral reef', 'jellyfish', 'sea urchin',
    'octopus', 'squid', 'cuttlefish', 'mollusc',
    'snail', 'earthworm',

    # ── PLANTS & FUNGI ───────────────────────────────────────────────────────
    'orchid', 'pitcher plant', 'sundew', 'cycad', 'tree fern',
    'rhododendron', 'magnolia', 'wild banana', 'bamboo species',
    'medicinal plant', 'plant species', 'endemic plant', 'invasive plant',
    'algae', 'seagrass', 'moss', 'lichen', 'fungi', 'mushroom species',
    'foraminifera', 'diatom', 'plankton', 'microorganism', 'zooplankton',

    # ── ECOLOGY & CONSERVATION ───────────────────────────────────────────────
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
    'invasive species', 'endemic species', 'new species', 'new to science',
    'species discovered', 'species found', 'species recorded',
    'camera trap', 'wildlife survey', 'wildlife census', 'wildlife monitoring',
    'WII', 'WWF', 'WTI', 'IUCN', 'wildlife institute',
    'ecosystem', 'ecology', 'ecological', 'carbon sequestration',
    'marine ecosystem', 'coastal ecosystem', 'freshwater ecosystem',
    'woodland', 'native forest', 'tree cover',
    'migratory', 'nesting', 'breeding', 'spawning',
    'animal behaviour', 'conservation biology',
    'citizen science', 'species',

    # ── PROTECTED AREAS ──────────────────────────────────────────────────────
    'kaziranga', 'sundarbans', 'corbett', 'bandipur', 'ranthambore',
    'bandhavgarh', 'kanha', 'tadoba', 'nagarhole', 'periyar',
    'satpura', 'melghat', 'pench', 'simlipal', 'manas',
    'gir forest', 'sariska', 'rajaji', 'dudhwa', 'mudumalai',
    'anamalai', 'kalakad', 'mundanthurai', 'agasthyamalai',
    'wayanad', 'parambikulam', 'silent valley', 'mukurthi',
    'pakke', 'eaglenest', 'dibru-saikhowa', 'nameri',
    'buxa', 'gorumara', 'jaldapara', 'chapramari',
    'orang', 'pobitora', 'laokhowa',
    'bhadra', 'kudremukh', 'pushpagiri', 'brahmagiri',
    'indravati', 'panna', 'achanakmar', 'udanti',
    'nokrek', 'dampa', 'khangchendzonga', 'singalila',
    # J&K / Ladakh
    'dachigam', 'hemis', 'kishtwar', 'salim ali', 'jasrota', 'surinsar', 'mansar',
    # Himachal Pradesh / Uttarakhand
    'great himalayan', 'pin valley', 'kibber', 'kugti', 'simbalbara',
    'nandhaur', 'govind pashu vihar', 'askot', 'sonanadi',
    # Uttar Pradesh
    'pilibhit', 'sohagi barwa', 'hastinapur', 'nawabganj', 'katarniaghat',
    # Bihar / Jharkhand
    'valmiki', 'betla', 'palamau',
    # Andhra Pradesh / Telangana
    'nagarjunasagar', 'papikonda', 'kawal', 'coringa', 'eturnagaram',
    'kinnersani', 'kolleru', 'pocharam', 'manjira',
    # Karnataka
    'biligiri', 'brt tiger', 'dandeli', 'kali tiger', 'ranibennur',
    # Odisha
    'simlipal', 'bhitarkanika', 'chilika', 'satkosia', 'debrigarh',
    'hadgarh', 'nandankanan',
    # West Bengal
    'buxa', 'gorumara', 'jaldapara', 'chapramari', 'neora valley', 'senchal',
    # Maharashtra
    'nawegaon', 'umred', 'radhanagari', 'bhimashankar', 'koyna', 'phansad',
    # Tamil Nadu
    'grizzled squirrel', 'guindy', 'pulicat', 'vedanthangal',
    'point calimere', 'megamalai', 'topslip', 'srivilliputhur',
    # Gujarat
    'wild ass', 'velavadar', 'nal sarovar', 'jessore', 'vansda', 'shoolpaneshwar',
    'rann of kutch',
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

def fix_encoding(text: str) -> str:
    """Fix cp1252/utf-8 mojibake (e.g. 'Ã¢â‚¬Ëœ' → curly quote).
    Some feeds double/triple encode; apply up to 3 passes until stable.
    Only accepts the fixed version if it contains no replacement chars (U+FFFD)
    and is actually different — avoids corrupting already-correct text."""
    if not text:
        return text
    for _ in range(3):
        try:
            fixed = text.encode('cp1252').decode('utf-8')
            if fixed == text:
                break
            # Reject if fix introduced replacement characters
            if '�' in fixed:
                break
            text = fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
    return text

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
        'researchmatters.in': 'Research Matters',
        'nature.com':         'Nature India',
        'assamtribune.com':    'Assam Tribune',
        'nenow.in':            'Northeast Now',
        'eastmojo.com':        'EastMojo',
        'greaterkashmir.com':  'Greater Kashmir',
        'risingkashmir.com':   'Rising Kashmir',
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

    for src in SOURCES:
        # SOURCES entries can be a plain URL string or a dict with url + source override
        if isinstance(src, dict):
            feed_url = src['url']
            forced_source = src.get('source')  # e.g. 'The Wire' for Google News proxies
        else:
            feed_url = src
            forced_source = None

        logger.info(f"Fetching {feed_url[:80]}")
        entries = fetch_feed(feed_url)

        for entry in entries:
            url = getattr(entry, 'link', None)
            if not url or url in seen_urls:
                continue

            title = fix_encoding(getattr(entry, 'title', '') or '')
            description = fix_encoding(getattr(entry, 'summary', '') or '')

            # Skip Google News search-result pages that sneak in as entries
            if title.startswith('You searched for'):
                continue

            # Strip "- Publication Name" suffix Google News appends to titles
            # e.g. "Tiger census results - Deccan Herald" → "Tiger census results"
            if forced_source:
                for sep in (f' - {forced_source}', f' | {forced_source}'):
                    if title.endswith(sep):
                        title = title[:-len(sep)].strip()
                        break

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

            sname = forced_source if forced_source else source_name(feed_url)

            article = {
                'headline': title.strip(),
                'url': url,
                'source': sname,
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
