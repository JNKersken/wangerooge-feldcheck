// Feldcheck Wangerooge – offline cache. Core files: network first (always newest data), tiles: cache first.
const CORE = 'fc-core-v1', TILES = 'fc-tiles';
const CORE_FILES = ['./', 'index.html', 'data.json', 'leaflet.js', 'tiles.json', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CORE).then((c) => c.addAll(CORE_FILES)).catch(() => {})); self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CORE && k !== TILES).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  if (/\/t\d+_\d+_\d+\.png$/.test(u.pathname)) {
    e.respondWith(caches.open(TILES).then((c) => c.match(e.request).then((hit) => hit || fetch(e.request).then((r) => { if (r.ok) c.put(e.request, r.clone()); return r; }))));
    return;
  }
  e.respondWith(fetch(e.request).then((r) => { if (r.ok) { const cp = r.clone(); caches.open(CORE).then((c) => c.put(e.request, cp)); } return r; })
    .catch(() => caches.match(e.request, {ignoreSearch: true}).then((hit) => hit || caches.match('index.html'))));
});
