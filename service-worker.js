// very small SW to cache the arcade and assets
const CACHE = 'cricket-v1';
const ASSETS = [
  '/', '/arcade',
  '/static/game/index.html',
  // icons
  '/static/images/icons/icon-192.png',
  '/static/images/icons/icon-512.png',
  // NOTE: Phaser CDN will be fetched network-first if not cached
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Try cache first for our own routes; fallback to network
  if (url.origin === location.origin) {
    e.respondWith(
      caches.match(e.request).then(res => res || fetch(e.request))
    );
  }
});
