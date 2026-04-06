const CACHE_NAME = "smarthome-v1";

// Jo files offline bhi kaam karein
const STATIC_ASSETS = [
  "/",
  "/static/style.css",
  "/static/script.js",
  "/static/login.js",
  "/static/image smart home3.jpg",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

// Install — static files cache karo
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate — purana cache saaf karo
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network first, cache fallback
self.addEventListener("fetch", event => {
  // API calls aur WebSocket ko bypass karo — sirf static assets cache karein
  const url = new URL(event.request.url);
  const isAPI = url.pathname.startsWith("/toggle") ||
                url.pathname.startsWith("/set") ||
                url.pathname.startsWith("/detect") ||
                url.pathname.startsWith("/get") ||
                url.pathname.startsWith("/check") ||
                url.pathname.startsWith("/login") ||
                url.pathname.startsWith("/logout") ||
                url.pathname.startsWith("/signup") ||
                url.pathname.startsWith("/socket.io");

  if (isAPI || event.request.method !== "GET") {
    event.respondWith(fetch(event.request));
    return;
  }

  // Static assets: network first, cache fallback
  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});