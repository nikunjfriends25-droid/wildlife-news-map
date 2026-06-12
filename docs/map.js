/* ══════════════════════════════════════════════════════════════════════════════
   Wildlife News Map — India
   ══════════════════════════════════════════════════════════════════════════════ */

// ── Constants ─────────────────────────────────────────────────────────────────
const INDIA_BOUNDS = [[6, 68], [37, 98]];

const CATEGORY_COLORS = {
  poaching:     '#ef4444',
  discovery:    '#f59e0b',
  conflict:     '#f97316',
  research:     '#06b6d4',
  conservation: '#818cf8',
};

const CATEGORY_LABELS = {
  poaching:     'Poaching & Crime',
  discovery:    'Species Discovery',
  conflict:     'Human-Wildlife Conflict',
  research:     'Research & Science',
  conservation: 'Conservation & Policy',
};

// Order matters — first match wins. conservation is the fallback (not listed here).
const CATEGORY_KEYWORDS = {
  poaching:  ['poach', 'snare', 'traffick', 'smuggl', 'ivory', 'wildlife crime', 'confiscat', 'illegal hunt', 'crime against'],
  discovery: ['new species', 'new-to-science', 'records first', 'first record', 'scientists discover', 'new fanged', 'new toad', 'new frog', 'new fish species', 'new gecko', 'new snake eel', 'emerges from ancient', 'solves evolutionary'],
  conflict:  ['elephant attack', 'leopard attack', 'tiger attack', 'bear attack', 'mauled', 'conflict hotspot', 'human-wildlife', 'man-animal', 'human-animal', 'drone squad'],
  research:  ['finds study', 'reveals survey', 'reveals study', 'population rises', 'population survey', 'census', 'behaviour', 'behavior', 'foraging', 'camera trap', 'odonate', 'migratory pastoralist'],
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
const activeCats = new Set(['poaching', 'discovery', 'conflict', 'research', 'conservation']);
const activeSrcs = new Set();

// ── Helpers ───────────────────────────────────────────────────────────────────
function categorize(headline) {
  const lower = (headline || '').toLowerCase();
  for (const [cat, words] of Object.entries(CATEGORY_KEYWORDS)) {
    if (words.some(w => lower.includes(w))) return cat;
  }
  return 'conservation'; // fallback — Conservation & Policy catches everything else
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
    discovery:    { bg: 'rgba(245,158,11,0.15)',  border: 'rgba(245,158,11,0.35)',  text: '#fcd34d', dot: '#f59e0b' },
    conflict:     { bg: 'rgba(249,115,22,0.15)',  border: 'rgba(249,115,22,0.35)',  text: '#fdba74', dot: '#f97316' },
    research:     { bg: 'rgba(6,182,212,0.15)',   border: 'rgba(6,182,212,0.35)',   text: '#67e8f9', dot: '#06b6d4' },
    conservation: { bg: 'rgba(129,140,248,0.15)', border: 'rgba(129,140,248,0.35)', text: '#a5b4fc', dot: '#818cf8' },
  };
  return colors[cat] || colors.conservation;
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
    if (!activeSrcs.has(a.source)) return false;
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

  ['poaching','discovery','conflict','research','conservation'].forEach(c => activeCats.add(c));
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

// ── Visit counter ─────────────────────────────────────────────────────────────
(function () {
  const wrap = document.getElementById('visit-count');
  const num  = document.getElementById('visit-num');
  if (!wrap || !num) return;

  fetch('https://api.counterapi.dev/v1/wildlens-india/pageviews/up', { cache: 'no-store' })
    .then(r => r.ok ? r.json() : Promise.reject('non-ok'))
    .then(data => {
      if (data && typeof data.count === 'number') {
        num.textContent = data.count.toLocaleString('en-IN');
        wrap.style.display = 'flex';
      }
    })
    .catch(() => {}); // non-critical — silently hide if unreachable
}());

// ── Tour ──────────────────────────────────────────────────────────────────────
function startTour() {
  // Driver.js v1 IIFE: this.driver={}, this.driver.js = module, module.driver = fn
  const mod = window.driver && window.driver.js;
  if (!mod || !mod.driver) {
    console.warn('WildLens: Driver.js not loaded — tour unavailable');
    return;
  }

  mod.driver({
    showProgress: true,
    progressText: '{{current}} / {{total}}',
    nextBtnText:  'Next →',
    prevBtnText:  '← Back',
    doneBtnText:  'Done',
    steps: [
      {
        element: '#panel-brand',
        popover: {
          title:       'Welcome to WildLens',
          description: 'India\'s wildlife and environment news, pinned live on an interactive map. Updated every 6 hours from multiple publications.',
          side: 'right', align: 'start',
        },
      },
      {
        element: '#cat-body',
        popover: {
          title:       'Filter by category',
          description: 'Five colour-coded types — Poaching & Crime, Species Discovery, Human-Wildlife Conflict, Research & Science, and Conservation & Policy. Click any chip to show or hide that type on the map.',
          side: 'right', align: 'start',
        },
      },
      {
        element: '#src-body',
        popover: {
          title:       'Filter by source',
          description: 'Choose which publications to include — Mongabay India, The Hindu, NDTV, Research Matters, Nature India, and more.',
          side: 'right', align: 'start',
        },
      },
      {
        element: '#search',
        popover: {
          title:       'Search',
          description: 'Search across headlines, place names, and source names in real time.',
          side: 'right', align: 'start',
        },
      },
      {
        element: '#map',
        popover: {
          title:       'The map',
          description: 'Each pin is a news article. Click a pin to see the headline, location, date, and a link to the full story. Clusters expand when you zoom in.',
          side: 'left', align: 'center',
        },
      },
    ],
  }).drive();
}

// Auto-start on first visit (after map has a moment to render)
if (!localStorage.getItem('wildlens-tour-done')) {
  localStorage.setItem('wildlens-tour-done', '1');
  setTimeout(startTour, 1400);
}

document.getElementById('tour-btn')?.addEventListener('click', startTour);

// ── Chat widget ───────────────────────────────────────────────────────────────
(function chatWidget() {
  const fab      = document.getElementById('chat-fab');
  const widget   = document.getElementById('chat-widget');
  const closeBtn = document.getElementById('chat-close');
  const msgs     = document.getElementById('chat-messages');
  const inp      = document.getElementById('chat-input');
  const sendBtn  = document.getElementById('chat-send');

  if (!fab || !widget) return;

  let isOpen = false;

  function openChat() {
    isOpen = true;
    widget.classList.add('open');
    inp.focus();
    if (!msgs.childElementCount) {
      addBot('Hi! Ask me about the articles on the map — try:<ul>' +
        '<li><em>How many tiger articles?</em></li>' +
        '<li><em>Show me poaching news</em></li>' +
        '<li><em>Latest elephant article</em></li>' +
        '<li><em>Which place has most articles?</em></li>' +
        '</ul>');
    }
  }
  function closeChat() { isOpen = false; widget.classList.remove('open'); }

  fab.addEventListener('click', () => isOpen ? closeChat() : openChat());
  closeBtn.addEventListener('click', closeChat);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) closeChat(); });

  function addMsg(role, html) {
    const div = document.createElement('div');
    div.className = `chat-msg chat-msg-${role}`;
    div.innerHTML = html;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }
  function addBot(html) { addMsg('bot', html); }

  const STOP_WORDS = new Set([
    'list', 'show', 'find', 'display', 'see', 'get', 'give', 'tell', 'please',
    'articles', 'article', 'news', 'related', 'about', 'to', 'for', 'from',
    'the', 'a', 'an', 'any', 'some', 'all', 'me', 'in', 'of', 'on', 'at',
    'with', 'how', 'many', 'what', 'which', 'where', 'latest', 'recent',
    'newest', 'last', 'count', 'number',
  ]);

  const SPECIES = [
    'snow leopard', 'sloth bear', 'tiger', 'elephant', 'leopard', 'lion',
    'rhino', 'rhinoceros', 'bear', 'wolf', 'gharial', 'crocodile', 'vulture',
    'bustard', 'dolphin', 'python', 'pangolin', 'jackal', 'deer', 'bird',
  ];

  const CAT_ALIAS = {
    poaching: 'poaching', crime: 'poaching', smuggl: 'poaching', traffick: 'poaching', snare: 'poaching',
    discovery: 'discovery', sighting: 'discovery',
    conflict: 'conflict', attack: 'conflict',
    research: 'research', census: 'research', study: 'research', survey: 'research',
    conservation: 'conservation', policy: 'conservation',
  };

  function artMatches(a, kw) {
    return (a.headline    || '').toLowerCase().includes(kw) ||
           (a.place_name  || '').toLowerCase().includes(kw);
  }

  function aLink(a) {
    return `<a href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(a.headline)}</a>`;
  }

  function respond(raw) {
    const q = raw.toLowerCase().trim();
    if (!q) return;
    addMsg('user', escapeHtml(raw));

    const arts = allArticles;
    if (!arts.length) { addBot('Articles are still loading — try again in a moment.'); return; }

    const isCount  = /\bhow many\b|\bcount\b|\bnumber of\b|\btotal\b/.test(q);
    const isLatest = /\blatest\b|\bmost recent\b|\bnewest\b|\blast\b/.test(q);
    const isShow   = /\bshow\b|\bfind\b|\blist\b|\bdisplay\b|\bsee\b/.test(q);
    const isTop    = /\bmost\b|\btop\b|\bwhich (place|state|location|area)\b|\bwhere (are|is) most\b/.test(q);
    const isHelp   = /\bhelp\b|\bwhat can\b|\bwhat do you\b/.test(q);
    const isStats  = /\bstats\b|\bsummary\b|\boverview\b/.test(q);

    if (isHelp) {
      addBot('I can answer:<ul>' +
        '<li><em>How many tiger articles?</em></li>' +
        '<li><em>Show me poaching news</em></li>' +
        '<li><em>Latest elephant article</em></li>' +
        '<li><em>Which place has most articles?</em></li>' +
        '<li><em>Articles from Mongabay</em></li>' +
        '<li><em>Stats / overview</em></li>' +
        '</ul>');
      return;
    }

    // detect subject
    const species  = SPECIES.find(s => q.includes(s));
    const catAlias = Object.keys(CAT_ALIAS).find(k => q.includes(k));
    const cat      = catAlias ? CAT_ALIAS[catAlias] : null;
    const source   = [...new Set(arts.map(a => a.source))].find(s => q.includes(s.toLowerCase()));

    let filtered = arts;
    let desc = 'all articles';
    let mapKw = '';

    if (species) {
      filtered = arts.filter(a => artMatches(a, species));
      desc = `${species} articles`;
      mapKw = species;
    } else if (cat) {
      filtered = arts.filter(a => categorize(a.headline) === cat);
      desc = `${CATEGORY_LABELS[cat]} articles`;
      mapKw = catAlias;
    } else if (source) {
      filtered = arts.filter(a => a.source === source);
      desc = `articles from ${source}`;
    } else {
      // free-text fallback: strip intent/stop words, search remaining terms
      const terms = q.split(/\s+/).filter(w => w.length > 2 && !STOP_WORDS.has(w));
      if (terms.length) {
        const phrase = terms.join(' ');
        // prefer exact phrase match, fall back to all-words match
        const phraseMatches = arts.filter(a => artMatches(a, phrase));
        filtered = phraseMatches.length
          ? phraseMatches
          : arts.filter(a => terms.every(t => artMatches(a, t)));
        if (filtered.length && filtered.length < arts.length) {
          desc = `"${phrase}" articles`;
          mapKw = phrase;
        } else {
          filtered = arts; // no meaningful match — keep all
        }
      }
    }

    // stats or bare total count
    if (isStats || (isCount && filtered === arts)) {
      const byCat = {};
      arts.forEach(a => { const c = categorize(a.headline); byCat[c] = (byCat[c] || 0) + 1; });
      const lines = Object.entries(byCat)
        .sort((a, b) => b[1] - a[1])
        .map(([c, n]) => `<li>${escapeHtml(CATEGORY_LABELS[c])}: ${n}</li>`).join('');
      addBot(`<strong>${arts.length} articles</strong> on the map, updated every 6 hours.<ul>${lines}</ul>`);
      return;
    }

    // top places
    if (isTop) {
      const counts = {};
      filtered.forEach(a => { counts[a.place_name] = (counts[a.place_name] || 0) + 1; });
      const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
      if (!top.length) { addBot(`No ${desc} found.`); return; }
      addBot(`Top locations for ${desc}:<ul>${top.map(([p, n]) => `<li>${escapeHtml(p)} — ${n}</li>`).join('')}</ul>`);
      return;
    }

    // latest
    if (isLatest) {
      const sorted = [...filtered].sort((a, b) => new Date(b.published) - new Date(a.published)).slice(0, 3);
      if (!sorted.length) { addBot(`No ${desc} found.`); return; }
      addBot(`Latest ${desc}:<ul>${sorted.map(a =>
        `<li>${aLink(a)} <span class="chat-meta">${escapeHtml(a.place_name)}, ${formatDate(a.published)}</span></li>`
      ).join('')}</ul>`);
      return;
    }

    // count
    if (isCount) {
      if (!filtered.length) { addBot(`No ${desc} found on the map right now.`); return; }
      addBot(`There are <strong>${filtered.length}</strong> ${desc} on the map.`);
      return;
    }

    // show / find — also updates the map search box
    if (isShow) {
      if (!filtered.length) { addBot(`No ${desc} found.`); return; }
      if (mapKw) {
        searchEl.value = mapKw;
        clearBtn.style.display = 'flex';
        applyFilters();
      }
      const preview = filtered.slice(0, 4).map(a =>
        `<li>${aLink(a)} <span class="chat-meta">${escapeHtml(a.place_name)}</span></li>`
      ).join('');
      const more = filtered.length > 4
        ? `<p style="margin-top:4px;color:var(--text-muted);font-size:10px">…and ${filtered.length - 4} more</p>`
        : '';
      addBot(`Found <strong>${filtered.length}</strong> ${desc}${mapKw ? ' — map updated' : ''}:<ul>${preview}</ul>${more}`);
      return;
    }

    // subject detected but no specific intent — suggest
    if (filtered !== arts && filtered.length > 0) {
      addBot(`Found <strong>${filtered.length}</strong> ${desc}. Try:<ul>` +
        `<li><em>Show me ${desc}</em></li>` +
        `<li><em>Latest ${species || catAlias || ''} article</em></li>` +
        `</ul>`);
      return;
    }

    // fallback
    addBot(`<strong>${arts.length}</strong> articles on the map. Try: <em>how many tiger articles?</em>, <em>show me poaching news</em>, or type <em>help</em>.`);
  }

  function send() {
    const v = inp.value.trim();
    if (!v) return;
    inp.value = '';
    respond(v);
  }

  sendBtn.addEventListener('click', send);
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
}());
