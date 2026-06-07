/* ══════════════════════════════════════════════════════════════════════════════
   Wildlife News Map — India
   ══════════════════════════════════════════════════════════════════════════════ */

// ── Constants ─────────────────────────────────────────────────────────────────
const INDIA_BOUNDS = [[6, 68], [37, 98]];

const CATEGORY_COLORS = {
  poaching:     '#ef4444',
  sighting:     '#22c55e',
  conservation: '#818cf8',
  other:        '#64748b',
};

const CATEGORY_LABELS = {
  poaching:     'Poaching',
  sighting:     'Sighting',
  conservation: 'Conservation',
  other:        'Other',
};

const CATEGORY_KEYWORDS = {
  poaching:     ['poach', 'snare', 'trap', 'traffick', 'smuggl', 'ivory', 'illegal hunt', 'kill', 'seized', 'arrested', 'wildlife crime', 'confiscat'],
  sighting:     ['sight', 'spot', 'seen', 'found', 'camera trap', 'photograph', 'recorded', 'survey', 'new species', 'discover', 'endemic', 'rare species'],
  conservation: ['conserv', 'protect', 'rescue', 'rehabilitat', 'restor', 'reserve', 'sanctuary', 'corridor', 'national park', 'habitat', 'conflict', 'forest fire', 'encroach', 'deforest', 'afforest', 'extinct', 'endanger', 'dies', 'death', 'infection', 'mining', 'degrad', 'biodiversity', 'mangrove', 'wetland'],
};

// ── Map init ──────────────────────────────────────────────────────────────────
const map = L.map('map', {
  center: [22, 82],
  zoom: 5,
  minZoom: 5,
  maxZoom: 15,
  maxBounds: [[2, 60], [40, 105]],   // slightly wider than India so fitBounds has room
  maxBoundsViscosity: 0.85,
  zoomControl: false,
});

// Zoom control — top right
L.control.zoom({ position: 'topright' }).addTo(map);

// Tile layer
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://carto.com/" target="_blank">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

// Fit India to fill the viewport — tight padding so India is prominent
map.fitBounds(INDIA_BOUNDS, { padding: [10, 10] });

// ── Cluster group ─────────────────────────────────────────────────────────────
const clusters = L.markerClusterGroup({
  maxClusterRadius: 50,
  spiderfyOnMaxZoom: true,
  showCoverageOnHover: false,
  iconCreateFunction(cluster) {
    const count = cluster.getChildCount();
    const large = count >= 10 ? ' large' : '';
    return L.divIcon({
      html: `<div class="cluster-icon${large}">${count}</div>`,
      className: '',
      iconSize: large ? [44, 44] : [38, 38],
    });
  },
});
map.addLayer(clusters);

// ── State ─────────────────────────────────────────────────────────────────────
let allArticles = [];
let allMarkers  = [];
const activeCats = new Set(['poaching', 'sighting', 'conservation', 'other']);
const activeSrcs = new Set();

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
  return Math.max(5, 10 - days * 0.12);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return dateStr; }
}

function popupBadgeStyle(cat) {
  const colors = {
    poaching:     { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.35)',   text: '#fca5a5', dot: '#ef4444' },
    sighting:     { bg: 'rgba(34,197,94,0.15)',    border: 'rgba(34,197,94,0.35)',   text: '#86efac', dot: '#22c55e' },
    conservation: { bg: 'rgba(129,140,248,0.15)',  border: 'rgba(129,140,248,0.35)', text: '#a5b4fc', dot: '#818cf8' },
    other:        { bg: 'rgba(100,116,139,0.15)',  border: 'rgba(100,116,139,0.35)', text: '#94a3b8', dot: '#64748b' },
  };
  return colors[cat] || colors.other;
}

function buildPopup(a) {
  const cat    = categorize(a.headline);
  const color  = CATEGORY_COLORS[cat];
  const badge  = popupBadgeStyle(cat);
  const label  = CATEGORY_LABELS[cat];

  return `
    <div class="popup">
      <div class="popup-header">
        <div class="popup-cat-badge" style="background:${badge.bg};border:1px solid ${badge.border};color:${badge.text}">
          <span class="popup-cat-dot" style="background:${badge.dot}"></span>
          ${label}
        </div>
        <div class="popup-headline">${escapeHtml(a.headline)}</div>
      </div>
      <div class="popup-meta">
        <div class="popup-meta-row">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          <span class="popup-meta-text">${escapeHtml(a.place_name)}</span>
        </div>
        <div class="popup-meta-row">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <span class="popup-meta-text">${escapeHtml(a.source)} · ${formatDate(a.published)}</span>
        </div>
      </div>
      <div class="popup-footer">
        <a class="popup-link" href="${a.url}" target="_blank" rel="noopener noreferrer">
          Read article
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>
        </a>
      </div>
    </div>`;
}

