const CACHE_NAME = 'homedashboard-v1';
const ASSETS = [
  '/',
  '/dashboard',
  '/static/dashboard.css',
  '/static/manifest.json'
];

/* ============================
   INSTALL
============================ */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
      .catch(() => undefined)
  );
  self.skipWaiting();
});

/* ============================
   ACTIVATE
============================ */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

/* ============================
   FETCH
============================ */
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      return fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => cached || Response.error());
    })
  );
});

/* ============================
   PUSH NOTIFICATIONS
============================ */
self.addEventListener("push", event => {
  let data = {};
  try { data = event.data.json(); } catch (e) {}

  const title = data.title || "HomeDashboard";
  const body = data.body || "Neue Nachricht";

  event.waitUntil(
    self.registration.showNotification(title, {
      body: body,
      icon: "/static/icons/trash.svg",   // SVG statt PNG
      badge: "/static/icons/badge.svg",  // SVG statt PNG
      vibrate: [100, 50, 100],
      actions: [
        {
          action: "open-dashboard",
          title: "Dashboard öffnen",
          icon: "/static/icons/home.svg" // SVG statt PNG
        }
      ]
    })
  );
});

/* ============================
   CLICK ACTION
============================ */
self.addEventListener("notificationclick", event => {
  event.notification.close();

  event.waitUntil(
    clients.openWindow("/dashboard")
  );
});
