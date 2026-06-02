// ── Constants ─────────────────────────────────────────────────────────────────
const INDIA_BOUNDS = [[6, 68], [37, 98]];
const INDIA_CENTER = [22, 83];
const INDIA_ZOOM   = 5;

const CATEGORY_COLORS = {
  poaching:     '#e74c3c',
  sighting:     '#27ae60',
  conservation: '#2980b9',
  other:        '#7f8c8d',
};

const CATEGORY_KEYWORDS = {
  poaching:     ['poach', 'snare', 'trap', 'traffick', 'smuggl', 'ivory', 'kill', 'hunt'],
  sighting:     ['sight', 'spot', 'seen', 'found', 'camera trap', 'photograph', 'recorded', 'survey'],
  conservation: ['conserv', 'protect', 'rescue', 'rehabilitat', 'restor', 'reserve', 'sanctuary', 'corridor', 'national park'],
};

// ── Map setup ─────────────────────────────────────────────────────────────────
const map = L.map('map', {
  center: INDIA_CENTER,
  zoom: INDIA_ZOOM,
  minZoom: 4,
  maxZoom: 14,
  maxBounds: INDIA_BOUNDS,
  maxBoundsViscosity: 1.0,   // hard lock — cannot pan outside India
});

// Restrict initial view tightly to India
map.fitBounds(INDIA_BOUNDS);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

// ── India boundary mask ───────────────────────────────────────────────────────
// Uses L.polygon (Leaflet [lat,lng]) to avoid GeoJSON winding-order issues.
fetch('india.geojson')
  .then(r => r.json())
  .then(data => {
    const geom = data.features[0].geometry;

    // World outer ring in Leaflet [lat, lng] — large enough to cover everything
    const world = [[90, -180], [90, 180], [-90, 180], [-90, -180]];

    // Convert India GeoJSON rings [lng,lat] → Leaflet [lat,lng]
    const toLatLng = ring => ring.map(([lng, lat]) => [lat, lng]);
    let indiaRings = [];
    if (geom.type === 'Polygon') {
      indiaRings = geom.coordinates.map(toLatLng);
    } else if (geom.type === 'MultiPolygon') {
      geom.coordinates.forEach(poly => poly.forEach(ring => indiaRings.push(toLatLng(ring))));
    }

    // Dark overlay: world with India cut out as holes
    L.polygon([world, ...indiaRings], {
      color: 'none',
      fillColor: '#1a1a2e',
      fillOpacity: 1,
      interactive: false,
    }).addTo(map);

    // India border outline
    L.geoJSON(data, {
      style: {
        color: '#4a7a9b',
        weight: 1.5,
        fillOpacity: 0,
        interactive: false,
      },
    }).addTo(map);
  })
  .catch(err => console.warn('Could not load India boundary:', err));

// ── Helpers ───────────────────────────────────────────────────────────────────
function categorize(headline) {
  const lower = (headline || '').toLowerCase();
  for (const [cat, words] of Object.entries(CATEGORY_KEYWORDS)) {
    if (words.some(w => lower.includes(w))) return cat;
  }
  return 'other';
}

function markerRadius(published) {
  const days = (Date.now() - new Date(published).getTime()) / 86400000;
  return Math.max(5, 10 - days * 0.2);
}

// ── Cluster layer ─────────────────────────────────────────────────────────────
const clusters = L.markerClusterGroup({
  maxClusterRadius: 40,
  iconCreateFunction(cluster) {
    return L.divIcon({
      html: `<div class="cluster-icon">${cluster.getChildCount()}</div>`,
      className: '',
      iconSize: [36, 36],
    });
  },
});
map.addLayer(clusters);

// ── State ─────────────────────────────────────────────────────────────────────
let allArticles = [];
let allMarkers  = [];
// JS-managed filter state — never read from DOM checkbox.checked
const activeCats = new Set(['poaching','sighting','conservation','other']);
const activeSrcs = new Set();

// ── Render markers from filtered list ────────────────────────────────────────
function renderMarkers(filtered) {
  clusters.clearLayers();
  filtered.forEach(({ article: a, marker }) => {
    clusters.addLayer(marker);
  });
  document.getElementById('stats').textContent =
    `Showing ${filtered.length} of ${allArticles.length} articles`;
}

