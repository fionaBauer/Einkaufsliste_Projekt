/**
 * Prepio Service Worker (ausgeliefert unter /sw.js, Scope "/")
 *
 * - Seiten: immer zuerst Netzwerk (nie veraltete Daten). Nur wenn das Netz weg oder
 *   extrem langsam ist (z.B. im Supermarkt), wird die zuletzt gesehene Version gezeigt.
 * - Statische Dateien: Cache, im Hintergrund aktualisiert.
 * - Prefetch: Die App meldet beim Antippen eines Links die Ziel-URL; die Seite wird
 *   vorgeladen und bei der Navigation wenige Sekunden lang direkt ausgeliefert.
 */
const VERSION = "prepio-v2";
const PAGE_CACHE = `${VERSION}-pages`;
const STATIC_CACHE = `${VERSION}-static`;
const NETWORK_TIMEOUT_MS = 6000;
const PREFETCH_TTL_MS = 8000;

const warm = new Map(); // url -> { time, promise }

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("message", (event) => {
    const data = event.data || {};
    if (data.type !== "prefetch" || !data.url) return;

    const existing = warm.get(data.url);
    if (existing && Date.now() - existing.time < PREFETCH_TTL_MS) return;

    const promise = fetch(data.url, { credentials: "include" })
        .then((res) => (res.ok && !res.redirected ? res : null))
        .catch(() => null);
    warm.set(data.url, { time: Date.now(), promise });
    event.waitUntil(promise);
});

function isCacheablePage(url) {
    return !url.pathname.startsWith("/accounts/") && !url.pathname.startsWith("/admin/");
}

function networkWithTimeout(request) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("timeout")), NETWORK_TIMEOUT_MS);
        fetch(request).then(
            (res) => { clearTimeout(timer); resolve(res); },
            (err) => { clearTimeout(timer); reject(err); }
        );
    });
}

async function handleNavigation(event) {
    const request = event.request;
    const url = new URL(request.url);

    const prefetched = warm.get(request.url);
    warm.delete(request.url);
    if (prefetched && Date.now() - prefetched.time < PREFETCH_TTL_MS) {
        const res = await prefetched.promise;
        if (res) return res;
    }

    try {
        const res = await networkWithTimeout(request);
        if (res.ok && !res.redirected && isCacheablePage(url)) {
            const copy = res.clone();
            event.waitUntil(caches.open(PAGE_CACHE).then((c) => c.put(request.url, copy)));
        }
        return res;
    } catch (err) {
        const cached = await caches.match(request.url, { cacheName: PAGE_CACHE });
        if (cached) return cached;
        // Langsam, aber nicht offline und nichts im Cache → doch aufs Netz warten
        return fetch(request);
    }
}

async function handleStatic(event) {
    const cache = await caches.open(STATIC_CACHE);
    const cached = await cache.match(event.request);
    const network = fetch(event.request)
        .then((res) => {
            if (res.ok) cache.put(event.request, res.clone());
            return res;
        })
        .catch(() => cached);
    if (cached) {
        event.waitUntil(network);
        return cached;
    }
    return network;
}

self.addEventListener("fetch", (event) => {
    const request = event.request;

    if (request.method !== "GET") {
        // Etwas wurde geändert → vorgeladene Seiten sind evtl. veraltet
        warm.clear();
        return;
    }

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;

    if (request.mode === "navigate") {
        event.respondWith(handleNavigation(event));
        return;
    }

    if (url.pathname.startsWith("/static/")) {
        event.respondWith(handleStatic(event));
    }
    // Alles andere (API, stille Updates) geht unverändert ans Netz.
});
