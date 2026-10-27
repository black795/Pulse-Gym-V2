/* Service worker de Pulse Gym: la app abre aunque no haya señal (pantalla "sin conexión").
   Los datos (/api) NUNCA se guardan aquí: siempre vienen del servidor. */
const VERSION = 'pulse-v1';
const BASE = ['/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(BASE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api')) return;

  // Pantallas: primero la red; si no hay señal, la copia guardada de la app.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(r => {
        const copia = r.clone();
        caches.open(VERSION).then(c => c.put('/', copia));
        return r;
      }).catch(() => caches.match('/')),
    );
    return;
  }

  // Archivos de la app (js, css, imágenes): copia guardada al instante y se actualiza por detrás.
  e.respondWith(
    caches.match(req).then(guardado => {
      const red = fetch(req).then(r => {
        if (r.ok) { const copia = r.clone(); caches.open(VERSION).then(c => c.put(req, copia)); }
        return r;
      }).catch(() => guardado);
      return guardado || red;
    }),
  );
});
