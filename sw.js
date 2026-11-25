/* Gravaen : ouverture instantanée et lecture hors ligne.
   Page et chiffres : réseau d'abord (toujours à jour), copie de secours sans réseau.
   Polices et images : copie locale, rafraîchie en arrière-plan. */
const V = 'gravaen-v1';
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(V).then(c => c.addAll(['/', '/manifest.webmanifest']).catch(() => {}))); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(n => n !== V).map(n => caches.delete(n)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin || u.pathname === '/sw.js') return;
  const fresh = r.mode === 'navigate' || u.pathname.startsWith('/data/') || u.pathname.endsWith('.json');
  if (fresh) {
    e.respondWith(fetch(r).then(res => { if (res.ok) { const c = res.clone(); caches.open(V).then(x => x.put(r.mode === 'navigate' ? '/' : r, c)); } return res; })
      .catch(() => caches.match(r.mode === 'navigate' ? '/' : r)));
  } else {
    e.respondWith(caches.match(r).then(hit => { const net = fetch(r).then(res => { if (res.ok) { const c = res.clone(); caches.open(V).then(x => x.put(r, c)); } return res; }).catch(() => hit); return hit || net; }));
  }
});
