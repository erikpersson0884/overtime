const CACHE_NAME = "overtime-offline-v1";
const offlineUrl = new URL("static/offline.html", self.registration.scope).href;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.add(offlineUrl)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key.startsWith("overtime-offline-") && key !== CACHE_NAME)
      .map((key) => caches.delete(key))
  )));
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match(offlineUrl)));
  }
});
