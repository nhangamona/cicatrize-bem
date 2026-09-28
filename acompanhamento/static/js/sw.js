// Cicatrize Bem - Service Worker para PWA
const CACHE_NAME = 'cicatrizebem-v1';
const STATIC_ASSETS = [
  '/login/',
  '/static/css/main.css',
  '/static/img/logo_cicatrizebem.png',
  '/static/img/logo_uepa.png',
  '/static/img/logo_cipe.png',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Ignora requisições POST ou para o admin
  if (event.request.method !== 'GET' || event.request.url.includes('/admin/')) {
    return;
  }

  // Network-first com fallback para cache
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            return caches.match('/login/');
          }
        });
      })
  );
});