function escapeHtml(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Render markers ────────────────────────────────────────────────────────────
function renderMarkers(filtered) {
  clusters.clearLayers();
  filtered.forEach(({ marker }) => clusters.addLayer(marker));
  const total = allArticles.length;
  const shown = filtered.length;
  document.getElementById('stats').textContent =
    shown === total
      ? `${total} article${total !== 1 ? 's' : ''} on map`
      : `${shown} of ${total} articles`;

  // Empty state
  const empty = document.getElementById('empty-state');
  if (empty) empty.classList.toggle('visible', shown === 0);
}

// ── Apply filters ─────────────────────────────────────────────────────────────
function applyFilters() {
  const query    = (document.getElementById('search').value || '').toLowerCase().trim();
  const dateFrom = document.getElementById('date-from').value;
  const dateTo   = document.getElementById('date-to').value;

  const filtered = allMarkers.filter(({ article: a }) => {
    if (!activeCats.has(categorize(a.headline))) return false;
    if (activeSrcs.size && !activeSrcs.has(a.source)) return false;
    if (dateFrom && a.published < dateFrom) return false;
    if (dateTo   && a.published > dateTo)   return false;
    if (query && !(
      (a.headline || '').toLowerCase().includes(query) ||
      (a.place_name || '').toLowerCase().includes(query) ||
      (a.source || '').toLowerCase().includes(query)
    )) return false;
    return true;
  });

  renderMarkers(filtered);
}

// ── Build source filters ──────────────────────────────────────────────────────
function buildSourceFilters(articles) {
  const sources = [...new Set(articles.map(a => a.source))].sort();
  sources.forEach(s => activeSrcs.add(s));

  const container = document.getElementById('source-filters');
  container.innerHTML = '';

  sources.forEach(src => {
    const chip = document.createElement('div');
    chip.className = 'filter-chip source-chip active';
    chip.setAttribute('role', 'checkbox');
    chip.setAttribute('aria-checked', 'true');
    chip.setAttribute('tabindex', '0');
    chip.dataset.src = src;

    chip.innerHTML = `
      <span class="chip-label">${escapeHtml(src)}</span>
      <span class="chip-check">
        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
      </span>`;

    const toggle = () => {
      const active = activeSrcs.has(src);
      if (active) { activeSrcs.delete(src); chip.classList.remove('active'); chip.setAttribute('aria-checked','false'); }
      else        { activeSrcs.add(src);    chip.classList.add('active');    chip.setAttribute('aria-checked','true'); }
      applyFilters();
    };

    chip.addEventListener('click', toggle);
    chip.addEventListener('keydown', e => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(); } });
    container.appendChild(chip);
  });
}

// ── Date defaults ─────────────────────────────────────────────────────────────
function setDefaultDates(articles) {
  const dates = articles.map(a => a.published).filter(Boolean).sort();
  if (dates.length) {
    document.getElementById('date-from').value = dates[0];
    document.getElementById('date-to').value   = dates[dates.length - 1];
  }
}

// ── Category chip wiring ──────────────────────────────────────────────────────
document.querySelectorAll('#cat-filters .filter-chip').forEach(chip => {
  const cat = chip.dataset.cat;

  const toggle = () => {
    const active = activeCats.has(cat);
    if (active) { activeCats.delete(cat); chip.classList.remove('active'); chip.setAttribute('aria-checked','false'); }
    else        { activeCats.add(cat);    chip.classList.add('active');    chip.setAttribute('aria-checked','true'); }
    applyFilters();
  };

  chip.addEventListener('click', toggle);
  chip.addEventListener('keydown', e => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(); } });
});

// ── Section collapse wiring ───────────────────────────────────────────────────
document.querySelectorAll('.section-header').forEach(header => {
  const bodyId = header.dataset.target;
  const body   = document.getElementById(bodyId);
  if (!body) return;

  header.addEventListener('click', () => {
    const open = header.classList.toggle('open');
    header.setAttribute('aria-expanded', open);
    body.classList.toggle('collapsed', !open);
  });
});

// ── Search wiring ─────────────────────────────────────────────────────────────
const searchEl = document.getElementById('search');
const clearBtn = document.getElementById('search-clear');

searchEl.addEventListener('input', () => {
  clearBtn.style.display = searchEl.value ? 'flex' : 'none';
  applyFilters();
});

clearBtn.addEventListener('click', () => {
  searchEl.value = '';
  clearBtn.style.display = 'none';
  searchEl.focus();
  applyFilters();
});

document.getElementById('date-from').addEventListener('change', applyFilters);
document.getElementById('date-to').addEventListener('change', applyFilters);

// ── Reset ─────────────────────────────────────────────────────────────────────
document.getElementById('reset-btn').addEventListener('click', () => {
  searchEl.value = '';
  clearBtn.style.display = 'none';

  ['poaching','sighting','conservation','other'].forEach(c => activeCats.add(c));
  document.querySelectorAll('#cat-filters .filter-chip').forEach(chip => {
    chip.classList.add('active');
    chip.setAttribute('aria-checked', 'true');
  });

  allArticles.forEach(a => activeSrcs.add(a.source));
  document.querySelectorAll('#source-filters .filter-chip').forEach(chip => {
    chip.classList.add('active');
    chip.setAttribute('aria-checked', 'true');
  });

  setDefaultDates(allArticles);
  applyFilters();
});

// ── Panel collapse ────────────────────────────────────────────────────────────
const panel  = document.getElementById('panel');
const toggle = document.getElementById('panel-toggle');

toggle.addEventListener('click', () => {
  const collapsed = panel.classList.toggle('collapsed');
  toggle.setAttribute('aria-label', collapsed ? 'Expand panel' : 'Collapse panel');
  setTimeout(() => map.invalidateSize(), 230);
});

// ── Load data ─────────────────────────────────────────────────────────────────
fetch('news.json')
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
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
        weight: 1.5,
        opacity: 0.9,
      });

      marker.bindPopup(buildPopup(a), {
        maxWidth: 300,
        closeButton: true,
        className: '',
      });

      // Subtle pulse on hover
      marker.on('mouseover', function() {
        this.setStyle({ weight: 2.5, fillOpacity: 1 });
      });
      marker.on('mouseout', function() {
        this.setStyle({ weight: 1.5, fillOpacity: 0.85 });
      });

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
