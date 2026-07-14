/**
 * Service Worker pour le cache local et le hot-reload instantané (< 300 ms) de la Sandbox.
 */
const CACHE_NAME = 'antigravity-sandbox-v1';
const ASSETS_TO_CACHE = [
  '/sandbox.html',
  // Ajouter les dépendances/CSS partagés si nécessaire
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Optionnel : Intercepter les requêtes de chargement de la sandbox pour servir depuis le cache
  if (event.request.url.includes('/sandbox.html')) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request);
      })
    );
  }
});