// ── Apply all filters ─────────────────────────────────────────────────────────
function applyFilters() {
  const query    = document.getElementById('search').value.toLowerCase().trim();
  const dateFrom = document.getElementById('date-from').value;
  const dateTo   = document.getElementById('date-to').value;

  const filtered = allMarkers.filter(({ article: a }) => {
    if (!activeCats.has(categorize(a.headline))) return false;
    if (!activeSrcs.has(a.source)) return false;
    if (dateFrom && a.published < dateFrom) return false;
    if (dateTo   && a.published > dateTo)   return false;
    if (query && !(
      a.headline.toLowerCase().includes(query) ||
      a.place_name.toLowerCase().includes(query) ||
      a.source.toLowerCase().includes(query)
    )) return false;
    return true;
  });

  renderMarkers(filtered);
}

// ── Build source checkboxes ───────────────────────────────────────────────────
function buildSourceFilters(articles) {
  const sources = [...new Set(articles.map(a => a.source))].sort();
  sources.forEach(s => activeSrcs.add(s));  // all on by default in JS state
  const container = document.getElementById('source-filters');
  container.innerHTML = '';
  sources.forEach(src => {
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.dataset.src = src;
    cb.checked = true;
    cb.autocomplete = 'off';
    cb.addEventListener('change', () => {
      cb.checked ? activeSrcs.add(src) : activeSrcs.delete(src);
      applyFilters();
    });
    label.appendChild(cb);
    label.append(' ' + src);
    container.appendChild(label);
  });
}

// ── Set default date range ────────────────────────────────────────────────────
function setDefaultDates(articles) {
  const dates = articles.map(a => a.published).sort();
  document.getElementById('date-from').value = dates[0] || '';
  document.getElementById('date-to').value   = dates[dates.length - 1] || '';
}

// ── Reset ─────────────────────────────────────────────────────────────────────
document.getElementById('reset-btn').addEventListener('click', () => {
  document.getElementById('search').value = '';
  ['poaching','sighting','conservation','other'].forEach(c => activeCats.add(c));
  document.querySelectorAll('#cat-filters input').forEach(i => i.checked = true);
  allArticles.map(a => a.source).forEach(s => activeSrcs.add(s));
  document.querySelectorAll('#source-filters input').forEach(i => i.checked = true);
  setDefaultDates(allArticles);
  applyFilters();
});

// ── Panel collapse/expand ─────────────────────────────────────────────────────
const panel  = document.getElementById('panel');
const toggle = document.getElementById('panel-toggle');
toggle.addEventListener('click', () => {
  panel.classList.toggle('collapsed');
  toggle.textContent = panel.classList.contains('collapsed') ? '›' : '‹';
  setTimeout(() => map.invalidateSize(), 300);
});

// ── Wire up category filters (JS state driven) ────────────────────────────────
document.querySelectorAll('#cat-filters input').forEach(i => {
  i.checked = true;  // visual default
  i.autocomplete = 'off';
  i.addEventListener('change', () => {
    i.checked ? activeCats.add(i.dataset.cat) : activeCats.delete(i.dataset.cat);
    applyFilters();
  });
});
document.getElementById('search').addEventListener('input', applyFilters);
document.getElementById('date-from').addEventListener('change', applyFilters);
document.getElementById('date-to').addEventListener('change', applyFilters);

// ── Load data ────────────────────────────────────────────────────────────────
fetch('news.json')
  .then(r => r.json())
  .then(articles => {
    allArticles = articles;

    allMarkers = articles.map(a => {
      const cat    = categorize(a.headline);
      const color  = CATEGORY_COLORS[cat];
      const radius = markerRadius(a.published);

      const marker = L.circleMarker([a.lat, a.lon], {
        radius,
        color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: 1,
      });

      marker.bindPopup(`
        <div class="popup">
          <div class="popup-meta">${a.source} &middot; ${a.published}</div>
          <div class="popup-headline">${a.headline}</div>
          <div class="popup-place">📍 ${a.place_name}</div>
          <a class="popup-link" href="${a.url}" target="_blank" rel="noopener">Read article →</a>
        </div>
      `, { maxWidth: 280 });

      return { article: a, marker };
    });

    buildSourceFilters(articles);
    setDefaultDates(articles);
    applyFilters();
  })
  .catch(err => {
    console.error('Failed to load news.json:', err);
    document.getElementById('stats').textContent = 'Failed to load articles.';
  });
