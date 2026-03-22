const CACHE_NAME = "einkaufsliste-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/static/core/css/home.css",
  "/static/core/js/home.js",
  "/static/ingredients/css/ingredient_list.css",
  "/static/ingredients/js/ingredient_list.js",
  "/static/inventory/css/inventory_list.css",
  "/static/inventory/js/inventory_list.js",
  "/static/recipes/css/recipe_detail.css",
  "/static/recipes/js/recipe_detail.js",
  "/static/recipes/css/recipe_list.css",
  "/static/recipes/js/recipe_list.js",
  "/static/shopping/css/shopping_list.css",
  "/static/shopping/js/shopping_list.js",
  "/static/global/icons/icon-192.png",
  "/static/global/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
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

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return (
        cachedResponse ||
        fetch(event.request).catch(() => caches.match("/"))
      );
    })
  );
});