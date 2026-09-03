/* Service worker - Academia */
self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open('ikigai-static').then((c) => c.add('/').catch(() => {})));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api/')) return;
  if (url.pathname.startsWith('/static/uploads/')) return;
  e.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      if (res.ok && url.pathname.startsWith('/static/')) {
        caches.open('ikigai-static').then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() =>
      caches.match(req).then((hit) => hit || caches.match('/')))
  );
});

self.addEventListener('push', (e) => {
  let data = {};
  try { data = e.data.json(); } catch (err) {}
  const title = data.title || 'IKIGAI VIEDMA';
  const body = data.body || '';
  const options = {
    body: body,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    vibrate: [200, 100, 200],
    renotify: true,
    data: { url: data.url || '/app' },
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/app';
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const client of list) {
      if ('focus' in client) return client.focus();
    }
    return clients.openWindow(url);
  }));
});
