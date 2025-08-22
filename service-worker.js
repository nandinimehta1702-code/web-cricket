// service-worker.js
const CACHE = "cricket-arcade-v1";

// add anything your page needs for first paint / offline play
const ASSETS = [
  "/arcade",
  "/static/game/index.html",
  "/static/game/manifest.json",
  "https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js",
  "/static/game/assets/batter_boy.png",
  "/static/game/assets/batter_girl.png",
  "/static/game/assets/bowler.png",
  "/static/game/assets/bat.png",
  "/static/game/assets/ball.png",
  "/static/game/assets/icon-192.png",
  "/static/game/assets/icon-512.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((resp) => {
        // best-effort runtime cache
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return resp;
      });
    })
  );
});


const CACHE = 'cricket-arcade-v4'; // bump this to force refresh
const ASSETS = [
  '/arcade',
  '/static/game/index.html',
  '/static/game/manifest.json',
  '/static/game/assets/bat.png',
  '/static/game/assets/ball.png',
  '/static/game/assets/batter_boy.png',
  '/static/game/assets/batter_girl.png',
  '/static/game/assets/bowler.png',
  '/static/game/assets/icon-192.png',
  '/static/game/assets/icon-512.png',
  'https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js'
];
