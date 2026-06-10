# Project: WildLens — India Wildlife News Map

**Status:** Active  
**Repo:** https://github.com/nikunjfriends25-droid/wildlens  
**Live site:** https://nikunjfriends25-droid.github.io/wildlens/  
**Regional dashboard:** https://nikunjfriends25-droid.github.io/wildlens/regional/  
**GitHub user:** nikunjfriends25-droid  
**Local path:** C:\wildlife-news-map

## What It Is
Free, zero-cost web platform displaying Indian wildlife & environment news as pins on an
interactive map of India. No backend, no paid APIs. GitHub Actions processes RSS feeds
every 6 hours; GitHub Pages serves the static site. Two dashboards: English + Regional.

## Architecture
- **English pipeline:** GitHub Actions → `scripts/fetch_and_process.py` every 6 hours
- **Regional pipeline:** GitHub Actions → `scripts/fetch_regional.py` (same job, runs after English)
- **Hosting:** GitHub Pages serves `docs/` folder (English) and `docs/regional/` (Regional)
- **Map:** Leaflet.js reads respective `news.json`, renders clustered pins

## Stack
- Python 3.11 (on Actions): feedparser, geopy Nominatim, deep-translator
- spaCy en_core_web_trf: NOT in requirements.txt; NOT installed locally; extractor.py degrades gracefully
- Leaflet.js 1.9.x + MarkerCluster + Driver.js v1 (guided tour, English only)
- CARTO dark tile layer
- CounterAPI (api.counterapi.dev) for visit counter — no signup (English dashboard only)
- GitHub Actions + GitHub Pages (all free)

## Key Files
| File | Purpose |
|------|---------|
| `scripts/fetch_and_process.py` | Main English pipeline — fetch, filter, extract, geocode, write news.json |
| `scripts/fetch_regional.py` | Regional pipeline — translate → filter → extract → geocode → regional/news.json |
| `scripts/extractor.py` | 2-pass location: gazetteer first, then spaCy NER (spaCy optional) |
| `scripts/geocoder.py` | Nominatim, 1s delay, India bounds check, in-memory cache |
| `scripts/requirements.txt` | feedparser, geopy, python-dateutil, deep-translator |
| `data/india_pa_gazetteer.csv` | 1,233 entries: NPs, TRs, WLSs, states, cities, regions |
| `docs/news.json` | Auto-generated English articles |
| `docs/regional/news.json` | Auto-generated regional language articles |
| `docs/index.html` | English dashboard (style.css?v=13, map.js?v=13) |
| `docs/map.js` | Clustering, categories, filters, guided tour (Driver.js), visit counter |
| `docs/style.css` | B&W monochrome dark theme, responsive left panel |
| `docs/regional/index.html` | Regional dashboard (style.css?v=2, map.js?v=2) |
| `docs/regional/map.js` | Regional map — uses headline_en for categorise/search, shows original in popup |
| `docs/regional/style.css` | Same design system + language badge + translation subtitle styles |
| `.github/workflows/fetch_news.yml` | Cron every 6h + workflow_dispatch; runs English then Regional pipeline |
| `backups/english-dashboard/v1_pre-regional/` | Full snapshot before regional build |

## RSS Sources — English Pipeline

**Direct RSS (working):**
- Mongabay India, Research Matters, Nature India
- NDTV, Indian Express
- The Hindu (env, national, state feeds: KL, KA, AP, TG, TN, other-states)
- Times of India (env + India news feeds)
- Assam Tribune, Northeast Now, EastMojo
- Greater Kashmir, Rising Kashmir
- Hindustan Times

**Google News proxies (direct RSS blocked by Cloudflare/403):**
- The Wire, Tribune India, Telegraph India, Deccan Herald
- Daily Excelsior (J&K/Jammu), The Pioneer (UP/MP), Central Chronicle (MP), Hill Post (HP/Uttarakhand)

**Dead / not used:**
- Down to Earth (downtoearth.org is a US food store; .in feed returns only 2 generic articles)

## RSS Sources — Regional Pipeline
| Language | Sources | Method |
|----------|---------|--------|
| Malayalam | Mathrubhumi, Manorama Online | Direct RSS |
| Hindi | Dainik Jagran, Amar Ujala, Patrika | Direct RSS |
| Assamese | Pratidin Time, Asomiya Pratidin | Direct RSS |
| Telugu | Sakshi (direct RSS), Eenadu (GN proxy) | Mixed |
| Kannada | Prajavani (direct RSS), Vijay Karnataka (GN proxy) | Mixed |
| Odia | Dharitri (direct RSS), Sambad (GN proxy) | Mixed |
| Bengali | Anandabazar Patrika, Sangbad Pratidin | GN proxy |
| Marathi | Loksatta, Maharashtra Times | GN proxy |
| Tamil | Dinamalar, Dinamani | GN proxy |
| Gujarati | Divya Bhaskar, Gujarat Samachar | GN proxy |

## Regional Pipeline — How it works
1. Fetches RSS in original language
2. Translates headline + 300 chars description → English via deep-translator (Google Translate, free, no API key)
3. Adds 0.3s sleep per translation to respect rate limit
4. Runs translated text through same KEYWORDS filter as English pipeline
5. Location extracted from translated text (gazetteer + optional spaCy)
6. Geocodes via Nominatim
7. Stores BOTH original headline (`headline`) and English (`headline_en`) in news.json
8. Regional map shows original in popup, translation as subtitle; searches both

