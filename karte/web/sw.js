// Feldcheck Wangerooge – offline cache. build_site.py fills in CORE (new name for every app/data version) and KEEP.
// App shell + data ('fc-core-…'): network first, but give up after 3 s (weak signal in the dunes) and use the stored copy.
// Map tiles ('fc-tiles') and PDF data ('fc-pdf': sheet SVGs, libraries): addressed by content ('…?v=<hash>'), so a stored
// copy is never stale. These two caches survive app updates; on activation only copies that are no longer in KEEP are dropped.
const CORE = 'fc-core', TILES = 'fc-tiles', PDF = 'fc-pdf';
const KEEP = [];
const CORE_FILES = ['./', 'index.html', 'data.json', 'briefkasten.json', 'leaflet.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png', 'favicon-32.png'];
// install fails (and the old version stays) if one core file cannot be loaded – never a half-filled cache
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CORE).then((c) => c.addAll(CORE_FILES.map((u) => new Request(u, {cache: 'reload'})))).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => {
  const keep = new Set(KEEP.map((p) => new URL(p, self.registration.scope).href));
  e.waitUntil((async () => {
    // only this app's caches (prefix fc-); other projects on the same github.io domain are left alone
    for (const k of await caches.keys()) if (k.startsWith('fc-') && ![CORE, TILES, PDF].includes(k)) await caches.delete(k);
    for (const name of [TILES, PDF]) { const c = await caches.open(name); for (const r of await c.keys()) if (!keep.has(r.url)) await c.delete(r); }
    await self.clients.claim();
  })());
});
const timeout = (ms) => new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms));
const offline = () => new Response('', {status: 504, statusText: 'offline'});
async function stored(cacheName, req){
  const c = await caches.open(cacheName), hit = await c.match(req);
  if (hit) return hit;
  try {
    const r = await fetch(req);
    if (r.ok && new URL(req.url).searchParams.has('v')) await c.put(req, r.clone());
    return r;
  } catch (e) {   // no network: an older copy of the same file is better than nothing
    return (await c.match(req, {ignoreSearch: true})) || offline();
  }
}
self.addEventListener('fetch', (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  if (/\/t\d+_\d+_\d+\.png$/.test(u.pathname)) { e.respondWith(stored(TILES, e.request)); return; }
  if (/\/(karten|lib)\//.test(u.pathname)) { e.respondWith(stored(PDF, e.request)); return; }
  const net = fetch(e.request).then((r) => { if (r.ok) { const cp = r.clone(); caches.open(CORE).then((c) => c.put(e.request, cp)); } return r; });
  e.respondWith(Promise.race([net, timeout(3000)]).catch(() => caches.match(e.request, {ignoreSearch: true})
    .then((hit) => hit || net.catch(() => null).then((r) => r || (e.request.mode === 'navigate' ? caches.match('index.html') : offline())))));
});
