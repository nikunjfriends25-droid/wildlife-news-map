const CATEGORY_COLORS = {
  poaching: '#e74c3c',
  sighting: '#27ae60',
  conservation: '#2980b9',
  other: '#7f8c8d',
};

const CATEGORY_KEYWORDS = {
  poaching: ['poach', 'snare', 'trap', 'kill', 'hunt', 'traffick', 'smuggl', 'ivory', 'skin'],
  sighting: ['sight', 'spot', 'seen', 'found', 'camera trap', 'photograph', 'recorded'],
  conservation: ['conserv', 'protect', 'rescue', 'rehabilitat', 'restor', 'reserve', 'sanctuary', 'corridor'],
};

function categorize(headline) {
  const lower = headline.toLowerCase();
  for (const [cat, words] of Object.entries(CATEGORY_KEYWORDS)) {
    if (words.some(w => lower.includes(w))) return cat;
  }
  return 'other';
}

function markerRadius(published) {
  const days = (Date.now() - new Date(published).getTime()) / 86400000;
  return Math.max(5, 10 - days * 0.25);
}

const map = L.map('map', {
  center: [22, 83],
  zoom: 5,
  minZoom: 4,
  maxBounds: [[4, 64], [40, 100]],
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

const clusters = L.markerClusterGroup({
  maxClusterRadius: 40,
  iconCreateFunction(cluster) {
    const count = cluster.getChildCount();
    return L.divIcon({
      html: `<div class="cluster-icon">${count}</div>`,
      className: '',
      iconSize: [36, 36],
    });
  },
});

fetch('news.json')
  .then(r => r.json())
  .then(articles => {
    document.getElementById('counter').textContent = `${articles.length} articles`;

    articles.forEach(a => {
      const cat = categorize(a.headline);
      const color = CATEGORY_COLORS[cat];
      const radius = markerRadius(a.published);

      const marker = L.circleMarker([a.lat, a.lon], {
        radius,
        color,
        fillColor: color,
        fillOpacity: 0.8,
        weight: 1,
      });

      marker.bindPopup(`
        <div class="popup">
          <div class="popup-source">${a.source} &middot; ${a.published}</div>
          <div class="popup-headline">${a.headline}</div>
          <div class="popup-place">📍 ${a.place_name}</div>
          <a class="popup-link" href="${a.url}" target="_blank" rel="noopener">Read article →</a>
        </div>
      `, { maxWidth: 280 });

      clusters.addLayer(marker);
    });

    map.addLayer(clusters);
  })
  .catch(err => {
    console.error('Failed to load news.json:', err);
    document.getElementById('counter').textContent = 'No data loaded';
  });