## Current Article Count
**English:** 86 articles. By source:
The Hindu (43), Mongabay (9), Indian Express (7), The Wire (7), Deccan Herald (5),
Telegraph India (4), Assam Tribune (2), HT (2), NDTV (2), Research Matters (2),
Times of India (2), Nature India (1), Hill Post (1)

**Regional:** 8 articles. By language: Odia (6), Hindi (1), Kannada (1)
(Other languages: feeds connected, articles accumulating with each 6h run)

## UI Features (English Dashboard docs/index.html)
- Left panel: Search → Category → Date Range → Source (collapsed by default)
- 5 categories: Poaching & Crime (#ef4444), Species Discovery (#f59e0b),
  Human-Wildlife Conflict (#f97316), Research & Science (#06b6d4), Conservation & Policy (#818cf8)
- Panel footer: article count stats, Reset filters, visit counter (CounterAPI), Tour button
- Guided tour: Driver.js v1 — auto-triggers once on first visit (localStorage key: wildlens-tour-done)
- Category + source filter chips; deselecting all shows 0 (not all) — activeSrcs guard removed
- "Regional Edition →" micro-link in panel header → docs/regional/

## UI Features (Regional Dashboard docs/regional/index.html)
- Same design as English dashboard
- Additional "Language" filter section (above Date Range)
- Language chips with native script labels: മലയാളം, हिन्दी, অসমীয়া, తెలుగు, ಕನ್ನಡ, ଓଡ଼ିଆ, বাংলা, मराठी, தமிழ், ગુજરાતી
- Popup: original-language headline (primary) + English translation as italic subtitle
- Language badge (colour-coded per language) in popup
- "← English Edition" back-link in panel header
- No tour, no visit counter (kept minimal)

## Language Colour Codes (Regional Map)
Malayalam=#10b981, Hindi=#f59e0b, Assamese=#6366f1, Telugu=#ec4899,
Kannada=#f97316, Odia=#14b8a6, Bengali=#8b5cf6, Marathi=#ef4444,
Tamil=#06b6d4, Gujarati=#84cc16

## Gazetteer — 1,233 entries
Full coverage: all tiger reserves, national parks, wildlife sanctuaries,
biosphere reserves, elephant reserves, major states, cities, forest divisions.

Key additions in this session:
- J&K/Ladakh: Dachigam NP, Hemis NP, Salim Ali NP, Kibber WS
- HP: Pin Valley NP, Kugti WS, Simbalbara NP, Great Himalayan NP (already existed)
- Uttarakhand: Nandhaur WS, Askot WS
- UP: Pilibhit TR (already existed), Katarniaghat WS, Sohagi Barwa WS, Hastinapur WS
- Bihar/Jharkhand: Valmiki TR, Betla NP, Palamau TR
- AP/TG: Nagarjunasagar-Srisailam TR, Papikonda NP, Kawal TR, Coringa WS,
  Sri Venkateswara NP, Eturnagaram, Kinnersani, Kolleru, Pocharam, Manjira
- KA: Biligiri Rangaswamy TR, Dandeli-Anshi TR, Anshi NP, Kali TR, Ranibennur WS
- OD: Simlipal TR, Satkosia TR, Bhitarkanika NP, Chilika, Debrigarh, Hadgarh, Nandankanan
- WB: Buxa TR, Gorumara NP, Jaldapara NP, Chapramari WS, Neora Valley NP, Senchal WS
- MH: Nawegaon NP, Umred-Karhandla WS, Bor TR, Radhanagari WS, Bhimashankar WS, Koyna WS
- TN: Kalakad-Mundanthurai TR, Guindy NP, Pulicat, Vedanthangal, Point Calimere, Megamalai
- GJ: Wild Ass Sanctuary, Velavadar NP, Nal Sarovar, Marine NP Gulf of Kutch, Barda, Jessore, Vansda

## EXCLUDE_KEYWORDS (key additions this session)
Added: 'legislators', 'lawmaker', 'offsite', 'review huddle', 'party huddle'
Reason: "Omar takes NC legislators to Dachigam for offsite review huddle" slipped through
because 'dachigam' is in KEYWORDS but 'legislators' wasn't blocked. Political meetings
at national parks are a false-positive pattern for J&K sources.

## Known Issues / Decisions
- spaCy NOT in requirements.txt and NOT installed locally; extractor degrades to gazetteer-only
- spaCy download step removed from GitHub Actions workflow (gazetteer handles most locations well)
- Google News appends "- Publication Name" to titles — stripped in pipeline for forced_source entries
- "You searched for" junk GN entries — filtered with `if title.startswith('You searched for')`
- Nominatim: always 1s sleep, always ", India" suffix, India bounds validation (lat 6-37, lon 68-98)
- CounterAPI namespace: wildlens-india / pageviews
- Driver.js v1 IIFE global: window.driver.js.driver (NOT window['driver.js'] — that fails)
- Down to Earth RSS: dead — not used
- deep-translator: uses Google Translate public endpoint, no API key, ~500k chars/day soft limit
- Translation sleep: 0.3s between calls in regional pipeline
- Regional articles removed from news.json must also have exclusions applied, else they re-appear
  (the URL is no longer in seen_urls after removal)

## Backups
- `backups/english-dashboard/v1_pre-regional/` — index.html, map.js, style.css, news.json,
  fetch_and_process.py — taken before regional dashboard was built (2026-06-10)
