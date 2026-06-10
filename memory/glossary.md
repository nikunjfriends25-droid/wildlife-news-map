# Glossary — WildLens Project

## Terms
| Term | Meaning |
|------|---------|
| gazetteer | `data/india_pa_gazetteer.csv` — 1,233 Indian protected areas with lat/lon for direct location matching without NER |
| news.json | `docs/news.json` — auto-generated array of English articles with lat/lon, served to Leaflet |
| regional/news.json | `docs/regional/news.json` — regional language articles; includes both `headline` (original) and `headline_en` (English translation) |
| PA | Protected Area (national park, tiger reserve, sanctuary etc.) |
| NER | Named Entity Recognition — spaCy's method to extract place names from text |
| cluster | Leaflet.markercluster — groups nearby pins into numbered circles on the map |
| Nominatim | Free OSM geocoder used to convert place names → lat/lon |
| GN proxy | Google News RSS proxy — used to bypass Cloudflare/403 on source sites that block direct RSS |
| forced_source | In SOURCES dict entries: overrides the source name (e.g. 'Deccan Herald') and triggers suffix stripping |
| deep-translator | Python library wrapping Google Translate public endpoint; free, no API key; used in regional pipeline |
| headline_en | The English translation of a regional article's headline; stored alongside original `headline` in regional/news.json |
| activeSrcs | JS Set in map.js tracking which sources are checked; guard `activeSrcs.size &&` was removed to fix "deselect all shows all" bug |
| seen_urls | Set of URLs already in news.json; articles with matching URLs are skipped to avoid duplicates |
| INDIA_CENTER | (20.5937, 78.9629) — generic geocoding result for "India"; articles landing here are rejected |

## Acronyms
| Acronym | Meaning |
|---------|---------|
| PA | Protected Area |
| NER | Named Entity Recognition |
| RSS | Really Simple Syndication (news feeds) |
| ToS | Terms of Service (Nominatim: 1s delay required) |
| GN | Google News (proxy approach for blocked sources) |
| TR | Tiger Reserve |
| NP | National Park |
| WS | Wildlife Sanctuary |
| WB | West Bengal |
| MH | Maharashtra |
| TN | Tamil Nadu |
| KA | Karnataka |
| AP | Andhra Pradesh |
| TG | Telangana |
| GJ | Gujarat |
| OD | Odisha |
| HP | Himachal Pradesh |

## False-Positive Patterns to Watch
| Pattern | Example | Fix |
|---------|---------|-----|
| Political meetings at national parks | "NC legislators to Dachigam for offsite huddle" | 'legislators', 'offsite' in EXCLUDE_KEYWORDS |
| Google News search-result pages | Title starts with "You searched for" | Filtered in pipeline with startswith check |
| Location extracted from suffix | "- Deccan Herald" → place="Deccan" | Suffix stripping in pipeline for forced_source entries |
| National park as celebrity venue | Generic event hosted at a PA | Covered by 'party', 'election' etc. in EXCLUDE_KEYWORDS |
